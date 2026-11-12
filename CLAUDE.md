# EditalLab

App interno para (A) analisar editais e documentos equivalentes e (B) gerar minutas de Termo de Referência e especificações técnicas, apoiado em (C) um catálogo técnico de serviços e equipamentos. Uso individual, local, por um arquiteto de soluções de uma empresa de IaaS com datacenter próprio em Joinville (DC JVE), atuante em conectividade (MPLS, backbone, links dedicados, internet), hospedagem e serviços de datacenter.

Idioma do projeto: português do Brasil em respostas, comentários, docstrings, documentação, mensagens de commit e nomes de domínio no código (ex.: `Processo`, `Arquivo`, `Analise`). Palavras reservadas e APIs de bibliotecas ficam como são.

## Estado atual

Fase 1 concluída, aguardando validação. Atualize esta seção ao fim de cada fase.

| Fase | Entrega | Estado |
|------|---------|--------|
| 0 | Planejamento e este `CLAUDE.md` | aprovada |
| 1 | Estrutura, configuração, modelo de processo e arquivos, ingestão (upload múltiplo e ZIP seguro), extração com marcadores, planilhas, mascaramento, testes | aguardando validação |
| 2 | Catálogo em duas camadas (Módulo C), perfis de documento, schemas Pydantic | pendente |
| 3 | Análise de edital (Módulo A): regime, análise em etapas, verificação de origem, cache, exportação | pendente |
| 4 | Geração de TR (Módulo B): perfis, espelhamento, ETP, neutralidade, template DOCX | pendente |
| 5 | Interface Streamlit e README final | pendente |

## Como trabalhar neste repositório

