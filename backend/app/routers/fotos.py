from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import select

from app.core.config import obter_config
from app.core.erros import ErroApi, nao_encontrado
from app.core.seguranca import Admin, Db, UsuarioOpcional
from app.models import FotoSala
from app.schemas import salas as ss
from app.services import apresentacao, arquivos
from app.services import salas as servico

router = APIRouter(prefix="/salas", tags=["fotos"])


def _fotos_da_sala(db: Db, sala_id: int) -> list[FotoSala]:
    return list(db.scalars(select(FotoSala).where(FotoSala.sala_id == sala_id).order_by(FotoSala.ordem, FotoSala.id)))


def _obter_foto(db: Db, sala_id: int, foto_id: int) -> FotoSala:
    foto = db.get(FotoSala, foto_id)
    if foto is None or foto.sala_id != sala_id:
        raise nao_encontrado("Foto não encontrada.")
    return foto


@router.get("/{sala_id}/fotos", response_model=list[ss.Foto])
def listar(sala_id: int, db: Db, usuario: UsuarioOpcional) -> list[ss.Foto]:
    sala = servico.obter_sala(db, sala_id, usuario)
    return [apresentacao.foto(f) for f in _fotos_da_sala(db, sala.id)]


@router.post("/{sala_id}/fotos", response_model=ss.Foto, status_code=status.HTTP_201_CREATED)
def enviar(
    sala_id: int,
    arquivo: Annotated[UploadFile, File(description="JPEG, PNG ou WebP")],
    db: Db,
    admin: Admin,
    legenda: Annotated[str | None, Form(max_length=200)] = None,
) -> ss.Foto:
    sala = servico.obter_sala(db, sala_id, admin)
    conteudo = arquivos.ler_limitado(arquivo.file, obter_config().upload_max_bytes)
    relativo = arquivos.gravar_foto(sala.id, conteudo)
    try:
        foto = FotoSala(
            sala_id=sala.id,
            arquivo=relativo,
            legenda=(legenda or "").strip() or None,
            ordem=servico.proxima_ordem_foto(db, sala.id),
        )
        db.add(foto)
        db.commit()
    except Exception:
        db.rollback()
        arquivos.apagar_arquivo(relativo)
        raise
    db.refresh(foto)
    return apresentacao.foto(foto)


@router.put("/{sala_id}/fotos/ordem", response_model=list[ss.Foto], summary="Reordenar a galeria")
def reordenar(sala_id: int, entrada: ss.FotoOrdemEntrada, db: Db, admin: Admin) -> list[ss.Foto]:
    sala = servico.obter_sala(db, sala_id, admin)
    fotos = {f.id: f for f in _fotos_da_sala(db, sala.id)}
    ids = entrada.foto_ids
    if len(ids) != len(set(ids)) or set(ids) != set(fotos):
        raise ErroApi(
            422, "ORDEM_FOTOS_INVALIDA", "Envie exatamente os ids de todas as fotos deste ambiente, sem repetir."
        )
    for posicao, foto_id in enumerate(ids, start=1):
        fotos[foto_id].ordem = posicao
    db.commit()
    return [apresentacao.foto(f) for f in _fotos_da_sala(db, sala.id)]


@router.patch("/{sala_id}/fotos/{foto_id}", response_model=ss.Foto, summary="Editar legenda")
def editar(sala_id: int, foto_id: int, entrada: ss.FotoLegendaEntrada, db: Db, admin: Admin) -> ss.Foto:
    servico.obter_sala(db, sala_id, admin)
    foto = _obter_foto(db, sala_id, foto_id)
    foto.legenda = entrada.legenda
    db.commit()
    db.refresh(foto)
    return apresentacao.foto(foto)


@router.delete("/{sala_id}/fotos/{foto_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(sala_id: int, foto_id: int, db: Db, admin: Admin) -> None:
    servico.obter_sala(db, sala_id, admin)
    foto = _obter_foto(db, sala_id, foto_id)
    relativo = foto.arquivo
    db.delete(foto)
    db.commit()
    arquivos.apagar_arquivo(relativo)
