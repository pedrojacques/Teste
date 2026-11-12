"""Serviço de processos: criação, entrada de arquivos, confirmação e extração.

É a fachada que a interface usa na Fase 1. Todas as funções recebem a sessão de
banco e as configurações por parâmetro.
"""

import datetime as dt
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from editallab.core.bd import Arquivo, Pagina, Processo
from editallab.core.config import Configuracoes
from editallab.core.erros import ErroEditalLab, ErroValidacaoArquivo
from editallab.core.esquemas import MetodoExtracao, TipoArquivo, TipoMarcador
from editallab.core.extracao import montar_texto_marcado, preparar_paginas
from editallab.core.extracao.modelos import PaginaMascarada
from editallab.core.ingestao import FonteDocumentos, Rejeicao, sugerir_tipo, validar_arquivo
from editallab.core.ingestao.armazenamento import gravar_original, ler_original

_log = logging.getLogger(__name__)


@dataclass
class ResultadoIngestao:
    """O que aconteceu com cada arquivo de uma entrada."""

    aceitos: list[Arquivo] = field(default_factory=list)
    duplicados: list[str] = field(default_factory=list)
    rejeitados: list[Rejeicao] = field(default_factory=list)


def criar_processo(sessao: Session, nome: str) -> Processo:
    """Cria um processo vazio. O regime jurídico fica indefinido até ser confirmado."""
    nome = " ".join(nome.split())[:200]
    if not nome:
        raise ErroEditalLab("Informe um nome para o processo.")
    processo = Processo(nome=nome)
    sessao.add(processo)
    sessao.flush()
    return processo


def adicionar_arquivos(
    sessao: Session, processo: Processo, fonte: FonteDocumentos, config: Configuracoes
) -> ResultadoIngestao:
    """Valida, armazena e registra os arquivos de uma fonte no processo.

    Arquivo cujo hash já existe no processo é ignorado. O tipo é apenas sugerido
    aqui; use `confirmar_arquivo` para registrar a confirmação do usuário. Pode ser
    chamada várias vezes ao longo do prazo (erratas e esclarecimentos chegam depois).
    """
    resultado = ResultadoIngestao()
    existentes = set(
        sessao.scalars(select(Arquivo.sha256).where(Arquivo.processo_id == processo.id))
    )
    for item in fonte.itens():
        try:
            validado = validar_arquivo(item.nome_original, item.conteudo, config)
        except ErroValidacaoArquivo as exc:
            _log.info("arquivo recusado: %s", exc.detalhe or exc.mensagem_usuario)
            resultado.rejeitados.append(Rejeicao(item.nome_original, exc.mensagem_usuario))
            continue
        if validado.sha256 in existentes:
            resultado.duplicados.append(validado.nome_sanitizado)
            continue
        gravar_original(validado.conteudo, validado.sha256, config)
        arquivo = Arquivo(
            processo=processo,
            nome_original=validado.nome_sanitizado,
            extensao=validado.extensao,
            sha256=validado.sha256,
            tamanho=validado.tamanho,
            tipo=sugerir_tipo(validado.nome_sanitizado, validado.extensao).value,
        )
        sessao.add(arquivo)
        existentes.add(validado.sha256)
        resultado.aceitos.append(arquivo)
    resultado.rejeitados.extend(fonte.rejeicoes)
    sessao.flush()
    return resultado


def confirmar_arquivo(
    sessao: Session, arquivo: Arquivo, tipo: TipoArquivo, data_documento: dt.date | None = None
) -> Arquivo:
    """Registra o tipo confirmado pelo usuário e a data do documento (para a precedência)."""
    arquivo.tipo = TipoArquivo(tipo).value
    arquivo.tipo_confirmado = True
    arquivo.data_documento = data_documento
    sessao.flush()
    return arquivo


def extrair_arquivo(sessao: Session, arquivo: Arquivo, config: Configuracoes) -> list[Pagina]:
    """Extrai, mascara e grava o texto de um arquivo. Substitui extração anterior."""
    conteudo = ler_original(arquivo.sha256, config)
    paginas = preparar_paginas(conteudo, arquivo.extensao, config)
    # Remove a extração anterior antes de inserir a nova (restrição de unicidade).
    arquivo.paginas.clear()
    sessao.flush()
    arquivo.paginas = [
        Pagina(
            numero=p.numero,
            aba=p.aba,
            tipo_marcador=p.tipo_marcador.value,
            metodo=p.metodo.value,
            texto=p.texto,
        )
        for p in paginas
    ]
    arquivo.extraido_em = dt.datetime.now(dt.UTC)
    sessao.flush()
    return arquivo.paginas


def extrair_pendentes(
    sessao: Session, processo: Processo, config: Configuracoes
) -> tuple[list[Arquivo], list[Rejeicao]]:
    """Extrai apenas os arquivos do processo que ainda não foram extraídos.

    Devolve os arquivos extraídos e as falhas (com mensagem amigável). Uma falha em
    um arquivo não impede a extração dos demais.
    """
    extraidos: list[Arquivo] = []
    falhas: list[Rejeicao] = []
    for arquivo in processo.arquivos:
        if arquivo.extraido_em is not None:
            continue
        try:
            extrair_arquivo(sessao, arquivo, config)
            extraidos.append(arquivo)
        except ErroEditalLab as exc:
            _log.warning("falha na extração do arquivo %s: %s", arquivo.sha256[:12], exc.detalhe)
            falhas.append(Rejeicao(arquivo.nome_original, exc.mensagem_usuario))
    return extraidos, falhas


def ordenar_por_precedencia(arquivos: list[Arquivo]) -> list[Arquivo]:
    """Ordena do mais antigo ao mais recente; o último prevalece na consolidação.

    Documentos originais vêm antes de erratas e esclarecimentos; entre estes, vale a
    data do documento e, no empate, a data de envio.
    """
    return sorted(
        arquivos, key=lambda a: (a.tipo_arquivo.prevalece_sobre_original, a.ordem_precedencia)
    )


def texto_marcado(arquivo: Arquivo) -> str:
    """Texto mascarado do arquivo com marcadores de origem, como será enviado ao modelo."""
    return montar_texto_marcado(
        PaginaMascarada(
            numero=p.numero,
            texto=p.texto,
            metodo=MetodoExtracao(p.metodo),
            tipo_marcador=TipoMarcador(p.tipo_marcador),
            aba=p.aba,
        )
        for p in arquivo.paginas
    )
