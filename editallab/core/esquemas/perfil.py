"""Schema do perfil de documento, que define a estrutura de uma minuta (Módulo B)."""

from pydantic import Field, model_validator

from editallab.core.esquemas.base import Esquema
from editallab.core.esquemas.catalogo import PADRAO_ID
from editallab.core.esquemas.enums import PapelSecao, RegimeJuridico

AVISO_PADRAO = (
    "Minuta gerada com apoio de IA. "
    "Validar com o responsável jurídico/contratual interno antes do uso."
)


class CampoCabecalho(Esquema):
    """Campo exibido no cabeçalho do documento e pedido no formulário."""

    id: str = Field(pattern=PADRAO_ID)
    rotulo: str = Field(min_length=1)
    obrigatorio: bool = False


class SecaoPerfil(Esquema):
    """Seção de um perfil: o que é e como deve ser redigida."""

    id: str = Field(pattern=PADRAO_ID)
    titulo: str = Field(min_length=1)
    ordem: int = Field(ge=1)
    instrucao_redacao: str = Field(min_length=1)
    papel: PapelSecao = PapelSecao.GERAL
    # A tabela de NMS/SLA e glosas do formulário é renderizada nesta seção.
    inclui_tabela_nms: bool = False


class PerfilDocumento(Esquema):
    """Estrutura de um tipo de documento. O motor de geração é o mesmo para todos."""

    id: str = Field(pattern=PADRAO_ID)
    nome: str = Field(min_length=1)
    versao: str = Field(min_length=1)
    descricao: str | None = None
    # Regimes para os quais este perfil é sugerido. O usuário sempre pode trocar.
    regimes_sugeridos: list[RegimeJuridico] = Field(default_factory=list)
    # Norma ou regulamento que inspira a estrutura. Mora aqui, nunca nos prompts.
    referencia_normativa: str | None = None
    usa_etp: bool
    exige_neutralidade: bool
    aviso: str = AVISO_PADRAO
    campos_cabecalho: list[CampoCabecalho] = Field(min_length=1)
    secoes: list[SecaoPerfil] = Field(min_length=1)

    @model_validator(mode="after")
    def _validar_estrutura(self) -> "PerfilDocumento":
        """Exige identificadores e ordens únicos e coerência com `usa_etp`."""
        ids = [s.id for s in self.secoes]
        ordens = [s.ordem for s in self.secoes]
        if len(set(ids)) != len(ids):
            raise ValueError("há seções com identificador repetido")
        if len(set(ordens)) != len(ordens):
            raise ValueError("há seções com a mesma ordem")
        campos = [c.id for c in self.campos_cabecalho]
        if len(set(campos)) != len(campos):
            raise ValueError("há campos de cabeçalho repetidos")
        fundamentacoes = [s for s in self.secoes if s.papel == PapelSecao.FUNDAMENTACAO]
        if self.usa_etp and len(fundamentacoes) != 1:
            raise ValueError(
                "perfil com usa_etp precisa de exatamente uma seção com papel 'fundamentacao'"
            )
        if sum(s.inclui_tabela_nms for s in self.secoes) > 1:
            raise ValueError("a tabela de NMS só pode ser incluída em uma seção")
        self.secoes.sort(key=lambda s: s.ordem)
        return self

    def secao(self, secao_id: str) -> SecaoPerfil:
        """Devolve a seção pelo identificador, ou levanta `KeyError`."""
        for s in self.secoes:
            if s.id == secao_id:
                return s
        raise KeyError(secao_id)
