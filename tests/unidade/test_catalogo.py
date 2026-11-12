import json
import shutil

import pytest
import yaml
from pydantic import ValidationError

from editallab.core.catalogo import carregar_catalogo
from editallab.core.erros import ErroCatalogo
from editallab.core.esquemas.catalogo import (
    CamadaInterna,
    ItemCatalogo,
    ItemCatalogoNeutro,
    contem_termo,
)


@pytest.fixture
def catalogo(config):
    return carregar_catalogo(config.dir_catalogo)


def _item(**interna):
    return {
        "id": "item-teste",
        "nome": "Roteador de acesso",
        "categoria": "equipamento",
        "neutra": {"descricao_funcional": "Roteador com no mínimo 4 portas."},
        "interna": interna,
    }


def test_carrega_os_itens_de_exemplo(catalogo):
    assert [i.id for i in catalogo.itens] == [
        "colocation-dc-jve",
        "link-mpls",
        "roteador-cpe",
        "switch-acesso",
    ]
    cpe = catalogo.obter("roteador-cpe")
    assert cpe.interna.modelo == "VTR-4100"
    assert cpe.neutra.requisitos_minimos and cpe.neutra.textos_padrao


def test_tipo_neutro_nao_possui_camada_interna(catalogo):
    assert "interna" not in ItemCatalogoNeutro.model_fields
    for item in catalogo.visao_neutra():
        assert type(item) is ItemCatalogoNeutro
        assert not hasattr(item, "interna")
        assert "interna" not in item.model_dump()


def test_visao_neutra_serializada_nao_contem_nenhum_termo_interno(catalogo):
    """Precursor do teste da Fase 4: o que o Módulo B recebe não carrega dado interno."""
    serializado = json.dumps(
        [i.model_dump(mode="json") for i in catalogo.visao_neutra()], ensure_ascii=False
    )
    termos = [t for lista in catalogo.termos_internos().values() for t in lista]
    assert len(termos) >= 8
    for termo in termos:
        assert not contem_termo(serializado, termo), termo
    for item in catalogo.itens:
        if item.interna.observacoes:
            assert item.interna.observacoes not in serializado


def test_visao_neutra_filtra_e_preserva_ordem(catalogo):
    visao = catalogo.visao_neutra(["switch-acesso", "link-mpls"])
    assert [i.id for i in visao] == ["switch-acesso", "link-mpls"]
    with pytest.raises(KeyError):
        catalogo.visao_neutra(["inexistente"])


@pytest.mark.parametrize(
    ("campo", "texto"),
    [
        ("nome", "Roteador VTR-4100"),
        ("descricao", "Roteador da linha vetrion com 4 portas."),
        ("descricao", "Compatível com Lumenár Sistemas."),
    ],
)
def test_recusa_termo_interno_na_camada_neutra(campo, texto):
    dados = _item(
        fabricante="Lumenar Sistemas", modelo="VTR-4100", outros_termos_restritos=["Vetrion"]
    )
    if campo == "nome":
        dados["nome"] = texto
    else:
        dados["neutra"]["descricao_funcional"] = texto
    with pytest.raises(ValidationError, match="termo interno"):
        ItemCatalogo.model_validate(dados)


def test_termo_interno_so_casa_palavra_inteira():
    assert contem_termo("roteador VTR-4100, novo", "vtr-4100")
    assert not contem_termo("porta 18021 ativa", "802")
    assert not contem_termo("alimentação", "LIM")
    assert CamadaInterna(fabricante="AB").termos_restritos() == []  # curto demais


def test_recusa_campo_desconhecido_e_id_invalido():
    with pytest.raises(ValidationError):
        ItemCatalogo.model_validate({**_item(), "preco": "100"})
    with pytest.raises(ValidationError):
        ItemCatalogo.model_validate({**_item(), "id": "Item Com Espaço"})


def test_carregamento_recusa_id_repetido_e_yaml_invalido(config, tmp_path):
    destino = tmp_path / "catalogo"
    shutil.copytree(config.dir_catalogo, destino)
    shutil.copy(destino / "link-mpls.yaml", destino / "copia.yaml")
    with pytest.raises(ErroCatalogo, match="repetido"):
        carregar_catalogo(destino)
    (destino / "copia.yaml").write_text("id: [sem fechar", encoding="utf-8")
    with pytest.raises(ErroCatalogo, match="inválido"):
        carregar_catalogo(destino)


def test_yaml_com_objeto_python_e_recusado(tmp_path):
    (tmp_path / "malicioso.yaml").write_text(
        "id: !!python/object/apply:os.system ['echo x']\n", encoding="utf-8"
    )
    with pytest.raises(ErroCatalogo):
        carregar_catalogo(tmp_path)


def test_hash_muda_quando_o_catalogo_muda(config, tmp_path, catalogo):
    destino = tmp_path / "catalogo"
    shutil.copytree(config.dir_catalogo, destino)
    assert carregar_catalogo(destino).hash == catalogo.hash
    caminho = destino / "switch-acesso.yaml"
    dados = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    dados["interna"]["modelo"] = "LS-9999"
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True), encoding="utf-8")
    assert carregar_catalogo(destino).hash != catalogo.hash
