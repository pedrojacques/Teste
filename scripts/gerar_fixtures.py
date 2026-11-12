"""Gera o processo fictício de conectividade MPLS usado nos testes.

Uso: `uv run python scripts/gerar_fixtures.py`

Todos os dados são inventados: órgão, CNPJ, pessoas, e-mails, telefones e CPF não
correspondem a ninguém. Os PDFs saem idênticos a cada execução; o XLSX muda de
hash porque o formato grava a data de criação. Os testes não dependem de hash fixo.
"""

from pathlib import Path

import pymupdf
from openpyxl import Workbook

DESTINO = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "processo_mpls"

EDITAL_PAGINAS = [
    """PREFEITURA MUNICIPAL DE VILA AURORA DO SUL
PREGÃO ELETRÔNICO Nº 12/2025
PROCESSO ADMINISTRATIVO Nº 345/2025

1. DO OBJETO
1.1. Contratação de empresa especializada para prestação de serviço de rede corporativa MPLS, interligando as unidades da Prefeitura Municipal de Vila Aurora do Sul, conforme Anexo I.
1.2. O critério de julgamento será o de menor preço global.

2. DA SESSÃO PÚBLICA
2.1. A sessão pública será realizada em 20/03/2025, às 09h00.
2.2. Pedidos de esclarecimento poderão ser enviados até 3 (três) dias úteis antes da data da sessão.

3. DO CONTATO
3.1. Pregoeira: Marina Fictícia da Silva, CPF 529.982.247-25.
3.2. E-mail: licitacoes@vilaaurora.exemplo.com.br. Telefone: (47) 3555-0142.
3.3. CNPJ do órgão: 12.345.678/0001-95.
""",
    """4. DOS REQUISITOS TÉCNICOS
4.1. Cada ponto deverá ser atendido por link dedicado com a banda indicada no Anexo I.
4.2. A disponibilidade mensal mínima de cada link será de 99,5%.
4.3. A latência máxima entre qualquer ponto e o concentrador será de 40 ms.
4.4. O prazo de instalação de todos os pontos será de 60 (sessenta) dias corridos, contados da assinatura do contrato.
4.5. O prazo máximo de reparo será de 6 (seis) horas.
4.6. A CONTRATADA deverá fornecer roteador CPE em cada ponto, em regime de comodato.

5. DA HABILITAÇÃO TÉCNICA
5.1. Atestado de capacidade técnica comprovando a prestação de serviço MPLS em, no mínimo, 5 (cinco) pontos simultâneos.

6. DOS NÍVEIS DE SERVIÇO E GLOSAS
""",
]

TABELA_SLA = [
    ["Indicador", "Meta", "Glosa"],
    ["Disponibilidade mensal", "99,5%", "2% por ponto percentual"],
    ["Prazo de reparo", "6 horas", "1% por hora excedente"],
]

ERRATA = """PREFEITURA MUNICIPAL DE VILA AURORA DO SUL
ERRATA Nº 01 AO PREGÃO ELETRÔNICO Nº 12/2025

A Prefeitura Municipal de Vila Aurora do Sul torna públicas as seguintes alterações no edital:

1. O item 4.4 passa a ter a seguinte redação: "O prazo de instalação de todos os pontos será de 90 (noventa) dias corridos, contados da assinatura do contrato."

2. O item 4.2 passa a ter a seguinte redação: "A disponibilidade mensal mínima de cada link será de 99,7%."

3. A sessão pública fica adiada para 02/04/2025, às 09h00.

Permanecem inalteradas as demais disposições do edital.

Vila Aurora do Sul, 10 de março de 2025.
"""

PONTOS = [
    ["Item", "Unidade", "Endereço", "Município", "Banda (Mbps)", "Contato local"],
    [1, "Paço Municipal (concentrador)", "Rua das Araucárias, 100", "Vila Aurora do Sul", 500, ""],
    [2, "Secretaria de Saúde", "Av. dos Imigrantes, 2500", "Vila Aurora do Sul", 100, ""],
    [3, "Secretaria de Educação", "Rua XV de Outubro, 45", "Vila Aurora do Sul", 100, ""],
    [4, "UBS Bairro Novo", "Rua das Hortênsias, 300", "Vila Aurora do Sul", 50, "(47) 99555-0101"],
    [
        5,
        "Escola Municipal Pinheiral",
        "Estrada Geral do Pinheiral, s/n",
        "Vila Aurora do Sul",
        50,
        "",
    ],
    [6, "Almoxarifado Central", "Rod. SC-999, km 12", "Vila Aurora do Sul", 30, ""],
]


def _pdf_deterministico(doc: pymupdf.Document, destino: Path) -> None:
    """Grava o PDF sem data de criação nem identificador aleatório."""
    doc.set_metadata({})
    doc.save(destino, garbage=4, deflate=True, no_new_id=True)
    doc.close()


def gerar_edital(destino: Path) -> None:
    doc = pymupdf.open()
    for texto in EDITAL_PAGINAS:
        pagina = doc.new_page()
        pagina.insert_textbox(pymupdf.Rect(60, 60, 535, 780), texto, fontsize=10.5, fontname="helv")
    # Tabela de SLA desenhada com linhas, na segunda página, para exercitar a extração.
    pagina = doc[1]
    x0, y0, largura, altura = 60, 400, (150, 100, 200), 22
    for i, linha in enumerate(TABELA_SLA):
        x = x0
        for j, celula in enumerate(linha):
            ret = pymupdf.Rect(x, y0 + i * altura, x + largura[j], y0 + (i + 1) * altura)
            pagina.draw_rect(ret, color=(0, 0, 0), width=0.7)
            pagina.insert_text((x + 4, ret.y1 - 7), celula, fontsize=10, fontname="helv")
            x += largura[j]
    _pdf_deterministico(doc, destino)


def gerar_errata(destino: Path) -> None:
    doc = pymupdf.open()
    pagina = doc.new_page()
    pagina.insert_textbox(pymupdf.Rect(60, 60, 535, 780), ERRATA, fontsize=10.5, fontname="helv")
    _pdf_deterministico(doc, destino)


def gerar_pontos(destino: Path) -> None:
    pasta = Workbook()
    aba = pasta.active
    aba.title = "Pontos"
    for linha in PONTOS:
        aba.append(linha)
    resumo = pasta.create_sheet("Resumo")
    resumo.append(["Total de pontos", len(PONTOS) - 1])
    resumo.append(["Banda total (Mbps)", sum(linha[4] for linha in PONTOS[1:])])
    pasta.save(destino)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    gerar_edital(DESTINO / "Edital_PE_12-2025.pdf")
    gerar_errata(DESTINO / "Errata_01_PE_12-2025.pdf")
    gerar_pontos(DESTINO / "Anexo_I_Lista_de_Pontos.xlsx")
    print(f"Fixtures geradas em {DESTINO}")


if __name__ == "__main__":
    main()
