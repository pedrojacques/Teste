import datetime as dt

import pytest
from sqlalchemy import inspect, select, text

from editallab.core import processos as svc
from editallab.core.bd import Arquivo, Base, Pagina
from editallab.core.erros import ErroEditalLab
from editallab.core.esquemas import TipoArquivo
from editallab.core.ingestao import FonteUpload
from editallab.core.ingestao.armazenamento import caminho_original
from tests.conftest import montar_zip


def _ingerir(sessao, config, arquivos, nome="PE 12/2025 - MPLS"):
    processo = svc.criar_processo(sessao, nome)
    resultado = svc.adicionar_arquivos(sessao, processo, FonteUpload(arquivos, config), config)
    return processo, resultado


def test_migracao_cria_o_mesmo_schema_dos_modelos(sessao):
    inspetor = inspect(sessao.get_bind())
    for tabela in Base.metadata.sorted_tables:
        colunas = {c["name"] for c in inspetor.get_columns(tabela.name)}
        assert colunas == set(tabela.columns.keys())


def test_processo_nasce_sem_regime_presumido(sessao):
    processo = svc.criar_processo(sessao, "  Processo   de teste ")
    assert processo.nome == "Processo de teste"
    assert processo.regime is None and processo.regime_detectado is None
    with pytest.raises(ErroEditalLab):
        svc.criar_processo(sessao, "   ")


def test_ingestao_registra_hash_tipo_sugerido_e_original(sessao, config, arquivos_processo):
    processo, resultado = _ingerir(sessao, config, arquivos_processo)
    assert len(resultado.aceitos) == 3 and not resultado.rejeitados
    tipos = {a.nome_original: a.tipo_arquivo for a in processo.arquivos}
    assert tipos == {
        "Anexo_I_Lista_de_Pontos.xlsx": TipoArquivo.ANEXO,
        "Edital_PE_12-2025.pdf": TipoArquivo.EDITAL,
        "Errata_01_PE_12-2025.pdf": TipoArquivo.ERRATA,
    }
    for arquivo in processo.arquivos:
        assert not arquivo.tipo_confirmado
        original = caminho_original(arquivo.sha256, config)
        assert original.name == arquivo.sha256  # nome em disco é o hash
        assert original.parent == config.dir_originais


def test_ingestao_por_zip_equivale_a_upload_multiplo(sessao, config, arquivos_processo):
    _, por_zip = _ingerir(sessao, config, [("pasta.zip", montar_zip(dict(arquivos_processo)))])
    _, avulso = _ingerir(sessao, config, arquivos_processo, nome="outro")
    assert {a.sha256 for a in por_zip.aceitos} == {a.sha256 for a in avulso.aceitos}


def test_arquivo_invalido_e_rejeitado_sem_derrubar_os_demais(sessao, config, arquivos_processo):
    entrada = [*arquivos_processo, ("virus.pdf", b"MZ executavel"), ("nota.txt", b"oi")]
    _, resultado = _ingerir(sessao, config, entrada)
    assert len(resultado.aceitos) == 3
    assert {r.nome for r in resultado.rejeitados} == {"virus.pdf", "nota.txt"}
    assert all("Traceback" not in r.motivo for r in resultado.rejeitados)


def test_errata_chega_depois_e_so_ela_e_extraida(sessao, config, arquivos_processo):
    errata = next(a for a in arquivos_processo if a[0].startswith("Errata"))
    iniciais = [a for a in arquivos_processo if a is not errata]
    processo, _ = _ingerir(sessao, config, iniciais)
    extraidos, falhas = svc.extrair_pendentes(sessao, processo, config)
    assert len(extraidos) == 2 and not falhas

    # Reenvio do conjunto completo: os dois já existentes são duplicados.
    resultado = svc.adicionar_arquivos(
        sessao, processo, FonteUpload(arquivos_processo, config), config
    )
    assert len(resultado.aceitos) == 1 and len(resultado.duplicados) == 2
    extraidos, _ = svc.extrair_pendentes(sessao, processo, config)
    assert [a.nome_original for a in extraidos] == ["Errata_01_PE_12-2025.pdf"]
    assert "90 (noventa) dias" in svc.texto_marcado(extraidos[0]).replace("\n", " ")


def test_banco_nao_recebe_dado_pessoal_nao_mascarado(sessao, config, arquivos_processo):
    processo, _ = _ingerir(sessao, config, arquivos_processo)
    svc.extrair_pendentes(sessao, processo, config)
    sessao.commit()
    tudo = "\n".join(sessao.scalars(select(Pagina.texto)))
    for proibido in ("529.982.247-25", "exemplo.com.br", "3555-0142", "99555-0101"):
        assert proibido not in tudo
    assert "[CPF]" in tudo and "12.345.678/0001-95" in tudo


def test_reextracao_substitui_paginas(sessao, config, arquivos_processo):
    processo, _ = _ingerir(sessao, config, arquivos_processo)
    svc.extrair_pendentes(sessao, processo, config)
    edital = next(a for a in processo.arquivos if a.tipo_arquivo == TipoArquivo.EDITAL)
    svc.extrair_arquivo(sessao, edital, config)
    sessao.commit()
    total = sessao.scalar(
        text("SELECT COUNT(*) FROM paginas WHERE arquivo_id = :id"), {"id": edital.id}
    )
    assert total == 2


def test_precedencia_original_antes_de_erratas_por_data(sessao, config, arquivos_processo):
    processo, _ = _ingerir(sessao, config, arquivos_processo)
    por_tipo = {a.tipo_arquivo: a for a in processo.arquivos}
    svc.confirmar_arquivo(
        sessao, por_tipo[TipoArquivo.EDITAL], TipoArquivo.EDITAL, dt.date(2025, 2, 20)
    )
    svc.confirmar_arquivo(
        sessao, por_tipo[TipoArquivo.ERRATA], TipoArquivo.ERRATA, dt.date(2025, 3, 10)
    )
    # Um esclarecimento com data anterior à errata, mas enviado depois.
    svc.confirmar_arquivo(
        sessao, por_tipo[TipoArquivo.ANEXO], TipoArquivo.ESCLARECIMENTO, dt.date(2025, 3, 5)
    )
    ordem = [a.tipo_arquivo for a in svc.ordenar_por_precedencia(processo.arquivos)]
    assert ordem == [TipoArquivo.EDITAL, TipoArquivo.ESCLARECIMENTO, TipoArquivo.ERRATA]
    assert all(a.tipo_confirmado for a in processo.arquivos)


def test_excluir_processo_remove_arquivos_e_paginas(sessao, config, arquivos_processo):
    processo, _ = _ingerir(sessao, config, arquivos_processo)
    svc.extrair_pendentes(sessao, processo, config)
    sessao.delete(processo)
    sessao.commit()
    assert sessao.scalar(select(Arquivo.id)) is None
    assert sessao.scalar(select(Pagina.id)) is None
