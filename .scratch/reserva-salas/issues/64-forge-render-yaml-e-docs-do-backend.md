# 64: `render.yaml` (Blueprint, opcional) e documentação de publicação do backend

Status: ready-for-human (código pronto; falta conferir o render.yaml na documentação oficial do Render, ver Resolução)
Responsável: Forge
Origem: Atlas
Prioridade: média (opcional: o guia funciona sem Blueprint)
Blocked by: 62, 63
Referências: ADR-0009; `docs/publicacao.md` (seção "Opção B: Blueprint"); `.env.example`; `backend/README.md`

## Contexto
O guia `docs/publicacao.md` ensina a criar o web service no Render pelos formulários (opção A). Um `render.yaml` na
raiz permite criar o mesmo serviço por **Blueprint** (opção B), com menos campos para o dono preencher. O arquivo é
público (está no repositório): **nenhum segredo** nele.

## O que fazer
1. `render.yaml` na **raiz** do repositório, com um único web service:
   - `type: web`, `name: sala-web-api`, `runtime: docker`, `plan: free`, `region: virginia`, `branch: main`,
     `rootDir: backend`, `dockerfilePath: ./Dockerfile`, `dockerContext: .`, `healthCheckPath: /saude`, `autoDeploy: true`;
   - `envVars`:
     - `DATABASE_URL`: `sync: false` (o Render pede o valor ao criar);
     - `JWT_SECRET`: `generateValue: true`;
     - `CORS_ORIGENS`: `sync: false`;
     - `ADMIN_RM`: `sync: false`; `ADMIN_SENHA`: `sync: false`; `ADMIN_NOME`: `value: Administrador`;
     - `TZ: America/Sao_Paulo`, `JWT_EXPIRA_MINUTOS: "480"`, `UPLOAD_MAX_MB: "5"`, `LOGIN_MAX_FALHAS_IP: "0"`;
     - **não** definir `PORT` (o Render define) nem `UPLOAD_DIR`.
   - Conferir os nomes dos campos na documentação oficial de Blueprint do Render (podem ter mudado) e validar o
     arquivo (o painel do Render mostra erros ao ler o Blueprint; se houver validador/esquema oficial, usar no CI).
2. Se decidir **não** fazer o `render.yaml`, registrar aqui o motivo e avisar o Atlas para tirar a opção B do guia.
3. `backend/README.md`: seção curta "Publicação (Render + Neon)" apontando para `docs/publicacao.md` e listando as
   variáveis de produção (nomes, para que servem, quais são segredo), sem valores reais.
4. `.env.example`: bloco comentado "Produção (Render)" com os nomes e um lembrete de que os valores ficam só no painel.

## Critérios de aceite
- [x] `render.yaml` sem nenhum valor secreto (revisão do Sentinela no ticket 68).
- [ ] (parcial: YAML válido; conferência na documentação oficial pendente, ver Resolução) YAML válido e com os campos conferidos na documentação oficial (link da página consultada nos comentários do ticket).
- [x] `backend/README.md` e `.env.example` atualizados; nomes de variáveis iguais aos do guia.

## Resolução (Forge, rodada 5)
- `render.yaml` na raiz, exatamente com os campos e variáveis pedidos (`sync: false` para `DATABASE_URL`,
  `CORS_ORIGENS`, `ADMIN_RM`, `ADMIN_SENHA`; `generateValue: true` para `JWT_SECRET`; valores fixos como texto;
  sem `PORT` nem `UPLOAD_DIR`). Nenhum valor secreto.
- YAML válido (lido com `yaml.safe_load` em `test_render_yaml_sem_segredos_e_com_os_campos_do_guia`, que também
  confere que `rootDir` + `dockerfilePath` apontam para `backend/Dockerfile`, que nenhum segredo tem `value` e que
  todos os nomes existem no `Config` da API).
- **Pendente (critério 2): conferência na documentação oficial.** Esta sessão não tem acesso a `render.com`
  (bloqueado pela rede); o esquema JSON oficial (`https://render.com/schema/render.yaml.json`, listado no SchemaStore)
  também fica nesse domínio, e não encontrei cópia dele no GitHub. Páginas a conferir:
  https://render.com/docs/blueprint-spec. Pontos que merecem atenção do Atlas/Sentinela:
  - `dockerfilePath`/`dockerContext` foram escritos **relativos a `rootDir`** (como no formulário e no guia). Se o
    Render os interpretar relativos à raiz do repositório, o certo seria `./backend/Dockerfile` e `./backend`;
  - `autoDeploy: true` pode ter sido substituído por `autoDeployTrigger` (`commit`/`checksPass`/`off`) em versões
    recentes da especificação; com `checksPass` o Render só publicaria depois do CI verde.
  O validador do painel do Render (ao ler o Blueprint) ou o esquema JSON podem entrar no CI quando o domínio estiver
  liberado. A opção A do guia não depende deste arquivo.
- `backend/README.md`: seção "Publicação (Render + Neon)" com a tabela das variáveis (nome, uso, segredo), mais
  "Fotos", "Fotos antigas" e "Mudanças da rodada 5 para quem já roda localmente". `.env.example`: bloco
  "Produção (Render)" com os mesmos nomes do guia e o lembrete de que os valores ficam só no painel.
