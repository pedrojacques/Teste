"""Enumerações de domínio, definidas uma única vez para todo o projeto."""

from enum import StrEnum


class TipoArquivo(StrEnum):
    """Papel de um arquivo dentro do processo."""

    EDITAL = "edital"
    TERMO_REFERENCIA = "termo_referencia"
    ANEXO = "anexo"
    PLANILHA = "planilha"
    ERRATA = "errata"
    ESCLARECIMENTO = "esclarecimento"
    CONTRATO = "contrato"
    OUTRO = "outro"

    @property
    def prevalece_sobre_original(self) -> bool:
        """Indica se o tipo altera o texto original (errata e esclarecimento)."""
        return self in (TipoArquivo.ERRATA, TipoArquivo.ESCLARECIMENTO)


class RegimeJuridico(StrEnum):
    """Regime jurídico de um processo. Sempre detectado e confirmado, nunca presumido."""

    LEI_14133 = "lei_14133"
    LEI_13303 = "lei_13303"
    PRIVADO = "privado"
    INDETERMINADO = "indeterminado"


class MetodoExtracao(StrEnum):
    """Como o texto de uma página foi obtido."""

    TEXTO = "texto"
    OCR = "ocr"
    OCR_INDISPONIVEL = "ocr_indisponivel"


class TipoMarcador(StrEnum):
    """Unidade de referência de origem usada em um trecho extraído."""

    PAGINA = "pagina"
    BLOCO = "bloco"
    ABA = "aba"


class StatusVerificacao(StrEnum):
    """Resultado da conferência do trecho literal contra a página citada."""

    PENDENTE = "pendente"
    VERIFICADO = "verificado"
    NAO_VERIFICADO = "nao_verificado"


class StatusAderencia(StrEnum):
    """Aderência de um requisito do edital ao portfólio."""

    ATENDE = "atende"
    ATENDE_COM_RESSALVA = "atende_com_ressalva"
    NAO_ATENDE = "nao_atende"
    NAO_AVALIADO = "nao_avaliado"


class CategoriaItem(StrEnum):
    """Natureza de um item do catálogo técnico."""

    SERVICO = "servico"
    EQUIPAMENTO = "equipamento"


class PapelSecao(StrEnum):
    """Tratamento especial que o motor de geração dá a uma seção do perfil."""

    GERAL = "geral"
    # Recebe a referência ao ETP ou, na falta, marcador de preenchimento pelo órgão.
    FUNDAMENTACAO = "fundamentacao"
    # Sempre campo para preenchimento: o modelo nunca escreve valores.
    ESTIMATIVA_VALOR = "estimativa_valor"
    # Conteúdo que só o órgão ou cliente pode fornecer; sai como marcador.
    PREENCHIMENTO_ORGAO = "preenchimento_orgao"
