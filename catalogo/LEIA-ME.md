# Catálogo técnico

Um arquivo YAML por item. Os quatro itens iniciais são **fictícios** e servem de modelo.

Cada item tem duas camadas:

- `neutra`: o que pode aparecer em documentos para clientes e órgãos. Requisitos mínimos funcionais, SLAs praticáveis e textos-padrão, **sem marca, modelo ou nome comercial**.
- `interna`: fabricante, modelo, part numbers e outros termos que identificam o produto. Usada só na análise de aderência e na checagem de neutralidade. Nunca vai para a geração de minutas.

O carregamento recusa o item se algum termo da camada interna aparecer no `nome` ou na camada `neutra`.

Campos: veja `editallab/core/esquemas/catalogo.py`.
