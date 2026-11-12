"""Fixtures compartilhadas. Tudo roda em pasta temporária, sem rede e sem API."""

import io
import zipfile
from pathlib import Path

import pytest

from editallab.core.bd import aplicar_migracoes, criar_engine, criar_fabrica_sessoes
from editallab.core.config import Configuracoes

DIR_PROCESSO = Path(__file__).parent / "fixtures" / "processo_mpls"


@pytest.fixture
def config(tmp_path):
    return Configuracoes(_env_file=None, dir_dados=tmp_path / "dados")


@pytest.fixture
def sessao(config):
    engine = criar_engine(config)
    aplicar_migracoes(engine)
    with criar_fabrica_sessoes(engine)() as s:
        yield s
    engine.dispose()


@pytest.fixture
def arquivos_processo() -> list[tuple[str, bytes]]:
    """Os três arquivos do processo fictício, como `(nome, bytes)`."""
    return [(p.name, p.read_bytes()) for p in sorted(DIR_PROCESSO.iterdir())]


def montar_zip(membros: dict[str, bytes]) -> bytes:
    """Monta um ZIP em memória a partir de `{nome: conteúdo}`."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, dados in membros.items():
            zf.writestr(nome, dados)
    return buffer.getvalue()
