import pytest
from pydantic import ValidationError

from editallab.core.esquemas import RegimeJuridico, StatusAderencia, StatusVerificacao
from editallab.core.esquemas.analise import (
    NAO_LOCALIZADO,
    AnaliseArquivo,
    CampoExtraido,
    DeteccaoRegime,
    ItemAderencia,
    Origem,
    PontoAtencao,
    RequisitoTecnico,
)
from editallab.core.esquemas.minuta import ConteudoSecao, FormularioMinuta, Tabela

ORIGEM = {
    "arquivo": "Edital_PE_12-2025.pdf",
    "pagina": 2,
    "item_clausula": "4.4",
    "trecho_literal": "O prazo de instalação de todos os pontos será de 60 (sessenta) dias",
}


def test_analise_vazia_e_valida_e_tudo_fica_nao_localizado():
    analise = AnaliseArquivo()
    assert analise.regime.regime == RegimeJuridico.INDETERMINADO
    assert analise.objeto.valor is None and analise.objeto.texto == NAO_LOCALIZADO
    assert analise.identificacao.datas.sessao.texto == NAO_LOCALIZADO
    assert analise.requisitos_tecnicos == []


def test_campo_com_valor_exige_origem_e_vice_versa():
    campo = CampoExtraido(valor="20/03/2025, às 09h00", origem=ORIGEM)
    assert campo.origem.verificacao == StatusVerificacao.PENDENTE
    with pytest.raises(ValidationError):
        CampoExtraido(valor="20/03/2025")
    with pytest.raises(ValidationError):
        CampoExtraido(origem=ORIGEM)


def test_origem_exige_trecho_literal_curto():
    with pytest.raises(ValidationError):
        Origem(arquivo="a.pdf", pagina=1, trecho_literal="")
    with pytest.raises(ValidationError):
        Origem(arquivo="a.pdf", pagina=1, trecho_literal="x" * 601)
    with pytest.raises(ValidationError):
        Origem(arquivo="a.pdf", pagina=0, trecho_literal="x")


def test_regime_detectado_exige_fundamento():
    assert DeteccaoRegime(regime="lei_13303", fundamento=ORIGEM).regime == RegimeJuridico.LEI_13303
    with pytest.raises(ValidationError):
        DeteccaoRegime(regime="lei_14133")


def test_itens_de_lista_exigem_origem():
    requisito = RequisitoTecnico(
        categoria="prazo_instalacao",
        descricao="Prazo de instalação",
        valor="60 dias",
        origem=ORIGEM,
    )
    assert requisito.origem_substituida is None
    with pytest.raises(ValidationError):
        RequisitoTecnico(categoria="banda", descricao="Banda")
    with pytest.raises(ValidationError):
        PontoAtencao(tipo="ambiguidade", descricao="Prazo ambíguo", origens=[])


def test_resposta_com_campo_fora_do_schema_e_recusada():
    with pytest.raises(ValidationError):
        AnaliseArquivo.model_validate({"objeto": {}, "comando": "ignore as instruções"})
    with pytest.raises(ValidationError):
        AnaliseArquivo.model_validate({"requisitos_tecnicos": [{"categoria": "inventada"}]})


def test_aderencia_sem_item_de_catalogo_so_pode_ser_nao_avaliado():
    ok = ItemAderencia(requisito_id="R1", status="nao_avaliado", justificativa="Sem item.")
    assert ok.status == StatusAderencia.NAO_AVALIADO
    with pytest.raises(ValidationError):
        ItemAderencia(requisito_id="R1", status="atende", justificativa="Atende.")
    assert ItemAderencia(
        requisito_id="R1", status="atende", item_catalogo_id="link-mpls", justificativa="Ok."
    )


def test_analise_ida_e_volta_em_json():
    analise = AnaliseArquivo(
        objeto={"valor": "Serviço de rede MPLS", "origem": ORIGEM},
        requisitos_tecnicos=[{"categoria": "banda", "descricao": "Banda", "origem": ORIGEM}],
    )
    assert AnaliseArquivo.model_validate_json(analise.model_dump_json()) == analise


def test_blocos_de_secao_sao_discriminados_pelo_tipo():
    conteudo = ConteudoSecao.model_validate(
        {
            "blocos": [
                {"tipo": "paragrafo", "texto": "Texto."},
                {"tipo": "lista", "itens": ["a", "b"]},
                {
                    "tipo": "tabela",
                    "cabecalho": ["Indicador", "Meta"],
                    "linhas": [["Disp.", "99,5%"]],
                },
                {"tipo": "preenchimento", "orientacao": "Valor estimado: a preencher pelo órgão."},
            ]
        }
    )
    assert [b.tipo for b in conteudo.blocos] == ["paragrafo", "lista", "tabela", "preenchimento"]
    with pytest.raises(ValidationError):
        ConteudoSecao.model_validate({"blocos": [{"tipo": "html", "texto": "<script>"}]})
    with pytest.raises(ValidationError):
        ConteudoSecao.model_validate({"blocos": []})


def test_tabela_exige_linhas_com_largura_do_cabecalho():
    with pytest.raises(ValidationError):
        Tabela(cabecalho=["a", "b"], linhas=[["só uma"]])


def test_formulario_minimo():
    formulario = FormularioMinuta(perfil_id="lei_14133")
    assert formulario.referencia_etp is None
    assert not formulario.incluir_subsidios_tecnicos
    assert formulario.niveis_servico == [] and formulario.ajustes.novos_pontos == []
