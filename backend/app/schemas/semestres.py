from datetime import date

from pydantic import BaseModel, ValidationInfo, field_validator

from app.schemas.comum import texto


class SemestreEntrada(BaseModel):
    nome: texto(20)
    data_inicio: date
    data_fim: date

    @field_validator("data_fim")
    @classmethod
    def _fim_maior(cls, v: date, info: ValidationInfo) -> date:
        inicio = info.data.get("data_inicio")
        if inicio is not None and v <= inicio:
            raise ValueError("deve ser posterior à data de início")
        return v
