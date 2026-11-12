import io
import stat
import zipfile

import pytest

from editallab.core.erros import ErroZipInseguro
from editallab.core.ingestao import FonteUpload
from editallab.core.ingestao.zip_seguro import extrair_zip_seguro
from tests.conftest import montar_zip

PDF = b"%PDF-1.7 conteudo ficticio"


def test_le_zip_valido_e_ignora_ocultos(config):
    conteudo = montar_zip(
        {"pasta/edital.pdf": PDF, "__MACOSX/._edital.pdf": b"x", "pasta/.DS_Store": b"x"}
    )
    lido = extrair_zip_seguro(conteudo, config)
    assert [nome for nome, _ in lido.membros] == ["pasta/edital.pdf"]
    assert len(lido.ignorados) == 2


@pytest.mark.parametrize(
    "nome", ["../fora.pdf", "a/../../fora.pdf", "/etc/fora.pdf", "C:\\fora.pdf", "..\\fora.pdf"]
)
def test_bloqueia_zip_slip(config, nome):
    with pytest.raises(ErroZipInseguro):
        extrair_zip_seguro(montar_zip({nome: PDF}), config)


def test_bloqueia_link_simbolico(config):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        info = zipfile.ZipInfo("atalho.pdf")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "/etc/passwd")
    with pytest.raises(ErroZipInseguro, match="links"):
        extrair_zip_seguro(buffer.getvalue(), config)


def test_bloqueia_zip_bomb_por_tamanho(config):
    pequeno = config.model_copy(update={"zip_max_descompactado_mb": 1})
    bomba = montar_zip({"a.pdf": b"%PDF-" + b"\0" * (3 * 1024 * 1024)})
    assert len(bomba) < 100_000  # compacta muito bem: é o cenário de bomba
    with pytest.raises(ErroZipInseguro):
        extrair_zip_seguro(bomba, pequeno)


def test_bloqueia_zip_bomb_por_soma_dos_membros(config):
    pequeno = config.model_copy(update={"zip_max_descompactado_mb": 1})
    membros = {f"{i}.pdf": b"%PDF-" + b"\0" * (400 * 1024) for i in range(4)}
    with pytest.raises(ErroZipInseguro):
        extrair_zip_seguro(montar_zip(membros), pequeno)


def test_bloqueia_excesso_de_arquivos(config):
    pequeno = config.model_copy(update={"zip_max_arquivos": 3})
    with pytest.raises(ErroZipInseguro, match="mais de 3"):
        extrair_zip_seguro(montar_zip({f"{i}.pdf": PDF for i in range(4)}), pequeno)


def test_bloqueia_zip_aninhado(config):
    interno = montar_zip({"edital.pdf": PDF})
    with pytest.raises(ErroZipInseguro, match="outro ZIP"):
        extrair_zip_seguro(montar_zip({"interno.zip": interno}), config)
    # ZIP aninhado com extensão disfarçada também é recusado.
    with pytest.raises(ErroZipInseguro, match="outro ZIP"):
        extrair_zip_seguro(montar_zip({"interno.pdf": interno}), config)


def test_recusa_zip_corrompido(config):
    with pytest.raises(ErroZipInseguro):
        extrair_zip_seguro(b"PK\x03\x04 lixo", config)


def test_fonte_upload_mistura_avulsos_e_zip(config, arquivos_processo):
    zip_ok = montar_zip(dict(arquivos_processo[:2]))
    zip_ruim = montar_zip({"../fora.pdf": PDF})
    fonte = FonteUpload(
        [arquivos_processo[2], ("pasta.zip", zip_ok), ("ruim.zip", zip_ruim), ("x.zip", b"nada")],
        config,
    )
    itens = list(fonte.itens())
    assert {i.nome_original for i in itens} == {n for n, _ in arquivos_processo}
    assert {r.nome for r in fonte.rejeicoes} == {"ruim.zip", "x.zip"}
