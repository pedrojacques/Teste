"""Carregamento dos perfis de documento e sugestão de perfil pelo regime confirmado."""

from pathlib import Path

from pydantic import ValidationError

from editallab.core.erros import ErroPerfil
from editallab.core.esquemas import RegimeJuridico
from editallab.core.esquemas.perfil import PerfilDocumento
from editallab.core.yaml_seguro import ler_yaml


def carregar_perfis(diretorio: Path) -> dict[str, PerfilDocumento]:
    """Lê e valida todos os `*.yaml` do diretório de perfis, indexados por identificador."""
    perfis: dict[str, PerfilDocumento] = {}
    for caminho in sorted(diretorio.glob("*.yaml")):
        try:
            perfil = PerfilDocumento.model_validate(ler_yaml(caminho))
        except (ValidationError, ValueError) as exc:
            raise ErroPerfil(
                f"O perfil '{caminho.name}' é inválido. Consulte o log.", str(exc)
            ) from exc
        if perfil.id in perfis:
            raise ErroPerfil(f"O identificador de perfil '{perfil.id}' está repetido.")
        perfis[perfil.id] = perfil
    return perfis


def sugerir_perfil(
    regime: RegimeJuridico | None, perfis: dict[str, PerfilDocumento]
) -> PerfilDocumento | None:
    """Sugere o perfil para o regime **confirmado** do processo.

    Devolve `None` quando o regime ainda não foi confirmado ou não há perfil que o
    declare. A relação entre regime e perfil vem do YAML (`regimes_sugeridos`), não
    do código. O usuário sempre pode escolher outro perfil.
    """
    if regime is None:
        return None
    for perfil in perfis.values():
        if regime in perfil.regimes_sugeridos:
            return perfil
    return None
