"""Ticket 24: filtros de GET /salas, catálogo (equipamentos/softwares/horários/semestres) e upload de fotos."""

import os
from pathlib import Path

import pytest

from app.core.config import obter_config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64


def ids_salas(client, headers=None, **params):
    r = client.get("/salas", params=params, headers=headers or {})
    assert r.status_code == 200, r.text
    return [s["nome"] for s in r.json()]


@pytest.fixture
def catalogo(client, admin):
    """Equipamentos/softwares por nome e salas por nome."""
    eq = {e["nome"]: e["id"] for e in client.get("/equipamentos").json()}
    sw = {s["nome"]: s["id"] for s in client.get("/softwares").json()}
    salas = {s["nome"]: s["id"] for s in client.get("/salas").json()}
    return eq, sw, salas


# ---------------------------------------------------------------- filtros de /salas
def test_filtro_tipo_e_capacidade(client, admin, catalogo):
    _, _, salas = catalogo
    client.post("/salas", headers=admin, json={"nome": "Auditório", "tipo": "auditorio", "capacidade": 200})
    assert len(ids_salas(client, tipo="lab_informatica")) == 13
    assert len(ids_salas(client, tipo=["sala", "auditorio"])) == 15
    assert ids_salas(client, capacidade_min=41) == ["Auditório"]
    assert len(ids_salas(client, capacidade_min=40, tipo="sala")) == 14
    assert client.get("/salas", params={"tipo": "piscina"}).status_code == 422
    assert client.get("/salas", params={"capacidade_min": 0}).status_code == 422
    nomes = ids_salas(client)
    assert nomes == sorted(nomes)


def test_filtro_equipamento_e_software_sao_E(client, admin, catalogo):
    eq, sw, salas = catalogo
    s1, s2 = salas["Sala 01"], salas["Sala 02"]
    client.put(f"/salas/{s1}/equipamentos", headers=admin, json=[{"equipamento_id": eq["Projetor"], "quantidade": 1}, {"equipamento_id": eq["Ar-condicionado"], "quantidade": 2}])
    client.put(f"/salas/{s2}/equipamentos", headers=admin, json=[{"equipamento_id": eq["Projetor"], "quantidade": 1}])
    client.put(f"/salas/{s1}/softwares", headers=admin, json={"software_ids": [sw["Git"]]})

    com_projetor = ids_salas(client, equipamento_id=eq["Projetor"])
    assert "Sala 01" in com_projetor and "Sala 02" in com_projetor and len(com_projetor) == 15
    assert ids_salas(client, equipamento_id=[eq["Projetor"], eq["Ar-condicionado"]]) == ["Sala 01"]
    assert len(ids_salas(client, software_id=sw["Git"])) == 14
    assert ids_salas(client, software_id=sw["Git"], tipo="sala") == ["Sala 01"]
    assert ids_salas(client, software_id=[sw["Git"], sw["Python"]], tipo="sala") == []
    assert ids_salas(client, equipamento_id=999999) == []


def test_filtro_busca(client, admin):
    client.post("/salas", headers=admin, json={"nome": "Lab de Redes", "tipo": "lab_outro", "capacidade": 20, "localizacao": "Bloco 100% novo", "descricao": "Switches_e_roteadores"})
    assert ids_salas(client, busca="redes") == ["Lab de Redes"]
    assert ids_salas(client, busca="100%") == ["Lab de Redes"]
    assert ids_salas(client, busca="es_e") == ["Lab de Redes"]
    assert ids_salas(client, busca="  ") == ids_salas(client)


def test_filtro_disponibilidade(client, admin, relogio, catalogo, aulas):
    _, _, salas = catalogo
    m = aulas["manha"]
    d = "2030-03-05"
    client.post("/reservas", headers=admin, json={"sala_id": salas["Sala 01"], "data": d, "horario_ids": [m[1]]})
    livres = ids_salas(client, data=d, horario_ids=[m[0], m[1]])
    assert "Sala 01" not in livres and len(livres) == 26
    assert "Sala 01" in ids_salas(client, data=d, horario_ids=[m[2]])  # encostada
    r = client.get("/salas", params={"data": d})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    r = client.get("/salas", params={"horario_ids": m[0]})
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    r = client.get("/salas", params={"data": d, "horario_ids": [m[0], m[2]]})
    assert r.json()["codigo"] == "AULAS_NAO_SEGUIDAS"
    r = client.get("/salas", params={"data": "2030-03-10", "horario_ids": m[0]})
    assert r.json()["codigo"] == "AULA_INVALIDA_NO_DIA"
    assert client.get("/salas", params={"data": "2020-01-07", "horario_ids": m[0]}).status_code == 200  # passada não é erro


