"""Sugestão do tipo de um arquivo a partir do nome. O usuário sempre confirma."""

import re
import unicodedata

from editallab.core.esquemas import TipoArquivo

# A ordem importa: errata e esclarecimento vêm antes porque costumam citar o edital
# no próprio nome ("Errata 01 do Edital 12-2025").
_REGRAS: tuple[tuple[TipoArquivo, str], ...] = (
    (TipoArquivo.ERRATA, r"\b(errata|retificac\w*|adendo|rerratificac\w*)\b"),
    (
        TipoArquivo.ESCLARECIMENTO,
        r"\b(esclarecimento\w*|questionamento\w*|respostas?|impugnac\w*)\b",
    ),
    (TipoArquivo.TERMO_REFERENCIA, r"\b(termo de referencia|tr|projeto basico)\b"),
    (TipoArquivo.CONTRATO, r"\b(contrato|aditivo|termo aditivo)\b"),
    (TipoArquivo.EDITAL, r"\b(edital|pregao|rfp|rfq|convocacao|concorrencia|chamamento)\b"),
    (TipoArquivo.PLANILHA, r"\b(planilha|tabela)\b"),
    (TipoArquivo.ANEXO, r"\b(anexo|apendice|encarte)\b"),
)


def _normalizar(nome: str) -> str:
    """Minúsculas, sem acentos, com separadores trocados por espaço."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[_\-.()\[\]]+", " ", sem_acento.lower())


def sugerir_tipo(nome_arquivo: str, extensao: str) -> TipoArquivo:
    """Sugere o tipo do arquivo pelo nome; planilhas sem pista no nome viram `planilha`."""
    nome = _normalizar(nome_arquivo.rsplit(".", 1)[0])
    for tipo, padrao in _REGRAS:
        if re.search(padrao, nome):
            return tipo
    if extensao in {".xlsx", ".csv"}:
        return TipoArquivo.PLANILHA
    return TipoArquivo.OUTRO
