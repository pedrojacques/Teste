import pytest

from editallab.core.privacidade import mascarar
from editallab.core.privacidade.mascaramento import cpf_valido

# Dados fictícios: o CPF abaixo tem dígitos verificadores válidos, mas é de exemplo.
CPF_FICTICIO = "529.982.247-25"


@pytest.mark.parametrize(
    ("entrada", "rotulo"),
    [
        (f"CPF {CPF_FICTICIO}", "[CPF]"),
        ("CPF nº 52998224725", "[CPF]"),
        ("documento 52998224725 anexado", "[CPF]"),
        ("contato: fulano.teste@orgao.exemplo.com.br", "[EMAIL]"),
        ("Telefone: (47) 3555-0142", "[TELEFONE]"),
        ("ligar para 47 99555-0101", "[TELEFONE]"),
        ("whatsapp +55 (47) 99555-0101", "[TELEFONE]"),
        ("fone 3555 0142", "[TELEFONE]"),
        ("RG 1.234.567-8", "[RG]"),
        ("carteira de identidade nº 4567890", "[RG]"),
        ("Agência 1234-5", "[DADOS_BANCARIOS]"),
        ("conta corrente nº 12345-6", "[DADOS_BANCARIOS]"),
        ("chave PIX: 3f2a9c1e-aaaa-bbbb-cccc-1234567890ab", "[DADOS_BANCARIOS]"),
    ],
)
def test_mascara_identificadores(entrada, rotulo):
    resultado = mascarar(entrada)
    assert rotulo in resultado.texto
    assert resultado.contagens[rotulo] >= 1
    assert not any(c.isdigit() for c in resultado.texto.replace("nº", ""))


@pytest.mark.parametrize(
    "texto",
    [
        "CNPJ 12.345.678/0001-95",
        "CNPJ 12345678000195",
        "Processo Administrativo nº 345/2025",
        "banda de 1000 Mbps e disponibilidade de 99,5%",
        "prazo de 60 (sessenta) dias corridos",
        "valor estimado de R$ 1.234.567,89",
        "protocolo 12345678901 2024",  # onze dígitos sem dígito verificador válido
        "a rede conta com 5 pontos e a agenda prevê 2024",
        "sessão em 20/03/2025, às 09h00",
        "Rod. SC-999, km 12, CEP 89200-000",
        "Lei 14.133/2021 e Lei 13.303/2016",
    ],
)
def test_preserva_dados_tecnicos_e_cnpj(texto):
    assert mascarar(texto).texto == texto


def test_mascaramento_e_idempotente():
    texto = f"CPF {CPF_FICTICIO}, tel (47) 3555-0142, a@b.exemplo.com, CNPJ 12.345.678/0001-95"
    uma_vez = mascarar(texto).texto
    assert mascarar(uma_vez).texto == uma_vez
    assert "12.345.678/0001-95" in uma_vez


def test_cpf_valido():
    assert cpf_valido("52998224725")
    assert not cpf_valido("52998224726")
    assert not cpf_valido("11111111111")
