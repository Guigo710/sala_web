# 71: Registrar no contrato e nos ADRs as correções do Sentinela na rodada 5; conferir o `render.yaml`

Status: ready-for-agent
Responsável: Atlas
Origem: Sentinela
Severidade: baixa
Prioridade: média (o item 4 é antes da primeira publicação com a opção B)
Blocked by: (nenhum)
Referências: ticket 64, 68; `docs/api-contrato.md` §1.4, §4.1; ADR-0003; `docs/publicacao.md`; `render.yaml`

## Contexto
Na verificação final (ticket 68) o Sentinela corrigiu direto alguns problemas pequenos. O código e os testes já
estão no repositório; falta o registro nos documentos do Atlas.

## O que fazer
1. **Contrato §1.4**: valor que passa pelo schema mas o Postgres recusa (id maior que `integer`, como
   `/salas/99999999999`; texto com o caractere NUL, como `?busca=%00`) responde `422 VALIDACAO` com
   `erros: [{"campo": "requisicao", ...}]`. Antes era `500 ERRO_INTERNO`. Handler em `app/core/erros.py`.
   Se preferir `404` para ids fora do intervalo, abrir ticket ao Forge (validação nos parâmetros de caminho).
2. **Contrato §4.1 / `GET /uploads`**: nome com NUL → `404` (como os demais nomes inexistentes).
3. **ADR-0003 (conflito)**: a criação de reserva (avulsa e recorrente) pega `pg_advisory_xact_lock(0x5A1A, sala_id)`
   antes de conferir os conflitos. Motivo: INSERTs simultâneos que se sobrepõem podem dar deadlock na restrição de
   exclusão (SQLSTATE 40P01, que não é `IntegrityError`) e viravam `500` (causa da falha intermitente de
   `test_concorrencia_mesmo_bloco_exatamente_um_sucesso`; o log do Postgres de 19/11 tem 7 "deadlock detected ...
   while checking exclusion constraint" numa só execução). A restrição de exclusão continua como garantia final.
4. **`render.yaml` (ticket 64, pendente)**: conferir em https://render.com/docs/blueprint-spec, de uma rede que
   alcance render.com, (a) se `dockerfilePath`/`dockerContext` são relativos a `rootDir` (hoje `./Dockerfile` e `.`)
   ou à raiz do repositório (seria `./backend/Dockerfile` e `./backend`), e (b) se `autoDeploy: true` ainda é aceito
   ou virou `autoDeployTrigger: commit`. O guia já manda usar a opção A (formulário) se o Blueprint der erro.
5. Revisar as correções feitas no `docs/publicacao.md` (lista no comentário do Sentinela no ticket 68).

## Critérios de aceite
- [ ] Contrato (versão 1.4.1 ou 1.5) e ADR-0003 atualizados.
- [ ] `render.yaml` conferido na documentação oficial (link e data no ticket 64), ou opção B retirada do guia.