- Ao fim de cada fase: rodar testes e lint, resumir o que foi feito e **parar para validação do usuário** antes de seguir.
- Commits pequenos, em Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`).
- Discordou de uma escolha de stack ou de arquitetura registrada aqui? Justifique e peça aprovação antes de mudar.
- Não criar código de fase futura "para adiantar".

### Comandos

```bash
uv sync                               # instala dependências (Python 3.12)
uv run pytest                         # testes padrão (API simulada, sem custo)
uv run pytest -m integracao           # testes com a API real (exigem ANTHROPIC_API_KEY)
uv run ruff check . && uv run ruff format --check .
uv run streamlit run editallab/ui/app.py
uv run python scripts/gerar_fixtures.py   # recria o processo fictício de teste
```

`pytest` é configurado com `addopts = -m "not integracao and not ocr"`. O marcador `ocr` cobre testes que dependem do binário Tesseract e são pulados se ele não estiver instalado.

## Conceitos de domínio

### Processo

Unidade de trabalho: o conjunto de arquivos de uma mesma contratação (edital, TR, anexos, planilhas, erratas, esclarecimentos, contrato vigente).

- Cada arquivo tem hash SHA-256 e um **tipo**: `edital`, `termo_referencia`, `anexo`, `planilha`, `errata`, `esclarecimento`, `contrato`, `outro`. O tipo é sugerido pelo nome do arquivo e confirmado pelo usuário no upload.
- Arquivos podem entrar depois no mesmo processo. Só o arquivo novo é extraído e analisado; em seguida a consolidação do processo é refeita.
- **Precedência**: errata e esclarecimento prevalecem sobre o texto original. Entre várias erratas/esclarecimentos, vale a ordem de precedência do arquivo (campo `ordem_precedencia`, derivado da data do documento informada no upload, com a data de upload como desempate). A análise consolidada registra de qual arquivo veio cada valor e lista como ponto de atenção tudo o que foi alterado.

### Regime jurídico

Valores: `lei_14133` (administração direta, autárquica e fundacional), `lei_13303` (empresas públicas e sociedades de economia mista, com regulamento interno próprio), `privado`, e `indeterminado` (somente na detecção).

- O regime é **dado detectado e confirmado**, nunca premissa. O processo guarda `regime_detectado` (com o trecho que o fundamenta) e `regime_confirmado` (definido pelo usuário).
- Nenhum prompt presume regime nem cita artigo de lei como premissa. O que depender de regime vem do perfil de documento ou do `regime_confirmado`.
- Nenhum `if regime == ...` espalhado no código: o comportamento por regime mora nos perfis YAML.

### Módulos

- **A, Análise**: extração estruturada com origem verificável, pontos de atenção e aderência ao portfólio.
- **B, Geração**: minuta em DOCX a partir de um perfil de documento, persistida por seção.
- **C, Catálogo**: YAML em `catalogo/`, cada item com camada `neutra` e camada `interna`.

Fora do escopo da v1 (mas a arquitetura não pode impedir): habilitação jurídica/fiscal completa, precificação, integração com PNCP/Compras.gov, integração com Google Drive, multiusuário, autenticação corporativa.

## Stack

- Python 3.12, gerenciado com `uv`.
- Núcleo: pacote `editallab/core`, **sem nenhum import de Streamlit**. A UI só chama funções do núcleo.
- UI v1: Streamlit, somente em `localhost`.
- Extração: PyMuPDF (texto e tabelas de PDF), `python-docx`, `openpyxl`, módulo `csv`; OCR com Tesseract (`por`) via `pytesseract`.
- LLM: SDK oficial `anthropic`; modelo vindo de `ANTHROPIC_MODEL`.
- Persistência: SQLite com SQLAlchemy 2.x (ORM), migrações com Alembic.
- Documentos: `python-docx` com template próprio em `templates/`.
- Validação: Pydantic v2. Configuração: `pydantic-settings`.
- Testes: `pytest`. Lint e formatação: `ruff`.

## Estrutura de pastas

```
.
├── CLAUDE.md
├── README.md
├── pyproject.toml / uv.lock
├── .env.example                # nomes das variáveis, sem valores reais
├── .gitignore                  # inclui .env e dados/
├── .streamlit/config.toml      # address = "localhost", limites de upload, XSRF ligado
├── alembic.ini / migracoes/
├── catalogo/                   # YAML dos itens (Módulo C), versionado
├── perfis/                     # YAML dos perfis de documento, versionado
├── templates/                  # template DOCX base
├── scripts/                    # gerar_fixtures.py, gerar_template.py
├── dados/                      # NÃO versionado: banco SQLite, originais, exportações
├── editallab/
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings), limites, caminhos
│   │   ├── erros.py            # exceções de domínio com mensagem amigável
│   │   ├── logs.py
│   │   ├── processos.py        # fachada de serviço do processo
│   │   ├── bd/                 # modelos SQLAlchemy, sessão, repositórios
│   │   ├── esquemas/           # schemas Pydantic (análise, minuta, catálogo, perfil)
│   │   ├── ingestao/           # fontes.py (interface), validacao.py, zip_seguro.py,
│   │   │                       # armazenamento.py, tipos.py (sugestão de tipo)
│   │   ├── extracao/           # pdf.py, docx.py, planilha.py, ocr.py, marcadores.py
│   │   ├── privacidade/        # mascaramento.py
│   │   ├── llm/                # cliente.py (interface + Anthropic + simulado),
│   │   │                       # prompts.py (carregador), cache.py
│   │   ├── catalogo/           # carregamento, visão neutra, visão completa
│   │   ├── analise/            # por_arquivo.py, consolidacao.py, verificacao.py,
│   │   │                       # aderencia.py, exportacao.py
│   │   └── geracao/            # perfis.py, espelhamento.py, secoes.py,
│   │                           # neutralidade.py, renderizacao_docx.py
│   ├── prompts/                # um arquivo por prompt, com id e versão
│   └── ui/                     # Streamlit (app.py e páginas)
└── tests/
    ├── fixtures/               # processo fictício MPLS (PDF, XLSX, errata PDF)
    ├── unidade/
    └── integracao/             # API real, marcador `integracao`
