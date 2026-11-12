"""Testes unitários de `validar_bloco` (RN03, ticket 08)."""

from datetime import date, time

import pytest
from sqlalchemy import select

from app.core.erros import ErroApi
from app.models import HorarioAula
from app.services.aulas import validar_bloco

TERCA = date(2030, 1, 8)
DOMINGO = date(2030, 1, 13)


def _ids(db, turno):
    return [h.id for h in db.scalars(select(HorarioAula).where(HorarioAula.turno == turno).order_by(HorarioAula.ordem))]


def _codigo(db, ids, data=TERCA):
    with pytest.raises(ErroApi) as e:
        validar_bloco(db, ids, data)
    return e.value.codigo


def test_bloco_valido_e_ordem_dos_ids_indiferente(db):
    manha = _ids(db, "manha")
    aulas, inicio, fim = validar_bloco(db, [manha[2], manha[0], manha[1]], TERCA)
    assert [a.ordem for a in aulas] == [1, 2, 3]
    assert (inicio, fim) == (time(7, 30), time(10, 20))


def test_turno_misto(db):
    assert _codigo(db, [_ids(db, "manha")[-1], _ids(db, "tarde")[0]]) == "AULAS_NAO_SEGUIDAS"


def test_buraco_na_ordem(db):
    manha = _ids(db, "manha")
    assert _codigo(db, [manha[0], manha[2]]) == "AULAS_NAO_SEGUIDAS"


def test_aula_inativa(db):
    manha = _ids(db, "manha")
    db.get(HorarioAula, manha[1]).ativo = False
    db.flush()
    assert _codigo(db, [manha[0], manha[1]]) == "AULAS_NAO_SEGUIDAS"
    db.rollback()


def test_dia_invalido(db):
    assert _codigo(db, [_ids(db, "manha")[0]], DOMINGO) == "AULA_INVALIDA_NO_DIA"
    assert _codigo(db, [_ids(db, "noite")[0]], date(2030, 1, 12)) == "AULA_INVALIDA_NO_DIA"  # sábado


def test_lista_vazia_repetida_e_inexistente(db):
    manha = _ids(db, "manha")
    assert _codigo(db, []) == "VALIDACAO"
    assert _codigo(db, [manha[0], manha[0]]) == "VALIDACAO"
    assert _codigo(db, [999999]) == "NAO_ENCONTRADO"
