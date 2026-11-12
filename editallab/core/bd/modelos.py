"""Modelos de persistência (SQLAlchemy ORM)."""

import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from editallab.core.esquemas import MetodoExtracao, RegimeJuridico, TipoArquivo, TipoMarcador


def _agora() -> dt.datetime:
    """Data e hora atuais em UTC."""
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    """Base declarativa de todos os modelos."""


class Processo(Base):
    """Conjunto de arquivos de uma mesma contratação."""

    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    # O regime é detectado na análise (Fase 3) e confirmado pelo usuário; começa vazio.
    regime_detectado: Mapped[str | None] = mapped_column(String(20), default=None)
    regime_trecho: Mapped[str | None] = mapped_column(Text, default=None)
    regime_confirmado: Mapped[str | None] = mapped_column(String(20), default=None)
    criado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_agora)

    arquivos: Mapped[list["Arquivo"]] = relationship(
        back_populates="processo", cascade="all, delete-orphan", order_by="Arquivo.id"
    )

    @property
    def regime(self) -> RegimeJuridico | None:
        """Regime confirmado pelo usuário, ou `None` enquanto não houver confirmação."""
        return RegimeJuridico(self.regime_confirmado) if self.regime_confirmado else None


class Arquivo(Base):
    """Arquivo de um processo. O original fica em disco, identificado pelo hash."""

    __tablename__ = "arquivos"
    __table_args__ = (UniqueConstraint("processo_id", "sha256", name="uq_arquivo_processo_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    processo_id: Mapped[int] = mapped_column(ForeignKey("processos.id", ondelete="CASCADE"))
    nome_original: Mapped[str] = mapped_column(String(200))
    extensao: Mapped[str] = mapped_column(String(10))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    tamanho: Mapped[int] = mapped_column(Integer)
    tipo: Mapped[str] = mapped_column(String(30))
    tipo_confirmado: Mapped[bool] = mapped_column(default=False)
    # Data do próprio documento, informada no upload; define a precedência entre erratas.
    data_documento: Mapped[dt.date | None] = mapped_column(Date, default=None)
    enviado_em: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    extraido_em: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    processo: Mapped[Processo] = relationship(back_populates="arquivos")
    paginas: Mapped[list["Pagina"]] = relationship(
        back_populates="arquivo", cascade="all, delete-orphan", order_by="Pagina.numero"
    )

    @property
    def tipo_arquivo(self) -> TipoArquivo:
        """Tipo do arquivo como enumeração."""
        return TipoArquivo(self.tipo)

    @property
    def ordem_precedencia(self) -> tuple[dt.date, dt.datetime, int]:
        """Chave de ordenação: data do documento e, no empate ou na falta, data de envio."""
        return (self.data_documento or self.enviado_em.date(), self.enviado_em, self.id or 0)


class Pagina(Base):
    """Texto extraído **e mascarado** de uma página, bloco ou aba de um arquivo."""

    __tablename__ = "paginas"
    __table_args__ = (UniqueConstraint("arquivo_id", "numero", name="uq_pagina_arquivo_numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    arquivo_id: Mapped[int] = mapped_column(ForeignKey("arquivos.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(Integer)
    aba: Mapped[str | None] = mapped_column(String(200), default=None)
    tipo_marcador: Mapped[str] = mapped_column(String(10), default=TipoMarcador.PAGINA.value)
    metodo: Mapped[str] = mapped_column(String(20), default=MetodoExtracao.TEXTO.value)
    texto: Mapped[str] = mapped_column(Text)

    arquivo: Mapped[Arquivo] = relationship(back_populates="paginas")