```

## Decisões de arquitetura

### Ingestão

- `FonteDocumentos` (Protocol) é a única porta de entrada de arquivos no núcleo: entrega itens `(nome_original, fluxo_de_bytes)`. Implementações da v1: upload múltiplo e ZIP. Uma fonte Google Drive entra depois implementando a mesma interface, sem mexer no núcleo.
- Todo arquivo, de qualquer fonte, passa pelo mesmo funil: sanitização do nome, whitelist de extensão, magic bytes, limite de tamanho, hash SHA-256, gravação em `dados/originais/<hash>` (nome em disco é o hash, nunca o nome original).
- Arquivo com hash já presente no processo é ignorado (idempotência).

### Extração e marcadores

- O texto é extraído e gravado **por página** (tabela `paginas`: arquivo, número, aba, texto mascarado, método `texto` ou `ocr`). Para planilhas, a "página" é a aba e cada linha leva seu número.
- Marcadores no texto enviado ao modelo: `[[PAGINA n]]` para PDF/DOCX; `[[BLOCO n]]` para DOCX sem quebras de página; `[[ABA "nome" LINHA n]]` para planilhas. Qualquer `[[` ou `]]` vindo do documento é neutralizado. DOCX não tem página física confiável: usa-se quebra de página explícita quando houver e, na falta, numeração por bloco, registrada como tal na origem.
- OCR só como fallback, por página, quando o texto nativo vier vazio ou abaixo de um limiar de caracteres.
- Tabelas de PDF são extraídas com `page.find_tables()` e anexadas ao texto da página em formato linha a linha.

### Mascaramento (LGPD)

- Ordem obrigatória: extrair -> **mascarar** -> gravar no banco -> enviar à API. Não existe caminho de código que grave ou envie texto não mascarado. O original fica apenas em `dados/originais/`.
- Mascarados por regex: CPF, RG, e-mail, telefone, dados bancários. Substituição por rótulo fixo (`[CPF]`, `[RG]`, `[EMAIL]`, `[TELEFONE]`, `[DADOS_BANCARIOS]`).
- **Não** mascarados: CNPJ e nomes de pessoas.
- Padrões conservadores para não destruir dado técnico: CPF no formato `000.000.000-00` ou precedido da palavra "CPF" é sempre mascarado, e onze dígitos corridos só com dígitos verificadores válidos; RG e dados bancários exigem palavra de contexto próxima ("RG", "agência", "conta", "PIX"); telefone exige formato com DDD. A regra de CNPJ é avaliada antes da de CPF.
- A verificação de trecho literal roda contra o mesmo texto mascarado enviado ao modelo.

### LLM

- `ClienteLLM` é uma interface com duas implementações: Anthropic (real) e simulada (testes). O núcleo recebe o cliente por injeção de dependência.
- Prompts ficam em `editallab/prompts/`, um arquivo por prompt, com cabeçalho contendo `id` e `versao`. Nunca embutidos no código. Mudou o texto do prompt, muda a `versao`.
- Texto de documentos é **dado não confiável**: vai delimitado por tags (ex.: `<documento arquivo="..." tipo="...">`), com instrução explícita de nunca seguir comandos contidos nele. Sequências que imitem as tags delimitadoras são neutralizadas antes do envio.
- Toda resposta é validada contra schema Pydantic. Falha de validação gera nova tentativa limitada e, persistindo, erro amigável; nunca se grava resposta fora do schema.
- Ao implementar chamadas (Fase 3), consultar a documentação atual do SDK para saída estruturada, cache de prompt e limites, em vez de confiar em memória.

### Análise (Módulo A)

Pipeline em três etapas, cada uma com cache próprio:

1. **Por arquivo** (ou por bloco de páginas, se o arquivo não couber em uma chamada): extração estruturada com origem. Chave de cache: hash do arquivo + bloco + versão do prompt + modelo + versão do schema.
2. **Consolidação do processo**: elimina duplicidades, aplica a precedência, sinaliza conflitos e alterações como pontos de atenção. A precedência é aplicada em código sempre que possível; o modelo é usado para deduplicar e redigir. Chave: hashes das análises por arquivo + versão do prompt + modelo.
3. **Aderência ao portfólio**: compara requisitos consolidados com o catálogo (duas camadas). Chave: hash da consolidação + hash do catálogo + versão do prompt + modelo. Sem item correspondente no catálogo, o resultado é `nao_avaliado`.

Regras invariáveis:

- **Ausência é resposta válida**: campo não localizado volta `null` com indicação "não localizado". Nunca inferir nem completar com conhecimento geral. Prazos e regras são transcritos como estão no documento, sem cálculo a partir da lei.
- **Origem verificável**: toda informação extraída carrega `arquivo`, `pagina` (ou aba e linha), `item_clausula` e `trecho_literal` curto. `verificacao.py` confere se o trecho existe na página citada, normalizando espaços, quebras de linha e hifenização de fim de linha. O que não conferir fica `nao_verificado` e aparece destacado na UI e nas exportações.
- Cada análise registra versão do prompt, modelo e hashes dos arquivos.
- Exportação em DOCX e Markdown.

### Catálogo (Módulo C)

- Um YAML por item em `catalogo/`, validado por schema Pydantic no carregamento.
- Camada `neutra`: requisitos mínimos funcionais, SLAs praticáveis, textos-padrão de especificação, sem marca nem modelo. Camada `interna`: fabricante, modelo, part number e demais dados internos.
- O núcleo expõe duas funções distintas: visão completa (Módulo A) e visão neutra (Módulo B). A visão neutra devolve um tipo Pydantic que **não possui** os campos internos, de modo que o vazamento seja impossível por construção.
- **Teste obrigatório**: nenhum valor da camada interna aparece em nenhum prompt montado pelo Módulo B.
- Itens iniciais são fictícios.

### Geração (Módulo B)

- **Perfil de documento** (YAML em `perfis/`): seções (`id`, `titulo`, `ordem`, `instrucao_redacao`), campos de cabeçalho, texto do aviso, `usa_etp`, `exige_neutralidade`. Um único motor para todos os perfis.
- Perfis iniciais: `lei_14133` (dez seções, `usa_etp` e `exige_neutralidade` ligados), `estatal_13303` (base genérica, `exige_neutralidade` ligado, `usa_etp` configurável), `privado` (sem seções próprias de direito público, `usa_etp` desligado).
- A referência legal de cada estrutura mora no YAML do perfil, não nos prompts.
- **Espelhamento**: extrai títulos e ordem das seções do documento atual do cliente e propõe um perfil editável antes da geração.
- **Persistência por seção**: a minuta é um conjunto de seções estruturadas no banco, cada uma com versão do prompt e modelo. O DOCX é sempre renderizado a partir delas. Regerar uma seção não toca nas demais.
- **ETP**: se a referência ficar vazia, a fundamentação sai com marcador de preenchimento pelo órgão e, opcionalmente, bloco de subsídios técnicos extraídos do contrato atual. O modelo nunca redige justificativa inventada.
- **Preços**: sempre campo para preenchimento. O modelo nunca inventa valores.
- **Neutralidade** (gera alertas, não bloqueia): (1) busca determinística, no texto gerado, pelos termos da camada interna, feita em código, sem enviar esses termos ao modelo; (2) revisão pelo modelo apontando valores exatos onde caberia requisito mínimo.
- Tabela de NMS/SLA e glosas é dado estruturado, editável no formulário antes da geração.

### Padrão dos DOCX gerados

Alvo de edição: **Google Docs**. Evitar o que se perde na conversão.

- Parágrafos justificados; fonte e margens definidas no template.
- Títulos com numeração escrita como **texto literal** (sem numeração automática do Word).
- Tabelas com cabeçalho destacado e bordas simples; sem células mescladas complexas.
- Cabeçalho com os campos do perfil (padrão: órgão e número do processo); rodapé com paginação.
- Sem caixas de texto, controles de conteúdo, sumário automático, seções com orientação mista ou estilos exóticos.
- Aviso padrão (ajustável por perfil): "Minuta gerada com apoio de IA. Validar com o responsável jurídico/contratual interno antes do uso."

## Regras de segurança (obrigatórias)

- **Segredos**: nunca em código. Somente variáveis de ambiente (`ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `EDITALLAB_DIR_DADOS` etc.). `.env.example` sem valores reais; `.env` no `.gitignore`. Chaves nunca aparecem em log.
- **Uploads**: whitelist de extensão (`.pdf`, `.docx`, `.xlsx`, `.csv`, e `.zip` apenas como contêiner) **e** magic bytes; limite de tamanho; nome sanitizado; armazenamento fora de diretórios servidos.
  - DOCX e XLSX são ZIP por dentro: valida-se a estrutura interna esperada e aplicam-se os mesmos limites de tamanho descompactado. Arquivos com macro (`.docm`, `.xlsm`) são recusados.
  - CSV não tem magic bytes: valida-se como texto decodificável, sem bytes nulos.
