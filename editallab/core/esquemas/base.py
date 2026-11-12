"""Base comum dos schemas Pydantic."""

from pydantic import BaseModel, ConfigDict


class Esquema(BaseModel):
    """Modelo estrito: campos desconhecidos são erro e textos têm espaços aparados.

    Recusar campos extras é o que impede que uma resposta do modelo, ou um YAML
    editado à mão, introduza dados fora do contrato.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
