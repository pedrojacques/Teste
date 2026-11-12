"""Armazenamento local dos arquivos originais.

Os originais ficam em `<dir_dados>/originais/<sha256>`, fora de qualquer diretório
servido. O nome em disco é sempre o hash, nunca o nome informado pelo usuário, de
modo que nenhum dado externo participa da montagem do caminho.
"""

import re
from pathlib import Path

from editallab.core.config import Configuracoes

_RE_SHA256 = re.compile(r"[0-9a-f]{64}")


def caminho_original(sha256: str, config: Configuracoes) -> Path:
    """Devolve o caminho do original identificado pelo hash."""
    if not _RE_SHA256.fullmatch(sha256):
        raise ValueError("hash SHA-256 inválido")
    return config.dir_originais / sha256


def gravar_original(conteudo: bytes, sha256: str, config: Configuracoes) -> Path:
    """Grava o original (se ainda não existir) com permissão restrita ao usuário."""
    destino = caminho_original(sha256, config)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        destino.write_bytes(conteudo)
        destino.chmod(0o600)
    return destino


def ler_original(sha256: str, config: Configuracoes) -> bytes:
    """Lê o conteúdo de um original já armazenado."""
    return caminho_original(sha256, config).read_bytes()
