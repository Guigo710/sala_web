# ADR-0009: Publicação na internet com Vercel (frontend), Render (API) e Neon (banco)

Status: aceito · Data: 2026-11-19 · Autor: Atlas · Rodada 5 · Complementa o ADR-0001 (o Docker Compose local continua)

## Contexto
Até a rodada 4 o sistema só rodava com `docker compose` numa máquina da equipe ou da escola. O dono do projeto
quer o sistema acessível pela internet, **com custo zero** e sem administrar servidor. Ele usa Windows e não é
especialista: a publicação tem de ser feita por cliques em painéis web, seguindo `docs/publicacao.md`.

Restrições conhecidas dos planos grátis (os números mudam; a fonte é a página oficial de cada serviço):
- **Render, web service Free**: uma instância; dorme após 15 minutos sem tráfego e leva cerca de 1 minuto para
  acordar; **disco efêmero** (tudo o que é gravado em disco some ao dormir, reiniciar ou fazer deploy); define a
  variável `PORT` e espera a aplicação escutar nela.
- **Render Postgres Free**: expira em 30 dias. Descartado.
- **Neon Free**: PostgreSQL gerenciado, cerca de 1 GB por projeto (conferir), conexão **só com SSL**, o banco
  "suspende" depois de alguns minutos sem uso e volta sozinho na próxima consulta (em geral em menos de 1 s).
- **Vercel Hobby**: hospedagem estática do build do Vite; uso não comercial; cada push gera uma implantação.

## Decisão

### Onde roda cada parte
| Parte | Serviço | Como |
|---|---|---|
| Frontend | Vercel (Hobby) | Build estático do Vite. Root Directory `frontend`, build `npm run build`, saída `dist`. `VITE_API_URL` = URL do Render (variável de ambiente do projeto no Vercel, lida no build). |
| API | Render (web service Free) | O `backend/Dockerfile` atual, Root Directory `backend`. Health check `GET /saude`. Ao iniciar: `alembic upgrade head`, seed idempotente (ADR-0006), importação de fotos antigas (ADR-0010, vazia na nuvem) e `uvicorn` na porta `$PORT`. |
| Banco | Neon (Free) | PostgreSQL 16, conexão **direta** (sem o pooler), `sslmode=require`. |
| Fotos | No próprio banco | ADR-0010 (substitui o armazenamento do ADR-0005). |

- **Região**: API e banco perto um do outro, porque uma requisição faz várias consultas. Recomendado: Render
  **Virginia (US East)** com Neon **AWS US East 1 (N. Virginia)**. Não há região do Render na América do Sul; a
  distância usuário → API (~120 ms) pesa menos que API → banco repetido a cada consulta.
- **Branches**: o site oficial (produção) acompanha o branch `main` nos dois serviços (auto-deploy a cada merge).
  Os outros branches viram **implantações de prévia** no Vercel (não confundir com a *Prévia* da recorrência,
  `GLOSSARY.md`). O Render só publica o `main`.
- **Blueprint opcional**: se existir `render.yaml` na raiz (ticket 64), o serviço pode ser criado por Blueprint;
  o `render.yaml` nunca contém segredos (`sync: false` ou `generateValue: true`).

### Configuração e segredos
- Segredos (`DATABASE_URL`, `JWT_SECRET`, `ADMIN_SENHA`) ficam **só** nos painéis (Render → Environment).
  Nunca no repositório, em `render.yaml`, `vercel.json`, issues, prints ou chat.
- `JWT_SECRET`: gerado pelo botão *Generate* do Render (ou `generateValue: true` no Blueprint).
- `ADMIN_SENHA` só serve para o seed criar o admin na primeira subida; depois do primeiro login e da troca de
  senha, o dono apaga a variável no Render.
- `VITE_API_URL` não é segredo (vai no JavaScript público). Mudou → é preciso refazer a implantação no Vercel
  (o valor entra no build).

### Conexão com o Neon
- `DATABASE_URL` no formato `postgresql+psycopg://USUARIO:SENHA@HOST/BANCO?sslmode=require` (mantendo outros
  parâmetros que o Neon puser, como `channel_binding=require`).
