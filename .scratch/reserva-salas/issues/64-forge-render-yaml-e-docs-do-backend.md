# 64: `render.yaml` (Blueprint, opcional) e documentação de publicação do backend

Status: ready-for-agent
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
- [ ] `render.yaml` sem nenhum valor secreto (revisão do Sentinela no ticket 68).
- [ ] YAML válido e com os campos conferidos na documentação oficial (link da página consultada nos comentários do ticket).
- [ ] `backend/README.md` e `.env.example` atualizados; nomes de variáveis iguais aos do guia.
