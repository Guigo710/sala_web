"""Galeria de fotos de um ambiente (contrato §4.4). As fotos ficam no banco, já reduzidas (ADR-0010)."""

import uuid
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.erros import ErroApi, nao_encontrado
from app.models import FotoSala, Professor
from app.services import arquivos, imagens
from app.services.comum import commit_traduzindo
from app.services.salas import obter_sala


def _fotos_da_sala(db: Session, sala_id: int) -> list[FotoSala]:
    return list(db.scalars(select(FotoSala).where(FotoSala.sala_id == sala_id).order_by(FotoSala.ordem, FotoSala.id)))


def _obter_foto(db: Session, sala_id: int, foto_id: int) -> FotoSala:
    foto = db.get(FotoSala, foto_id)
    if foto is None or foto.sala_id != sala_id:
        raise nao_encontrado("Foto não encontrada.")
    return foto


def _proxima_ordem(db: Session, sala_id: int) -> int:
    return (db.scalar(select(func.max(FotoSala.ordem)).where(FotoSala.sala_id == sala_id)) or 0) + 1


def listar(db: Session, sala_id: int, usuario: Professor | None) -> list[FotoSala]:
    sala = obter_sala(db, sala_id, usuario)
    return _fotos_da_sala(db, sala.id)


def nome_publico(sala_id: int) -> str:
    """Nome público de uma foto nova: `salas/{sala_id}/{uuid4}.jpg` (o nome enviado é descartado)."""
    return f"salas/{sala_id}/{uuid.uuid4()}.jpg"


def preparar(conteudo: bytes) -> bytes:
    """Confere a assinatura (JPEG/PNG/WebP) e devolve o JPEG reduzido que vai para o banco (ADR-0010)."""
    if arquivos.tipo_por_assinatura(conteudo[:16]) is None:
        raise ErroApi(415, "TIPO_ARQUIVO_INVALIDO", "Envie uma imagem JPEG, PNG ou WebP.")
    return imagens.reduzir(conteudo)


def enviar(db: Session, sala_id: int, admin: Professor, arquivo: BinaryIO, legenda: str | None) -> FotoSala:
    """Lê com limite, confere a assinatura, reduz e grava a linha com os bytes. Nada vai para o disco."""
    sala = obter_sala(db, sala_id, admin)
    jpeg = preparar(arquivos.ler_limitado(arquivo, obter_config().upload_max_bytes))
    foto = FotoSala(
        sala_id=sala.id,
        arquivo=nome_publico(sala.id),
        conteudo=jpeg,
        tipo_mime=imagens.TIPO_MIME,
        tamanho=len(jpeg),
        legenda=(legenda or "").strip() or None,
        ordem=_proxima_ordem(db, sala.id),
    )
    db.add(foto)
    commit_traduzindo(db)
    db.refresh(foto)
    return foto


def obter_conteudo(db: Session, arquivo: str) -> tuple[bytes, str] | None:
    """(bytes, tipo MIME) da foto com esse nome público; `None` se não existe ou ainda não tem conteúdo.

    Consulta só as duas colunas (não carrega a sala nem a linha inteira).
    """
    linha = db.execute(
        select(FotoSala.conteudo, FotoSala.tipo_mime).where(FotoSala.arquivo == arquivo)
    ).first()
    if linha is None or linha.conteudo is None:
        return None
    return linha.conteudo, linha.tipo_mime or imagens.TIPO_MIME


def reordenar(db: Session, sala_id: int, admin: Professor, foto_ids: list[int]) -> list[FotoSala]:
    sala = obter_sala(db, sala_id, admin)
    fotos = {f.id: f for f in _fotos_da_sala(db, sala.id)}
    if len(foto_ids) != len(set(foto_ids)) or set(foto_ids) != set(fotos):
        raise ErroApi(
            422, "ORDEM_FOTOS_INVALIDA", "Envie exatamente os ids de todas as fotos deste ambiente, sem repetir."
        )
    for posicao, foto_id in enumerate(foto_ids, start=1):
        fotos[foto_id].ordem = posicao
    commit_traduzindo(db)
    return _fotos_da_sala(db, sala.id)


def editar_legenda(db: Session, sala_id: int, foto_id: int, admin: Professor, legenda: str | None) -> FotoSala:
    obter_sala(db, sala_id, admin)
    foto = _obter_foto(db, sala_id, foto_id)
    foto.legenda = legenda
    commit_traduzindo(db)
    db.refresh(foto)
    return foto


def excluir(db: Session, sala_id: int, foto_id: int, admin: Professor) -> None:
    obter_sala(db, sala_id, admin)
    foto = _obter_foto(db, sala_id, foto_id)
    db.delete(foto)
    commit_traduzindo(db)