- **Conexão direta, não a do pooler (PgBouncer)**: a API é uma instância com pool pequeno, longe do limite de
  conexões do Neon; o pooler em modo transação complica migrations (Alembic) e parâmetros de sessão. Ticket 63.
- Pool do SQLAlchemy ajustado para um banco que suspende e derruba conexões ociosas: `pool_pre_ping`,
  `pool_recycle` menor que a suspensão do Neon, `connect_timeout` que tolere o banco acordando, tamanhos por
  variável de ambiente. O fuso da sessão passa a ser definido por `SET TIME ZONE` no evento `connect` (não pelo
  parâmetro de inicialização `options`), que funciona igual no Postgres local, no Neon e atrás de pooler. Ticket 63.

### CORS (contrato §1.5)
- A origem do site oficial do Vercel (ex.: `https://sala-web.vercel.app`) entra em `CORS_ORIGENS` no Render,
  exata, sem barra no fim. Domínio próprio, se um dia houver, também entra.
- **As implantações de prévia do Vercel não acessam a API**: cada uma tem outra origem, e a API não aceita
  curingas nem expressão regular (qualquer pessoa pode criar um projeto em `*.vercel.app`). Para testar uma prévia
  contra a API, acrescente temporariamente a URL fixa do branch (`https://<projeto>-git-<branch>-<conta>.vercel.app`)
  em `CORS_ORIGENS` e retire depois.
- O backend normaliza as origens (tira a barra final), registra no log as origens liberadas ao iniciar e recusa
  subir com `*`. Ticket 62.

### Limites de tentativas em memória (ADR-0007 e ticket 50)
- Os contadores (login e troca da própria senha) continuam **em memória, por processo**. Isso só é correto porque
  o Render Free roda **uma única instância** e o `uvicorn` sobe com **um único worker**. **Limitação registrada**:
  se um dia houver mais de uma instância ou worker, cada um conta separado e o limite efetivo se multiplica;
  aí os contadores precisam ir para um armazenamento comum (tabela no Postgres ou Redis), em ADR novo.
- Dormir, reiniciar ou fazer deploy zera os contadores. Aceito: o Render só dorme após 15 minutos **sem tráfego**,
  mais que a janela de 5 minutos, e um ataque em andamento mantém a instância acordada.
- **IP atrás do proxy do Render**: a API não recebe conexões diretas; todas chegam pelo balanceador do Render, então
  `request.client.host` é o IP do balanceador, igual para todos os usuários. Consequências e decisão:
  - a contagem por par (IP, RM) passa a funcionar, na prática, **por RM**: 5 senhas erradas de um RM bloqueiam
    aquele RM por 5 minutos para todos. Aceito (é o bloqueio de conta usual);
  - o teto por IP (20 falhas de qualquer RM) viraria um **bloqueio global**: 20 senhas erradas de qualquer pessoa
    travariam o login de todo mundo por 5 minutos. Por isso o teto passa a ser configurável por
    `LOGIN_MAX_FALHAS_IP` (padrão 20; **0 desliga**) e **na produção do Render fica `0`**. Ticket 62;
  - `FORWARDED_ALLOW_IPS=*` continua proibido: o uvicorn passaria a confiar no `X-Forwarded-For` mandado pelo
    próprio cliente, e qualquer um trocaria de "IP" a cada tentativa, anulando todos os limites;
  - melhoria futura (fora desta rodada): confirmar como o proxy do Render preenche o `X-Forwarded-For`, configurar
    `FORWARDED_ALLOW_IPS` com a rede do proxy e religar o teto por IP.
- Decisão do ticket 53 sobre a opção "mais forte" (revogar as sessões da conta ao estourar o limite da troca de
  senha): **não adotada na v1**. Ver adendo no ADR-0007.

### Cabeçalhos e CSP do frontend no Vercel (substitui, só no Vercel, a CSP com nonce do ticket 52)
O nginx do Compose gera um nonce novo por resposta (`$request_id` + `sub_filter`). O Vercel serve arquivos
estáticos sem processar o HTML por requisição, então não há nonce por resposta. Opções avaliadas:

