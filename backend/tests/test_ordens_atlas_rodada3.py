"""Ordens de Atlas, rodada 3: tickets 32 (`ativo` obrigatório no PUT), 34 (seed de semestres) e
35 (confirmação de recorrência sem N+1)."""

from datetime import timedelta

import pytest
from sqlalchemy import event, func, select

from app.core.db import engine
from app.core.tempo import hoje
from app.models import Semestre
from app.seed import executar as executar_seed
from app.seed import seed_semestres
from tests.conftest import TERCA_REF


# ---------------------------------------------------------------- ticket 32
def _corpo_sala(sala: dict) -> dict:
    return {k: sala[k] for k in ("nome", "tipo", "descricao", "capacidade", "localizacao")}


def _corpo_horario(h: dict) -> dict:
    return {k: h[k] for k in ("turno", "ordem", "inicio", "fim", "dias_semana")}


def test_put_sala_exige_ativo(client, admin, sala_id):
    sala = client.get(f"/salas/{sala_id}").json()
    desativar = client.put(f"/salas/{sala_id}", headers=admin, json=_corpo_sala(sala) | {"ativo": False})
    assert desativar.status_code == 200 and desativar.json()["ativo"] is False
    r = client.put(f"/salas/{sala_id}", headers=admin, json=_corpo_sala(sala))
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    assert r.json()["erros"][0]["campo"] == "body.ativo"
    # o PUT recusado não reativou o ambiente
    assert client.get(f"/salas/{sala_id}", headers=admin).json()["ativo"] is False
    r = client.put(f"/salas/{sala_id}", headers=admin, json=_corpo_sala(sala) | {"ativo": True, "capacidade": 33})
    assert r.status_code == 200 and (r.json()["ativo"], r.json()["capacidade"]) == (True, 33)


def test_put_horario_exige_ativo(client, admin, aulas):
    hid = aulas["noite"][-1]
    h = client.get(f"/horarios/{hid}").json()
    assert client.put(f"/horarios/{hid}", headers=admin, json=_corpo_horario(h) | {"ativo": False}).status_code == 200
    r = client.put(f"/horarios/{hid}", headers=admin, json=_corpo_horario(h))
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    assert r.json()["erros"][0]["campo"] == "body.ativo"
    assert client.get(f"/horarios/{hid}").json()["ativo"] is False
    r = client.put(f"/horarios/{hid}", headers=admin, json=_corpo_horario(h) | {"ativo": True})
    assert r.status_code == 200 and r.json()["ativo"] is True


def test_post_sem_ativo_continua_criando_ativo(client, admin):
    r = client.post("/salas", headers=admin, json={"nome": "Sala Nova 32", "tipo": "sala", "capacidade": 10})
    assert r.status_code == 201 and r.json()["ativo"] is True
    r = client.post(
        "/horarios",
        headers=admin,
        json={"turno": "noite", "ordem": 9, "inicio": "23:00", "fim": "23:30", "dias_semana": [1]},
    )
    assert r.status_code == 201 and r.json()["ativo"] is True


def test_openapi_ativo_obrigatorio_so_no_put(client):
    doc = client.get("/openapi.json").json()

    def esquema(caminho: str, metodo: str) -> dict:
        ref = doc["paths"][caminho][metodo]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        return doc["components"]["schemas"][ref.rsplit("/", 1)[1]]

    assert "ativo" in esquema("/salas/{sala_id}", "put")["required"]
    assert "ativo" in esquema("/horarios/{horario_id}", "put")["required"]
    assert "ativo" not in esquema("/salas", "post").get("required", [])
    assert "ativo" not in esquema("/horarios", "post").get("required", [])


# ---------------------------------------------------------------- ticket 34
def _semestres(db) -> list[str]:
    db.expire_all()
    return sorted(db.scalars(select(Semestre.nome)))


def _esvaziar_semestres(db) -> None:
    db.execute(Semestre.__table__.delete())
    db.commit()


def test_seed_semestres_tabela_vazia_cria_quatro_e_depois_nada(db):
    _esvaziar_semestres(db)
    seed_semestres(db)
    db.commit()
    ano = hoje().year
    esperado = sorted([f"{ano}-1", f"{ano}-2", f"{ano + 1}-1", f"{ano + 1}-2"])
    assert _semestres(db) == esperado
    executar_seed(db)
    executar_seed(db)
    assert _semestres(db) == esperado


def test_seed_nao_recria_semestre_excluido(db):
    ano = hoje().year
    db.execute(Semestre.__table__.delete().where(Semestre.nome == f"{ano + 1}-1"))
    db.commit()
    executar_seed(db)
    assert f"{ano + 1}-1" not in _semestres(db)
    assert len(_semestres(db)) == 3


def test_seed_com_semestre_do_admin_nao_cria_nenhum(db):
    _esvaziar_semestres(db)
    db.add(Semestre(nome="Especial", data_inicio=hoje() + timedelta(days=400), data_fim=hoje() + timedelta(days=430)))
    db.commit()
    executar_seed(db)
    assert _semestres(db) == ["Especial"]


# ---------------------------------------------------------------- ticket 35
@pytest.fixture
def contar_selects():
    contagem = {"n": 0}

    def ouvir(_conn, _cursor, sql, *_a):
        if sql.lstrip().upper().startswith("SELECT"):
            contagem["n"] += 1

    event.listen(engine, "before_cursor_execute", ouvir)
    yield contagem
    event.remove(engine, "before_cursor_execute", ouvir)


def _confirmar(client, professor, sala_id, aulas, n: int, contagem: dict) -> tuple[dict, int]:
    datas = [(TERCA_REF + timedelta(weeks=k)).isoformat() for k in range(n)]
    corpo = {"sala_id": sala_id, "data_inicio": TERCA_REF.isoformat(), "horario_ids": aulas["manha"][:2], "datas": datas}
    contagem["n"] = 0
    r = client.post("/reservas/recorrentes", headers=professor, json=corpo)
    assert r.status_code == 201, r.text
    return r.json(), contagem["n"]


def test_confirmar_recorrencia_numero_fixo_de_selects(
    client, relogio, semestre_ref, professor, admin, sala_id, aulas, contar_selects
):
    pequeno, selects_2 = _confirmar(client, professor, sala_id, aulas, 2, contar_selects)
    outra_sala = client.get("/salas", params={"busca": "Laboratório 02"}).json()[0]["id"]
    grande, selects_15 = _confirmar(client, professor, outra_sala, aulas, 15, contar_selects)
    assert len(pequeno["reservas"]) == 2 and len(grande["reservas"]) == 15
    assert selects_15 == selects_2, (selects_2, selects_15)

    # resposta igual à do GET do grupo, com as reservas ordenadas por data
    for criado in (pequeno, grande):
        datas = [x["data"] for x in criado["reservas"]]
        assert datas == sorted(datas)
        lido = client.get(f"/reservas/grupos/{criado['grupo']['id']}", headers=professor).json()
        assert criado == lido
        for x in criado["reservas"]:
            assert x["criado_em"] and x["sala"]["id"] and x["professor"]["nome"] == "Professor Um"
            assert x["status"] == "ativa" and x["pode_cancelar"] is True
