"""Carregamento do catálogo técnico e suas duas visões.

- Visão completa (`Catalogo.itens`): usada pelo Módulo A para avaliar aderência.
- Visão neutra (`Catalogo.visao_neutra()`): única visão entregue ao Módulo B.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from editallab.core.erros import ErroCatalogo
from editallab.core.esquemas.catalogo import ItemCatalogo, ItemCatalogoNeutro
from editallab.core.yaml_seguro import ler_yaml


@dataclass(frozen=True)
class Catalogo:
    """Conjunto de itens do catálogo, ordenado por identificador."""

    itens: tuple[ItemCatalogo, ...]

    def obter(self, item_id: str) -> ItemCatalogo:
        """Devolve o item completo pelo identificador, ou levanta `KeyError`."""
        for item in self.itens:
            if item.id == item_id:
                return item
        raise KeyError(item_id)

    def visao_neutra(self, ids: list[str] | None = None) -> list[ItemCatalogoNeutro]:
        """Itens sem a camada interna. Com `ids`, devolve só os pedidos, na ordem pedida."""
        if ids is None:
            return [item.visao_neutra() for item in self.itens]
        return [self.obter(item_id).visao_neutra() for item_id in ids]

    def termos_internos(self) -> dict[str, list[str]]:
        """Termos restritos por item, para a busca determinística de neutralidade.

        Uso exclusivo em código. Estes termos nunca são enviados ao modelo.
        """
        return {i.id: i.interna.termos_restritos() for i in self.itens if i.interna}

    @property
    def hash(self) -> str:
        """Hash do conteúdo do catálogo; compõe a chave de cache da aderência."""
        canonico = json.dumps(
            [i.model_dump(mode="json") for i in self.itens], sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def carregar_catalogo(diretorio: Path) -> Catalogo:
    """Lê e valida todos os `*.yaml` do diretório do catálogo.

    Levanta `ErroCatalogo` se algum arquivo for inválido, se houver identificador
    repetido ou se um termo interno tiver vazado para a camada neutra.
    """
    itens: dict[str, ItemCatalogo] = {}
    for caminho in sorted(diretorio.glob("*.yaml")):
        try:
            item = ItemCatalogo.model_validate(ler_yaml(caminho))
        except (ValidationError, ValueError) as exc:
            raise ErroCatalogo(
                f"O item de catálogo '{caminho.name}' é inválido. Consulte o log.", str(exc)
            ) from exc
        if item.id in itens:
            raise ErroCatalogo(
                f"O identificador '{item.id}' está repetido no catálogo ({caminho.name})."
            )
        itens[item.id] = item
    return Catalogo(itens=tuple(itens[k] for k in sorted(itens)))
