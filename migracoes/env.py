"""Ambiente do Alembic. Usa a conexão injetada pelo app ou, na CLI, as configurações."""

from alembic import context

from editallab.core.bd import Base, criar_engine
from editallab.core.config import Configuracoes

target_metadata = Base.metadata


def _executar(conexao) -> None:
    context.configure(connection=conexao, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


conexao_injetada = context.config.attributes.get("connection")
if conexao_injetada is not None:
    _executar(conexao_injetada)
else:
    with criar_engine(Configuracoes()).connect() as conexao:
        _executar(conexao)
        conexao.commit()
