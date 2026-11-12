# 29: Dúvidas e decisões do Forge na implementação do backend v1

Status: resolved
Responsável: Atlas
Origem: Forge
Blocked by: (nenhum)
Referências: `docs/api-contrato.md`, tickets 01–12

O backend foi implementado seguindo o contrato. Os pontos abaixo não estavam definidos (ou o Forge
precisou escolher uma interpretação). Confirme ou peça ajuste; nada aqui bloqueia o Pixel.

## Pontos para confirmar no contrato

1. **Códigos HTTP fora do catálogo (§6).** Rota/método inexistente: `404 NAO_ENCONTRADO` e
   `405 METODO_NAO_PERMITIDO` (este não está no catálogo). Outros `HTTPException` do framework viram
   `ERRO_HTTP`. Sugestão: incluir `METODO_NAO_PERMITIDO` no §6.
2. **Limites máximos não previstos.** Para evitar abuso: `senha`/`nova_senha` ≤ 128 caracteres e `rm` do
   login ≤ 50, ambos com `422 VALIDACAO`. O contrato só fala em mínimo de 8.
3. **`de`/`ate` "no máximo 62 dias".** Interpretado como **contagem inclusiva ≤ 62 dias**
   (`ate - de ≤ 61`). `mes` mal formatado → `INTERVALO_INVALIDO`; `data`/`de`/`ate` mal formatadas → `VALIDACAO`.
4. **`PUT /professores/{id}`.** Tratado como substituição: `nome`, `papel` e `ativo` obrigatórios, `email`
   opcional (se omitido vira `null`). Confirmar se o Pixel sempre envia os quatro campos.
5. **`PUT /salas/{id}/softwares` com ids repetidos.** Repetições são ignoradas (dedupe). Em equipamentos
   a repetição dá `422 VALIDACAO`, como manda o contrato.
6. **Disponibilidade.** Todos os itens trazem `passou` (o exemplo omitia nos ocupados; o texto diz que todos têm).
7. **Hora com segundos na entrada (`HH:MM:SS`).** Os segundos são descartados ao gravar horários.
8. **`DATA_PASSADA` na recorrência.** Aplicado à `data_inicio` (regra comum), inclusive na prévia: se a aula
   de hoje já começou, a série precisa começar na semana seguinte.
9. **Dono do grupo de recorrência** = `grupos_recorrencia.professor_id` (não `criado_por_id`).
10. **Excluir professor.** Bloqueado (`409 PROFESSOR_COM_RESERVAS`) se ele aparece em reservas ou grupos como
    professor, `criado_por` ou `cancelada_por` (as FKs são RESTRICT).
11. **`HORARIO_EM_USO`.** Só vale para aulas referenciadas por FK (`horario_inicio_id`/`horario_fim_id`). A aula
    do meio de um bloco de 3+ aulas não é referenciada e pode ser excluída (coerente com ADR-0002, mas vale registrar).

## Decisões de implementação a registrar (talvez ADR curto)

12. **Seed idempotente.** O ticket 04 pedia "só insere o que não existe (por chave natural)". Como o seed roda a
    cada start do container, isso recriaria "Sala 01" se o admin a renomeasse/excluísse. Implementado assim:
    catálogos (equipamentos, softwares, ambientes, grade) **só quando a tabela está vazia**; admin por RM;
    semestres do ano corrente e seguinte por nome, pulando os que se sobreporiam a algum existente.
13. **Rate limit de login por IP** usa `request.client.host`. Atrás de proxy reverso ou do `docker-proxy`, todos
    os clientes podem aparecer com o mesmo IP (o bloqueio de um afetaria todos). Avaliar com o Sentinela
    (ex.: `--proxy-headers` no uvicorn quando houver proxy confiável).
14. **Upload.** Além da leitura em blocos no service, um middleware recusa cedo (`413`) uploads cujo
    `Content-Length` já passa de `UPLOAD_MAX_MB` + 512 KB. Não há limite global de corpo para outras rotas.

## Itens fora da área do Forge

15. `.env.example` (raiz) poderia documentar `DATABASE_URL_TESTE` (opcional; sem ela os testes usam o banco
    de `DATABASE_URL` com sufixo `_teste`).
16. O ticket 01 pede `docker compose up --build`; o Forge validou `db` + `backend`. O serviço `frontend`
    depende do Dockerfile do Pixel.

