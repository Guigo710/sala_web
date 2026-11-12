"""Seed: `python -m app.seed` (roda a cada start do container). Política do ADR-0006.

- Admin inicial: criado a partir de ADMIN_RM/ADMIN_SENHA/ADMIN_NOME se esse RM ainda não existir.
  Uma conta existente nunca é alterada. Se o admin com ADMIN_RM for excluído, o próximo start o recria
  (recuperação de acesso; para impedir, retire ADMIN_RM/ADMIN_SENHA do .env).
- Equipamentos, softwares, ambientes (com associações), grade de aulas e semestres: cada tabela recebe
  os dados de partida **somente se estiver vazia**. Semestres de partida: os dois do ano corrente e os
  dois do seguinte; daí em diante o admin cadastra os novos.
- O seed nunca atualiza nem apaga linhas. Consequência: se o admin esvaziar uma tabela inteira, o próximo
  start recoloca os dados de partida daquela tabela.
Todos os nomes são genéricos e editáveis pelo painel admin.
"""

import logging
from datetime import date, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import ADMIN_SENHA_EXEMPLO, obter_config
from app.core.db import SessionLocal
from app.core.seguranca import hash_senha
from app.core.tempo import hoje
from app.models import Equipamento, HorarioAula, Professor, Sala, SalaEquipamento, Semestre, Software

log = logging.getLogger("sala_web.seed")

EQUIPAMENTOS = [
    ("Computador", "Desktop para alunos"),
    ("Projetor", "Projetor multimídia"),
    ("Ar-condicionado", None),
    ("Quadro branco", None),
    ("Lousa digital", None),
    ("Carrinho de notebooks", None),
    ("Caixa de som", None),
]

SOFTWARES = [  # (nome, versão, categoria)
    ("Visual Studio Code", None, "IDE"),
    ("PostgreSQL", "16", "Banco de dados"),
    ("Python", "3.12", "Linguagem de programação"),
    ("LibreOffice", None, "Escritório"),
    ("Git", None, "Controle de versão"),
]

SEG_SAB = [1, 2, 3, 4, 5, 6]
SEG_SEX = [1, 2, 3, 4, 5]
GRADE = {  # turno: (dias, [(início, fim), ...])
    "manha": (SEG_SAB, ["07:30-08:20", "08:20-09:10", "09:30-10:20", "10:20-11:10", "11:10-12:00"]),
    "tarde": (SEG_SEX, ["13:00-13:50", "13:50-14:40", "14:50-15:40", "15:40-16:30", "16:30-17:20"]),
    "noite": (SEG_SEX, ["19:00-19:50", "19:50-20:40", "20:50-21:40", "21:40-22:30"]),
}


def _hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


def _tabela_vazia(db: Session, modelo: type) -> bool:
    return db.scalar(select(func.count()).select_from(modelo)) == 0


def seed_admin(db: Session) -> None:
    config = obter_config()
    if not config.ADMIN_RM or not config.ADMIN_SENHA:
        log.warning("ADMIN_RM/ADMIN_SENHA não definidos: admin inicial não criado.")
        return
    if db.scalar(select(Professor.id).where(Professor.rm == config.ADMIN_RM)) is not None:
        return
    if config.ADMIN_SENHA == ADMIN_SENHA_EXEMPLO:
        log.error(
            "ADMIN_SENHA ainda é o valor de exemplo do .env.example: admin inicial NÃO criado. "
            "Defina uma senha própria no .env e rode o seed de novo."
        )
        return
    if len(config.ADMIN_SENHA) < 8:
        log.warning("ADMIN_SENHA com menos de 8 caracteres: troque-a após o primeiro login.")
    db.add(
        Professor(
            rm=config.ADMIN_RM,
            nome=config.ADMIN_NOME,
            senha_hash=hash_senha(config.ADMIN_SENHA),
            papel="admin",
            ativo=True,
        )
    )
    log.info("Admin inicial criado (RM %s).", config.ADMIN_RM)


def seed_equipamentos(db: Session) -> None:
    if _tabela_vazia(db, Equipamento):
        db.add_all(Equipamento(nome=n, descricao=d) for n, d in EQUIPAMENTOS)
        log.info("%d equipamentos criados.", len(EQUIPAMENTOS))


def seed_softwares(db: Session) -> None:
    if _tabela_vazia(db, Software):
        db.add_all(Software(nome=n, versao=v, categoria=c) for n, v, c in SOFTWARES)
        log.info("%d softwares criados.", len(SOFTWARES))


def seed_salas(db: Session) -> None:
    if not _tabela_vazia(db, Sala):
        return
    db.flush()
    equip = {e.nome: e for e in db.scalars(select(Equipamento))}
    softwares = list(db.scalars(select(Software)))

    for i in range(1, 15):
        db.add(
            Sala(nome=f"Sala {i:02d}", tipo="sala", capacidade=40, descricao="Sala de aula.", localizacao=None)
        )
    for i in range(1, 14):
        lab = Sala(
            nome=f"Laboratório {i:02d}",
            tipo="lab_informatica",
            capacidade=30,
            descricao="Laboratório de informática.",
        )
        if "Computador" in equip:
            lab.equipamentos.append(SalaEquipamento(equipamento=equip["Computador"], quantidade=30))
        if "Projetor" in equip:
            lab.equipamentos.append(SalaEquipamento(equipamento=equip["Projetor"], quantidade=1))
        lab.softwares.extend(softwares)
        db.add(lab)
    log.info("14 salas e 13 laboratórios criados.")


def seed_grade(db: Session) -> None:
    if not _tabela_vazia(db, HorarioAula):
        return
    total = 0
    for turno, (dias, aulas) in GRADE.items():
        for ordem, faixa in enumerate(aulas, start=1):
            ini, fim = faixa.split("-")
            db.add(HorarioAula(turno=turno, ordem=ordem, inicio=_hora(ini), fim=_hora(fim), dias_semana=dias))
            total += 1
    log.info("Grade com %d aulas criada.", total)


def _primeira_segunda(ano: int, mes: int) -> date:
    d = date(ano, mes, 1)
    return d + timedelta(days=(7 - d.weekday()) % 7)


def semestres_padrao(ano: int) -> list[tuple[str, date, date]]:
    return [
        (f"{ano}-1", _primeira_segunda(ano, 2), date(ano, 6, 30)),
        (f"{ano}-2", _primeira_segunda(ano, 8), date(ano, 12, 19)),
    ]


def seed_semestres(db: Session) -> None:
    """Semestres de partida (ano corrente e seguinte) só com a tabela vazia (ADR-0006)."""
    if not _tabela_vazia(db, Semestre):
        return
    ano = hoje().year
    for nome, inicio, fim in semestres_padrao(ano) + semestres_padrao(ano + 1):
        db.add(Semestre(nome=nome, data_inicio=inicio, data_fim=fim))
        log.info("Semestre %s criado (%s a %s).", nome, inicio, fim)


def executar(db: Session) -> None:
    seed_admin(db)
    seed_equipamentos(db)
    seed_softwares(db)
    db.flush()
    seed_salas(db)
    seed_grade(db)
    seed_semestres(db)
    db.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    with SessionLocal() as db:
        executar(db)
    log.info("Seed concluído.")


if __name__ == "__main__":
    main()
