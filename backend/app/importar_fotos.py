"""Importação das fotos antigas do disco para o banco: `python -m app.importar_fotos` (ADR-0010, ticket 61).

Roda a cada start do container, depois do seed e antes do uvicorn. Idempotente:
- só olha as fotos com `conteudo IS NULL` (as que vieram de antes da migration 0003);
- para cada uma, lê `UPLOAD_DIR/<arquivo>` (nunca fora de UPLOAD_DIR), passa pela mesma redução do upload e
  grava `conteudo`, `tipo_mime`, `tamanho` e um nome novo `salas/{sala_id}/{uuid4}.jpg`; um commit por foto;
- arquivo ausente, ilegível ou imagem inválida: WARNING com id e nome; a linha fica como está;
- nunca apaga arquivos do disco nem linhas do banco;
- termina sempre com código 0 (avisos não podem impedir a API de subir).
Na nuvem (Render) não há fotos antigas: o comando não encontra nada a fazer.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import obter_config
from app.core.db import SessionLocal
from app.core.erros import ErroApi
from app.models import FotoSala
from app.services import arquivos, imagens
from app.services import fotos as servico_fotos

log = logging.getLogger("sala_web.importar_fotos")

# Arquivos maiores que isto não são fotos que a API aceitou (UPLOAD_MAX_MB, mesmo se o limite tiver sido
# reduzido depois); nem são lidos.
_LIMITE_LEITURA_PADRAO = 20 * 1024 * 1024


@dataclass
class Resumo:
    importadas: int = 0
    nao_encontradas: int = 0
    com_erro: int = 0

    @property
    def total(self) -> int:
        return self.importadas + self.nao_encontradas + self.com_erro


def _ler(caminho: Path, limite: int) -> bytes:
    if caminho.stat().st_size > limite:
        raise ValueError(f"arquivo com mais de {limite // (1024 * 1024)} MB")
    return caminho.read_bytes()


def importar(db: Session, pasta: Path | None = None, limite_bytes: int | None = None) -> Resumo:
    """Importa as fotos pendentes. `pasta` (padrão: UPLOAD_DIR) só para testes; o caminho continua conferido."""
    config = obter_config()
    pasta = (pasta or config.upload_dir).resolve()
    limite = limite_bytes or max(_LIMITE_LEITURA_PADRAO, config.upload_max_bytes)
    resumo = Resumo()

    pendentes = list(
        db.execute(
            select(FotoSala.id, FotoSala.sala_id, FotoSala.arquivo)
            .where(FotoSala.conteudo.is_(None))
            .order_by(FotoSala.id)
        )
    )
    if not pendentes:
        log.info("Importação de fotos: nenhuma foto pendente.")
        return resumo
    if not pasta.is_dir():
        # Sem a pasta antiga não há o que importar; as linhas ficam como estão (a URL responde 404).
        log.info(
            "Importação de fotos: %d foto(s) sem conteúdo, mas a pasta %s não existe; nada a importar.",
            len(pendentes), pasta,
        )
        resumo.nao_encontradas = len(pendentes)
        return resumo

    for foto_id, sala_id, arquivo in pendentes:
        try:
            caminho = arquivos.caminho_absoluto(arquivo, base=pasta)
        except ValueError:
            log.warning("Foto %d (%s): caminho fora de UPLOAD_DIR; ignorada.", foto_id, arquivo)
            resumo.com_erro += 1
            continue
        try:
            original = _ler(caminho, limite)
        except FileNotFoundError:
            log.warning("Foto %d (%s): arquivo não encontrado em %s; ficará indisponível.", foto_id, arquivo, pasta)
            resumo.nao_encontradas += 1
            continue
        except (OSError, ValueError) as erro:
            log.warning("Foto %d (%s): não foi possível ler o arquivo (%s).", foto_id, arquivo, erro)
            resumo.com_erro += 1
            continue
        try:
            jpeg = servico_fotos.preparar(original)
        except ErroApi as erro:
            log.warning("Foto %d (%s): imagem inválida (%s).", foto_id, arquivo, erro.detail)
            resumo.com_erro += 1
            continue

        foto = db.get(FotoSala, foto_id)
        if foto is None:  # excluída enquanto a importação rodava
            continue
        foto.conteudo = jpeg
        foto.tipo_mime = imagens.TIPO_MIME
        foto.tamanho = len(jpeg)
        foto.arquivo = servico_fotos.nome_publico(sala_id)
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            log.warning("Foto %d (%s): falha ao gravar no banco.", foto_id, arquivo, exc_info=True)
            resumo.com_erro += 1
            continue
        resumo.importadas += 1
        log.info("Foto %d importada: %s -> %s (%d bytes).", foto_id, arquivo, foto.arquivo, len(jpeg))

    log.info(
        "Importação de fotos concluída: %d importada(s), %d não encontrada(s), %d com erro.",
        resumo.importadas, resumo.nao_encontradas, resumo.com_erro,
    )
    return resumo


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
    try:
        with SessionLocal() as db:
            importar(db)
    except Exception:  # noqa: BLE001
        # Nunca impede a API de subir: as fotos pendentes ficam para a próxima subida.
        log.warning("Importação de fotos interrompida; a API sobe assim mesmo.", exc_info=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
