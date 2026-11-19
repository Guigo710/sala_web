from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.schemas import salas as ss
from app.services import apresentacao
from app.services import fotos as servico

router = APIRouter(prefix="/salas", tags=["fotos"])


@router.get("/{sala_id}/fotos", response_model=list[ss.Foto])
def listar(sala_id: int, db: Db, usuario: UsuarioOpcional) -> list[ss.Foto]:
    return [apresentacao.foto(f) for f in servico.listar(db, sala_id, usuario)]


@router.post("/{sala_id}/fotos", response_model=ss.Foto, status_code=status.HTTP_201_CREATED)
def enviar(
    sala_id: int,
    arquivo: Annotated[UploadFile, File(description="JPEG, PNG ou WebP")],
    db: Db,
    admin: Admin,
    legenda: Annotated[str | None, Form(max_length=200)] = None,
) -> ss.Foto:
    return apresentacao.foto(servico.enviar(db, sala_id, admin, arquivo.file, legenda))


@router.put("/{sala_id}/fotos/ordem", response_model=list[ss.Foto], summary="Reordenar a galeria")
def reordenar(sala_id: int, entrada: ss.FotoOrdemEntrada, db: Db, admin: Admin) -> list[ss.Foto]:
    return [apresentacao.foto(f) for f in servico.reordenar(db, sala_id, admin, entrada.foto_ids)]


@router.patch("/{sala_id}/fotos/{foto_id}", response_model=ss.Foto, summary="Editar legenda")
def editar(sala_id: int, foto_id: int, entrada: ss.FotoLegendaEntrada, db: Db, admin: Admin) -> ss.Foto:
    return apresentacao.foto(servico.editar_legenda(db, sala_id, foto_id, admin, entrada.legenda))


@router.delete("/{sala_id}/fotos/{foto_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(sala_id: int, foto_id: int, db: Db, admin: Admin) -> None:
    servico.excluir(db, sala_id, foto_id, admin)
