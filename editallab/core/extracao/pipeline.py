"""Ponto único de extração: devolve somente texto já mascarado.

`preparar_paginas` é a única função que o restante do núcleo deve chamar para obter
texto de um arquivo. Ela garante a ordem extrair -> neutralizar marcadores -> mascarar,
de modo que texto não mascarado nunca chegue ao banco nem ao modelo.
"""

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroExtracao
from editallab.core.esquemas import TipoMarcador
from editallab.core.extracao.docx import extrair_docx
from editallab.core.extracao.marcadores import marcador_linha, neutralizar_marcadores
from editallab.core.extracao.modelos import PaginaExtraida, PaginaMascarada
from editallab.core.extracao.pdf import extrair_pdf
from editallab.core.extracao.planilha import extrair_csv, extrair_xlsx
from editallab.core.privacidade import mascarar

_EXTRATORES = {
    ".pdf": extrair_pdf,
    ".docx": extrair_docx,
    ".xlsx": extrair_xlsx,
    ".csv": extrair_csv,
}


def _proteger(texto: str) -> str:
    """Neutraliza marcadores forjados e mascara dados pessoais."""
    return mascarar(neutralizar_marcadores(texto)).texto


def _finalizar(pagina: PaginaExtraida) -> PaginaMascarada:
    """Converte uma página bruta na versão protegida, montando os marcadores de linha."""
    if pagina.tipo_marcador == TipoMarcador.ABA:
        aba = _proteger(pagina.aba or "")
        # Cada linha é mascarada isoladamente, antes de receber o marcador, para que
        # o marcador nunca seja confundido com dado do documento.
        texto = "\n".join(
            f"{marcador_linha(aba, numero)} {_proteger(linha)}" for numero, linha in pagina.linhas
        )
    else:
        aba = None
        texto = _proteger(pagina.texto)
    return PaginaMascarada(
        numero=pagina.numero,
        texto=texto,
        metodo=pagina.metodo,
        tipo_marcador=pagina.tipo_marcador,
        aba=aba,
    )


def preparar_paginas(
    conteudo: bytes, extensao: str, config: Configuracoes
) -> list[PaginaMascarada]:
    """Extrai o texto de um arquivo validado e devolve as páginas já mascaradas."""
    extrator = _EXTRATORES.get(extensao.lower())
    if extrator is None:
        raise ErroExtracao("Tipo de arquivo sem extrator disponível.", f"extensão {extensao!r}")
    return [_finalizar(pagina) for pagina in extrator(conteudo, config)]
