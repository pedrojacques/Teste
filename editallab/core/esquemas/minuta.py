"""Schemas da geração de minutas (Módulo B): formulário, seções e alertas."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from editallab.core.esquemas.base import Esquema


class LinhaNMS(Esquema):
    """Linha da tabela de níveis mínimos de serviço e glosas, editável no formulário."""

    indicador: str = Field(min_length=1)
    meta: str = Field(min_length=1)
    forma_medicao: str | None = None
    glosa: str | None = None


class PontoAjuste(Esquema):
    """Ponto novo ou alterado em relação ao contrato atual."""

    nome: str = Field(min_length=1)
    endereco: str | None = None
    banda: str | None = None
    observacao: str | None = None


class AjustesDesejados(Esquema):
    """Mudanças pedidas em relação ao documento de origem. Vazio significa manter."""

    novos_pontos: list[PontoAjuste] = Field(default_factory=list)
    nova_banda: str | None = None
    novo_sla: str | None = None
    novo_prazo_instalacao: str | None = None
    novo_prazo_reparo: str | None = None
    nova_vigencia: str | None = None
    outras_orientacoes: str | None = None


class FormularioMinuta(Esquema):
    """Tudo o que o usuário informa antes de gerar uma minuta."""

    perfil_id: str = Field(min_length=1)
    # Valores dos campos de cabeçalho definidos no perfil, por identificador.
    cabecalho: dict[str, str] = Field(default_factory=dict)
    # Referência ao Estudo Técnico Preliminar. Vazia: a fundamentação sai como marcador.
    referencia_etp: str | None = None
    incluir_subsidios_tecnicos: bool = False
    ajustes: AjustesDesejados = Field(default_factory=AjustesDesejados)
    niveis_servico: list[LinhaNMS] = Field(default_factory=list)
    # Itens do catálogo cujas especificações neutras entram na minuta.
    itens_catalogo: list[str] = Field(default_factory=list)


class Paragrafo(Esquema):
    """Parágrafo de texto corrido."""

    tipo: Literal["paragrafo"] = "paragrafo"
    texto: str = Field(min_length=1)


class Lista(Esquema):
    """Lista de itens, renderizada com marcadores escritos como texto."""

    tipo: Literal["lista"] = "lista"
    itens: list[str] = Field(min_length=1)


class Tabela(Esquema):
    """Tabela simples: uma linha de cabeçalho e linhas de dados, sem mesclagem."""

    tipo: Literal["tabela"] = "tabela"
    cabecalho: list[str] = Field(min_length=1)
    linhas: list[list[str]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _linhas_com_mesma_largura(self) -> "Tabela":
        """Toda linha precisa ter o mesmo número de colunas do cabeçalho."""
        if any(len(linha) != len(self.cabecalho) for linha in self.linhas):
            raise ValueError("linha de tabela com número de colunas diferente do cabeçalho")
        return self


class MarcadorPreenchimento(Esquema):
    """Lacuna deixada de propósito para o órgão ou cliente preencher (preço, ETP etc.)."""

    tipo: Literal["preenchimento"] = "preenchimento"
    orientacao: str = Field(min_length=1)


Bloco = Annotated[Paragrafo | Lista | Tabela | MarcadorPreenchimento, Field(discriminator="tipo")]


class ConteudoSecao(Esquema):
    """Conteúdo de uma seção, como devolvido pelo modelo e gravado no banco."""

    blocos: list[Bloco] = Field(min_length=1)


class SecaoMinuta(Esquema):
    """Seção de uma minuta. O DOCX é sempre renderizado a partir destas seções."""

    secao_id: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    ordem: int = Field(ge=1)
    conteudo: ConteudoSecao
    # Rastreabilidade; nulos quando a seção foi montada sem chamada ao modelo.
    versao_prompt: str | None = None
    modelo: str | None = None


class OrigemAlerta(StrEnum):
    """Qual parte da checagem de neutralidade gerou o alerta."""

    DETERMINISTICA = "deterministica"
    MODELO = "modelo"


class AlertaNeutralidade(Esquema):
    """Alerta de possível direcionamento. Informa, não bloqueia a exportação."""

    origem: OrigemAlerta
    secao_id: str = Field(min_length=1)
    trecho: str = Field(min_length=1)
    motivo: str = Field(min_length=1)
    sugestao: str | None = None
