# 29: Dúvidas e decisões do Forge na implementação do backend v1

Status: needs-triage
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
