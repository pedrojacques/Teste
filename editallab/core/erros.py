"""Exceções de domínio.

Toda exceção carrega uma `mensagem_usuario` segura para exibição. Detalhes técnicos
ficam em `detalhe` e vão somente para o log.
"""


class ErroEditalLab(Exception):
    """Base das exceções do EditalLab."""

    def __init__(self, mensagem_usuario: str, detalhe: str | None = None) -> None:
        # `str(exc)` devolve sempre a mensagem amigável: se uma exceção vazar para a
        # interface, não leva detalhe técnico junto. O detalhe é lido de `.detalhe`.
        super().__init__(mensagem_usuario)
        self.mensagem_usuario = mensagem_usuario
        self.detalhe = detalhe


class ErroValidacaoArquivo(ErroEditalLab):
    """Arquivo recusado na validação de upload (extensão, conteúdo, tamanho ou nome)."""


class ErroZipInseguro(ErroEditalLab):
    """ZIP recusado por inteiro por representar risco (zip slip, zip bomb, ZIP aninhado)."""


class ErroExtracao(ErroEditalLab):
    """Falha ao extrair texto de um arquivo já aceito."""


class OcrIndisponivel(ErroEditalLab):
    """O Tesseract (ou o idioma configurado) não está instalado nesta máquina."""
