"""Regras da grade de aulas (RN02/RN03): validação de bloco de aulas seguidas."""

from collections.abc import Sequence
from datetime import date, time

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.core.erros import ErroApi, erro_validacao, nao_encontrado
from app.models import ORDEM_TURNO, HorarioAula

ordem_turno_sql = case(ORDEM_TURNO, value=HorarioAula.turno, else_=9)


def validar_bloco(
    db: Session, horario_ids: Sequence[int], data: date, campo: str = "body.horario_ids"
) -> tuple[list[HorarioAula], time, time]:
    """Valida 1..N aulas seguidas para `data` (RN03).

    Devolve (aulas ordenadas por ordem, início da primeira, fim da última).
    Erros: 422 VALIDACAO (vazia/repetida), 404 (inexistente), 422 AULAS_NAO_SEGUIDAS, 422 AULA_INVALIDA_NO_DIA.
    """
    ids = list(horario_ids)
    if not ids:
        raise erro_validacao(campo, "informe pelo menos uma aula")
    if len(set(ids)) != len(ids):
        raise erro_validacao(campo, "aulas repetidas")

    aulas = list(db.scalars(select(HorarioAula).where(HorarioAula.id.in_(ids))))
    if len(aulas) != len(ids):
        raise nao_encontrado("Aula não encontrada.")

    aulas.sort(key=lambda a: a.ordem)
    turnos = {a.turno for a in aulas}
    ordens = [a.ordem for a in aulas]
    consecutivas = all(b - a == 1 for a, b in zip(ordens, ordens[1:], strict=False))
    inicio, fim = aulas[0].inicio, aulas[-1].fim
    if not all(a.ativo for a in aulas) or len(turnos) != 1 or not consecutivas or fim <= inicio:
        raise ErroApi(
            422,
            "AULAS_NAO_SEGUIDAS",
            "Escolha aulas ativas, do mesmo turno e em sequência (sem pular aulas).",
        )

    dia = data.isoweekday()
    if any(dia not in a.dias_semana for a in aulas):
        raise ErroApi(422, "AULA_INVALIDA_NO_DIA", "Uma ou mais aulas escolhidas não acontecem neste dia da semana.")

    return aulas, inicio, fim
