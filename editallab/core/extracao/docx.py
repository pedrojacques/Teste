"""Extração de texto de DOCX, preservando a ordem de parágrafos e tabelas.

DOCX não tem página física confiável. Quando o arquivo traz quebras de página
(explícitas ou as registradas pelo Word na última renderização), elas delimitam
as páginas. Sem nenhuma quebra, o texto é dividido em blocos de tamanho
aproximadamente fixo, e a origem é registrada como `bloco`.
"""

import io

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroExtracao
from editallab.core.esquemas import TipoMarcador
from editallab.core.extracao.modelos import PaginaExtraida


def _paragrafo_com_quebras(paragrafo: Paragraph) -> list[str]:
    """Divide o texto do parágrafo nos pontos de quebra de página."""
    partes = [""]
    for no in paragrafo._p.iter():
        if no.tag == qn("w:t"):
            partes[-1] += no.text or ""
        elif no.tag == qn("w:tab"):
            partes[-1] += "\t"
        elif no.tag == qn("w:lastRenderedPageBreak"):
            partes.append("")
        elif no.tag == qn("w:br"):
            if no.get(qn("w:type")) == "page":
                partes.append("")
            else:
                partes[-1] += "\n"
    return partes


def _texto_tabela(tabela: Table) -> str:
    """Tabela em linhas `célula | célula`, sem repetir células mescladas."""
    linhas: list[str] = []
    for linha in tabela.rows:
        celulas: list[str] = []
        vistos: set[int] = set()
        for celula in linha.cells:
            if id(celula._tc) in vistos:
                continue
            vistos.add(id(celula._tc))
            celulas.append(" ".join(celula.text.split()))
        if any(celulas):
            linhas.append(" | ".join(celulas))
    return "\n".join(linhas)


def extrair_docx(conteudo: bytes, config: Configuracoes) -> list[PaginaExtraida]:
    """Extrai o texto de um DOCX em páginas (se houver quebras) ou em blocos."""
    try:
        documento = Document(io.BytesIO(conteudo))
    except Exception as exc:  # noqa: BLE001 - python-docx levanta tipos variados
        raise ErroExtracao("Não foi possível ler o DOCX.", str(exc)) from exc

    # Cada página é uma lista de trechos (parágrafos ou tabelas).
    paginas: list[list[str]] = [[]]
    for item in documento.iter_inner_content():
        if isinstance(item, Table):
            texto = _texto_tabela(item)
            if texto:
                paginas[-1].append(texto)
            continue
        partes = _paragrafo_com_quebras(item)
        for indice, parte in enumerate(partes):
            if indice > 0:
                paginas.append([])
            if parte.strip():
                paginas[-1].append(parte.strip())

    if len(paginas) > 1:
        return [
            PaginaExtraida(numero=n, texto="\n".join(trechos))
            for n, trechos in enumerate(paginas, start=1)
        ]

    # Sem quebras: agrupa trechos inteiros em blocos de tamanho aproximado.
    blocos: list[list[str]] = [[]]
    tamanho = 0
    for trecho in paginas[0]:
        if blocos[-1] and tamanho + len(trecho) > config.docx_caracteres_por_bloco:
            blocos.append([])
            tamanho = 0
        blocos[-1].append(trecho)
        tamanho += len(trecho)
    return [
        PaginaExtraida(numero=n, texto="\n".join(trechos), tipo_marcador=TipoMarcador.BLOCO)
        for n, trechos in enumerate(blocos, start=1)
    ]
