"""Configuração de log local.

Regra do projeto: logs nunca contêm texto de documentos nem segredos, apenas
identificadores (hash, id), nomes de etapas e mensagens de erro técnicas.
"""

import logging
from pathlib import Path


def configurar_logs(dir_dados: Path, nivel: int = logging.INFO) -> None:
    """Direciona os logs do pacote `editallab` para `<dir_dados>/editallab.log`."""
    dir_dados.mkdir(parents=True, exist_ok=True)
    manipulador = logging.FileHandler(dir_dados / "editallab.log", encoding="utf-8")
    manipulador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    raiz = logging.getLogger("editallab")
    raiz.setLevel(nivel)
    if not any(isinstance(m, logging.FileHandler) for m in raiz.handlers):
        raiz.addHandler(manipulador)
