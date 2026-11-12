"""Marcadores de origem inseridos no texto extraído.

Formatos: `[[PAGINA n]]`, `[[BLOCO n]]` (DOCX sem quebras de página) e
`[[ABA "nome" LINHA n]]` (planilhas). Como o texto dos documentos não é confiável,
qualquer `[[` ou `]]` vindo do documento é neutralizado para não imitar um marcador.
"""

from collections.abc import Iterable

from editallab.core.esquemas import TipoMarcador
from editallab.core.extracao.modelos import PaginaMascarada


def neutralizar_marcadores(texto: str) -> str:
    """Quebra sequências `[[` e `]]` vindas do documento, que poderiam forjar marcadores."""
    return texto.replace("[[", "[ [").replace("]]", "] ]")


def marcador_pagina(numero: int, tipo: TipoMarcador = TipoMarcador.PAGINA) -> str:
    """Marcador de página ou de bloco."""
    rotulo = "BLOCO" if tipo == TipoMarcador.BLOCO else "PAGINA"
    return f"[[{rotulo} {numero}]]"


def marcador_linha(aba: str, linha: int) -> str:
    """Marcador de linha de planilha."""
    nome = aba.replace('"', "'").replace("[", "(").replace("]", ")")
    return f'[[ABA "{nome}" LINHA {linha}]]'


def montar_texto_marcado(paginas: Iterable[PaginaMascarada]) -> str:
    """Concatena as páginas de um arquivo, cada uma precedida do seu marcador.

    Abas de planilha já trazem o marcador em cada linha e são apenas concatenadas.
    """
    partes: list[str] = []
    for pagina in paginas:
        if pagina.tipo_marcador == TipoMarcador.ABA:
            partes.append(pagina.texto)
        else:
            partes.append(f"{marcador_pagina(pagina.numero, pagina.tipo_marcador)}\n{pagina.texto}")
    return "\n\n".join(partes)