| Opção | Por que não / por que sim |
|---|---|
| Nonce fixo gravado no build | Um nonce conhecido por todos equivale a `'unsafe-inline'`, só que enganoso. Rejeitada. |
| Middleware do Vercel (edge) reescrevendo o HTML a cada acesso | Uma execução de função por página, mais código, mais limites do plano. Desproporcional. Rejeitada. |
| Hash do `<style>` do FullCalendar | Depende de detalhes internos do FullCalendar (o conteúdo é inserido por CSSOM e muda entre versões). Frágil. Rejeitada. |
| **`style-src 'self' 'unsafe-inline'` só no Vercel**, mantendo `script-src 'self'` | **Escolhida.** |

Justificativa: o que a CSP protege de verdade aqui é o token em `localStorage` (ADR-0004), e quem o rouba é
**script**; `script-src 'self'` continua sem `'unsafe-inline'` e sem `'unsafe-eval'`. Liberar estilos inline abre
espaço só para injeção de CSS, cujo vazamento de dados depende de carregar `url(...)` de outro domínio, e isso
continua barrado por `img-src`, `font-src` e `connect-src`. O React escapa texto, então nem a injeção de CSS tem
caminho conhecido.

Como fica (ticket 65):
- `frontend/vercel.json`: fallback de rotas do React Router para `index.html` (só caminhos sem extensão; arquivo
  inexistente com extensão continua 404), cache longo em `/assets/*`, `nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` e uma CSP fixa no cabeçalho:
  `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https:;
  connect-src 'self' https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self';
  frame-ancestors 'none'`.
- O `vercel.json` é estático e a URL do Render só existe depois de criar o serviço; para não obrigar o dono a editar
  arquivo e fazer commit, o build no Vercel (variável `VERCEL=1`, definida pelo próprio Vercel) grava no
  `index.html` uma `<meta http-equiv="Content-Security-Policy">` que restringe `img-src` e `connect-src` à origem de
  `VITE_API_URL`. O navegador aplica as duas políticas (cabeçalho e meta) e só permite o que ambas permitem, então o
  efeito final é `img-src`/`connect-src` = `'self'` + a API. O marcador `__CSP_NONCE__` sai do `index.html` nesse build.
- No Compose (nginx) nada muda: continua a CSP com nonce do ticket 52.

### Porta e processo
- O `CMD` do `backend/Dockerfile` passa a usar `--port ${PORT:-8000}` (o Render define `PORT`; o Compose continua
  em 8000) e continua com um único worker. Ticket 62.

## Consequências
- Custo zero, sem servidor para administrar; atualizar = merge no `main` (Vercel e Render publicam sozinhos).
- **Primeiro acesso depois de 15 minutos parados leva cerca de 1 minuto** (API acordando; o banco também pode estar
  suspenso). O frontend mostra um aviso de "servidor acordando" e acorda a API assim que a página abre (ticket 66).
  Não usar serviços de "ping" para manter a API acordada: consome as horas grátis do Render e impede o Neon de
  suspender, gastando as horas de computação do plano grátis.
- Disco efêmero: nada do sistema pode depender de arquivo gravado em disco em produção (motivo do ADR-0010).
- Frontend e API publicam separados: numa mudança de contrato, por alguns minutos um pode estar na versão nova e o
  outro na antiga. Aceito; mudanças de contrato devem ser compatíveis para trás quando possível.
- Migration que falha derruba o deploy do Render, mas a versão anterior continua no ar (o Render só troca quando a
  nova passa no health check).
- Implantações de prévia do Vercel não falam com a API sem ajuste manual de `CORS_ORIGENS`.
- Teto de login por IP desligado na produção: um atacante pode tentar 4 senhas a cada 5 minutos por RM, em vários RMs.
  Mitigado por senhas de 8+ caracteres; revisto quando o IP real do cliente for confirmado.
- Dependência de três fornecedores e de planos grátis que mudam. O `docker compose` continua sendo a forma de rodar
  tudo localmente ou num servidor da escola, sem nenhum deles.
- Implementação: tickets 60 a 64 (Forge), 65 a 67 (Pixel), 68 (Sentinela). Guia do dono: `docs/publicacao.md`.
