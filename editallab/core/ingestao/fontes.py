"""Fontes de documentos.

`FonteDocumentos` é a única porta de entrada de arquivos no núcleo. A v1 tem a fonte
de upload (arquivos avulsos e ZIP). Uma fonte Google Drive, por exemplo, entra depois
implementando o mesmo protocolo, sem alterar o restante do núcleo.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Protocol

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroValidacaoArquivo, ErroZipInseguro
from editallab.core.ingestao.zip_seguro import extrair_zip_seguro, tem_magic_zip


@dataclass(frozen=True)
class ItemFonte:
    """Um arquivo bruto entregue por uma fonte, ainda não validado."""

    nome_original: str
    conteudo: bytes


@dataclass(frozen=True)
class Rejeicao:
    """Arquivo recusado ou ignorado, com o motivo em linguagem para o usuário."""

    nome: str
    motivo: str


class FonteDocumentos(Protocol):
    """Contrato de qualquer origem de arquivos de um processo."""

    rejeicoes: list[Rejeicao]

    def itens(self) -> Iterator[ItemFonte]:
        """Entrega os arquivos brutos, um a um. Recusas ficam em `rejeicoes`."""
        ...


@dataclass
class FonteUpload:
    """Arquivos enviados pela interface: vários avulsos e/ou ZIP, que é aberto com segurança."""

    arquivos: list[tuple[str, bytes]]
    config: Configuracoes
    rejeicoes: list[Rejeicao] = field(default_factory=list)

    def itens(self) -> Iterator[ItemFonte]:
        """Entrega cada arquivo avulso e cada membro dos ZIPs enviados."""
        for nome, conteudo in self.arquivos:
            if PurePosixPath(nome.replace("\\", "/")).suffix.lower() != ".zip":
                yield ItemFonte(nome, conteudo)
                continue
            try:
                if not tem_magic_zip(conteudo):
                    raise ErroValidacaoArquivo("O conteúdo do arquivo não corresponde a um ZIP.")
                if len(conteudo) > config_limite_zip(self.config):
                    raise ErroValidacaoArquivo("O ZIP excede o tamanho máximo permitido.")
                lido = extrair_zip_seguro(conteudo, self.config)
            except (ErroZipInseguro, ErroValidacaoArquivo) as exc:
                self.rejeicoes.append(Rejeicao(nome, exc.mensagem_usuario))
                continue
            self.rejeicoes.extend(Rejeicao(n, motivo) for n, motivo in lido.ignorados)
            for nome_membro, dados in lido.membros:
                yield ItemFonte(nome_membro, dados)


def config_limite_zip(config: Configuracoes) -> int:
    """Tamanho máximo do próprio ZIP compactado (igual ao limite descompactado)."""
    return config.zip_max_descompactado