def test_sala_inativa_some_para_publico(client, admin, professor, catalogo):
    _, _, salas = catalogo
    sid = salas["Sala 05"]
    client.put(f"/salas/{sid}", headers=admin, json={"nome": "Sala 05", "tipo": "sala", "capacidade": 40, "ativo": False})
    for headers in ({}, professor):
        assert "Sala 05" not in ids_salas(client, headers, incluir_inativas=True)
        assert client.get(f"/salas/{sid}", headers=headers).status_code == 404
        assert client.get(f"/salas/{sid}/disponibilidade", headers=headers, params={"data": "2030-03-05"}).status_code == 404
        assert client.get(f"/salas/{sid}/fotos", headers=headers).status_code == 404
    assert "Sala 05" not in ids_salas(client, admin)
    assert "Sala 05" in ids_salas(client, admin, incluir_inativas=True)
    assert client.get(f"/salas/{sid}", headers=admin).json()["ativo"] is False


def test_excluir_sala_com_reserva(client, admin, relogio, catalogo, aulas):
    _, _, salas = catalogo
    sid = salas["Sala 06"]
    r = client.post("/reservas", headers=admin, json={"sala_id": sid, "data": "2030-03-05", "horario_ids": [aulas["manha"][0]]})
    client.post(f"/reservas/{r.json()['id']}/cancelar", headers=admin)
    r = client.delete(f"/salas/{sid}", headers=admin)
    assert (r.status_code, r.json()["codigo"]) == (409, "SALA_COM_RESERVAS")
    assert client.delete(f"/salas/{salas['Sala 07']}", headers=admin).status_code == 204


# ---------------------------------------------------------------- catálogo
def test_equipamentos_da_sala(client, admin, catalogo):
    eq, _, salas = catalogo
    sid = salas["Sala 01"]
    r = client.put(f"/salas/{sid}/equipamentos", headers=admin, json=[{"equipamento_id": eq["Projetor"], "quantidade": 1}, {"equipamento_id": eq["Projetor"], "quantidade": 2}])
    assert (r.status_code, r.json()["codigo"]) == (422, "VALIDACAO")
    r = client.put(f"/salas/{sid}/equipamentos", headers=admin, json=[{"equipamento_id": 999999}])
    assert r.status_code == 404
    r = client.put(f"/salas/{sid}/equipamentos", headers=admin, json=[{"equipamento_id": eq["Projetor"], "quantidade": 0}])
    assert r.status_code == 422
    r = client.put(f"/salas/{sid}/equipamentos", headers=admin, json=[{"equipamento_id": eq["Projetor"], "especificacao": "Full HD"}])
    assert r.json()["equipamentos"] == [{"equipamento_id": eq["Projetor"], "nome": "Projetor", "quantidade": 1, "especificacao": "Full HD"}]
    assert client.put(f"/salas/{sid}/equipamentos", headers=admin, json=[]).json()["equipamentos"] == []


def test_excluir_equipamento_remove_das_salas(client, admin, catalogo):
    eq, _, salas = catalogo
    assert client.delete(f"/equipamentos/{eq['Computador']}", headers=admin).status_code == 204
    lab = client.get(f"/salas/{salas['Laboratório 01']}").json()
    assert [e["nome"] for e in lab["equipamentos"]] == ["Projetor"]


def test_softwares_duplicidade_e_categorias(client, admin):
    r = client.post("/softwares", headers=admin, json={"nome": "Git", "versao": None, "categoria": "X"})
    assert (r.status_code, r.json()["codigo"]) == (409, "NOME_DUPLICADO")
    assert client.post("/softwares", headers=admin, json={"nome": "Git", "versao": "2.40"}).status_code == 201
    cats = client.get("/softwares/categorias").json()
    assert cats == sorted(cats) and "IDE" in cats


