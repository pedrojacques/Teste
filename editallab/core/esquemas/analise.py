"""Schemas do resultado da análise de edital (Módulo A).

Princípios refletidos nos tipos:

- **Ausência é resposta válida**: todo campo simples é um `CampoExtraido` cujo `valor`
  pode ser `None` (não localizado). Nada é inferido.
- **Valores como estão escritos**: datas, prazos, bandas e valores são texto transcrito
  do documento, sem conversão nem cálculo.
- **Origem verificável**: toda informação carrega uma `Origem` com trecho literal.
"""

from enum import StrEnum

from pydantic import Field, model_validator

from editallab.core.esquemas.base import Esquema
from editallab.core.esquemas.enums import RegimeJuridico, StatusAderencia, StatusVerificacao

NAO_LOCALIZADO = "não localizado"


class Origem(Esquema):
    """De onde veio uma informação: arquivo, posição e trecho literal curto."""

    arquivo: str = Field(min_length=1)
    pagina: int | None = Field(default=None, ge=1)
    aba: str | None = None
    linha: int | None = Field(default=None, ge=1)
    item_clausula: str | None = None
    trecho_literal: str = Field(min_length=1, max_length=600)
    # Preenchido pelo código na conferência do trecho, nunca pelo modelo.
    verificacao: StatusVerificacao = StatusVerificacao.PENDENTE


class CampoExtraido(Esquema):
    """Campo simples. `valor` nulo significa que a informação não consta nos documentos."""

    valor: str | None = None
    origem: Origem | None = None
    # Origem do valor anterior, quando errata ou esclarecimento o substituiu.
    origem_substituida: Origem | None = None

    @model_validator(mode="after")
    def _valor_exige_origem(self) -> "CampoExtraido":
        """Um valor sem origem não é aceito: seria informação não rastreável."""
        if self.valor is not None and self.origem is None:
            raise ValueError("campo com valor precisa informar a origem")
        if self.valor is None and self.origem is not None:
            raise ValueError("campo não localizado não pode ter origem")
        return self

    @property
    def texto(self) -> str:
        """Valor para exibição, com a indicação padrão quando ausente."""
        return self.valor if self.valor is not None else NAO_LOCALIZADO


class ItemRastreavel(Esquema):
    """Base dos itens de lista: todos têm origem e, se alterados, a origem substituída."""

    origem: Origem
    origem_substituida: Origem | None = None


class DeteccaoRegime(Esquema):
    """Regime jurídico detectado no documento, para confirmação do usuário."""

    regime: RegimeJuridico = RegimeJuridico.INDETERMINADO
    fundamento: Origem | None = None

    @model_validator(mode="after")
    def _regime_exige_fundamento(self) -> "DeteccaoRegime":
        """Sem trecho que o fundamente, o regime só pode ser `indeterminado`."""
        if self.regime != RegimeJuridico.INDETERMINADO and self.fundamento is None:
            raise ValueError("regime detectado precisa do trecho que o fundamenta")
        return self


class Datas(Esquema):
    """Datas e prazos do processo, transcritos como aparecem no documento."""

    sessao: CampoExtraido = Field(default_factory=CampoExtraido)
    impugnacao: CampoExtraido = Field(default_factory=CampoExtraido)
    esclarecimentos: CampoExtraido = Field(default_factory=CampoExtraido)
    vigencia: CampoExtraido = Field(default_factory=CampoExtraido)


class Identificacao(Esquema):
    """Dados gerais da contratação."""

    orgao_entidade: CampoExtraido = Field(default_factory=CampoExtraido)
    modalidade: CampoExtraido = Field(default_factory=CampoExtraido)
    numero_processo: CampoExtraido = Field(default_factory=CampoExtraido)
    criterio_julgamento: CampoExtraido = Field(default_factory=CampoExtraido)
    valor_estimado: CampoExtraido = Field(default_factory=CampoExtraido)
    datas: Datas = Field(default_factory=Datas)


class ItemLote(ItemRastreavel):
    """Item de um lote."""

    identificador: str | None = None
    descricao: str = Field(min_length=1)
    quantidade: str | None = None
    unidade: str | None = None


class Lote(ItemRastreavel):
    """Lote ou grupo de itens. Objeto sem divisão em lotes vira um lote único."""

    identificador: str | None = None
    descricao: str = Field(min_length=1)
    itens: list[ItemLote] = Field(default_factory=list)


class CategoriaRequisito(StrEnum):
    """Natureza de um requisito técnico."""

    BANDA = "banda"
    SLA = "sla"
    DISPONIBILIDADE = "disponibilidade"
    LATENCIA = "latencia"
    PERDA_PACOTES = "perda_pacotes"
    PRAZO_INSTALACAO = "prazo_instalacao"
    PRAZO_REPARO = "prazo_reparo"
    REDUNDANCIA = "redundancia"
    EQUIPAMENTO = "equipamento"
    OUTRO = "outro"


