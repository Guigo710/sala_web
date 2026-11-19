# 61: Importar para o banco as fotos já gravadas em disco; Compose sem gravação em `uploads`

Status: resolved
Responsável: Forge
Origem: Atlas
Prioridade: alta
Blocked by: 60
Referências: ADR-0010 ("Fotos já gravadas em disco"); ADR-0001 (nota da rodada 5); contrato 1.4 §2;
`docker-compose.yml` (volume `uploads`, serviço `uploads-permissoes`); `backend/Dockerfile` (`CMD`, `/app/uploads`);
`backend/README.md`; ticket 51

## Contexto
Quem já usa o Compose tem fotos no volume `uploads` e linhas em `fotos_sala` apontando para elas. Depois da
migration `0003` essas linhas ficam com `conteudo` nulo e a `url` responderia `404`. Ninguém pode perder fotos.

## O que fazer
1. Comando idempotente **`python -m app.importar_fotos`** (ex.: `app/importar_fotos.py`):
   - seleciona as fotos com `conteudo IS NULL`;
   - para cada uma, lê `UPLOAD_DIR/<arquivo>` usando o `caminho_absoluto` atual (continua barrando caminho fora de
     `UPLOAD_DIR`), passa pela mesma redução do ticket 60 e grava `conteudo`, `tipo_mime`, `tamanho` e
     `arquivo = salas/{sala_id}/{uuid4}.jpg` (nome novo); **um commit por foto**;
   - arquivo ausente, ilegível ou imagem inválida: `WARNING` no log com id e nome, linha fica como está, segue para a próxima;
   - nunca apaga arquivos do disco nem linhas do banco;
   - `UPLOAD_DIR` inexistente ou nenhuma foto pendente: termina em silêncio (uma linha `INFO` com o resumo basta);
   - resumo no final: importadas, não encontradas, com erro;
   - termina com código 0 mesmo com avisos (não pode impedir a API de subir).
2. `backend/Dockerfile`: `CMD` passa a ser
   `alembic upgrade head && python -m app.seed && python -m app.importar_fotos && uvicorn ... --port ${PORT:-8000}`
   (a parte do `PORT` é do ticket 62; combinem num único `CMD`). Usuário continua `10001`. A pasta `/app/uploads` pode
   continuar existindo (ponto de montagem), mas o processo não precisa mais gravar nela.
3. `docker-compose.yml`:
   - backend monta `uploads:/app/uploads:ro` (só leitura) e mantém `UPLOAD_DIR: /app/uploads`;
   - remover o serviço `uploads-permissoes` e a dependência dele (ninguém grava mais no volume);
   - manter o volume `uploads` declarado (não apagar dados de ninguém); comentário explicando que só serve para a
     importação e que será retirado numa rodada futura.
4. `backend/README.md`: como conferir a importação (log do backend) e, **depois de conferir as fotos na tela**, como
   liberar o espaço: tirar a montagem do volume e `docker volume rm <projeto>_uploads` (com aviso de que é irreversível).
   Remover a seção do `chown` do ticket 51 ou marcá-la como histórica.
5. `.env.example`: `UPLOAD_DIR` passa a ser descrito como "pasta das fotos antigas, só para importar (ADR-0010)".
6. CI (job E2E): o passo "Subir a API" passa a rodar também `python -m app.importar_fotos` (deve ser no-op).

## Critérios de aceite
- [x] Atualização real com Compose: no commit anterior a esta rodada, subir, enviar 2 fotos (uma PNG), apagar à mão
      uma terceira do volume (linha órfã); trocar para o código novo e `docker compose up --build`:
      as 2 fotos aparecem na tela com `url` nova terminada em `.jpg`; a órfã gera `WARNING` e responde `404`; o log traz o resumo.
- [x] Segunda subida: nada é reimportado (resumo com zero importadas; mesmas URLs).
- [x] Clone novo (volume vazio) sobe sem erro e sem aviso.
- [x] `docker compose exec backend id` → uid 10001; `docker compose exec backend touch /app/uploads/x` falha (só leitura).
- [x] Teste pytest do comando com pasta temporária: importa, ignora ausente, não importa duas vezes, recusa `../`.

## Resolução (Forge, rodada 5)
- `backend/app/importar_fotos.py` (`python -m app.importar_fotos`): só `conteudo IS NULL`; caminho conferido por
  `caminho_absoluto` (recusa `../`, absoluto e link para fora); mesma `preparar` do upload; nome novo `.jpg`; um commit
  por foto; ausente/ilegível/inválida/fora da pasta → `WARNING` com id e nome; nunca apaga; sem pendentes ou sem pasta →
  uma linha `INFO`; resumo final; `main()` sempre devolve 0 (até com o banco fora: loga e deixa a API tentar subir).
- `Dockerfile`: `CMD` = `alembic upgrade head && python -m app.seed && python -m app.importar_fotos && exec uvicorn ...
  --port ${PORT:-8000}`; `/app/uploads` continua como ponto de montagem (agora de root), usuário 10001.
- `docker-compose.yml`: `uploads:/app/uploads:ro`, `uploads-permissoes` removido (e a dependência), volume `uploads`
  mantido com comentário. Serviço `frontend` não tocado; volumes e projeto com os mesmos nomes.
- `.env.example` (`UPLOAD_DIR`), `backend/README.md` (seção "Fotos antigas": conferir no log, liberar espaço com aviso
  de irreversível e cópia opcional; seção do `chown` marcada como histórica), CI (passo "Subir a API" roda o comando).
- Conferido de verdade com Docker: commit `f73d5ef` (antes da rodada) no ar com o projeto `sala_web`, 3 fotos enviadas
  (PNG 2400×1800 com alfa, JPEG 3000×2000, JPEG pequeno) e o arquivo da terceira apagado do volume; código novo com
  `docker compose up --build` no mesmo projeto: log `Foto 1 importada: ...png -> ...jpg`, `Foto 2 importada`, `WARNING`
  da foto 3, resumo `2 importada(s), 1 não encontrada(s), 0 com erro`; as duas URLs novas `.jpg` → `200 image/jpeg`, a
  órfã → `404`; arquivos antigos continuam no volume. Segunda subida: `0 importada(s)`, mesmas URLs.
  Clone novo (projeto/volumes novos): sobe, só a linha `INFO ... nenhuma foto pendente`.
  `exec backend id` → `uid=10001(app)`; `exec backend touch /app/uploads/x` → `Read-only file system`.
  Observação: quem já tinha o container `uploads-permissoes` pode ver o aviso de órfão do Compose; o README manda
  rodar `docker compose up -d --remove-orphans` uma vez.
- Testes: `test_importar_fotos_antigas` (importa PNG e WebP, ignora ausente, recusa `../` e caminho absoluto, imagem
  inválida, não apaga nada, segunda execução sem reimportar), silêncio sem pendentes/sem pasta, `main()` → 0, e o
  comando real por `subprocess`.
