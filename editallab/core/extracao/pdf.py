"""Extração de texto e tabelas de PDF, página a página, com OCR como fallback."""

import logging
from collections.abc import Callable

import pymupdf

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroExtracao, OcrIndisponivel
from editallab.core.esquemas import MetodoExtracao
from editallab.core.extracao.modelos import PaginaExtraida
from editallab.core.extracao.ocr import ocr_pagina

_log = logging.getLogger(__name__)

FuncaoOcr = Callable[[pymupdf.Page, str], str]


def _texto_tabelas(pagina: pymupdf.Page) -> str:
    """Devolve as tabelas da página em linhas `célula | célula`, ou vazio se não houver."""
    try:
        tabelas = pagina.find_tables().tables
    except Exception:  # noqa: BLE001 - detecção de tabela é melhor esforço
        _log.warning("falha ao detectar tabelas na página %s", pagina.number + 1)
        return ""
    blocos: list[str] = []
    for indice, tabela in enumerate(tabelas, start=1):
        # O texto de cada célula é lido pelo retângulo da célula: `tabela.extract()`
        # cola palavras e embaralha pontuação em alguns PDFs.
        linhas = [
            " | ".join(
                " ".join(pagina.get_text("text", clip=pymupdf.Rect(celula)).split())
                if celula
                else ""
                for celula in linha.cells
            )
            for linha in tabela.rows
        ]
        linhas = [linha for linha in linhas if linha.replace("|", "").strip()]
        if linhas:
            blocos.append(f"(TABELA {indice})\n" + "\n".join(linhas))
    return "\n\n".join(blocos)


def extrair_pdf(
    conteudo: bytes, config: Configuracoes, ocr: FuncaoOcr = ocr_pagina
) -> list[PaginaExtraida]:
    """Extrai o texto de cada página do PDF.

    Página com texto nativo abaixo de `ocr_limiar_caracteres` é tratada como
    escaneada e passa por OCR. Sem Tesseract, a página fica vazia e marcada como
    `ocr_indisponivel`, para a interface avisar o usuário.
    """
    try:
        documento = pymupdf.open(stream=conteudo, filetype="pdf")
    except Exception as exc:  # noqa: BLE001 - PyMuPDF levanta tipos variados
        raise ErroExtracao("Não foi possível ler o PDF.", str(exc)) from exc
    paginas: list[PaginaExtraida] = []
    with documento:
        if documento.needs_pass:
            raise ErroExtracao("O PDF está protegido por senha e não pode ser lido.")
        for pagina in documento:
            numero = pagina.number + 1
            texto = pagina.get_text("text").strip()
            metodo = MetodoExtracao.TEXTO
            if len(texto) < max(config.ocr_limiar_caracteres, 1):
                try:
                    texto = ocr(pagina, config.ocr_idioma).strip()
                    metodo = MetodoExtracao.OCR
                except OcrIndisponivel:
                    metodo = MetodoExtracao.OCR_INDISPONIVEL
            else:
                tabelas = _texto_tabelas(pagina)
                if tabelas:
                    texto = f"{texto}\n\n{tabelas}"
            paginas.append(PaginaExtraida(numero=numero, texto=texto, metodo=metodo))
    return paginas
