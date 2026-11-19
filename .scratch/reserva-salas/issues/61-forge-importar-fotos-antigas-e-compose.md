# 61: Importar para o banco as fotos já gravadas em disco; Compose sem gravação em `uploads`

Status: ready-for-agent
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
- [ ] Atualização real com Compose: no commit anterior a esta rodada, subir, enviar 2 fotos (uma PNG), apagar à mão
      uma terceira do volume (linha órfã); trocar para o código novo e `docker compose up --build`:
      as 2 fotos aparecem na tela com `url` nova terminada em `.jpg`; a órfã gera `WARNING` e responde `404`; o log traz o resumo.
- [ ] Segunda subida: nada é reimportado (resumo com zero importadas; mesmas URLs).
- [ ] Clone novo (volume vazio) sobe sem erro e sem aviso.
- [ ] `docker compose exec backend id` → uid 10001; `docker compose exec backend touch /app/uploads/x` falha (só leitura).
- [ ] Teste pytest do comando com pasta temporária: importa, ignora ausente, não importa duas vezes, recusa `../`.
