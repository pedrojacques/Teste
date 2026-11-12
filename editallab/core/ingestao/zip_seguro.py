"""Leitura segura de arquivos ZIP enviados pelo usuário.

Nada é gravado em disco aqui: os membros são lidos em memória, com limites medidos
durante a leitura (o tamanho declarado no cabeçalho do ZIP não é confiável).
Defesas: zip slip (caminho absoluto, `..`, link simbólico), zip bomb (tamanho total,
tamanho por arquivo e quantidade de entradas), ZIP aninhado e membros cifrados.
"""

import io
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroZipInseguro

MAGIC_ZIP = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_BLOCO = 64 * 1024
# Extensões de formatos que são ZIP por dentro e passam pela validação própria.
_OOXML = {".docx", ".xlsx"}


@dataclass
class ConteudoZip:
    """Membros lidos de um ZIP e os que foram ignorados sem risco (ex.: arquivos ocultos)."""

    membros: list[tuple[str, bytes]] = field(default_factory=list)
    ignorados: list[tuple[str, str]] = field(default_factory=list)


def tem_magic_zip(conteudo: bytes) -> bool:
    """Indica se os bytes começam com uma assinatura de ZIP."""
    return conteudo.startswith(MAGIC_ZIP)


def ler_membro_limitado(zf: zipfile.ZipFile, info: zipfile.ZipInfo, limite: int) -> bytes:
    """Lê um membro do ZIP em blocos e interrompe se passar de `limite` bytes."""
    partes: list[bytes] = []
    total = 0
    with zf.open(info) as fluxo:
        while bloco := fluxo.read(_BLOCO):
            total += len(bloco)
            if total > limite:
                raise ErroZipInseguro(
                    "O conteúdo compactado excede o tamanho máximo permitido.",
                    f"membro excedeu {limite} bytes ao descompactar",
                )
            partes.append(bloco)
    return b"".join(partes)


def _caminho_inseguro(nome: str) -> bool:
    """Detecta caminho absoluto, com unidade de disco ou com componente `..`."""
    normalizado = nome.replace("\\", "/")
    if normalizado.startswith("/") or (len(normalizado) > 1 and normalizado[1] == ":"):
        return True
    return ".." in PurePosixPath(normalizado).parts


def _oculto(nome: str) -> bool:
    """Arquivos de sistema que o macOS e o Windows colocam em pastas compactadas."""
    partes = PurePosixPath(nome.replace("\\", "/")).parts
    return any(p.startswith(".") or p == "__MACOSX" for p in partes) or partes[-1] in {
        "Thumbs.db",
        "desktop.ini",
    }


def extrair_zip_seguro(conteudo: bytes, config: Configuracoes) -> ConteudoZip:
    """Lê os membros de um ZIP aplicando todas as defesas.

    Qualquer sinal de risco recusa o ZIP **inteiro** com `ErroZipInseguro`. Membros
    inofensivos mas inúteis (ocultos, pastas) são apenas ignorados. A validação de tipo
    de cada membro (extensão e magic bytes) é feita depois, no mesmo funil dos uploads.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(conteudo))
    except zipfile.BadZipFile as exc:
        raise ErroZipInseguro("O arquivo ZIP está corrompido ou não é um ZIP válido.") from exc

    resultado = ConteudoZip()
    with zf:
        entradas = zf.infolist()
        if len(entradas) > config.zip_max_arquivos:
            raise ErroZipInseguro(
                f"O ZIP contém mais de {config.zip_max_arquivos} arquivos.",
                f"{len(entradas)} entradas",
            )
        # Primeiro passo: recusa por estrutura, antes de descompactar qualquer coisa.
        for info in entradas:
            nome = info.filename
            if _caminho_inseguro(nome):
                raise ErroZipInseguro(
                    "O ZIP contém caminhos que saem da pasta de destino e foi recusado.",
                    "zip slip",
                )
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ErroZipInseguro("O ZIP contém links simbólicos e foi recusado.", "symlink")
            if info.flag_bits & 0x1:
                raise ErroZipInseguro("O ZIP está protegido por senha e não pode ser lido.")
            if not info.is_dir() and nome.lower().endswith(".zip"):
                raise ErroZipInseguro(
                    "O ZIP contém outro ZIP dentro dele. Envie os arquivos em um único nível."
                )

        restante = config.zip_max_descompactado
        for info in entradas:
            if info.is_dir():
                continue
            nome = info.filename
            if _oculto(nome):
                resultado.ignorados.append((nome, "arquivo oculto ou de sistema"))
                continue
            dados = ler_membro_limitado(zf, info, min(restante, config.max_tamanho_arquivo))
            restante -= len(dados)
            if restante <= 0:
                raise ErroZipInseguro(
                    "O conteúdo do ZIP excede o tamanho máximo permitido após descompactar."
                )
            extensao = PurePosixPath(nome).suffix.lower()
            if tem_magic_zip(dados) and extensao not in _OOXML:
                raise ErroZipInseguro(
                    "O ZIP contém outro ZIP dentro dele. Envie os arquivos em um único nível.",
                    "ZIP aninhado com extensão disfarçada",
                )
            resultado.membros.append((nome, dados))
    return resultado
