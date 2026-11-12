"""Ticket 23: recorrência (RN06), cancelamento (RN07), consultas e `pode_cancelar`.

Tempo controlado: `relogio` em TERCA_REF (terça 05/03/2030); semestre "2030-1" de 04/02 a 25/06/2030.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.models import GrupoRecorrencia, Reserva
from tests.conftest import TERCA_REF


def semana(k: int) -> str:
    return (TERCA_REF + timedelta(weeks=k)).isoformat()


SERIE_COMPLETA = [semana(k) for k in range(17)]  # 05/03 … 25/06/2030 (data_fim inclusive)


def contar(db, modelo) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(modelo))


@pytest.fixture
def corpo(sala_id, aulas):
    return {"sala_id": sala_id, "data_inicio": TERCA_REF.isoformat(), "horario_ids": aulas["manha"][:2]}


# ---------------------------------------------------------------- prévia
def test_previa_serie_ate_o_fim_do_semestre_inclusive(client, db, relogio, semestre_ref, professor, corpo):
    antes = (contar(db, Reserva), contar(db, GrupoRecorrencia))
    r = client.post("/reservas/recorrentes/previa", headers=professor, json=corpo)
    assert r.status_code == 200, r.text
    p = r.json()
    assert [o["data"] for o in p["ocorrencias"]] == SERIE_COMPLETA
    assert (p["total"], p["livres"], p["em_conflito"]) == (17, 17, 0)
    assert p["dia_semana"] == 2 and (p["inicio"], p["fim"]) == ("07:30", "09:10")
    assert p["semestre"]["nome"] == "2030-1"
    assert p["horario_ids"] == corpo["horario_ids"]
    assert p["sala"]["id"] == corpo["sala_id"]
    # prévia não grava nada
    assert (contar(db, Reserva), contar(db, GrupoRecorrencia)) == antes


def test_previa_comecando_no_meio_e_terminando_antes_do_fim(client, relogio, semestre_ref, professor, corpo):
    # quinta 20/06/2030: 20/06 e … nada mais (27/06 passa de 25/06)
    r = client.post("/reservas/recorrentes/previa", headers=professor, json={**corpo, "data_inicio": "2030-06-20"})
    assert [o["data"] for o in r.json()["ocorrencias"]] == ["2030-06-20"]


def test_previa_mostra_conflitos_com_nome_sem_rm(client, relogio, semestre_ref, admin, professor, corpo, aulas):
    ocupadas = [semana(2), semana(5)]
    for d in ocupadas:
        assert client.post("/reservas", headers=admin, json={"sala_id": corpo["sala_id"], "data": d, "horario_ids": [aulas["manha"][1]]}).status_code == 201
    p = client.post("/reservas/recorrentes/previa", headers=professor, json=corpo).json()
    assert (p["livres"], p["em_conflito"]) == (15, 2)
    conflito = {o["data"]: o for o in p["ocorrencias"] if not o["livre"]}
    assert sorted(conflito) == ocupadas
    c = conflito[semana(2)]["conflitos"][0]
    assert (c["inicio"], c["fim"], c["professor"]["nome"]) == ("08:20", "09:10", "Administrador")
    assert "rm" not in c["professor"]


@pytest.mark.parametrize("rota", ["/reservas/recorrentes/previa", "/reservas/recorrentes"])
def test_sem_semestre(client, relogio, professor, corpo, rota):
    extra = {"datas": ["2030-03-05"]} if rota.endswith("recorrentes") else {}
    r = client.post(rota, headers=professor, json={**corpo, **extra})  # só existem semestres 2026/2027 do seed
    assert (r.status_code, r.json()["codigo"]) == (422, "SEM_SEMESTRE")


def test_previa_aplica_regras_comuns(client, relogio, semestre_ref, professor, corpo, aulas):
    casos = [
        ({"horario_ids": [aulas["manha"][0], aulas["manha"][2]]}, 422, "AULAS_NAO_SEGUIDAS"),
        ({"data_inicio": "2030-03-10"}, 422, "AULA_INVALIDA_NO_DIA"),  # domingo
        ({"professor_id": 1}, 403, "SEM_PERMISSAO"),
        ({"sala_id": 999999}, 404, "NAO_ENCONTRADO"),
    ]
    for extra, status, codigo in casos:
        r = client.post("/reservas/recorrentes/previa", headers=professor, json={**corpo, **extra})
        assert (r.status_code, r.json()["codigo"]) == (status, codigo), extra


def test_previa_data_inicial_ja_comecou(client, relogio, semestre_ref, professor, corpo):
    relogio.definir(TERCA_REF, "08:00")
    r = client.post("/reservas/recorrentes/previa", headers=professor, json=corpo)
    assert (r.status_code, r.json()["codigo"]) == (422, "DATA_PASSADA")


# ---------------------------------------------------------------- confirmação
def test_confirmacao_grava_grupo_e_reservas(client, db, relogio, semestre_ref, professor, corpo):
    datas = [semana(0), semana(3), semana(1)]
    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": datas, "observacao": "Prog I"})
    assert r.status_code == 201, r.text
    grupo, reservas = r.json()["grupo"], r.json()["reservas"]
    assert [x["data"] for x in reservas] == sorted(datas)
    assert all(x["grupo_recorrencia_id"] == grupo["id"] and x["observacao"] == "Prog I" for x in reservas)
    assert grupo["dia_semana"] == 2 and grupo["semestre"]["nome"] == "2030-1"
    assert (grupo["total_ocorrencias"], grupo["ocorrencias_ativas"]) == (3, 3)
    assert (grupo["inicio"], grupo["fim"]) == ("07:30", "09:10")
    assert contar(db, Reserva) == 3 and contar(db, GrupoRecorrencia) == 1


@pytest.mark.parametrize(
    "data_errada",
    [
        "2030-03-06",  # quarta: dia da semana errado
        "2030-02-26",  # terça antes da data inicial
        "2030-07-02",  # terça depois do fim do semestre
    ],
)
def test_data_fora_da_serie(client, db, relogio, semestre_ref, professor, corpo, data_errada):
    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": [semana(0), data_errada]})
    assert (r.status_code, r.json()["codigo"]) == (422, "DATA_FORA_DA_SERIE")
    assert contar(db, Reserva) == 0


@pytest.mark.parametrize("datas", [[], [semana(1), semana(1)]])
def test_datas_vazias_ou_repetidas(client, relogio, semestre_ref, professor, corpo, datas):
    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": datas})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")


def test_confirmacao_atomica_com_conflito(client, db, relogio, semestre_ref, admin, professor, corpo, aulas):
    """Uma data ocupada entre a prévia e a confirmação: nada é gravado e o 409 lista os conflitos atuais."""
    previa = client.post("/reservas/recorrentes/previa", headers=professor, json=corpo).json()
    livres = [o["data"] for o in previa["ocorrencias"] if o["livre"]]
    assert len(livres) == 17
    for d in (semana(4), semana(9)):
        client.post("/reservas", headers=admin, json={"sala_id": corpo["sala_id"], "data": d, "horario_ids": [aulas["manha"][0]]})
    antes = (contar(db, Reserva), contar(db, GrupoRecorrencia))
    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": livres})
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLITO_RESERVA"
    assert sorted(c["data"] for c in r.json()["conflitos"]) == [semana(4), semana(9)]
    assert (contar(db, Reserva), contar(db, GrupoRecorrencia)) == antes


def test_admin_cria_recorrencia_em_nome_do_professor(client, relogio, semestre_ref, admin, novo_professor, corpo):
    prof_h, prof = novo_professor("dono1", "Dona da Série")
    r = client.post("/reservas/recorrentes", headers=admin, json={**corpo, "datas": [semana(0)], "professor_id": prof["id"]})
    assert r.status_code == 201, r.text
    grupo = r.json()["grupo"]
    assert grupo["professor"]["id"] == prof["id"]
    # o dono vê e cancela o grupo
    assert client.get(f"/reservas/grupos/{grupo['id']}", headers=prof_h).status_code == 200
    assert client.post(f"/reservas/grupos/{grupo['id']}/cancelar", headers=prof_h).json()["canceladas"] == 1


def test_grupo_visivel_so_para_dono_e_admin(client, relogio, semestre_ref, admin, professor, novo_professor, corpo):
    grupo = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": [semana(0), semana(1)]}).json()["grupo"]
    outro, _ = novo_professor("intruso")
    assert client.get(f"/reservas/grupos/{grupo['id']}").status_code == 401
    r = client.get(f"/reservas/grupos/{grupo['id']}", headers=outro)
    assert (r.status_code, r.json()["codigo"]) == (403, "SEM_PERMISSAO")
    r = client.post(f"/reservas/grupos/{grupo['id']}/cancelar", headers=outro)
    assert (r.status_code, r.json()["codigo"]) == (403, "SEM_PERMISSAO")
    for quem in (professor, admin):
        r = client.get(f"/reservas/grupos/{grupo['id']}", headers=quem)
        assert r.status_code == 200 and len(r.json()["reservas"]) == 2
    assert client.get("/reservas/grupos/999999", headers=admin).status_code == 404


# ---------------------------------------------------------------- cancelamento avulsa
@pytest.fixture
def reserva_terca(client, relogio, professor, sala_id, aulas):
    """Reserva do professor na terça de referência, 3ª aula (09:30–10:20); criada às 06:00."""
    r = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": TERCA_REF.isoformat(), "horario_ids": [aulas["manha"][2]]})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize(("hora", "status", "codigo"), [("09:29", 200, None), ("09:30", 422, "RESERVA_JA_INICIADA"), ("15:00", 422, "RESERVA_JA_INICIADA")])
def test_dono_cancela_ate_o_inicio(client, relogio, professor, reserva_terca, hora, status, codigo):
    relogio.definir(TERCA_REF, hora)
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=professor)
    assert r.status_code == status, r.text
    if codigo:
        assert r.json()["codigo"] == codigo


def test_pode_cancelar_por_usuario_e_momento(client, relogio, admin, professor, novo_professor, reserva_terca):
    outro, _ = novo_professor("vizinho")
    rid = reserva_terca["id"]

    def pode(headers=None):
        return client.get(f"/reservas/{rid}", headers=headers or {}).json()["pode_cancelar"]

    assert (pode(), pode(professor), pode(outro), pode(admin)) == (False, True, False, True)
    relogio.definir(TERCA_REF, "09:30")
    assert (pode(professor), pode(admin)) == (False, True)
    # token inválido em rota pública é ignorado (vira visitante)
    assert pode({"Authorization": "Bearer lixo"}) is False


def test_outro_professor_nao_cancela(client, relogio, novo_professor, reserva_terca):
    outro, _ = novo_professor("vizinho")
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=outro)
    assert (r.status_code, r.json()["codigo"]) == (403, "SEM_PERMISSAO")
    assert client.post(f"/reservas/{reserva_terca['id']}/cancelar").status_code == 401


def test_admin_cancela_sempre_inclusive_passada(client, relogio, admin, professor, reserva_terca):
    relogio.definir(TERCA_REF + timedelta(days=30), "12:00")
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=admin, json={"motivo": "Correção"})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["status"] == "cancelada" and c["motivo_cancelamento"] == "Correção"
    assert c["cancelada_por"]["nome"] == "Administrador" and c["pode_cancelar"] is False
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=admin)
    assert (r.status_code, r.json()["codigo"]) == (409, "RESERVA_JA_CANCELADA")
    assert client.post("/reservas/999999/cancelar", headers=admin).status_code == 404


def test_motivo_longo_e_corpo_opcional(client, relogio, professor, reserva_terca):
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=professor, json={"motivo": "x" * 201})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    r = client.post(f"/reservas/{reserva_terca['id']}/cancelar", headers=professor)
    assert r.status_code == 200 and r.json()["motivo_cancelamento"] is None


# ---------------------------------------------------------------- cancelamento de grupo
@pytest.fixture
def grupo_4_semanas(client, relogio, semestre_ref, professor, corpo):
    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": [semana(k) for k in range(4)]})
    assert r.status_code == 201, r.text
    return r.json()["grupo"]


@pytest.mark.parametrize("quem", ["professor", "admin"])
def test_cancelar_grupo_so_futuras(client, request, relogio, grupo_4_semanas, quem):
    headers = request.getfixturevalue(quem)
    # 2ª ocorrência (12/03) começando às 07:30: as duas primeiras já começaram
    relogio.definir(TERCA_REF + timedelta(weeks=1), "07:30")
    r = client.post(f"/reservas/grupos/{grupo_4_semanas['id']}/cancelar", headers=headers, json={"motivo": "Fim da disciplina"})
    assert r.status_code == 200, r.text
    assert r.json()["canceladas"] == 2 and r.json()["grupo_recorrencia_id"] == grupo_4_semanas["id"]
    detalhe = client.get(f"/reservas/grupos/{grupo_4_semanas['id']}", headers=headers).json()
    assert [(x["data"], x["status"]) for x in detalhe["reservas"]] == [
        (semana(0), "ativa"), (semana(1), "ativa"), (semana(2), "cancelada"), (semana(3), "cancelada"),
    ]
    assert sorted(r.json()["reservas_ids"]) == sorted(x["id"] for x in detalhe["reservas"][2:])
    assert detalhe["grupo"]["ocorrencias_ativas"] == 2 and detalhe["grupo"]["total_ocorrencias"] == 4
    # de novo: nada a cancelar
    r = client.post(f"/reservas/grupos/{grupo_4_semanas['id']}/cancelar", headers=headers)
    assert r.json() == {"grupo_recorrencia_id": grupo_4_semanas["id"], "canceladas": 0, "reservas_ids": []}


def test_cancelar_uma_ocorrencia_do_grupo(client, relogio, professor, grupo_4_semanas):
    detalhe = client.get(f"/reservas/grupos/{grupo_4_semanas['id']}", headers=professor).json()
    alvo = detalhe["reservas"][1]["id"]
    assert client.post(f"/reservas/{alvo}/cancelar", headers=professor).status_code == 200
    r = client.post(f"/reservas/grupos/{grupo_4_semanas['id']}/cancelar", headers=professor)
    assert r.json()["canceladas"] == 3


# ---------------------------------------------------------------- consultas
def test_minhas_reservas_periodo_status_e_ordem(client, relogio, professor, admin, sala_id, aulas):
    m = aulas["manha"]
    criar = lambda d, h: client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": d, "horario_ids": [h]}).json()  # noqa: E731
    hoje_cedo = criar(TERCA_REF.isoformat(), m[0])  # 07:30–08:20
    hoje_tarde = criar(TERCA_REF.isoformat(), m[3])  # 10:20–11:10
    amanha = criar((TERCA_REF + timedelta(days=1)).isoformat(), m[0])
    cancelada = criar((TERCA_REF + timedelta(days=2)).isoformat(), m[0])
    client.post(f"/reservas/{cancelada['id']}/cancelar", headers=professor)
    client.post("/reservas", headers=admin, json={"sala_id": sala_id, "data": TERCA_REF.isoformat(), "horario_ids": [m[4]]})

    relogio.definir(TERCA_REF, "08:20")  # a das 07:30 acabou de terminar
    ids = lambda **q: [x["id"] for x in client.get("/reservas/minhas", headers=professor, params=q).json()]  # noqa: E731
    assert ids() == [hoje_tarde["id"], amanha["id"]]
    assert ids(periodo="passadas") == [hoje_cedo["id"]]
    assert ids(periodo="todas") == [amanha["id"], hoje_tarde["id"], hoje_cedo["id"]]
    assert ids(status="cancelada") == [cancelada["id"]]
    assert ids(periodo="todas", status="todas") == [cancelada["id"], amanha["id"], hoje_tarde["id"], hoje_cedo["id"]]
    assert client.get("/reservas/minhas", headers=professor, params={"periodo": "ontem"}).json()["codigo"] == "VALIDACAO"
    assert client.get("/reservas/minhas").status_code == 401


@pytest.mark.parametrize(
    ("params", "status"),
    [
        ({}, 422),
        ({"mes": "2030-03", "data": "2030-03-05"}, 422),
        ({"mes": "2030-13"}, 422),
        ({"mes": "março"}, 422),
        ({"de": "2030-03-01"}, 422),
        ({"de": "2030-03-10", "ate": "2030-03-01"}, 422),
        ({"de": "2030-03-01", "ate": "2030-05-01"}, 200),  # 62 dias inclusivos
        ({"de": "2030-03-01", "ate": "2030-05-02"}, 422),  # 63
        ({"mes": "2030-02"}, 200),
        ({"data": "2030-03-05"}, 200),
    ],
)
def test_agenda_intervalo(client, params, status):
    r = client.get("/reservas", params=params)
    assert r.status_code == status, r.text
    if status == 422:
        assert r.json()["codigo"] == "INTERVALO_INVALIDO"


def test_agenda_filtros(client, relogio, admin, professor, novo_professor, sala_id, aulas):
    m = aulas["manha"]
    outra = client.get("/salas", params={"busca": "Laboratório 02"}).json()[0]["id"]
    terceira = client.get("/salas", params={"busca": "Laboratório 03"}).json()[0]["id"]
    d = TERCA_REF.isoformat()
    a = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": d, "horario_ids": [m[0]]}).json()
    b = client.post("/reservas", headers=admin, json={"sala_id": outra, "data": d, "horario_ids": [m[0]]}).json()
    c = client.post("/reservas", headers=admin, json={"sala_id": terceira, "data": d, "horario_ids": [m[1]]}).json()
    client.post(f"/reservas/{c['id']}/cancelar", headers=admin)
    ids = lambda **q: [x["id"] for x in client.get("/reservas", params={"mes": "2030-03", **q}).json()]  # noqa: E731
    assert ids() == [a["id"], b["id"]]  # data, início, nome da sala
    assert set(ids(sala_id=[sala_id, terceira])) == {a["id"]}
    assert ids(professor_id=a["professor"]["id"]) == [a["id"]]
    assert ids(status="cancelada") == [c["id"]]
    assert set(ids(status="todas")) == {a["id"], b["id"], c["id"]}


def test_agenda_ordenacao_por_nome_da_sala(client, relogio, admin, sala_id, aulas):
    d = TERCA_REF.isoformat()
    salas = {s["nome"]: s["id"] for s in client.get("/salas").json()}
    for nome in ("Sala 03", "Laboratório 05", "Sala 01"):
        client.post("/reservas", headers=admin, json={"sala_id": salas[nome], "data": d, "horario_ids": [aulas["manha"][0]]})
    nomes = [x["sala"]["nome"] for x in client.get("/reservas", params={"data": d}).json()]
    assert nomes == ["Laboratório 05", "Sala 01", "Sala 03"]


def test_disponibilidade_do_dia(client, relogio, professor, sala_id, aulas):
    m = aulas["manha"]
    reserva = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": TERCA_REF.isoformat(), "horario_ids": m[1:3]}).json()
    relogio.definir(TERCA_REF, "08:00")
    disp = client.get(f"/salas/{sala_id}/disponibilidade", params={"data": TERCA_REF.isoformat()}).json()
    assert disp["dia_semana"] == 2 and len(disp["aulas"]) == 14
    por_id = {a["horario"]["id"]: a for a in disp["aulas"]}
    assert por_id[m[0]]["livre"] is True and por_id[m[0]]["passou"] is True
    assert por_id[m[1]]["livre"] is False and por_id[m[1]]["reserva"]["id"] == reserva["id"]
    assert por_id[m[2]]["reserva"]["professor"] == {"id": reserva["professor"]["id"], "nome": "Professor Um"}
    assert por_id[m[3]]["livre"] is True and por_id[m[3]]["passou"] is False
    domingo = client.get(f"/salas/{sala_id}/disponibilidade", params={"data": "2030-03-10"}).json()
    assert domingo["aulas"] == []
    sabado = client.get(f"/salas/{sala_id}/disponibilidade", params={"data": "2030-03-09"}).json()
    assert len(sabado["aulas"]) == 5


def test_ordenacao_minhas_passadas_usa_data_e_inicio(client, relogio, professor, sala_id, aulas):
    """Reservas criadas no passado (relógio recuado) aparecem em 'passadas' em ordem decrescente."""
    m = aulas["manha"]
    relogio.definir(date(2030, 3, 1), "06:00")
    ids = []
    for dias, h in ((4, m[0]), (4, m[3]), (6, m[0])):
        r = client.post("/reservas", headers=professor, json={"sala_id": sala_id, "data": (date(2030, 3, 1) + timedelta(days=dias)).isoformat(), "horario_ids": [h]})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    relogio.definir(date(2030, 3, 20), "06:00")
    passadas = [x["id"] for x in client.get("/reservas/minhas", headers=professor, params={"periodo": "passadas"}).json()]
    assert passadas == [ids[2], ids[1], ids[0]]
