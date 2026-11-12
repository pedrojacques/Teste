"""Extração de planilhas XLSX e CSV, preservando aba e número de linha."""

import csv
import datetime as dt
import io

from openpyxl import load_workbook

from editallab.core.config import Configuracoes
from editallab.core.erros import ErroExtracao
from editallab.core.esquemas import TipoMarcador
from editallab.core.extracao.modelos import PaginaExtraida
from editallab.core.ingestao.validacao import decodificar_texto

ABA_CSV = "CSV"


def _formatar_celula(valor: object) -> str:
    """Converte o valor de uma célula em texto simples de uma linha."""
    if valor is None:
        return ""
    if isinstance(valor, dt.datetime):
        if valor.time() == dt.time(0):
            return valor.strftime("%d/%m/%Y")
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, dt.date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return " ".join(str(valor).split())


def _linha_texto(celulas: list[str]) -> str:
    """Junta as células com ` | `, descartando as vazias do fim da linha."""
    while celulas and not celulas[-1]:
        celulas.pop()
    return " | ".join(celulas)


def extrair_xlsx(conteudo: bytes, config: Configuracoes) -> list[PaginaExtraida]:
    """Extrai cada aba de um XLSX como uma página, com as linhas numeradas como no arquivo.

    Usa os valores calculados (não as fórmulas) e respeita o limite de linhas por aba.
    """
    try:
        pasta = load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - openpyxl levanta tipos variados
        raise ErroExtracao("Não foi possível ler a planilha.", str(exc)) from exc
    paginas: list[PaginaExtraida] = []
    try:
        for numero, aba in enumerate(pasta.worksheets, start=1):
            linhas: list[tuple[int, str]] = []
            for indice, linha in enumerate(aba.iter_rows(values_only=True), start=1):
                if indice > config.planilha_max_linhas_por_aba:
                    break
                texto = _linha_texto([_formatar_celula(v) for v in linha])
                if texto:
                    linhas.append((indice, texto))
            paginas.append(
                PaginaExtraida(
                    numero=numero, aba=aba.title, linhas=linhas, tipo_marcador=TipoMarcador.ABA
                )
            )
    finally:
        pasta.close()
    return paginas


def extrair_csv(conteudo: bytes, config: Configuracoes) -> list[PaginaExtraida]:
    """Extrai um CSV como uma única aba, detectando o separador (`;`, `,` ou tabulação)."""
    texto = decodificar_texto(conteudo)
    try:
        dialeto = csv.Sniffer().sniff(texto[:8192], delimiters=";,\t|")
    except csv.Error:

        class dialeto(csv.excel):  # noqa: N801 - dialeto local, sem alterar o global
            delimiter = ";" if texto.count(";") > texto.count(",") else ","

    linhas: list[tuple[int, str]] = []
    try:
        for indice, linha in enumerate(csv.reader(io.StringIO(texto), dialeto), start=1):
            if indice > config.planilha_max_linhas_por_aba:
                break
            conteudo_linha = _linha_texto([" ".join(c.split()) for c in linha])
            if conteudo_linha:
                linhas.append((indice, conteudo_linha))
    except csv.Error as exc:
        raise ErroExtracao("Não foi possível ler o CSV.", str(exc)) from exc
    return [PaginaExtraida(numero=1, aba=ABA_CSV, linhas=linhas, tipo_marcador=TipoMarcador.ABA)]