- **ZIP**: bloqueio de caminhos fora do destino (zip slip), inclusive links simbólicos; limite de tamanho descompactado total e por arquivo, medido durante a leitura e não pelo cabeçalho; limite de quantidade de arquivos; ZIP aninhado é recusado; cada arquivo interno passa pelo mesmo funil de validação.
- **Banco**: somente ORM ou consultas parametrizadas. Proibido montar SQL com f-string ou concatenação.
- **XSS**: conteúdo vindo de documentos ou do modelo é sempre escapado. `unsafe_allow_html=True` é proibido com qualquer conteúdo que não seja constante do próprio código.
- **SSRF**: o app não busca URLs informadas pelo usuário nem presentes em documentos. A única saída de rede é a API da Anthropic.
- **Acesso**: sem autenticação na v1. Streamlit em `localhost`, configurado em `.streamlit/config.toml` versionado. O README avisa para não expor a porta.
- **Prompt injection**: ver seção LLM. Resposta do modelo nunca é executada nem usada como caminho de arquivo, SQL ou comando.
- **Erros**: detalhes vão para o log local; o usuário vê mensagem amigável, sem stack trace nem detalhe de infraestrutura. Logs não contêm texto de documentos.
- **LGPD**: ver seção Mascaramento. Testes, exemplos e fixtures somente com dados fictícios (CPF de teste gerado com dígitos válidos mas inexistente em fixture pública, e-mails em domínio `exemplo.com.br`, telefones fictícios).
- À API vai apenas texto extraído e mascarado, nunca o arquivo original.

