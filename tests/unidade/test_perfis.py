import copy

import pytest
from pydantic import ValidationError

from editallab.core.erros import ErroPerfil
from editallab.core.esquemas import PapelSecao, RegimeJuridico
from editallab.core.esquemas.perfil import AVISO_PADRAO, PerfilDocumento
from editallab.core.geracao.perfis import carregar_perfis, sugerir_perfil


@pytest.fixture
def perfis(config):
    return carregar_perfis(config.dir_perfis)


def test_carrega_os_tres_perfis_iniciais(perfis):
    assert set(perfis) == {"lei_14133", "estatal_13303", "privado"}
    for perfil in perfis.values():
        assert perfil.aviso == AVISO_PADRAO
        assert [c.id for c in perfil.campos_cabecalho] == ["orgao", "numero_processo"]
        assert [s.ordem for s in perfil.secoes] == sorted(s.ordem for s in perfil.secoes)
        assert sum(s.inclui_tabela_nms for s in perfil.secoes) == 1


def test_perfil_lei_14133(perfis):
    perfil = perfis["lei_14133"]
    assert perfil.usa_etp and perfil.exige_neutralidade
    assert [s.id for s in perfil.secoes] == [
        "objeto",
        "fundamentacao",
        "solucao",
        "requisitos",
        "execucao",
        "gestao",
        "medicao_pagamento",
        "selecao_fornecedor",
        "estimativa_valor",
        "adequacao_orcamentaria",
    ]
    assert perfil.secao("fundamentacao").papel == PapelSecao.FUNDAMENTACAO
    assert perfil.secao("estimativa_valor").papel == PapelSecao.ESTIMATIVA_VALOR
    assert perfil.secao("adequacao_orcamentaria").papel == PapelSecao.PREENCHIMENTO_ORGAO


def test_perfil_estatal(perfis):
    perfil = perfis["estatal_13303"]
    assert perfil.exige_neutralidade and not perfil.usa_etp
    # usa_etp é configurável: ligar funciona porque há uma seção de fundamentação.
    ligado = PerfilDocumento.model_validate({**perfil.model_dump(), "usa_etp": True})
    assert ligado.usa_etp


def test_perfil_privado_nao_tem_secoes_de_direito_publico(perfis):
    perfil = perfis["privado"]
    assert not perfil.usa_etp and not perfil.exige_neutralidade
    assert perfil.referencia_normativa is None
    papeis = {s.papel for s in perfil.secoes}
    assert PapelSecao.FUNDAMENTACAO not in papeis
    assert PapelSecao.PREENCHIMENTO_ORGAO not in papeis
    ids = {s.id for s in perfil.secoes}
    assert not ids & {"adequacao_orcamentaria", "selecao_fornecedor", "fundamentacao"}


def test_todo_perfil_trata_preco_como_campo_de_preenchimento(perfis):
    for perfil in perfis.values():
        assert any(s.papel == PapelSecao.ESTIMATIVA_VALOR for s in perfil.secoes)


@pytest.mark.parametrize(
    ("regime", "esperado"),
    [
        (RegimeJuridico.LEI_14133, "lei_14133"),
        (RegimeJuridico.LEI_13303, "estatal_13303"),
        (RegimeJuridico.PRIVADO, "privado"),
    ],
)
def test_sugestao_de_perfil_pelo_regime_confirmado(perfis, regime, esperado):
    assert sugerir_perfil(regime, perfis).id == esperado


def test_sem_regime_confirmado_nao_ha_sugestao(perfis):
    assert sugerir_perfil(None, perfis) is None
    assert sugerir_perfil(RegimeJuridico.INDETERMINADO, perfis) is None


def _alterado(perfis, mutacao):
    dados = copy.deepcopy(perfis["lei_14133"].model_dump())
    mutacao(dados)
    return dados


@pytest.mark.parametrize(
    "mutacao",
    [
        lambda d: d["secoes"][1].update(id="objeto"),
        lambda d: d["secoes"][1].update(ordem=1),
        lambda d: d["secoes"][1].update(papel="geral"),  # usa_etp sem fundamentação
        lambda d: d["secoes"][0].update(inclui_tabela_nms=True),  # duas tabelas de NMS
        lambda d: d.update(secoes=[]),
        lambda d: d.update(campo_novo=1),
        lambda d: d["secoes"][0].update(papel="inexistente"),
    ],
)
def test_validacoes_do_perfil(perfis, mutacao):
    with pytest.raises(ValidationError):
        PerfilDocumento.model_validate(_alterado(perfis, mutacao))


def test_secoes_sao_ordenadas_no_carregamento(perfis):
    dados = _alterado(perfis, lambda d: d["secoes"].reverse())
    assert [s.ordem for s in PerfilDocumento.model_validate(dados).secoes] == list(range(1, 11))


def test_perfil_invalido_gera_erro_amigavel(tmp_path):
    (tmp_path / "ruim.yaml").write_text("id: x\nnome: y\n", encoding="utf-8")
    with pytest.raises(ErroPerfil) as info:
        carregar_perfis(tmp_path)
    assert "ruim.yaml" in info.value.mensagem_usuario
    assert "validation" not in info.value.mensagem_usuario.lower()
