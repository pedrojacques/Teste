"""Criação do banco, aplicação de migrações e fábrica de sessões."""

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from editallab.core.config import RAIZ_PROJETO, Configuracoes


def criar_engine(config: Configuracoes) -> Engine:
    """Cria o engine SQLite do projeto, com chaves estrangeiras ativadas."""
    config.dir_dados.mkdir(parents=True, exist_ok=True)
    engine = create_engine(config.url_banco)

    @event.listens_for(engine, "connect")
    def _ativar_fk(conexao, _registro) -> None:  # noqa: ANN001 - assinatura do SQLAlchemy
        conexao.execute("PRAGMA foreign_keys=ON")

    return engine


def aplicar_migracoes(engine: Engine) -> None:
    """Leva o schema do banco à versão mais recente (Alembic `upgrade head`)."""
    cfg = Config()
    cfg.set_main_option("script_location", str(RAIZ_PROJETO / "migracoes"))
    with engine.begin() as conexao:
        cfg.attributes["connection"] = conexao
        command.upgrade(cfg, "head")


def criar_fabrica_sessoes(engine: Engine) -> sessionmaker[Session]:
    """Devolve a fábrica de sessões ligada ao engine."""
    return sessionmaker(engine, expire_on_commit=False)
