"""Reserva semanal recorrente: prévia e confirmação (RN06)."""

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import ErroApi, erro_validacao
from app.models import GrupoRecorrencia, Professor, Reserva, Semestre
from app.schemas import reservas as sr
from app.schemas.comum import Semestre as SemestreSaida
from app.services import apresentacao
from app.services.reservas import (
    Bloco,
    buscar_conflitos,
    eh_violacao_conflito,
    erro_conflito,
    nova_reserva,
    preparar_bloco,
    reservas_do_grupo,
)


def semestre_da_data(db: Session, data: date) -> Semestre:
    semestre = db.scalars(
        select(Semestre).where(Semestre.data_inicio <= data, Semestre.data_fim >= data)
    ).first()
    if semestre is None:
        raise ErroApi(
            422, "SEM_SEMESTRE", "Não há semestre letivo cadastrado que contenha a data inicial."
        )
    return semestre


def datas_da_serie(data_inicio: date, data_fim: date) -> list[date]:
    datas, atual = [], data_inicio
    while atual <= data_fim:
        datas.append(atual)
        atual += timedelta(days=7)
    return datas


def _montar(db: Session, usuario: Professor, entrada: sr.PreviaEntrada) -> tuple[Bloco, Semestre, list[date]]:
    bloco = preparar_bloco(
        db, usuario, entrada.sala_id, entrada.data_inicio, entrada.horario_ids, entrada.professor_id
    )
    semestre = semestre_da_data(db, entrada.data_inicio)
    return bloco, semestre, datas_da_serie(entrada.data_inicio, semestre.data_fim)


def previa(db: Session, usuario: Professor, entrada: sr.PreviaEntrada) -> sr.PreviaSaida:
    bloco, semestre, serie = _montar(db, usuario, entrada)
    por_data: dict[date, list[Reserva]] = defaultdict(list)
    for r in buscar_conflitos(db, bloco.sala.id, serie, bloco.inicio, bloco.fim):
        por_data[r.data].append(r)

    ocorrencias = [
        sr.OcorrenciaPrevia(
            data=d, livre=not por_data[d], conflitos=[apresentacao.conflito(r) for r in por_data[d]]
        )
        for d in serie
    ]
    livres = sum(1 for o in ocorrencias if o.livre)
    return sr.PreviaSaida(
        sala=apresentacao.sala_ref(bloco.sala),
        semestre=SemestreSaida.model_validate(semestre),
        dia_semana=entrada.data_inicio.isoweekday(),
        inicio=bloco.inicio,
        fim=bloco.fim,
        horario_ids=[a.id for a in bloco.aulas],
        ocorrencias=ocorrencias,
        total=len(ocorrencias),
        livres=livres,
        em_conflito=len(ocorrencias) - livres,
    )


def confirmar(
    db: Session, usuario: Professor, entrada: sr.RecorrenteEntrada
) -> tuple[GrupoRecorrencia, list[Reserva]]:
    if not entrada.datas:
        raise erro_validacao("body.datas", "informe pelo menos uma data")
    if len(set(entrada.datas)) != len(entrada.datas):
        raise erro_validacao("body.datas", "datas repetidas")

    bloco, semestre, serie = _montar(db, usuario, entrada)
    na_serie = set(serie)
    fora = sorted(d for d in entrada.datas if d not in na_serie)
    if fora:
        raise ErroApi(
            422,
            "DATA_FORA_DA_SERIE",
            f"A data {fora[0].strftime('%d/%m/%Y')} não pertence à série semanal desta reserva.",
        )

    datas = sorted(entrada.datas)
    conflitos = buscar_conflitos(db, bloco.sala.id, datas, bloco.inicio, bloco.fim)
    if conflitos:
        raise erro_conflito(conflitos)

    grupo = GrupoRecorrencia(
        sala_id=bloco.sala.id,
        professor_id=bloco.dono.id,
        semestre_id=semestre.id,
        dia_semana=entrada.data_inicio.isoweekday(),
        inicio=bloco.inicio,
        fim=bloco.fim,
        criado_por_id=usuario.id,
    )
    db.add(grupo)
    try:
        db.flush()
        reservas = [nova_reserva(bloco, d, usuario, entrada.observacao) for d in datas]
        for r in reservas:
            r.grupo_recorrencia_id = grupo.id
        db.add_all(reservas)
        db.commit()
    except IntegrityError as e:
        # Tudo ou nada: uma violação desfaz o grupo e todas as ocorrências.
        db.rollback()
        if eh_violacao_conflito(e):
            raise erro_conflito(buscar_conflitos(db, bloco.sala.id, datas, bloco.inicio, bloco.fim)) from None
        raise
    db.refresh(grupo)
    # Uma consulta para todas as ocorrências (com sala/professor por join), em vez de um refresh por data.
    return grupo, reservas_do_grupo(db, grupo.id, recarregar=True)
