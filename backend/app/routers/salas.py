from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.models import TIPOS_SALA
from app.schemas import reservas as sr
from app.schemas import salas as ss
from app.services import apresentacao
from app.services import salas as servico

router = APIRouter(prefix="/salas", tags=["salas"])


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
    return servico.disponibilidade(db, sala_id, usuario, data)


@router.post("", response_model=ss.SalaDetalhe, status_code=status.HTTP_201_CREATED)
def criar(entrada: ss.SalaEntrada, db: Db, _: Admin) -> ss.SalaDetalhe:
    return apresentacao.sala_detalhe(servico.criar(db, entrada))


@router.put("/{sala_id}", response_model=ss.SalaDetalhe)
def atualizar(sala_id: int, entrada: ss.SalaAtualizar, db: Db, admin: Admin) -> ss.SalaDetalhe:
    return apresentacao.sala_detalhe(servico.atualizar(db, sala_id, entrada, admin))


@router.delete("/{sala_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(sala_id: int, db: Db, admin: Admin) -> None:
    servico.excluir(db, sala_id, admin)


@router.put("/{sala_id}/equipamentos", response_model=ss.SalaDetalhe, summary="Substituir equipamentos da sala")
def definir_equipamentos(
    sala_id: int, itens: list[ss.SalaEquipamentoEntrada], db: Db, admin: Admin
) -> ss.SalaDetalhe:
    return apresentacao.sala_detalhe(servico.definir_equipamentos(db, sala_id, itens, admin))


@router.put("/{sala_id}/softwares", response_model=ss.SalaDetalhe, summary="Substituir softwares da sala")
def definir_softwares(sala_id: int, entrada: ss.SalaSoftwaresEntrada, db: Db, admin: Admin) -> ss.SalaDetalhe:
    return apresentacao.sala_detalhe(servico.definir_softwares(db, sala_id, entrada.software_ids, admin))
