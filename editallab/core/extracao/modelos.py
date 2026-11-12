"""Estruturas de dados da extração de texto."""

from dataclasses import dataclass, field

from editallab.core.esquemas import MetodoExtracao, TipoMarcador


@dataclass
class PaginaExtraida:
    """Texto bruto de uma unidade do documento (página, bloco ou aba de planilha).

    Em planilhas, `linhas` guarda `(número da linha, texto da linha)` e `texto` fica
    vazio; o texto final com marcadores é montado depois do mascaramento.
    """

    numero: int
    texto: str = ""
    metodo: MetodoExtracao = MetodoExtracao.TEXTO
    tipo_marcador: TipoMarcador = TipoMarcador.PAGINA
    aba: str | None = None
    linhas: list[tuple[int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class PaginaMascarada:
    """Página pronta para gravação e envio ao modelo: texto já mascarado e neutralizado."""

    numero: int
    texto: str
    metodo: MetodoExtracao
    tipo_marcador: TipoMarcador
    aba: str | None = None
