"""Schemas do catálogo técnico (Módulo C), com camada neutra e camada interna.

`ItemCatalogoNeutro` é um tipo à parte que **não possui** a camada interna. O
Módulo B só recebe esse tipo, de modo que fabricante, modelo e part number não
têm como chegar a um prompt de geração.
"""

import re
import unicodedata

from pydantic import Field, model_validator

from editallab.core.esquemas.base import Esquema
from editallab.core.esquemas.enums import CategoriaItem

PADRAO_ID = r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$"
# Termos internos menores que isto geram falso positivo demais na busca textual.
TAMANHO_MIN_TERMO = 3


def normalizar_para_busca(texto: str) -> str:
    """Minúsculas e sem acentos, para comparação de termos insensível a grafia."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def contem_termo(texto: str, termo: str) -> bool:
    """Indica se `termo` aparece em `texto` como palavra inteira (sem acento nem caixa)."""
    padrao = r"(?<![a-z0-9])" + re.escape(normalizar_para_busca(termo)) + r"(?![a-z0-9])"
    return re.search(padrao, normalizar_para_busca(texto)) is not None


class RequisitoMinimo(Esquema):
    """Requisito funcional mínimo, redigido sem marca nem modelo."""

    parametro: str = Field(min_length=1)
    valor_minimo: str = Field(min_length=1)
    observacao: str | None = None


class SlaPraticavel(Esquema):
    """Nível de serviço que a empresa consegue praticar para o item."""

    indicador: str = Field(min_length=1)
    valor: str = Field(min_length=1)
    observacao: str | None = None


class CamadaNeutra(Esquema):
    """Conteúdo que pode aparecer em documentos para clientes e órgãos."""

    descricao_funcional: str = Field(min_length=1)
    requisitos_minimos: list[RequisitoMinimo] = Field(default_factory=list)
    slas_praticaveis: list[SlaPraticavel] = Field(default_factory=list)
    textos_padrao: list[str] = Field(default_factory=list)

    def textos(self) -> list[str]:
        """Todos os textos da camada, para a conferência de neutralidade."""
        saida = [self.descricao_funcional, *self.textos_padrao]
        for r in self.requisitos_minimos:
            saida += [r.parametro, r.valor_minimo, r.observacao or ""]
        for s in self.slas_praticaveis:
            saida += [s.indicador, s.valor, s.observacao or ""]
        return saida


class CamadaInterna(Esquema):
    """Dados de uso interno. Nunca saem para prompts de geração nem para minutas."""

    fabricante: str | None = None
    modelo: str | None = None
    part_numbers: list[str] = Field(default_factory=list)
    # Outros nomes que denunciam o produto: linha, nome comercial, fornecedor.
    outros_termos_restritos: list[str] = Field(default_factory=list)
    observacoes: str | None = None

    def termos_restritos(self) -> list[str]:
        """Termos que não podem aparecer em texto neutro (fabricante, modelo, PN etc.)."""
        candidatos = [
            self.fabricante,
            self.modelo,
            *self.part_numbers,
            *self.outros_termos_restritos,
        ]
        return [t for t in candidatos if t and len(t) >= TAMANHO_MIN_TERMO]


class ItemCatalogoNeutro(Esquema):
    """Visão de um item sem a camada interna. Único tipo entregue ao Módulo B."""

    id: str = Field(pattern=PADRAO_ID)
    nome: str = Field(min_length=1)
    categoria: CategoriaItem
    neutra: CamadaNeutra


class ItemCatalogo(ItemCatalogoNeutro):
    """Item completo do catálogo, com as duas camadas. Usado pelo Módulo A."""

    interna: CamadaInterna = Field(default_factory=CamadaInterna)

    @model_validator(mode="after")
    def _camada_neutra_sem_termos_internos(self) -> "ItemCatalogo":
        """Recusa o item se algum termo interno vazou para o nome ou para a camada neutra."""
        for termo in self.interna.termos_restritos():
            for texto in (self.nome, *self.neutra.textos()):
                if contem_termo(texto, termo):
                    raise ValueError(
                        f"o termo interno {termo!r} aparece no nome ou na camada neutra do item"
                    )
        return self

    def visao_neutra(self) -> ItemCatalogoNeutro:
        """Devolve o item sem a camada interna."""
        return ItemCatalogoNeutro(
            id=self.id, nome=self.nome, categoria=self.categoria, neutra=self.neutra
        )