class RequisitoTecnico(ItemRastreavel):
    """Requisito técnico exigido. `id` é atribuído pelo código na consolidação."""

    id: str | None = None
    categoria: CategoriaRequisito
    descricao: str = Field(min_length=1)
    valor: str | None = None


class Localidade(ItemRastreavel):
    """Ponto ou localidade a atender, normalmente vindo de tabela ou planilha."""

    identificador: str | None = None
    nome: str = Field(min_length=1)
    endereco: str | None = None
    municipio: str | None = None
    banda: str | None = None
    observacao: str | None = None


class TipoHabilitacao(StrEnum):
    """Natureza de uma exigência de habilitação técnica."""

    ATESTADO = "atestado"
    QUANTITATIVO_MINIMO = "quantitativo_minimo"
    CERTIFICACAO = "certificacao"
    VISITA_TECNICA = "visita_tecnica"
    OUTRO = "outro"


class RequisitoHabilitacao(ItemRastreavel):
    """Exigência de habilitação técnica."""

    tipo: TipoHabilitacao
    descricao: str = Field(min_length=1)


class TipoPenalidade(StrEnum):
    """Natureza de uma cláusula de sanção ou de nível de serviço."""

    PENALIDADE = "penalidade"
    GLOSA = "glosa"
    NIVEL_MINIMO_SERVICO = "nivel_minimo_servico"


class Penalidade(ItemRastreavel):
    """Penalidade, glosa ou nível mínimo de serviço."""

    tipo: TipoPenalidade
    descricao: str = Field(min_length=1)
    valor: str | None = None


class TipoPontoAtencao(StrEnum):
    """Por que um ponto merece atenção."""

    CLAUSULA_RESTRITIVA = "clausula_restritiva"
    INCONSISTENCIA = "inconsistencia"
    AMBIGUIDADE = "ambiguidade"
    PASSIVEL_ESCLARECIMENTO = "passivel_esclarecimento"
    PASSIVEL_IMPUGNACAO = "passivel_impugnacao"
    # Gerados na consolidação do processo:
    ALTERACAO = "alteracao"
    CONFLITO = "conflito"


class PontoAtencao(Esquema):
    """Ponto de atenção, com as origens que o sustentam."""

    tipo: TipoPontoAtencao
    descricao: str = Field(min_length=1)
    origens: list[Origem] = Field(min_length=1)


class Alteracao(ItemRastreavel):
    """Mudança trazida por errata ou esclarecimento sobre um item do texto original."""

    item_alterado: str = Field(min_length=1)
    descricao: str = Field(min_length=1)
    novo_valor: str | None = None


class AnaliseArquivo(Esquema):
    """Resultado da análise de um arquivo (ou de um bloco de páginas dele)."""

    regime: DeteccaoRegime = Field(default_factory=DeteccaoRegime)
    identificacao: Identificacao = Field(default_factory=Identificacao)
    objeto: CampoExtraido = Field(default_factory=CampoExtraido)
    lotes: list[Lote] = Field(default_factory=list)
    requisitos_tecnicos: list[RequisitoTecnico] = Field(default_factory=list)
    localidades: list[Localidade] = Field(default_factory=list)
    habilitacao_tecnica: list[RequisitoHabilitacao] = Field(default_factory=list)
    penalidades: list[Penalidade] = Field(default_factory=list)
    pontos_atencao: list[PontoAtencao] = Field(default_factory=list)
    # Preenchido apenas para erratas e esclarecimentos.
    alteracoes: list[Alteracao] = Field(default_factory=list)


class AnaliseConsolidada(AnaliseArquivo):
    """Análise do processo inteiro, já com a precedência de erratas aplicada."""


class ItemAderencia(Esquema):
    """Aderência de um requisito técnico ao catálogo."""

    requisito_id: str = Field(min_length=1)
    status: StatusAderencia
    item_catalogo_id: str | None = None
    justificativa: str = Field(min_length=1)

    @model_validator(mode="after")
    def _coerencia_com_catalogo(self) -> "ItemAderencia":
        """Sem item correspondente no catálogo, o único status possível é `nao_avaliado`."""
        if self.item_catalogo_id is None and self.status != StatusAderencia.NAO_AVALIADO:
            raise ValueError("sem item de catálogo correspondente, o status deve ser nao_avaliado")
        return self


class ResultadoAderencia(Esquema):
    """Aderência do processo ao portfólio."""

    itens: list[ItemAderencia] = Field(default_factory=list)