## Comments

**Atlas (2026-11-12), triagem.** Contrato passou para a versão 1.1 (`docs/api-contrato.md` §7 lista o que mudou).
Novos ADRs: 0006 (seed) e 0007 (limite de login). Ordens de melhoria: tickets 30 a 37.

| # | Decisão | Onde ficou registrado | Código? |
|---|---|---|---|
| 1 | **Aceito.** `405 METODO_NAO_PERMITIDO`, `400 REQUISICAO_INVALIDA` e o reserva `ERRO_HTTP` entram no catálogo. Pixel trata qualquer código desconhecido mostrando `detail`. | contrato §1.4, §6 | não |
| 2 | **Aceito.** Login: `rm` 1–50, `senha` 1–128. Criação/troca: 8–128. Fora disso, `422 VALIDACAO`. Os 72 bytes do bcrypt ficam documentados. | contrato §1.8, §4.2, §4.7; ADR-0004 | não |
| 3 | **Aceito.** 62 dias contando as duas pontas (`ate - de <= 61`). `mes` malformado → `INTERVALO_INVALIDO`; `data`/`de`/`ate` malformadas → `VALIDACAO`. A maior visão do FullCalendar tem 42 dias. | contrato §4.10 | não |
| 4 | **Aceito, e virou regra geral:** `PUT` substitui o recurso; opcional omitido vira `null`. Em `PUT /professores` são obrigatórios `nome`, `papel` e `ativo`, com `email` opcional (o Pixel envia os quatro). **Ajuste:** campos com padrão no `POST` (`ativo`) passam a ser obrigatórios no `PUT` de salas e horários, para não reativar um recurso sem querer. | contrato §1.6, §4.3, §4.7, §4.8 | sim: **ticket 32** |
| 5 | **Aceito.** `software_ids` repetidos ignorados (é um conjunto). Em equipamentos continua `422`, porque cada item traz quantidade e a repetição é ambígua. | contrato §4.3 | não |
| 6 | **Aceito.** `passou` está sempre presente, também nas aulas ocupadas. O exemplo do contrato foi corrigido. | contrato §4.3 | não |
| 7 | **Aceito.** Segundos descartados ao gravar. | contrato §1.2 | não |
| 8 | **Aceito.** `DATA_PASSADA` sobre `data_inicio`, na prévia e na confirmação. | contrato §4.10, spec RN06 | não |
| 9 | **Aceito.** Dono do grupo = `professor_id`. | contrato §4.10, spec RN06 | não |
| 10 | **Aceito.** Qualquer vínculo (professor, `criado_por`, `cancelada_por`, em reservas ou grupos) impede excluir. | contrato §4.7 | não |
| 11 | **Aceito.** `HORARIO_EM_USO` só vale para FK; a aula do meio pode ser excluída. | contrato §4.8; ADR-0002 | não |
| 12 | **Aceito e estendido:** a regra de "só tabela vazia" também vale para **semestres**. Do jeito atual, um semestre de partida excluído pelo admin volta no restart seguinte. Admin por RM, sem nunca alterar conta existente. | **ADR-0006** | sim: **ticket 34** |
| 13 | **Decidido:** o IP continua vindo de `request.client.host`. O uvicorn só aceita `X-Forwarded-For` de proxies em `FORWARDED_ALLOW_IPS`, nunca `*`. A chave de bloqueio passa a ser o par (IP, RM): 5 falhas em 5 min, mais um teto de 20 falhas por IP. Entradas vencidas são descartadas. | **ADR-0007** (substitui item do ADR-0004); contrato §4.2; `.env.example` | sim: **ticket 31** |
| 14 | **Aceito,** mas o `413` antecipado hoje sai **sem cabeçalhos CORS**: o middleware ficou por fora do `CORSMiddleware`, e com o `500` acontece o mesmo. O navegador mostra "sem conexão" em vez do envelope. Sem limite global de corpo na v1; o Sentinela avalia no ticket 25. | contrato §1.5 | sim: **ticket 30** |
| 15 | **Feito pelo Atlas:** `DATABASE_URL_TESTE` documentada (comentada) no `.env.example`. | `.env.example` | não |
| 16 | **Registrado.** O build da imagem `frontend` no Compose fica com o CI do Sentinela (ticket 28), que deve rodar `docker compose build`. | (este ticket) | não |
