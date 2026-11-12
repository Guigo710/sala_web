"""Testes de fumaça dos fluxos principais (a suíte completa é do Sentinela)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from tests.conftest import proximo_dia_semana


def test_saude(client):
    r = client.get("/saude")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_admin_e_me(client, admin):
    r = client.get("/auth/me", headers=admin)
    assert r.status_code == 200
    assert r.json()["papel"] == "admin"
    assert "senha_hash" not in r.json()


def test_credenciais_invalidas_e_rate_limit(client):
    for _ in range(5):
        r = client.post("/auth/login", json={"rm": "admin", "senha": "errada"})
        assert r.status_code == 401
        assert r.json() == {"detail": "RM ou senha inválidos.", "codigo": "CREDENCIAIS_INVALIDAS"}
    r = client.post("/auth/login", json={"rm": "admin", "senha": "senhaAdmin123"})
    assert r.status_code == 429
    assert r.json()["codigo"] == "MUITAS_TENTATIVAS"


def test_envelope_de_validacao(client, admin):
    r = client.post("/salas", headers=admin, json={"nome": "X", "tipo": "sala", "capacidade": 0})
    assert r.status_code == 422
    corpo = r.json()
    assert corpo["codigo"] == "VALIDACAO"
    assert {"campo": "body.capacidade", "mensagem": "deve ser maior que 0"} in corpo["erros"]


def test_permissoes(client, professor):
    assert client.post("/salas", json={"nome": "X", "tipo": "sala", "capacidade": 1}).status_code == 401
    r = client.post("/salas", headers=professor, json={"nome": "X", "tipo": "sala", "capacidade": 1})
    assert r.status_code == 403
    assert r.json()["codigo"] == "SEM_PERMISSAO"


def test_seed(client):
    salas = client.get("/salas").json()
    assert sum(s["tipo"] == "sala" for s in salas) == 14
    assert sum(s["tipo"] == "lab_informatica" for s in salas) == 13
    sabado = client.get("/horarios", params={"dia_semana": 6}).json()
    assert len(sabado) == 5 and all(h["turno"] == "manha" for h in sabado)


def test_seed_idempotente(client, db):
    from app.seed import executar

    executar(db)
    executar(db)
    assert len(client.get("/salas").json()) == 27
    assert len(client.get("/horarios").json()) == 14


def test_criar_sala(client, admin):
    r = client.post(
        "/salas",
        headers=admin,
        json={"nome": "Auditório", "tipo": "auditorio", "capacidade": 120, "localizacao": "Bloco A"},
    )
    assert r.status_code == 201
    sala = r.json()
    assert sala["tipo_rotulo"] == "Auditório"
    assert sala["fotos"] == [] and sala["foto_capa_url"] is None
    r = client.post("/salas", headers=admin, json={"nome": "Auditório", "tipo": "auditorio", "capacidade": 1})
    assert r.status_code == 409 and r.json()["codigo"] == "NOME_DUPLICADO"


def test_reserva_avulsa_e_conflito(client, professor, admin, sala_id, aulas_manha):
    terca = proximo_dia_semana(2).isoformat()
    r = client.post(
        "/reservas",
        headers=professor,
        json={"sala_id": sala_id, "data": terca, "horario_ids": [aulas_manha[1], aulas_manha[0]]},
    )
    assert r.status_code == 201, r.text
    reserva = r.json()
    assert (reserva["inicio"], reserva["fim"], reserva["quantidade_aulas"]) == ("07:30", "09:10", 2)
    assert reserva["pode_cancelar"] is True

    r = client.post(
        "/reservas", headers=admin, json={"sala_id": sala_id, "data": terca, "horario_ids": [aulas_manha[1]]}
    )
    assert r.status_code == 409
    assert r.json()["codigo"] == "CONFLITO_RESERVA"
    assert r.json()["conflitos"][0]["reserva_id"] == reserva["id"]

    # encostada (09:30 começa depois de 09:10) não conflita
    r = client.post(
        "/reservas", headers=admin, json={"sala_id": sala_id, "data": terca, "horario_ids": [aulas_manha[2]]}
    )
    assert r.status_code == 201

    # agenda pública não expõe RM e não deixa visitante cancelar
    agenda = client.get("/reservas", params={"data": terca}).json()
    assert len(agenda) == 2
    assert all("rm" not in r["professor"] and r["pode_cancelar"] is False for r in agenda)


def test_regras_de_criacao(client, professor, sala_id, aulas_manha):
    terca = proximo_dia_semana(2).isoformat()
    domingo = proximo_dia_semana(7).isoformat()
    casos = [
        ({"data": terca, "horario_ids": [aulas_manha[0], aulas_manha[2]]}, 422, "AULAS_NAO_SEGUIDAS"),
        ({"data": domingo, "horario_ids": [aulas_manha[0]]}, 422, "AULA_INVALIDA_NO_DIA"),
        ({"data": "2020-01-07", "horario_ids": [aulas_manha[0]]}, 422, "DATA_PASSADA"),
        ({"data": terca, "horario_ids": [aulas_manha[0]], "professor_id": 1}, 403, "SEM_PERMISSAO"),
    ]
    for extra, status, codigo in casos:
        r = client.post("/reservas", headers=professor, json={"sala_id": sala_id, **extra})
        assert (r.status_code, r.json()["codigo"]) == (status, codigo), extra


def test_concorrencia_um_201_e_resto_409(admin, sala_id, aulas_manha):
    quinta = proximo_dia_semana(4, semanas_a_frente=2).isoformat()

    def tentar(_):
        with TestClient(app) as c:
            return c.post(
                "/reservas", headers=admin, json={"sala_id": sala_id, "data": quinta, "horario_ids": [aulas_manha[0]]}
            ).status_code

    with ThreadPoolExecutor(6) as ex:
        codigos = sorted(ex.map(tentar, range(6)))
    assert codigos == [201, 409, 409, 409, 409, 409]


def test_recorrencia_previa_e_confirmacao(client, db, admin, professor, sala_id, aulas_manha):
    # semestre próprio cobrindo 4 quartas a partir da próxima (independe da data de hoje)
    inicio = proximo_dia_semana(3, semanas_a_frente=1)
    fim = inicio + timedelta(weeks=3)
    db.execute(text("DELETE FROM semestres"))
    db.commit()
    r = client.post(
        "/semestres",
        headers=admin,
        json={"nome": "T-1", "data_inicio": (inicio - timedelta(days=1)).isoformat(), "data_fim": fim.isoformat()},
    )
    assert r.status_code == 201, r.text

    ocupada = (inicio + timedelta(weeks=1)).isoformat()
    assert (
        client.post(
            "/reservas", headers=admin, json={"sala_id": sala_id, "data": ocupada, "horario_ids": [aulas_manha[0]]}
        ).status_code
        == 201
    )

    corpo = {"sala_id": sala_id, "data_inicio": inicio.isoformat(), "horario_ids": [aulas_manha[0], aulas_manha[1]]}
    r = client.post("/reservas/recorrentes/previa", headers=professor, json=corpo)
    assert r.status_code == 200, r.text
    previa = r.json()
    assert previa["dia_semana"] == 3
    assert previa["total"] == 4
    assert previa["em_conflito"] == 1
    assert previa["ocorrencias"][1] == {
        "data": ocupada,
        "livre": False,
        "conflitos": [previa["ocorrencias"][1]["conflitos"][0]],
    }
    todas = [o["data"] for o in previa["ocorrencias"]]
    livres = [o["data"] for o in previa["ocorrencias"] if o["livre"]]

    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": todas})
    assert r.status_code == 409 and r.json()["codigo"] == "CONFLITO_RESERVA"

    r = client.post(
        "/reservas/recorrentes", headers=professor, json={**corpo, "datas": [(inicio + timedelta(days=1)).isoformat()]}
    )
    assert r.status_code == 422 and r.json()["codigo"] == "DATA_FORA_DA_SERIE"

    r = client.post("/reservas/recorrentes", headers=professor, json={**corpo, "datas": livres})
    assert r.status_code == 201, r.text
    grupo = r.json()["grupo"]
    assert grupo["total_ocorrencias"] == len(livres) == grupo["ocorrencias_ativas"]
    assert [x["data"] for x in r.json()["reservas"]] == sorted(livres)

    r = client.post(f"/reservas/grupos/{grupo['id']}/cancelar", headers=professor)
    assert r.status_code == 200
    assert r.json()["canceladas"] == len(livres)


def test_sem_semestre(client, professor, sala_id, aulas_manha):
    r = client.post(
        "/reservas/recorrentes/previa",
        headers=professor,
        json={"sala_id": sala_id, "data_inicio": "2035-03-06", "horario_ids": [aulas_manha[0]]},
    )
    assert r.status_code == 422 and r.json()["codigo"] == "SEM_SEMESTRE"


def test_cancelamento(client, professor, admin, sala_id, aulas_manha):
    sexta = proximo_dia_semana(5).isoformat()
    corpo = {"sala_id": sala_id, "data": sexta, "horario_ids": [aulas_manha[0]]}
    reserva = client.post("/reservas", headers=professor, json=corpo).json()

    r = client.post(f"/reservas/{reserva['id']}/cancelar", headers=professor, json={"motivo": "Aula remanejada"})
    assert r.status_code == 200
    cancelada = r.json()
    assert cancelada["status"] == "cancelada"
    assert cancelada["motivo_cancelamento"] == "Aula remanejada"
    assert cancelada["cancelada_por"]["nome"] == "Professor Um"
    assert cancelada["cancelada_em"] is not None

    r = client.post(f"/reservas/{reserva['id']}/cancelar", headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "RESERVA_JA_CANCELADA"

    # horário liberado: dá para reservar de novo
    assert client.post("/reservas", headers=admin, json=corpo).status_code == 201
    # cancelada continua no histórico
    assert client.get(f"/reservas/{reserva['id']}").json()["status"] == "cancelada"


def test_cancelar_reserva_ja_iniciada(client, db, professor, admin, sala_id, aulas_manha):
    from app.core.tempo import hoje
    from app.models import Professor, Reserva

    prof = db.query(Professor).filter_by(rm="prof01").one()
    ontem = Reserva(
        sala_id=sala_id,
        professor_id=prof.id,
        data=hoje() - timedelta(days=1),
        inicio=__import__("datetime").time(7, 30),
        fim=__import__("datetime").time(8, 20),
        horario_inicio_id=aulas_manha[0],
        horario_fim_id=aulas_manha[0],
        quantidade_aulas=1,
        criado_por_id=prof.id,
    )
    db.add(ontem)
    db.commit()

    minhas = client.get("/reservas/minhas", headers=professor, params={"periodo": "passadas"}).json()
    assert [r["id"] for r in minhas] == [ontem.id]
    assert minhas[0]["pode_cancelar"] is False
    assert client.get("/reservas/minhas", headers=professor).json() == []

    r = client.post(f"/reservas/{ontem.id}/cancelar", headers=professor)
    assert r.status_code == 422 and r.json()["codigo"] == "RESERVA_JA_INICIADA"
    r = client.post(f"/reservas/{ontem.id}/cancelar", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "cancelada"


def test_upload_foto(client, admin, sala_id):
    r = client.post(
        f"/salas/{sala_id}/fotos",
        headers=admin,
        files={"arquivo": ("../../evil.jpg", b"\xff\xd8\xff\xe0" + b"0" * 64, "image/jpeg")},
        data={"legenda": "Vista da porta"},
    )
    assert r.status_code == 201, r.text
    foto = r.json()
    assert foto["url"].startswith(f"/uploads/salas/{sala_id}/") and foto["url"].endswith(".jpg")
    assert "evil" not in foto["url"]
    assert client.get(foto["url"]).status_code == 200

    texto = client.post(f"/salas/{sala_id}/fotos", headers=admin, files={"arquivo": ("a.jpg", b"ola", "image/jpeg")})
    assert texto.status_code == 415 and texto.json()["codigo"] == "TIPO_ARQUIVO_INVALIDO"

    grande = b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 1)
    r = client.post(f"/salas/{sala_id}/fotos", headers=admin, files={"arquivo": ("g.jpg", grande, "image/jpeg")})
    assert r.status_code == 413 and r.json()["codigo"] == "ARQUIVO_GRANDE"

    assert client.delete(f"/salas/{sala_id}/fotos/{foto['id']}", headers=admin).status_code == 204
    assert client.get(foto["url"]).status_code == 404
