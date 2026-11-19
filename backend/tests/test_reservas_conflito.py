"""Ticket 23: conflito (service + constraint), concorrência e aulas seguidas (RN03, RN04, RN05).

Tempo controlado: o fixture `relogio` fixa "agora" em TERCA_REF (terça 05/03/2030) às 06:00, salvo
quando o teste muda a hora.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.models import Professor, Reserva
from tests.conftest import TERCA_REF

TERCA = TERCA_REF.isoformat()
SABADO = (TERCA_REF + timedelta(days=4)).isoformat()
DOMINGO = (TERCA_REF + timedelta(days=5)).isoformat()


def reservar(client, headers, sala_id, data, horario_ids, **extra):
    return client.post("/reservas", headers=headers, json={"sala_id": sala_id, "data": data, "horario_ids": horario_ids, **extra})


def total_reservas(db) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Reserva))


# ---------------------------------------------------------------- RN04 conflito
# Grade da manhã: 1ª 07:30–08:20, 2ª 08:20–09:10, 3ª 09:30–10:20, 4ª 10:20–11:10, 5ª 11:10–12:00.
# Reserva existente: 2ª+3ª = 08:20–10:20.
@pytest.mark.parametrize(
    ("ordens", "esperado"),
    [
        ([2, 3], 409),  # mesmo bloco
        ([1, 2], 409),  # sobreposição parcial no começo
        ([3, 4], 409),  # sobreposição parcial no fim
        ([3], 409),  # contido
        ([1, 2, 3, 4], 409),  # contém
        ([1], 201),  # encosta antes (fim 08:20 = início 08:20)
        ([4], 201),  # encosta depois (início 10:20 = fim 10:20)
        ([4, 5], 201),
    ],
)
def test_regra_de_conflito(client, relogio, admin, professor, sala_id, aulas, ordens, esperado):
    manha = aulas["manha"]
    assert reservar(client, professor, sala_id, TERCA, [manha[1], manha[2]]).status_code == 201
    r = reservar(client, admin, sala_id, TERCA, [manha[o - 1] for o in ordens])
    assert r.status_code == esperado, r.text
    if esperado == 409:
        corpo = r.json()
        assert corpo["codigo"] == "CONFLITO_RESERVA"
        assert corpo["detail"] == "Sala não disponível neste horário."
        (c,) = corpo["conflitos"]
        assert c["data"] == TERCA and (c["inicio"], c["fim"]) == ("08:20", "10:20")
        assert c["sala_id"] == sala_id
        assert c["professor"] == {"id": c["professor"]["id"], "nome": "Professor Um"}


def test_conflito_lista_todas_as_reservas_sobrepostas(client, relogio, admin, professor, sala_id, aulas):
    manha = aulas["manha"]
    a = reservar(client, professor, sala_id, TERCA, [manha[0]]).json()
    b = reservar(client, admin, sala_id, TERCA, [manha[2]]).json()
    r = reservar(client, admin, sala_id, TERCA, manha[:4])
    assert r.status_code == 409
    assert [c["reserva_id"] for c in r.json()["conflitos"]] == [a["id"], b["id"]]


def test_outra_sala_ou_outra_data_nao_conflita(client, relogio, admin, professor, sala_id, aulas):
    manha = aulas["manha"]
    outra_sala = client.get("/salas", params={"busca": "Laboratório 02"}).json()[0]["id"]
    assert reservar(client, professor, sala_id, TERCA, manha[:2]).status_code == 201
    assert reservar(client, admin, outra_sala, TERCA, manha[:2]).status_code == 201
    quarta = (TERCA_REF + timedelta(days=1)).isoformat()
    assert reservar(client, admin, sala_id, quarta, manha[:2]).status_code == 201


def test_cancelada_nao_bloqueia_e_continua_no_historico(client, relogio, admin, professor, sala_id, aulas):
    manha = aulas["manha"]
    primeira = reservar(client, professor, sala_id, TERCA, manha[:2]).json()
    assert client.post(f"/reservas/{primeira['id']}/cancelar", headers=professor).status_code == 200
    segunda = reservar(client, admin, sala_id, TERCA, manha[:2])
    assert segunda.status_code == 201
    agenda = client.get("/reservas", params={"data": TERCA, "status": "todas"}).json()
    assert {(r["id"], r["status"]) for r in agenda} == {(primeira["id"], "cancelada"), (segunda.json()["id"], "ativa")}
    # reativar a cancelada seria uma sobreposição: o banco recusa (constraint parcial só sobre ativas)


def test_constraint_do_banco_barra_sobreposicao_sem_passar_pelo_service(db, relogio, sala_id, aulas, admin):
    """ADR-0003: mesmo um INSERT direto (sem a checagem do service) é recusado pelo Postgres."""
    admin_id = db.scalar(select(Professor.id).where(Professor.rm == "admin"))
    manha = aulas["manha"]

    def nova(inicio, fim, status="ativa"):
        extra = {}
        if status == "cancelada":
            from app.core.tempo import agora_tz

            extra = {"cancelada_em": agora_tz(), "cancelada_por_id": admin_id}
        return Reserva(
            sala_id=sala_id, professor_id=admin_id, criado_por_id=admin_id, data=TERCA_REF,
            inicio=inicio, fim=fim, horario_inicio_id=manha[0], horario_fim_id=manha[0],
            quantidade_aulas=1, status=status, **extra,
        )

    db.add(nova(time(7, 30), time(9, 10)))
    db.commit()
    db.add(nova(time(9, 10), time(10, 0)))  # encostada: aceita
    db.commit()
    db.add(nova(time(8, 0), time(8, 30), status="cancelada"))  # cancelada pode sobrepor
    db.commit()
    db.add(nova(time(8, 0), time(8, 30)))
    with pytest.raises(IntegrityError) as erro:
        db.commit()
    db.rollback()
    assert erro.value.orig.sqlstate == "23P01"
    assert erro.value.orig.diag.constraint_name == "ex_reservas_sem_sobreposicao"


def test_constraint_vira_409_com_conflitos_quando_o_service_nao_ve(client, relogio, admin, professor, sala_id, aulas, monkeypatch):
    """Simula a corrida: a checagem do service não vê nada; o INSERT bate na constraint → mesmo 409."""
    from app.services import reservas as servico

    manha = aulas["manha"]
    existente = reservar(client, professor, sala_id, TERCA, manha[:2]).json()
    original = servico.buscar_conflitos
    chamadas = {"n": 0}

    def cego_na_primeira(*args, **kwargs):
        chamadas["n"] += 1
        return [] if chamadas["n"] == 1 else original(*args, **kwargs)

    monkeypatch.setattr(servico, "buscar_conflitos", cego_na_primeira)
    r = reservar(client, admin, sala_id, TERCA, [manha[1]])
    assert r.status_code == 409, r.text
    assert r.json()["codigo"] == "CONFLITO_RESERVA"
    assert [c["reserva_id"] for c in r.json()["conflitos"]] == [existente["id"]]


# ---------------------------------------------------------------- concorrência
def _disparar_em_paralelo(n, funcao):
    barreira = threading.Barrier(n)

    def tarefa(i):
        with TestClient(app) as c:
            barreira.wait()
            return funcao(c, i)

    with ThreadPoolExecutor(n) as ex:
        return list(ex.map(tarefa, range(n)))


def test_concorrencia_mesmo_bloco_exatamente_um_sucesso(client, novo_professor, sala_id, aulas, db):
    n = 8
    quinta = (TERCA_REF + timedelta(days=2)).isoformat()  # data futura real (2030): não precisa de relógio
    profs = [novo_professor(f"conc{i}")[0] for i in range(n)]
    manha = aulas["manha"]

    respostas = _disparar_em_paralelo(
        n, lambda c, i: c.post("/reservas", headers=profs[i], json={"sala_id": sala_id, "data": quinta, "horario_ids": manha[:2]})
    )
    codigos = sorted(r.status_code for r in respostas)
    assert codigos == [201] + [409] * (n - 1), [r.text for r in respostas]
    assert all(r.json()["codigo"] == "CONFLITO_RESERVA" for r in respostas if r.status_code == 409)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Reserva).where(Reserva.status == "ativa")) == 1


def test_concorrencia_blocos_que_se_sobrepoem_parcialmente(client, admin, sala_id, aulas, db):
    """[1ª,2ª] contra [2ª,3ª] contra [2ª] ao mesmo tempo: só um pode ficar."""
    sexta = (TERCA_REF + timedelta(days=3)).isoformat()
    m = aulas["manha"]
    blocos = [[m[0], m[1]], [m[1], m[2]], [m[1]], [m[0], m[1], m[2]]]
    respostas = _disparar_em_paralelo(
        len(blocos),
        lambda c, i: c.post("/reservas", headers=admin, json={"sala_id": sala_id, "data": sexta, "horario_ids": blocos[i]}),
    )
    assert sorted(r.status_code for r in respostas) == [201, 409, 409, 409], [r.text for r in respostas]
    assert total_reservas(db) == 1


def test_concorrencia_recorrencias_que_disputam_uma_data_sao_atomicas(client, admin, novo_professor, semestre_ref, sala_id, aulas, db):
    """Duas confirmações recorrentes simultâneas que compartilham datas: uma grava tudo, a outra nada."""
    p1, _ = novo_professor("rec1")
    p2, _ = novo_professor("rec2")
    m = aulas["manha"]
    serie = [(TERCA_REF + timedelta(weeks=k)).isoformat() for k in range(4)]
    corpos = [
        {"sala_id": sala_id, "data_inicio": serie[0], "horario_ids": m[:2], "datas": serie},
        {"sala_id": sala_id, "data_inicio": serie[0], "horario_ids": [m[1]], "datas": serie[2:]},
    ]
    headers = [p1, p2]
    respostas = _disparar_em_paralelo(2, lambda c, i: c.post("/reservas/recorrentes", headers=headers[i], json=corpos[i]))
    assert sorted(r.status_code for r in respostas) == [201, 409], [r.text for r in respostas]
    vencedor = next(r for r in respostas if r.status_code == 201).json()
    db.expire_all()
    assert total_reservas(db) == len(vencedor["reservas"])
    grupos = db.scalar(select(func.count(func.distinct(Reserva.grupo_recorrencia_id))))
    assert grupos == 1


# ---------------------------------------------------------------- RN03 aulas seguidas (via API)
@pytest.mark.parametrize(
    ("montar", "data", "status", "codigo"),
    [
        (lambda a: [a["manha"][-1], a["tarde"][0]], TERCA, 422, "AULAS_NAO_SEGUIDAS"),  # turno misto
        (lambda a: [a["manha"][0], a["manha"][2]], TERCA, 422, "AULAS_NAO_SEGUIDAS"),  # buraco
        (lambda a: [a["manha"][0], a["manha"][1], a["manha"][3]], TERCA, 422, "AULAS_NAO_SEGUIDAS"),
        (lambda a: [a["noite"][0]], SABADO, 422, "AULA_INVALIDA_NO_DIA"),  # noite não vale sábado
        (lambda a: [a["tarde"][0], a["tarde"][1]], SABADO, 422, "AULA_INVALIDA_NO_DIA"),
        (lambda a: [a["manha"][0]], DOMINGO, 422, "AULA_INVALIDA_NO_DIA"),
        (lambda a: [], TERCA, 422, "VALIDACAO"),
        (lambda a: [a["manha"][0], a["manha"][0]], TERCA, 422, "VALIDACAO"),
        (lambda a: [999999], TERCA, 404, "NAO_ENCONTRADO"),
        (lambda a: [a["manha"][4], a["manha"][3], a["manha"][2]], TERCA, 201, None),  # ordem dos ids não importa
        (lambda a: [a["manha"][0], a["manha"][1]], SABADO, 201, None),  # há aula aos sábados (manhã)
        (lambda a: [a["noite"][2], a["noite"][3]], TERCA, 201, None),
    ],
)
def test_aulas_seguidas(client, relogio, professor, sala_id, aulas, montar, data, status, codigo):
    r = reservar(client, professor, sala_id, data, montar(aulas))
    assert r.status_code == status, r.text
    if codigo:
        assert r.json()["codigo"] == codigo


def test_aula_inativa_nao_pode_ser_reservada(client, relogio, admin, professor, sala_id, aulas):
    m = aulas["manha"]
    h = client.get(f"/horarios/{m[1]}").json()
    corpo = {k: h[k] for k in ("turno", "ordem", "inicio", "fim", "dias_semana")} | {"ativo": False}
    assert client.put(f"/horarios/{m[1]}", headers=admin, json=corpo).status_code == 200
    r = reservar(client, professor, sala_id, TERCA, [m[0], m[1]])
    assert (r.status_code, r.json()["codigo"]) == (422, "AULAS_NAO_SEGUIDAS")
    r = reservar(client, professor, sala_id, TERCA, [m[1]])
    assert (r.status_code, r.json()["codigo"]) == (422, "AULAS_NAO_SEGUIDAS")


def test_bloco_guarda_snapshot_e_intervalo_dentro_do_bloco(client, relogio, admin, professor, sala_id, aulas):
    """O intervalo 09:10–09:30 fica dentro do bloco 2ª+3ª; editar a grade depois não muda a reserva."""
    m = aulas["manha"]
    reserva = reservar(client, professor, sala_id, TERCA, [m[1], m[2]]).json()
    assert (reserva["inicio"], reserva["fim"], reserva["quantidade_aulas"]) == ("08:20", "10:20", 2)
    assert (reserva["horario_inicio_id"], reserva["horario_fim_id"]) == (m[1], m[2])
    h = client.get(f"/horarios/{m[2]}").json()
    corpo = {k: h[k] for k in ("turno", "ordem", "dias_semana", "ativo")} | {"inicio": "09:40", "fim": "10:15"}
    assert client.put(f"/horarios/{m[2]}", headers=admin, json=corpo).status_code == 200
    assert client.get(f"/reservas/{reserva['id']}").json()["fim"] == "10:20"


# ---------------------------------------------------------------- RN05 data passada
@pytest.mark.parametrize(
    ("agora", "ordem", "status"),
    [
        ("09:00", 1, 422),  # 07:30 já passou
        ("09:30", 3, 422),  # começa exatamente agora → já começou
        ("09:29", 3, 201),
        ("09:00", 4, 201),
    ],
)
def test_data_passada_hoje(client, relogio, professor, sala_id, aulas, agora, ordem, status):
    relogio.definir(TERCA_REF, agora)
    r = reservar(client, professor, sala_id, TERCA, [aulas["manha"][ordem - 1]])
    assert r.status_code == status, r.text
    if status == 422:
        assert r.json()["codigo"] == "DATA_PASSADA"


def test_data_passada_vale_para_admin_e_ontem(client, relogio, admin, sala_id, aulas):
    ontem = (TERCA_REF - timedelta(days=1)).isoformat()
    r = reservar(client, admin, sala_id, ontem, [aulas["noite"][0]])
    assert (r.status_code, r.json()["codigo"]) == (422, "DATA_PASSADA")


def test_reserva_avulsa_fora_de_semestre_e_permitida(client, relogio, professor, sala_id, aulas):
    r = reservar(client, professor, sala_id, "2035-01-09", [aulas["manha"][0]])  # nenhum semestre em 2035
    assert r.status_code == 201, r.text


# ---------------------------------------------------------------- sala e professor_id
def test_sala_inexistente_e_inativa(client, relogio, admin, professor, sala_id, aulas):
    m = aulas["manha"]
    r = reservar(client, professor, 999999, TERCA, [m[0]])
    assert (r.status_code, r.json()["codigo"]) == (404, "NAO_ENCONTRADO")
    sala = client.get(f"/salas/{sala_id}").json()
    corpo = {k: sala[k] for k in ("nome", "tipo", "descricao", "capacidade", "localizacao")} | {"ativo": False}
    assert client.put(f"/salas/{sala_id}", headers=admin, json=corpo).status_code == 200
    for quem in (professor, admin):
        r = reservar(client, quem, sala_id, TERCA, [m[0]])
        assert (r.status_code, r.json()["codigo"]) == (422, "SALA_INATIVA")


def test_professor_id_no_corpo(client, db, relogio, admin, professor, novo_professor, sala_id, aulas):
    m = aulas["manha"]
    outro_h, outro = novo_professor("outro1", "Outro Prof")
    # professor não pode reservar em nome de outro (nem de si mesmo pelo corpo)
    for pid in (outro["id"], 1):
        r = reservar(client, professor, sala_id, TERCA, [m[0]], professor_id=pid)
        assert (r.status_code, r.json()["codigo"]) == (403, "SEM_PERMISSAO")
    # admin pode: dono = professor indicado, criado_por = admin
    r = reservar(client, admin, sala_id, TERCA, [m[0]], professor_id=outro["id"])
    assert r.status_code == 201, r.text
    assert r.json()["professor"] == {"id": outro["id"], "nome": "Outro Prof"}
    linha = db.get(Reserva, r.json()["id"])
    admin_id = db.scalar(select(Professor.id).where(Professor.rm == "admin"))
    assert (linha.professor_id, linha.criado_por_id) == (outro["id"], admin_id)
    # aparece em "minhas" do dono, que pode cancelar
    minhas = client.get("/reservas/minhas", headers=outro_h).json()
    assert [x["id"] for x in minhas] == [r.json()["id"]] and minhas[0]["pode_cancelar"] is True
    # professor inexistente / inativo
    r = reservar(client, admin, sala_id, TERCA, [m[1]], professor_id=999999)
    assert (r.status_code, r.json()["codigo"]) == (404, "NAO_ENCONTRADO")
    assert client.put(f"/professores/{outro['id']}", headers=admin, json={"nome": "Outro Prof", "email": None, "papel": "professor", "ativo": False}).status_code == 200
    r = reservar(client, admin, sala_id, TERCA, [m[1]], professor_id=outro["id"])
    assert (r.status_code, r.json()["codigo"]) == (422, "PROFESSOR_INATIVO")


def test_observacao_limite(client, relogio, professor, sala_id, aulas):
    m = aulas["manha"]
    r = reservar(client, professor, sala_id, TERCA, [m[0]], observacao="x" * 201)
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    r = reservar(client, professor, sala_id, TERCA, [m[0]], observacao="x" * 200)
    assert r.status_code == 201