## Convenções de código

- Docstrings em todas as funções, classes e métodos públicos. Type hints em todo o código.
- Comentários explicam o porquê, não o quê.
- Funções do núcleo recebem dependências (sessão de banco, cliente LLM, configurações) por parâmetro; nada de estado global.
- Exceções de domínio herdam de `ErroEditalLab` e carregam `mensagem_usuario`. `str(exc)` devolve a mensagem amigável; o detalhe técnico fica em `.detalhe` e vai só para o log.
- `extracao.preparar_paginas` é o único ponto de entrada para obter texto de um arquivo, e já devolve o texto mascarado. Não chame os extratores diretamente fora de testes.
- `core/processos.py` é a fachada de serviço que a UI usa (criar processo, adicionar arquivos, confirmar tipo, extrair pendentes).
- Enums de domínio (`TipoArquivo`, `RegimeJuridico`, `StatusAderencia`, `StatusVerificacao`) definidos uma única vez em `core/esquemas/`.

## Testes

- Testes padrão usam a API simulada: sem chamada real, sem custo, sem rede.
- Testes de integração com a API real: `tests/integracao/`, marcador `integracao`, fora da execução padrão.
- Fixture principal em `tests/fixtures/`: processo **fictício** curto de conectividade MPLS com edital em PDF, anexo XLSX com a lista de pontos e errata em PDF que altera pelo menos um prazo e um requisito. Gerada por `scripts/gerar_fixtures.py` para ser reproduzível.
- Testes que não podem faltar:
  - zip slip, zip bomb (tamanho e quantidade), ZIP aninhado, extensão falsa com magic bytes divergentes;
  - mascaramento de cada identificador e preservação de CNPJ;
  - nenhum texto não mascarado chega ao banco nem ao cliente LLM;
  - verificação de trecho: confere, não confere, confere apesar de quebra de linha;
  - precedência de errata sobre o original e registro da alteração como ponto de atenção;
  - cache: segunda análise idêntica não chama o cliente LLM;
  - camada interna do catálogo ausente de todos os prompts do Módulo B;
  - checagem determinística de neutralidade encontra termo interno plantado;
  - numeração de títulos do DOCX como texto literal.
