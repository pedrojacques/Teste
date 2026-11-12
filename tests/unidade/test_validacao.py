import io
import zipfile

import pytest

from editallab.core.erros import ErroValidacaoArquivo
from editallab.core.esquemas import TipoArquivo
from editallab.core.ingestao import sanitizar_nome, sugerir_tipo, validar_arquivo
from tests.conftest import montar_zip


def test_aceita_os_arquivos_do_processo_ficticio(config, arquivos_processo):
    for nome, conteudo in arquivos_processo:
        validado = validar_arquivo(nome, conteudo, config)
        assert len(validado.sha256) == 64
        assert validado.tamanho == len(conteudo)


def test_aceita_csv(config):
    validado = validar_arquivo("pontos.csv", b"item;banda\n1;100\n", config)
    assert validado.extensao == ".csv"


@pytest.mark.parametrize("nome", ["script.exe", "macro.xlsm", "doc.docm", "nota.txt", "semext"])
def test_recusa_extensao_fora_da_whitelist(config, nome):
    with pytest.raises(ErroValidacaoArquivo):
        validar_arquivo(nome, b"%PDF-1.7 conteudo", config)


@pytest.mark.parametrize(
    ("nome", "conteudo"),
    [
        ("falso.pdf", b"MZ\x90\x00 executavel disfarcado"),
        ("falso.docx", b"%PDF-1.7 um pdf com nome de docx"),
        ("falso.xlsx", b"texto simples"),
        ("falso.csv", b"%PDF-1.7 um pdf com nome de csv"),
        ("binario.csv", b"a;b\n\x00\x01\x02"),
    ],
)
def test_recusa_magic_bytes_divergentes(config, nome, conteudo):
    with pytest.raises(ErroValidacaoArquivo):
        validar_arquivo(nome, conteudo, config)


def test_recusa_zip_comum_renomeado_para_docx(config):
    with pytest.raises(ErroValidacaoArquivo):
        validar_arquivo("falso.docx", montar_zip({"a.txt": b"x"}), config)


def test_recusa_xlsx_trocado_por_docx(config, arquivos_processo):
    xlsx = next(c for n, c in arquivos_processo if n.endswith(".xlsx"))
    with pytest.raises(ErroValidacaoArquivo):
        validar_arquivo("planilha.docx", xlsx, config)


def test_recusa_ooxml_com_macro(config, arquivos_processo):
    xlsx = next(c for n, c in arquivos_processo if n.endswith(".xlsx"))
    buffer = io.BytesIO(xlsx)
    with zipfile.ZipFile(buffer, "a") as zf:
        zf.writestr("xl/vbaProject.bin", b"macro")
    with pytest.raises(ErroValidacaoArquivo, match="macros"):
        validar_arquivo("planilha.xlsx", buffer.getvalue(), config)


def test_recusa_ooxml_bomba(config, arquivos_processo):
    xlsx = next(c for n, c in arquivos_processo if n.endswith(".xlsx"))
    buffer = io.BytesIO(xlsx)
    with zipfile.ZipFile(buffer, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/media/grande.bin", b"\0" * (2 * 1024 * 1024))
    pequeno = config.model_copy(update={"zip_max_descompactado_mb": 1})
    with pytest.raises(ErroValidacaoArquivo, match="descompactar"):
        validar_arquivo("planilha.xlsx", buffer.getvalue(), pequeno)


def test_recusa_arquivo_vazio_e_acima_do_limite(config):
    with pytest.raises(ErroValidacaoArquivo):
        validar_arquivo("vazio.pdf", b"", config)
    pequeno = config.model_copy(update={"max_tamanho_arquivo_mb": 1})
    with pytest.raises(ErroValidacaoArquivo, match="limite"):
        validar_arquivo("grande.pdf", b"%PDF-" + b"0" * (1024 * 1024 + 1), pequeno)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Users\\x\\Edital 12.pdf", "Edital 12.pdf"),
        ("edital<script>.pdf", "edital_script_.pdf"),
        ("Anexo I - Lista de Pontos (v2).xlsx", "Anexo I - Lista de Pontos (v2).xlsx"),
        ("nome\x00com\ncontrole.pdf", "nomecomcontrole.pdf"),
        ("...", "arquivo"),
    ],
)
def test_sanitizar_nome(entrada, esperado):
    assert sanitizar_nome(entrada) == esperado


def test_sanitizar_nome_limita_tamanho():
    nome = sanitizar_nome("a" * 500 + ".pdf")
    assert len(nome) <= 150 and nome.endswith(".pdf")


@pytest.mark.parametrize(
    ("nome", "ext", "tipo"),
    [
        ("Edital_PE_12-2025.pdf", ".pdf", TipoArquivo.EDITAL),
        ("Errata_01_PE_12-2025.pdf", ".pdf", TipoArquivo.ERRATA),
        ("Errata ao Edital 12.pdf", ".pdf", TipoArquivo.ERRATA),
        ("Anexo_I_Lista_de_Pontos.xlsx", ".xlsx", TipoArquivo.ANEXO),
        ("Anexo I - Termo de Referência.pdf", ".pdf", TipoArquivo.TERMO_REFERENCIA),
        ("TR_conectividade.docx", ".docx", TipoArquivo.TERMO_REFERENCIA),
        ("Respostas aos esclarecimentos 02.pdf", ".pdf", TipoArquivo.ESCLARECIMENTO),
        ("Contrato 045-2021.pdf", ".pdf", TipoArquivo.CONTRATO),
        ("pontos.csv", ".csv", TipoArquivo.PLANILHA),
        ("documento.pdf", ".pdf", TipoArquivo.OUTRO),
    ],
)
def test_sugerir_tipo(nome, ext, tipo):
    assert sugerir_tipo(nome, ext) == tipo
