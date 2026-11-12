"""Leitura de YAML de configuração (catálogo e perfis), sempre com `safe_load`."""

from pathlib import Path
from typing import Any

import yaml

_TAMANHO_MAX = 1024 * 1024


def ler_yaml(caminho: Path) -> Any:
    """Lê um arquivo YAML sem permitir construção de objetos arbitrários.

    Levanta `ValueError` para arquivo grande demais ou com sintaxe inválida.
    """
    if caminho.stat().st_size > _TAMANHO_MAX:
        raise ValueError("arquivo YAML grande demais")
    try:
        return yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML inválido: {type(exc).__name__}") from exc
