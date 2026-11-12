from typing import Annotated, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from app.schemas.comum import HoraEntrada

DiaSemana = Annotated[int, Field(ge=1, le=7)]


class HorarioEntrada(BaseModel):
    turno: Literal["manha", "tarde", "noite"]
    ordem: int = Field(gt=0, le=32767)
    inicio: HoraEntrada
    fim: HoraEntrada
    dias_semana: list[DiaSemana] = Field(min_length=1)
    ativo: bool = True

    @field_validator("fim")
    @classmethod
    def _fim_maior(cls, v, info: ValidationInfo):  # noqa: ANN001, ANN206
        inicio = info.data.get("inicio")
        if inicio is not None and v <= inicio:
            raise ValueError("deve ser maior que o início")
        return v

    @field_validator("dias_semana")
    @classmethod
    def _dias_unicos(cls, v: list[int]) -> list[int]:
        return sorted(set(v))


class HorarioAtualizar(HorarioEntrada):
    """`PUT /horarios/{id}`: mesmos campos e validações, mas `ativo` obrigatório (contrato §1.6)."""

    ativo: bool