def test_horarios_regras(client, admin, aulas):
    base = {"turno": "manha", "ordem": 9, "inicio": "12:00", "fim": "12:50", "dias_semana": [1], "ativo": True}
    assert client.post("/horarios", headers=admin, json={**base, "ordem": 1}).json()["codigo"] == "ORDEM_DUPLICADA"
    assert client.post("/horarios", headers=admin, json={**base, "inicio": "11:30"}).json()["codigo"] == "HORARIO_SOBREPOSTO"
    assert client.post("/horarios", headers=admin, json={**base, "fim": "11:00"}).status_code == 422
    assert client.post("/horarios", headers=admin, json={**base, "dias_semana": []}).status_code == 422
    assert client.post("/horarios", headers=admin, json={**base, "dias_semana": [0, 8]}).status_code == 422
    r = client.post("/horarios", headers=admin, json={**base, "inicio": "12:00:59"})
    assert r.status_code == 201 and r.json()["inicio"] == "12:00"
    sabado = client.get("/horarios", params={"dia_semana": 6}).json()
    assert all(6 in h["dias_semana"] for h in sabado)


def test_horario_em_uso(client, admin, relogio, sala_id, aulas):
    m = aulas["manha"]
    client.post("/reservas", headers=admin, json={"sala_id": sala_id, "data": "2030-03-05", "horario_ids": [m[0], m[1]]})
    r = client.delete(f"/horarios/{m[0]}", headers=admin)
    assert (r.status_code, r.json()["codigo"]) == (409, "HORARIO_EM_USO")


def test_semestres_regras(client, admin, relogio, semestre_ref, professor, sala_id, aulas):
    base = {"nome": "X", "data_inicio": "2030-06-01", "data_fim": "2030-07-30"}
    assert client.post("/semestres", headers=admin, json=base).json()["codigo"] == "SEMESTRE_SOBREPOSTO"
    assert client.post("/semestres", headers=admin, json={**base, "nome": "2030-1", "data_inicio": "2031-01-01", "data_fim": "2031-01-30"}).json()["codigo"] == "NOME_DUPLICADO"
    assert client.post("/semestres", headers=admin, json={"nome": "Y", "data_inicio": "2031-03-01", "data_fim": "2031-03-01"}).status_code == 422
    corpo = {"sala_id": sala_id, "data_inicio": "2030-03-05", "horario_ids": [aulas["manha"][0]], "datas": ["2030-03-05"]}
    assert client.post("/reservas/recorrentes", headers=professor, json=corpo).status_code == 201
    r = client.delete(f"/semestres/{semestre_ref['id']}", headers=admin)
    assert (r.status_code, r.json()["codigo"]) == (409, "SEMESTRE_EM_USO")
    assert client.get("/semestres/atual").json()["nome"] == "2030-1"


# ---------------------------------------------------------------- upload de fotos
def _arquivos_em_disco() -> set[Path]:
    base = obter_config().upload_dir
    return {p for p in base.rglob("*") if p.is_file()}


def enviar(client, headers, sala_id, nome, conteudo, tipo="image/jpeg", **data):
    return client.post(f"/salas/{sala_id}/fotos", headers=headers, files={"arquivo": (nome, conteudo, tipo)}, data=data)


@pytest.mark.parametrize(("conteudo", "ext"), [(JPG, "jpg"), (PNG, "png"), (WEBP, "webp")])
def test_upload_formatos_aceitos_extensao_pelo_conteudo(client, admin, sala_id, conteudo, ext):
    r = enviar(client, admin, sala_id, "foto.gif", conteudo, "application/octet-stream")
    assert r.status_code == 201, r.text
    assert r.json()["url"].endswith(f".{ext}")
    servido = client.get(r.json()["url"])
    assert servido.status_code == 200 and servido.content == conteudo


@pytest.mark.parametrize(
    "conteudo",
    [
        b"GIF89a" + b"\x00" * 32,
        b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>",
        b"<html><script>alert(1)</script></html>",
        b"%PDF-1.4",
        b"",
        b"\xff\xd8",  # JPEG truncado (assinatura incompleta)
        b"RIFF\x00\x00\x00\x00WAVEfmt ",  # RIFF que não é WebP
    ],
)
def test_upload_tipo_falso_415(client, admin, sala_id, conteudo):
    antes = _arquivos_em_disco()
    r = enviar(client, admin, sala_id, "foto.jpg", conteudo, "image/jpeg")
    assert (r.status_code, r.json()["codigo"]) == (415, "TIPO_ARQUIVO_INVALIDO")
    assert _arquivos_em_disco() == antes


