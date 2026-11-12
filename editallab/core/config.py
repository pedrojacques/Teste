"""Configurações do EditalLab, lidas de variáveis de ambiente e do arquivo `.env`."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
"""Raiz do repositório, usada para localizar as migrações do banco."""

_MB = 1024 * 1024


class Configuracoes(BaseSettings):
    """Parâmetros de execução. Cada campo corresponde a `EDITALLAB_<NOME>` no ambiente."""

    model_config = SettingsConfigDict(
        env_prefix="EDITALLAB_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    dir_dados: Path = Path("dados")
    dir_catalogo: Path = RAIZ_PROJETO / "catalogo"
    dir_perfis: Path = RAIZ_PROJETO / "perfis"
    max_tamanho_arquivo_mb: int = Field(default=50, gt=0)
    zip_max_descompactado_mb: int = Field(default=200, gt=0)
    zip_max_arquivos: int = Field(default=200, gt=0)
    ocr_idioma: str = "por"
    ocr_limiar_caracteres: int = Field(default=20, ge=0)
    planilha_max_linhas_por_aba: int = Field(default=20000, gt=0)
    docx_caracteres_por_bloco: int = Field(default=3000, gt=0)

    @property
    def max_tamanho_arquivo(self) -> int:
        """Tamanho máximo de um arquivo, em bytes."""
        return self.max_tamanho_arquivo_mb * _MB

    @property
    def zip_max_descompactado(self) -> int:
        """Tamanho máximo do conteúdo descompactado de um ZIP, em bytes."""
        return self.zip_max_descompactado_mb * _MB

    @property
    def dir_originais(self) -> Path:
        """Pasta onde ficam os arquivos originais, nomeados pelo hash."""
        return self.dir_dados / "originais"

    @property
    def url_banco(self) -> str:
        """URL SQLAlchemy do banco SQLite local."""
        return f"sqlite:///{(self.dir_dados / 'editallab.db').as_posix()}"
