from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from app.core.erros import ErroApi, erro_validacao, nao_encontrado
from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.models import TIPOS_SALA, Equipamento, Sala, SalaEquipamento, Software, sala_softwares
from app.schemas import reservas as sr
from app.schemas import salas as ss
from app.services import apresentacao
from app.services import salas as servico

router = APIRouter(prefix="/salas", tags=["salas"])

_DUPLICADO = "Já existe um ambiente com este nome."


def _duplicado() -> ErroApi:
    return ErroApi(409, "NOME_DUPLICADO", _DUPLICADO)


def _checar_nome(db: Db, nome: str, ignorar_id: int | None = None) -> None:
    stmt = select(Sala.id).where(Sala.nome == nome)
    if ignorar_id is not None:
        stmt = stmt.where(Sala.id != ignorar_id)
    if db.scalar(stmt) is not None:
        raise _duplicado()


def _commit_nome(db: Db) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _duplicado() from None


@router.get("/tipos", response_model=list[ss.TipoSalaSaida], summary="Tipos de ambiente (valor e rótulo)")
def tipos() -> list[ss.TipoSalaSaida]:
    return [ss.TipoSalaSaida(valor=v, rotulo=r) for v, r in TIPOS_SALA.items()]


@router.get("", response_model=list[ss.SalaResumo], summary="Listar ambientes com filtros")
def listar(
    db: Db,
    usuario: UsuarioOpcional,
    tipo: Annotated[list[ss.TipoSala] | None, Query()] = None,
    capacidade_min: Annotated[int | None, Query(ge=1)] = None,
    equipamento_id: Annotated[list[int] | None, Query()] = None,
    software_id: Annotated[list[int] | None, Query()] = None,
    busca: str | None = None,
    data: date | None = None,
    horario_ids: Annotated[list[int] | None, Query()] = None,
    incluir_inativas: bool = False,
) -> list[ss.SalaResumo]:
    if data is not None and not horario_ids:
        raise erro_validacao("query.horario_ids", "informe as aulas junto com a data")
    if horario_ids and data is None:
        raise erro_validacao("query.data", "informe a data junto com as aulas")
    salas = servico.listar(
        db,
        usuario,
        tipos=tipo,
        capacidade_min=capacidade_min,
        equipamento_ids=equipamento_id,
        software_ids=software_id,
        busca=busca,
        data=data,
        horario_ids=horario_ids,
        incluir_inativas=incluir_inativas,
    )
    return [apresentacao.sala_resumo(s) for s in salas]


@router.get("/{sala_id}", response_model=ss.SalaDetalhe)
def obter(sala_id: int, db: Db, usuario: UsuarioOpcional) -> ss.SalaDetalhe:
    return apresentacao.sala_detalhe(servico.obter_sala(db, sala_id, usuario))


@router.get("/{sala_id}/disponibilidade", response_model=sr.Disponibilidade)
def disponibilidade(sala_id: int, data: date, db: Db, usuario: UsuarioOpcional) -> sr.Disponibilidade:
    return servico.disponibilidade(db, servico.obter_sala(db, sala_id, usuario), data)


@router.post("", response_model=ss.SalaDetalhe, status_code=status.HTTP_201_CREATED)
def criar(entrada: ss.SalaEntrada, db: Db, _: Admin) -> ss.SalaDetalhe:
    _checar_nome(db, entrada.nome)
    sala = Sala(**entrada.model_dump())
    db.add(sala)
    _commit_nome(db)
    return apresentacao.sala_detalhe(servico.recarregar(db, sala.id))


@router.put("/{sala_id}", response_model=ss.SalaDetalhe)
def atualizar(sala_id: int, entrada: ss.SalaEntrada, db: Db, admin: Admin) -> ss.SalaDetalhe:
    sala = servico.obter_sala(db, sala_id, admin)
    _checar_nome(db, entrada.nome, ignorar_id=sala.id)
    for campo, valor in entrada.model_dump().items():
        setattr(sala, campo, valor)
    _commit_nome(db)
    return apresentacao.sala_detalhe(servico.recarregar(db, sala.id))


@router.delete("/{sala_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(sala_id: int, db: Db, admin: Admin) -> None:
    servico.excluir(db, servico.obter_sala(db, sala_id, admin))


@router.put("/{sala_id}/equipamentos", response_model=ss.SalaDetalhe, summary="Substituir equipamentos da sala")
def definir_equipamentos(
    sala_id: int, itens: list[ss.SalaEquipamentoEntrada], db: Db, admin: Admin
) -> ss.SalaDetalhe:
    sala = servico.obter_sala(db, sala_id, admin)
    ids = [i.equipamento_id for i in itens]
    if len(set(ids)) != len(ids):
        raise erro_validacao("body", "equipamento repetido na lista")
    existentes = set(db.scalars(select(Equipamento.id).where(Equipamento.id.in_(ids)))) if ids else set()
    if len(existentes) != len(set(ids)):
        raise nao_encontrado("Equipamento não encontrado.")
    db.execute(delete(SalaEquipamento).where(SalaEquipamento.sala_id == sala.id))
    for i in itens:
        db.add(
            SalaEquipamento(
                sala_id=sala.id,
                equipamento_id=i.equipamento_id,
                quantidade=i.quantidade,
                especificacao=i.especificacao,
            )
        )
    db.commit()
    return apresentacao.sala_detalhe(servico.recarregar(db, sala.id))


@router.put("/{sala_id}/softwares", response_model=ss.SalaDetalhe, summary="Substituir softwares da sala")
def definir_softwares(sala_id: int, entrada: ss.SalaSoftwaresEntrada, db: Db, admin: Admin) -> ss.SalaDetalhe:
    sala = servico.obter_sala(db, sala_id, admin)
    ids = list(dict.fromkeys(entrada.software_ids))
    existentes = set(db.scalars(select(Software.id).where(Software.id.in_(ids)))) if ids else set()
    if len(existentes) != len(ids):
        raise nao_encontrado("Software não encontrado.")
    db.execute(delete(sala_softwares).where(sala_softwares.c.sala_id == sala.id))
    if ids:
        db.execute(insert(sala_softwares), [{"sala_id": sala.id, "software_id": i} for i in ids])
    db.commit()
    return apresentacao.sala_detalhe(servico.recarregar(db, sala.id))
