"""Validação de arquivos recebidos: nome, extensão, magic bytes e tamanho.

Todo arquivo, venha de upload direto, de ZIP ou de uma fonte futura, passa por
`validar_arquivo` antes de ser gravado.
"""

import hashlib
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroValidacaoArquivo, ErroZipInseguro
from editallab.core.ingestao.zip_seguro import ler_membro_limitado, tem_magic_zip

EXTENSOES_ACEITAS = frozenset({".pdf", ".docx", ".xlsx", ".csv"})
_TAMANHO_MAX_NOME = 150
# Membro obrigatório de cada formato OOXML, usado como verificação de conteúdo.
_MEMBRO_OOXML = {".docx": "word/document.xml", ".xlsx": "xl/workbook.xml"}


@dataclass(frozen=True)
class ArquivoValidado:
    """Arquivo aprovado na validação, pronto para armazenamento."""

    nome_original: str
    nome_sanitizado: str
    extensao: str
    sha256: str
    conteudo: bytes

    @property
    def tamanho(self) -> int:
        """Tamanho do conteúdo em bytes."""
        return len(self.conteudo)


def sanitizar_nome(nome: str) -> str:
    """Reduz um nome de arquivo a um nome seguro para exibição e registro.

    Remove diretórios, caracteres de controle e tudo o que não for letra, dígito,
    espaço, ponto, hífen ou sublinhado. O nome sanitizado nunca é usado como caminho
    em disco (o arquivo é gravado pelo hash).
    """
    base = PurePosixPath(nome.replace("\\", "/")).name
    base = unicodedata.normalize("NFC", base)
    base = "".join(c for c in base if unicodedata.category(c)[0] != "C")
    base = re.sub(r"[^\w .\-()]", "_", base, flags=re.UNICODE)
    base = re.sub(r"\s+", " ", base).strip(" .")
    if len(base) > _TAMANHO_MAX_NOME:
        sufixo = PurePosixPath(base).suffix[:10]
        base = base[: _TAMANHO_MAX_NOME - len(sufixo)] + sufixo
    return base or "arquivo"


def _validar_ooxml(conteudo: bytes, extensao: str, config: Configuracoes) -> None:
    """Confere a estrutura interna de DOCX/XLSX e aplica os limites de descompactação."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(conteudo))
    except zipfile.BadZipFile as exc:
        raise ErroValidacaoArquivo("O arquivo está corrompido.", "OOXML ilegível") from exc
    with zf:
        nomes = set(zf.namelist())
        if "[Content_Types].xml" not in nomes or _MEMBRO_OOXML[extensao] not in nomes:
            raise ErroValidacaoArquivo(
                f"O conteúdo do arquivo não corresponde a um {extensao[1:].upper()} válido.",
                "estrutura OOXML ausente",
            )
        if any(PurePosixPath(n).name.lower() == "vbaproject.bin" for n in nomes):
            raise ErroValidacaoArquivo("Arquivos com macros não são aceitos.", "vbaProject.bin")
        if len(nomes) > 5000:
            raise ErroValidacaoArquivo("O arquivo tem estrutura interna anormal.", "muitas partes")
        restante = config.zip_max_descompactado
        try:
            for info in zf.infolist():
                restante -= len(ler_membro_limitado(zf, info, restante))
        except ErroZipInseguro as exc:
            raise ErroValidacaoArquivo(
                "O arquivo excede o tamanho máximo permitido após descompactar.", exc.detalhe
            ) from exc


def _validar_csv(conteudo: bytes) -> None:
    """CSV não tem assinatura: exige texto decodificável e sem bytes de controle."""
    if b"\x00" in conteudo:
        raise ErroValidacaoArquivo("O arquivo CSV contém dados binários.", "byte nulo em CSV")
    texto = decodificar_texto(conteudo)
    controles = sum(1 for c in texto if ord(c) < 32 and c not in "\t\r\n")
    if controles:
        raise ErroValidacaoArquivo("O arquivo CSV contém dados binários.", "controle em CSV")


def decodificar_texto(conteudo: bytes) -> str:
    """Decodifica bytes de texto como UTF-8 (com ou sem BOM) ou, na falha, Windows-1252."""
    try:
        return conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        return conteudo.decode("cp1252", errors="replace")


def validar_arquivo(nome_original: str, conteudo: bytes, config: Configuracoes) -> ArquivoValidado:
    """Valida um arquivo e devolve seus metadados, ou levanta `ErroValidacaoArquivo`.

    Verifica, nesta ordem: tamanho, extensão permitida e correspondência entre a
    extensão e o conteúdo real (magic bytes ou estrutura interna).
    """
    nome = sanitizar_nome(nome_original)
    extensao = PurePosixPath(nome).suffix.lower()
    if not conteudo:
        raise ErroValidacaoArquivo("O arquivo está vazio.")
    if len(conteudo) > config.max_tamanho_arquivo:
        raise ErroValidacaoArquivo(
            f"O arquivo excede o limite de {config.max_tamanho_arquivo_mb} MB."
        )
    if extensao not in EXTENSOES_ACEITAS:
        raise ErroValidacaoArquivo(
            "Tipo de arquivo não aceito. Envie PDF, DOCX, XLSX ou CSV.", f"extensão {extensao!r}"
        )
    if extensao == ".pdf":
        if not conteudo.startswith(b"%PDF-"):
            raise ErroValidacaoArquivo(
                "O conteúdo do arquivo não corresponde a um PDF válido.", "magic bytes"
            )
    elif extensao in _MEMBRO_OOXML:
        if not tem_magic_zip(conteudo):
            raise ErroValidacaoArquivo(
                f"O conteúdo do arquivo não corresponde a um {extensao[1:].upper()} válido.",
                "magic bytes",
            )
        _validar_ooxml(conteudo, extensao, config)
    else:
        if conteudo.startswith(b"%PDF-") or tem_magic_zip(conteudo):
            raise ErroValidacaoArquivo("O conteúdo do arquivo não corresponde a um CSV.", "magic")
        _validar_csv(conteudo)
    return ArquivoValidado(
        nome_original=nome_original,
        nome_sanitizado=nome,
        extensao=extensao,
        sha256=hashlib.sha256(conteudo).hexdigest(),
        conteudo=conteudo,
    )
