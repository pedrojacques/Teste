"""OCR com Tesseract, usado apenas como fallback para páginas de PDF sem texto."""

import io
import logging

import pymupdf
import pytesseract
from PIL import Image

from editallab.core.erros import OcrIndisponivel

_log = logging.getLogger(__name__)
_DPI = 300


def ocr_disponivel(idioma: str) -> bool:
    """Indica se o Tesseract e o idioma pedido estão instalados."""
    try:
        return idioma in pytesseract.get_languages(config="")
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, OSError):
        return False


def ocr_pagina(pagina: pymupdf.Page, idioma: str) -> str:
    """Renderiza a página como imagem e devolve o texto reconhecido.

    Levanta `OcrIndisponivel` se o Tesseract ou o idioma não estiverem instalados.
    """
    imagem = pagina.get_pixmap(dpi=_DPI, alpha=False)
    try:
        with Image.open(io.BytesIO(imagem.tobytes("png"))) as img:
            return pytesseract.image_to_string(img, lang=idioma)
    except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError, OSError) as exc:
        _log.warning("OCR indisponível: %s", type(exc).__name__)
        raise OcrIndisponivel(
            "Este PDF parece escaneado e o OCR (Tesseract) não está instalado ou configurado.",
            str(exc),
        ) from exc
