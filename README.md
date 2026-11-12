# EditalLab

App interno para análise de editais e geração de Termos de Referência com apoio de IA.

Em construção, por fases. O plano, as decisões de arquitetura e as regras de segurança estão em [`CLAUDE.md`](CLAUDE.md). O README completo (instalação do Tesseract, uso da interface e roteiro de validação no Google Docs) entra na Fase 5.

## Desenvolvimento

```bash
uv sync                    # instala dependências (Python 3.12)
cp .env.example .env       # preencha os valores; o .env não é versionado
uv run pytest              # testes com API simulada, sem custo
uv run ruff check . && uv run ruff format --check .
```

Os dados locais (banco SQLite e arquivos originais) ficam em `dados/`, fora do versionamento.
