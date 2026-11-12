"""Mascaramento de identificadores pessoais estruturados (LGPD).

Aplicado ao texto extraído **antes** de gravar no banco e **antes** de enviar à API.
São mascarados CPF, RG, e-mail, telefone e dados bancários. CNPJ e nomes de pessoas
não são mascarados.

Os padrões são propositalmente conservadores: preferimos deixar passar um identificador
mal formatado a destruir um dado técnico (banda, quantidade, número de processo).
"""

import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

ROTULO_CPF = "[CPF]"
ROTULO_RG = "[RG]"
ROTULO_EMAIL = "[EMAIL]"
ROTULO_TELEFONE = "[TELEFONE]"
ROTULO_BANCARIO = "[DADOS_BANCARIOS]"

# CNPJ formatado ou com 14 dígitos corridos. É protegido antes das demais regras.
_RE_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# O formato com pontos e hífen é inconfundível e é sempre mascarado.
_RE_CPF_FORMATADO = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}\s?-\s?\d{2}(?!\d)")
# Onze dígitos corridos só são CPF se os dígitos verificadores conferirem.
_RE_CPF_CORRIDO = re.compile(r"(?<![\d.,/-])\d{11}(?![\d.,/-]*\d)")
_RE_CPF_CONTEXTO = re.compile(r"(?i)(\bCPF(?:/MF)?\b[\s:nNºo°.]{0,6})(\d[\d.\s-]{9,13}\d)")
_RE_RG = re.compile(
    r"(?i)(\b(?:RG|R\.G\.|c[ée]dula\s+de\s+identidade|carteira\s+de\s+identidade|identidade)"
    r"[\s:nNºo°.]{0,6})(\d[\d.]{3,11}(?:-?[\dXx])?)"
)
_RE_TELEFONES = (
    # (47) 3433-0000, (47) 99999-0000, +55 (47) ...
    re.compile(r"(?:\+55\s?)?\(\d{2}\)\s?\d{4,5}[-.\s]?\d{4}(?!\d)"),
    # 47 3433-0000, +55 47 99999-0000
    re.compile(r"(?<![\d.,/-])(?:\+55\s?)?\d{2}\s9?\d{4}-\d{4}(?!\d)"),
    # +5547999990000
    re.compile(r"\+55\d{10,11}(?!\d)"),
)
_RE_TELEFONE_CONTEXTO = re.compile(
    r"(?i)(\b(?:telefone|tel|fone|celular|cel|whatsapp|fax)\b\.?[\s:]{0,3})"
    r"(\+?\d[\d\s().-]{6,16}\d)"
)
_RE_AGENCIA = re.compile(r"(?i)(\bag(?:[êe]ncia|\.)[\s:nNºo°.]{0,6})(\d{3,5}(?:-[\dXx])?)")
_RE_CONTA = re.compile(
    r"(?i)(\b(?:conta(?:\s+corrente|\s+poupan[çc]a)?|c/c)[\s:nNºo°.]{0,6})"
    r"(\d[\d.]{3,11}(?:-[\dXx])?)"
)
_RE_PIX = re.compile(r"(?i)(\b(?:chave\s+)?pix\b[\s:]{0,3})([A-Za-z0-9][A-Za-z0-9-]{7,40})")


@dataclass(frozen=True)
class ResultadoMascaramento:
    """Texto mascarado e a contagem de substituições por rótulo."""

    texto: str
    contagens: dict[str, int] = field(default_factory=dict)


def cpf_valido(digitos: str) -> bool:
    """Confere os dois dígitos verificadores de um CPF de onze dígitos."""
    if len(digitos) != 11 or not digitos.isdigit() or digitos == digitos[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d) * (tamanho + 1 - i) for i, d in enumerate(digitos[:tamanho]))
        if (soma * 10 % 11) % 10 != int(digitos[tamanho]):
            return False
    return True


def mascarar(texto: str) -> ResultadoMascaramento:
    """Substitui identificadores pessoais estruturados por rótulos fixos.

    A operação é idempotente: aplicar de novo sobre um texto já mascarado não altera nada.
    """
    contagens: Counter[str] = Counter()
    texto = texto.replace("\x00", "")

    # 1. Protege CNPJ, que não é dado pessoal, para nenhuma regra seguinte tocá-lo.
    protegidos: list[str] = []

    def _proteger(m: re.Match[str]) -> str:
        protegidos.append(m.group(0))
        return f"\x00{len(protegidos) - 1}\x00"

    texto = _RE_CNPJ.sub(_proteger, texto)

    def _trocar(rotulo: str) -> Callable[[re.Match[str]], str]:
        def _f(m: re.Match[str]) -> str:
            contagens[rotulo] += 1
            return rotulo

        return _f

    def _trocar_valor(rotulo: str) -> Callable[[re.Match[str]], str]:
        """Mantém a palavra de contexto (grupo 1) e mascara apenas o valor (grupo 2)."""

        def _f(m: re.Match[str]) -> str:
            contagens[rotulo] += 1
            return m.group(1) + rotulo

        return _f

    def _cpf_corrido(m: re.Match[str]) -> str:
        if cpf_valido(m.group(0)):
            contagens[ROTULO_CPF] += 1
            return ROTULO_CPF
        return m.group(0)

    texto = _RE_EMAIL.sub(_trocar(ROTULO_EMAIL), texto)
    texto = _RE_CPF_FORMATADO.sub(_trocar(ROTULO_CPF), texto)
    texto = _RE_CPF_CONTEXTO.sub(_trocar_valor(ROTULO_CPF), texto)
    for padrao in _RE_TELEFONES:
        texto = padrao.sub(_trocar(ROTULO_TELEFONE), texto)
    texto = _RE_TELEFONE_CONTEXTO.sub(_trocar_valor(ROTULO_TELEFONE), texto)
    texto = _RE_CPF_CORRIDO.sub(_cpf_corrido, texto)
    texto = _RE_RG.sub(_trocar_valor(ROTULO_RG), texto)
    texto = _RE_AGENCIA.sub(_trocar_valor(ROTULO_BANCARIO), texto)
    texto = _RE_CONTA.sub(_trocar_valor(ROTULO_BANCARIO), texto)
    texto = _RE_PIX.sub(_trocar_valor(ROTULO_BANCARIO), texto)

    # 2. Devolve os CNPJs protegidos.
    texto = re.sub(r"\x00(\d+)\x00", lambda m: protegidos[int(m.group(1))], texto)
    return ResultadoMascaramento(texto=texto, contagens=dict(contagens))
