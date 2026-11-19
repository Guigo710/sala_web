# 60: Fotos reduzidas no upload e guardadas no banco

Status: resolved
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
- [x] `alembic upgrade head` e `alembic downgrade -1` funcionam num banco com fotos antigas (linhas com `conteudo` nulo).
- [x] Upload de JPEG 4000×3000 com EXIF de orientação 6 e GPS → `201`; o `GET` da `url` devolve JPEG com lado maior
      1600, em pé (3000×4000 → 1200×1600), sem EXIF/GPS.
- [x] PNG com transparência → JPEG com fundo branco. Imagem 800×600 → continua 800×600 (sem ampliar).
- [x] Imagem de 41 MP (ex.: PNG 8000×5200 de cor sólida, poucos KB) → `413 ARQUIVO_GRANDE` sem estourar memória.
- [x] Arquivo com assinatura JPEG e resto inválido → `415 TIPO_ARQUIVO_INVALIDO`. Acima de 5 MB → `413` como hoje.
- [x] `GET /uploads/<arquivo>` → `200`, `Content-Type: image/jpeg`, `Cache-Control: public, max-age=31536000, immutable`,
      `ETag`, CSP `sandbox`, `nosniff`; com `If-None-Match` → `304`; nome inexistente → `404` com envelope.
- [x] `GET /salas` e `GET /salas/{id}` não leem a coluna `conteudo` (teste conferindo o SQL emitido ou o atributo não carregado).
- [x] Nada é gravado em disco no upload (teste com `UPLOAD_DIR` apontando para pasta somente leitura ou inexistente).
- [x] Suíte pytest verde; testes novos em `tests/test_fotos_banco.py` (Sentinela revisa no ticket 68).

## Resolução (Forge, rodada 5)
- Migration `backend/alembic/versions/0003_fotos_no_banco.py` (3 colunas + `SET STORAGE EXTERNAL`; `downgrade` remove).
- `FotoSala.conteudo` com `deferred=True, deferred_raiseload=True` (acesso sem `undefer` levanta erro em vez de
  consultar escondido); `tipo_mime`, `tamanho`; `url` continua `"/uploads/" + arquivo`.
- `pillow==13.0.0` em `requirements.txt` (`Pillow>=11.0` no `.in`).
- `app/services/imagens.py`: `reduzir(bytes) -> bytes`, pura. `Image.open(..., formats=JPEG/PNG/WEBP)`, confere
  `largura*altura > 40 MP` antes de `load()` (413), `Image.MAX_IMAGE_PIXELS = 40 MP` e `DecompressionBombWarning`
  tratado como erro (ambos viram o mesmo 413); erro de decodificação → 415; `draft("RGB", tamanho_final)` em JPEG
  (o tamanho final, não `(1600, 1600)`, senão o `draft` não reduz fotos 4:3); `exif_transpose`; `thumbnail` LANCZOS;
  alfa (RGBA/LA/PA/P com `transparency`) sobre branco; `img.info` zerado antes de salvar (sem EXIF/XMP/comentário);
  ICC mantido só se for perfil RGB (um perfil CMYK/cinza num JPEG RGB deixaria as cores erradas); q80 progressivo
  otimizado, > 600 KB → q70 uma vez.
- `services/fotos.enviar`: lê com limite → `preparar` (assinatura + `reduzir`) → linha com nome `salas/{id}/{uuid4}.jpg`.
- Entrega: `app/routers/uploads.py` (`GET /uploads/{arquivo:path}`, sessão própria e curta) + `services/fotos.entregar`
  (lê só `conteudo`/`tipo_mime`; com `If-None-Match` igual — lista, `W/` ou `*` — responde `304` sem ler os bytes).
  `CabecalhosSeguranca` usa a constante `CACHE_UPLOADS` só como `setdefault`; sem CORP.
- Removidos `StaticFiles`, `mkdir` de `UPLOAD_DIR`, `gravar_foto`, `apagar_arquivo`, `apagar_pasta_sala`.
  `arquivos.caminho_absoluto` ficou (só para a importação) e ganhou o parâmetro `base`.
- Testes novos em `backend/tests/test_fotos_banco.py` (migration com foto antiga, celular 4000×3000 com orientação 6 e
  GPS → 1200×1600 sem APP1/COM/GPS/XMP, transparência, sem ampliar, 41 MP com pico de memória < 10 MB, bomba de 100 MP,
  415, ICC, regravação q70, cabeçalhos/ETag/304/404, SQL emitido por `/salas` sem `conteudo`, atributo não carregado,
  `UPLOAD_DIR` inexistente e somente leitura). Testes antigos de upload passaram a usar imagens reais
  (`tests/apoio_imagens.py`); os que conferiam arquivos em disco agora conferem que **nada** vai para o disco e que a
  URL some (404) depois da exclusão. `test_migration_0002` desce até `0001` explicitamente (antes era `-1`).
