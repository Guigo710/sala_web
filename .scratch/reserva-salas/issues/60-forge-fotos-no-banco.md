# 60: Fotos reduzidas no upload e guardadas no banco

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: alta (bloqueia a publicação: o disco do Render é efêmero)
Blocked by: (nenhum)
Referências: ADR-0010 (decisão completa); ADR-0005 (parcialmente substituído); contrato 1.4 §1.9, §2, §3.5, §4.1,
§4.4, §6; `backend/app/services/fotos.py`, `backend/app/services/arquivos.py`, `backend/app/models/foto.py`,
`backend/app/main.py` (`StaticFiles`), `backend/app/core/middlewares.py` (`CabecalhosSeguranca`)

## Contexto
Na publicação a API roda no Render Free, com disco efêmero: fotos gravadas em `UPLOAD_DIR` somem a cada sono,
reinício ou deploy. As fotos passam a ficar no PostgreSQL, já reduzidas. A URL pública **não muda de formato**
(`/uploads/salas/{sala_id}/{uuid}.jpg`), então o frontend continua igual.

## O que fazer
1. **Migration `0003_fotos_no_banco`** (§2 do contrato): `conteudo bytea` (nulo permitido), `tipo_mime varchar(30)`,
   `tamanho integer`, `ALTER COLUMN conteudo SET STORAGE EXTERNAL`. `downgrade` remove as colunas.
2. **Modelo**: `FotoSala.conteudo` com `deferred(...)` (ou `deferred=True` no `mapped_column`), para listas, detalhe,
   capa e galeria nunca carregarem os bytes. `url` continua `"/uploads/" + arquivo`.
3. **Pillow** em `requirements.in` e `requirements.txt` (versão exata, como no ticket 36).
4. **Redução** (módulo próprio, ex.: `app/services/imagens.py`, função pura `reduzir(conteudo: bytes) -> bytes`,
   fácil de testar), exatamente como no §4.4 / ADR-0010:
   - assinatura continua conferida antes (`tipo_por_assinatura`); limite de entrada `UPLOAD_MAX_MB` sem mudança;
   - abrir com `Image.open` e conferir `largura * altura` **antes** de `load()`: > 40 MP → `413 ARQUIVO_GRANDE`
     ("A foto passa do limite de 40 megapixels."). Configurar `Image.MAX_IMAGE_PIXELS` coerente e tratar
     `DecompressionBombError`/`DecompressionBombWarning` como esse mesmo `413`;
   - erro de decodificação (`UnidentifiedImageError`, `OSError`, `SyntaxError` do Pillow) → `415 TIPO_ARQUIVO_INVALIDO`;
   - para JPEG grande, `img.draft("RGB", (1600, 1600))` antes de carregar (economiza memória e CPU no Render);
   - `ImageOps.exif_transpose`; `thumbnail((1600, 1600), Image.LANCZOS)` (não amplia); RGB com transparência
     composta sobre branco; salvar JPEG `quality=80, progressive=True, optimize=True`, sem `exif`, com
     `icc_profile` se houver; > 600 KB → regrava uma vez com `quality=70`.
5. **Upload** (`services/fotos.enviar`): lê com limite → reduz → grava a linha com `arquivo = salas/{sala_id}/{uuid4}.jpg`,
   `conteudo`, `tipo_mime = "image/jpeg"`, `tamanho`. Nada em disco.
6. **Entrega**: trocar o `StaticFiles` por uma rota `GET /uploads/{arquivo:path}` (router próprio, ex.: `routers/uploads.py`,
   fora do schema OpenAPI se quiser) que busca por `arquivo`:
   - achou com `conteudo` → `200` com `Content-Type` da coluna, `Content-Length`, `ETag: "<uuid>"`,
     `Cache-Control: public, max-age=31536000, immutable`;
   - `If-None-Match` com o mesmo ETag (aceitar lista e `W/`) → `304` sem corpo, com `ETag` e `Cache-Control`;
   - não achou ou `conteudo` nulo → `404 NAO_ENCONTRADO` (envelope);
   - sessão de banco curta (a rota não precisa de usuário; não carregar a sala).
   O `CabecalhosSeguranca` continua pondo `Content-Disposition`, CSP `sandbox` e `nosniff` em `/uploads/` (`< 400`);
   trocar o `setdefault("Cache-Control", "public, max-age=86400")` para não sobrescrever o da rota (ou mover o valor
   novo para lá). Não enviar `Cross-Origin-Resource-Policy`.
7. **Exclusão**: excluir foto/sala só apaga registros. Remover `gravar_foto`, `apagar_arquivo`, `apagar_pasta_sala`
   e o `mkdir` de `UPLOAD_DIR` em `main.py` quando não houver mais uso (a importação do ticket 61 só **lê** disco).
8. `backend/README.md`: estrutura (sem `StaticFiles`), fotos no banco.

## Critérios de aceite
- [ ] `alembic upgrade head` e `alembic downgrade -1` funcionam num banco com fotos antigas (linhas com `conteudo` nulo).
- [ ] Upload de JPEG 4000×3000 com EXIF de orientação 6 e GPS → `201`; o `GET` da `url` devolve JPEG com lado maior
      1600, em pé (3000×4000 → 1200×1600), sem EXIF/GPS.
- [ ] PNG com transparência → JPEG com fundo branco. Imagem 800×600 → continua 800×600 (sem ampliar).
- [ ] Imagem de 41 MP (ex.: PNG 8000×5200 de cor sólida, poucos KB) → `413 ARQUIVO_GRANDE` sem estourar memória.
- [ ] Arquivo com assinatura JPEG e resto inválido → `415 TIPO_ARQUIVO_INVALIDO`. Acima de 5 MB → `413` como hoje.
- [ ] `GET /uploads/<arquivo>` → `200`, `Content-Type: image/jpeg`, `Cache-Control: public, max-age=31536000, immutable`,
      `ETag`, CSP `sandbox`, `nosniff`; com `If-None-Match` → `304`; nome inexistente → `404` com envelope.
- [ ] `GET /salas` e `GET /salas/{id}` não leem a coluna `conteudo` (teste conferindo o SQL emitido ou o atributo não carregado).
- [ ] Nada é gravado em disco no upload (teste com `UPLOAD_DIR` apontando para pasta somente leitura ou inexistente).
- [ ] Suíte pytest verde; testes novos em `tests/test_fotos_banco.py` (Sentinela revisa no ticket 68).
