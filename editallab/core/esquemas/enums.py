"""Enumerações de domínio, definidas uma única vez para todo o projeto."""

from enum import StrEnum


class TipoArquivo(StrEnum):
    """Papel de um arquivo dentro do processo."""

    EDITAL = "edital"
    TERMO_REFERENCIA = "termo_referencia"
    ANEXO = "anexo"
    PLANILHA = "planilha"
    ERRATA = "errata"
    ESCLARECIMENTO = "esclarecimento"
    CONTRATO = "contrato"
    OUTRO = "outro"

    @property
    def prevalece_sobre_original(self) -> bool:
        """Indica se o tipo altera o texto original (errata e esclarecimento)."""
        return self in (TipoArquivo.ERRATA, TipoArquivo.ESCLARECIMENTO)


class RegimeJuridico(StrEnum):
    """Regime jurídico de um processo. Sempre detectado e confirmado, nunca presumido."""

    LEI_14133 = "lei_14133"
    LEI_13303 = "lei_13303"
    PRIVADO = "privado"
    INDETERMINADO = "indeterminado"


class MetodoExtracao(StrEnum):
    """Como o texto de uma página foi obtido."""

    TEXTO = "texto"
    OCR = "ocr"
    OCR_INDISPONIVEL = "ocr_indisponivel"


class TipoMarcador(StrEnum):
    """Unidade de referência de origem usada em um trecho extraído."""

    PAGINA = "pagina"
    BLOCO = "bloco"
    ABA = "aba"
