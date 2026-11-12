"""Extração de texto com marcadores de origem. Use `preparar_paginas`."""

from editallab.core.extracao.marcadores import montar_texto_marcado
from editallab.core.extracao.modelos import PaginaMascarada
from editallab.core.extracao.pipeline import preparar_paginas

__all__ = ["PaginaMascarada", "montar_texto_marcado", "preparar_paginas"]