def test_upload_grande_413_nos_dois_caminhos(client, admin, sala_id):
    limite = obter_config().upload_max_bytes
    antes = _arquivos_em_disco()
    # um pouco acima do limite: passa pelo middleware (folga multipart) e é barrado na leitura em blocos
    r = enviar(client, admin, sala_id, "g.jpg", JPG + b"0" * (limite - len(JPG) + 1))
    assert (r.status_code, r.json()["codigo"]) == (413, "ARQUIVO_GRANDE")
    # muito acima: barrado cedo pelo Content-Length
    r = enviar(client, admin, sala_id, "g.jpg", JPG + b"0" * (limite + 1024 * 1024))
    assert (r.status_code, r.json()["codigo"]) == (413, "ARQUIVO_GRANDE")
    # exatamente no limite: aceito
    r = enviar(client, admin, sala_id, "ok.jpg", JPG + b"0" * (limite - len(JPG)))
    assert r.status_code == 201
    assert len(_arquivos_em_disco() - antes) == 1


@pytest.mark.parametrize("nome", ["../../x.jpg", "..\\..\\x.jpg", "/etc/passwd", "a/../../../b.jpg", "x.jpg\x00.sh", "....//....//x.jpg", "%2e%2e%2fx.jpg"])
def test_upload_nome_malicioso_nao_escapa(client, admin, sala_id, nome):
    base = obter_config().upload_dir
    r = enviar(client, admin, sala_id, nome, JPG)
    assert r.status_code == 201, r.text
    url = r.json()["url"]
    assert url.startswith(f"/uploads/salas/{sala_id}/")
    nome_disco = url.rsplit("/", 1)[1]
    assert len(nome_disco) == 36 + 4 and nome_disco.endswith(".jpg")  # uuid4 + .jpg
    caminho = (base / url.removeprefix("/uploads/")).resolve()
    assert base in caminho.parents and caminho.is_file()
    assert not (base.parent / "x.jpg").exists() and not Path("/tmp/x.jpg").exists()


def test_upload_legenda_e_professor(client, admin, professor, sala_id):
    r = enviar(client, admin, sala_id, "a.jpg", JPG, legenda="x" * 201)
    assert r.status_code == 422
    r = enviar(client, professor, sala_id, "a.jpg", JPG)
    assert r.status_code == 403
    r = enviar(client, {}, sala_id, "a.jpg", JPG)
    assert r.status_code == 401
    r = enviar(client, admin, 999999, "a.jpg", JPG)
    assert r.status_code == 404


def test_estaticos_nao_permitem_traversal(client, admin, sala_id):
    enviar(client, admin, sala_id, "a.jpg", JPG)
    for caminho in ("/uploads/../app/main.py", "/uploads/%2e%2e/%2e%2e/etc/passwd", "/uploads/..%2f..%2fetc%2fpasswd", "/uploads/salas/"):
        r = client.get(caminho)
        assert r.status_code == 404, (caminho, r.status_code)
        assert "import" not in r.text and "root:" not in r.text


def test_galeria_ordem_capa_e_exclusao(client, admin, sala_id):
    f1 = enviar(client, admin, sala_id, "1.jpg", JPG).json()
    f2 = enviar(client, admin, sala_id, "2.png", PNG, "image/png").json()
    assert (f1["ordem"], f2["ordem"]) == (1, 2)
    assert client.get("/salas", params={"busca": "Laboratório 01"}).json()[0]["foto_capa_url"] == f1["url"]
    r = client.put(f"/salas/{sala_id}/fotos/ordem", headers=admin, json={"foto_ids": [f2["id"], f1["id"]]})
    assert [f["id"] for f in r.json()] == [f2["id"], f1["id"]]
    assert client.get("/salas", params={"busca": "Laboratório 01"}).json()[0]["foto_capa_url"] == f2["url"]
    for errado in ([f1["id"]], [f1["id"], f1["id"]], [f1["id"], f2["id"], 999]):
        r = client.put(f"/salas/{sala_id}/fotos/ordem", headers=admin, json={"foto_ids": errado})
        assert (r.status_code, r.json()["codigo"]) == (422, "ORDEM_FOTOS_INVALIDA")
    outra = client.get("/salas", params={"busca": "Laboratório 02"}).json()[0]["id"]
    assert client.patch(f"/salas/{outra}/fotos/{f1['id']}", headers=admin, json={"legenda": "x"}).status_code == 404
    assert client.patch(f"/salas/{sala_id}/fotos/{f1['id']}", headers=admin, json={"legenda": "Porta"}).json()["legenda"] == "Porta"
    # excluir a sala apaga registros e arquivos
    caminhos = [obter_config().upload_dir / f["url"].removeprefix("/uploads/") for f in (f1, f2)]
    assert all(p.exists() for p in caminhos)
    assert client.delete(f"/salas/{sala_id}", headers=admin).status_code == 204
    assert not any(p.exists() for p in caminhos)
    assert os.path.isdir(obter_config().upload_dir)
