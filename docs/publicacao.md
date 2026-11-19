# Como publicar o sala_web na internet

Guia passo a passo para o dono do projeto. Tudo é feito **pelo navegador**, com cliques; não precisa de terminal.
Escrito para Windows, mas funciona igual em qualquer sistema. Tempo estimado: 1 hora na primeira vez.

Decisões técnicas por trás deste guia: `docs/adr/0009-publicacao-vercel-render-neon.md` e
`docs/adr/0010-fotos-no-banco.md`.

---

## 0. Visão geral

```
 Navegador do professor
        │
        ▼
 Vercel  ──────────────►  Render  ──────────────►  Neon
 (site: telas)            (API: regras)            (banco: dados e fotos)
 https://....vercel.app   https://....onrender.com
```

| Parte | Serviço | Plano | O que fica lá |
|---|---|---|---|
| Site (frontend) | Vercel | Hobby (grátis) | As telas, geradas a partir da pasta `frontend` |
| API (backend) | Render | Free (grátis) | O programa que atende o site, a partir da pasta `backend` |
| Banco de dados | Neon | Free (grátis) | Ambientes, reservas, contas **e as fotos** |

Ordem do guia: **Neon → Render → Vercel → voltar ao Render**. Essa ordem existe porque cada serviço precisa de um
endereço do anterior.

### O que você vai anotar
Durante o guia você vai copiar 4 informações. Guarde-as num **gerenciador de senhas** ou num papel.
**Não** salve num arquivo dentro da pasta do projeto, não mande em grupo de mensagens e não cole em issues.

| # | Informação | É segredo? | Exemplo |
|---|---|---|---|
| A | Endereço do banco (Neon) | **Sim** | `postgresql+psycopg://neondb_owner:...@ep-....neon.tech/neondb?sslmode=require` |
| B | Senha inicial do admin | **Sim** | uma senha forte que você inventar |
| C | Endereço da API (Render) | Não | `https://sala-web-api.onrender.com` |
| D | Endereço do site (Vercel) | Não | `https://sala-web.vercel.app` |

### Avisos importantes antes de começar
- **Segredos nunca vão para o repositório.** O endereço do banco, a senha do admin e o `JWT_SECRET` ficam **só**
  nos painéis do Render. O arquivo `.env` do seu computador também nunca vai para o GitHub (o `.gitignore` já
  impede, mas não force).
- **A API dorme.** No plano grátis do Render, depois de 15 minutos sem ninguém usar, a API "dorme". O primeiro
  acesso depois disso demora **cerca de 1 minuto**; o site mostra um aviso de "servidor acordando". É normal.
- **Os limites dos planos grátis mudam.** Os números deste guia eram os vigentes em novembro de 2026. Antes de
  começar, e de vez em quando, confira as páginas oficiais de preços:
  [vercel.com/pricing](https://vercel.com/pricing), [render.com/pricing](https://render.com/pricing),
  [neon.com/pricing](https://neon.com/pricing).
- **Se algum serviço pedir cartão de crédito, pare** e fale com o grupo: este guia só usa planos grátis.
- Os nomes dos botões podem mudar um pouco com o tempo. Se não achar um botão com o nome exato, procure algo
  parecido na mesma região da tela.

---

## 1. Criar as contas

Use a **mesma conta do GitHub** que tem acesso ao repositório `sala_web` nos três serviços. Assim eles conseguem
ler o código.

1. **Neon**: abra [neon.com](https://neon.com) → **Sign up** → **Continue with GitHub** → autorize.
2. **Render**: abra [render.com](https://render.com) → **Get Started** (ou **Sign up**) → **GitHub** → autorize.
3. **Vercel**: abra [vercel.com](https://vercel.com) → **Sign Up** → escolha o plano **Hobby** → **Continue with GitHub** → autorize.

Se algum pedir nome de time/organização, pode usar seu nome ou "sala-web".

---

## 2. Criar o banco no Neon

1. No painel do Neon, crie um projeto (botão **New Project** ou a tela inicial de boas-vindas):
   - **Project name**: `sala-web`
   - **Postgres version**: **16** (se não houver, a mais próxima; o sistema funciona em 16 ou 17)
   - **Cloud provider**: **AWS**
   - **Region**: **AWS US East 1 (N. Virginia)** (fica perto da API, que você vai criar na região Virginia do Render)
   - Clique em **Create project**.
2. Na página do projeto, clique no botão **Connect** (fica no topo do painel do projeto).
3. Na janela que abrir:
   - **Branch**: `production` (ou `main`, o que vier marcado)
   - **Database**: `neondb` · **Role**: `neondb_owner` (os que vierem marcados)
   - **Connection pooling**: **desligado** (a chave deve ficar apagada). Usamos a conexão direta.
   - Se houver opções de formato, escolha **Connection string**.
   - Clique em **Show password** (se existir) e depois no botão de **copiar**.
4. Você copiou algo assim (uma linha só):
   ```
   postgresql://neondb_owner:AbCdEf123@ep-nome-123456.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
5. **Troque só o começo**: `postgresql://` vira `postgresql+psycopg://`. Fica assim:
   ```
   postgresql+psycopg://neondb_owner:AbCdEf123@ep-nome-123456.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
   ```
   - Mantenha **tudo** o que vem depois do `?`.
   - Se não houver `?sslmode=require` no fim, acrescente `?sslmode=require`. A conexão do Neon **exige SSL**.
   - Confira que o endereço (a parte depois do `@`) **não** tem a palavra `-pooler`. Se tiver, volte ao passo 3 e
     desligue **Connection pooling**.
   - Se esquecer de trocar o começo, a API troca sozinha (aceita `postgresql://` e `postgres://`); mas faça a troca
     mesmo assim, para o valor anotado ficar igual ao deste guia.
6. Isto é a **informação A** (segredo). Anote.

Você **não** precisa criar tabelas: a API cria tudo sozinha na primeira vez que subir.

---

## 3. Criar a API no Render

Há duas formas. Use a **opção A** (formulário): é a recomendada. A **opção B** (Blueprint) usa o arquivo
`render.yaml` da raiz do repositório, que ainda **não foi conferido** na documentação oficial do Render. Se a opção B
der qualquer erro, vale a opção A (veja o fim da opção B).

### Antes: escolher a senha inicial do admin (informação B)
Invente uma senha com **pelo menos 12 caracteres** (letras, números e símbolos). Ela só serve para o primeiro
login; você vai trocá-la logo depois. Anote.

### Opção A: pelo formulário
1. No painel do Render, clique em **+ New** → **Web Service**.
2. Em **Source Code** / **Git Provider**, escolha **GitHub**. Se o repositório `sala_web` não aparecer, clique em
   **Configure GitHub** (ou **Configure account**), escolha **Only select repositories**, marque `sala_web` e salve.
   Volte e selecione `sala_web` → **Connect**.
3. Preencha:

   | Campo | Valor |
   |---|---|
   | **Name** | `sala-web-api` (vira parte do endereço) |
   | **Language** (ou **Runtime**) | **Docker** |
   | **Branch** | `main` |
   | **Region** | **Virginia (US East)** |
   | **Root Directory** | `backend` |
   | **Dockerfile Path** | deixe o sugerido, `./Dockerfile` (o Render já parte da pasta `backend`; o arquivo é `backend/Dockerfile`) |
   | **Instance Type** | **Free** |

4. Em **Environment Variables**, clique em **Add Environment Variable** para cada linha:

   | NAME | VALUE | Observação |
   |---|---|---|
   | `DATABASE_URL` | a **informação A** | segredo |
   | `JWT_SECRET` | clique em **Generate** (gerar), se o botão existir | segredo; ver abaixo se não houver o botão |
   | `ADMIN_RM` | `admin` | o "RM" do primeiro login |
   | `ADMIN_SENHA` | a **informação B** | segredo; você vai apagar depois |
   | `ADMIN_NOME` | `Administrador` | |
   | `CORS_ORIGENS` | `http://localhost:5173` | provisório; troca no passo 5 |
   | `LOGIN_MAX_FALHAS_IP` | `0` | obrigatório no Render (ADR-0009) |
   | `TZ` | `America/Sao_Paulo` | |
   | `JWT_EXPIRA_MINUTOS` | `480` | opcional (8 horas de sessão) |
   | `UPLOAD_MAX_MB` | `5` | opcional (tamanho máximo da foto enviada) |

   **Não** crie `PORT` (o Render cria sozinho) nem `UPLOAD_DIR`.

   Sem botão **Generate** para o `JWT_SECRET`? Gere no Windows: tecla Windows → digite `PowerShell` → Enter →
   cole a linha abaixo → Enter → copie o resultado (uma linha longa de letras e números) e cole no valor:
   ```
   $b = New-Object byte[] 48; [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); [Convert]::ToBase64String($b)
   ```
   O `JWT_SECRET` precisa ter **pelo menos 32 caracteres**; a API se recusa a subir com o valor de exemplo.

5. Abra **Advanced** (avançado) e preencha:
   - **Health Check Path**: `/saude`
   - **Auto-Deploy**: **On Commit** (ou **Yes**)
6. Clique em **Deploy Web Service** (ou **Create Web Service**).
7. Espere. A primeira vez leva alguns minutos (o Render monta a imagem e a API cria as tabelas). Acompanhe na aba
   **Logs**. Quando aparecer **Live** (verde) no topo, terminou.
8. No topo da página do serviço há o endereço da API, algo como `https://sala-web-api.onrender.com`
   (pode ter letras a mais, se o nome já existia). Isto é a **informação C**. Anote **sem barra no fim**.
9. Teste: abra no navegador `https://SEU-ENDERECO.onrender.com/saude`. Deve aparecer:
   ```
   {"status":"ok"}
   ```
   Se aparecer `{"status":"erro"}` ou a página não abrir, veja **Problemas comuns** no fim.

### Opção B: por Blueprint (só se existir `render.yaml` na raiz do repositório)
1. No painel do Render, **+ New** → **Blueprint**.
2. Escolha o repositório `sala_web` (mesmo procedimento do passo 2 da opção A) → **Connect**.
3. O Render lê o `render.yaml` e mostra o serviço `sala-web-api`. Dê um nome ao Blueprint (ex.: `sala-web`).
4. Ele vai pedir os valores marcados como secretos: `DATABASE_URL` (informação A), `ADMIN_RM` (`admin`),
   `ADMIN_SENHA` (informação B), `CORS_ORIGENS` (`http://localhost:5173` por enquanto). O `JWT_SECRET` é gerado sozinho.
5. Clique em **Apply** (ou **Deploy Blueprint**). Depois siga os passos 7 a 9 da opção A.

**Se a opção B der erro** (o painel acusa erro ao ler o `render.yaml`, ou o primeiro deploy falha nos **Logs**
dizendo que não achou o `Dockerfile`), não tente consertar o arquivo: apague o que foi criado (serviço
`sala-web-api` → **Settings** → no fim da página, **Delete Web Service**; e o Blueprint, em **Blueprints** →
`sala-web` → **Settings** → **Delete Blueprint**) e faça a **opção A**. Apagar antes evita que o endereço novo
ganhe letras a mais (`sala-web-api-xxxx.onrender.com`).

---

## 4. Criar o site no Vercel

1. No painel do Vercel, clique em **Add New...** → **Project**.
2. Em **Import Git Repository**, escolha **GitHub**. Se `sala_web` não aparecer, clique em
   **Adjust GitHub App Permissions** (ou **Install**), libere o repositório `sala_web` e volte.
   Ao lado de `sala_web`, clique em **Import**.
3. Na tela **Configure Project**:

   | Campo | Valor |
   |---|---|
   | **Project Name** | `sala-web` (vira parte do endereço) |
   | **Framework Preset** | **Vite** (normalmente é detectado sozinho) |
   | **Root Directory** | clique em **Edit**, escolha a pasta `frontend` → **Continue** |

4. Abra **Build and Output Settings** e confira (ligue a chave **Override** ao lado de cada um, se for preciso mudar):
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: deixe o padrão
5. Abra **Environment Variables** e adicione:
   - **Key**: `VITE_API_URL`
   - **Value**: a **informação C** (ex.: `https://sala-web-api.onrender.com`), **sem barra no fim**
   - clique em **Add**
6. Clique em **Deploy**. Espere 1 ou 2 minutos até aparecer a tela de parabéns → **Continue to Dashboard**.
7. Na página do projeto, em **Domains**, está o endereço oficial do site, algo como `https://sala-web.vercel.app`.
   Isto é a **informação D**. Anote **sem barra no fim**.
   - Use o endereço de **Domains**, não os endereços compridos de cada implantação
     (como `sala-web-abc123-seunome.vercel.app`).

O site já abre, mas ainda **não consegue falar com a API**: falta o passo 5.

> O `VITE_API_URL` entra no site no momento da montagem. Se um dia mudar o endereço da API, troque a variável em
> **Settings → Environment Variables** e depois vá em **Deployments**, clique nos **...** da implantação mais recente
> → **Redeploy**. Só trocar a variável não basta.

---

## 5. Voltar ao Render e liberar o site (CORS)

A API só aceita pedidos vindos dos endereços listados em `CORS_ORIGENS`.

1. No Render, abra o serviço `sala-web-api` → no menu da esquerda, **Environment**.
2. Edite `CORS_ORIGENS` e troque o valor pela **informação D**, por exemplo:
   ```
   https://sala-web.vercel.app
   ```
   - Exatamente como aparece em **Domains**, com `https://` e **sem barra no fim**.
   - Para mais de um endereço, separe por vírgula (ex.: se um dia houver domínio próprio).
3. Clique em **Save Changes** e escolha **Save, rebuild, and deploy** (ou **Save and deploy**).
4. Espere ficar **Live** de novo. Na aba **Logs** deve aparecer uma linha com "CORS liberado para:" e o seu endereço.

---

## 6. Primeiro acesso e login do admin

1. Abra a **informação D** (o site no Vercel). Se a API estava dormindo, aparece o aviso de servidor acordando;
   espere até 1 minuto.
2. Clique em **Entrar**. RM: `admin` (o `ADMIN_RM`), senha: a **informação B**.
3. Troque a senha agora: no topo, à direita, clique no seu nome (**Administrador**, com o selo **admin**); abre a
   página **Minha conta**. Na parte **Trocar senha**, digite a senha atual (informação B) e a nova, e clique em
   **Trocar senha**. Use uma senha nova e forte, só sua (mínimo de 8 caracteres).
4. Volte ao Render → **Environment** → apague a variável `ADMIN_SENHA` (ícone de lixeira) → **Save, rebuild, and deploy**.
   Ela só servia para criar o admin na primeira vez. Daí em diante os **Logs** mostram, a cada subida, o aviso
   `ADMIN_RM/ADMIN_SENHA não definidos: admin inicial não criado.`: é esperado e não é erro.
5. Recomendado: no painel de admin, crie uma **segunda conta de admin** para outra pessoa do grupo. Se alguém
   esquecer a senha, o outro admin redefine.
6. O sistema começa com dados genéricos (ambientes, grade de horários, semestres de exemplo). Ajuste pelo painel de
   admin: ambientes reais, fotos, equipamentos, softwares, professores, horários e semestres.

---

## 7. Conferência final

Marque cada item:

- [ ] `https://SUA-API.onrender.com/saude` mostra `{"status":"ok"}`.
- [ ] O site do Vercel abre, mostra a agenda e a lista de ambientes.
- [ ] Login do admin funciona e a senha foi trocada; `ADMIN_SENHA` foi apagada no Render.
- [ ] Envio de uma foto de ambiente pelo admin funciona e a foto aparece no detalhe do ambiente.
- [ ] No Render: **Manual Deploy** → **Restart service** (ou **Deploy latest commit**). Depois que voltar a **Live**,
      a foto **continua aparecendo** (prova de que está guardada no banco, não no disco do Render).
- [ ] Abrir o site direto num endereço interno, como `https://SEU-SITE.vercel.app/agenda`, funciona (não dá 404).
- [ ] Uma reserva de teste é criada e cancelada pelo admin.
- [ ] Cabeçalhos de segurança do site: no Chrome ou Edge, abra o site, aperte **F12** → aba **Network** (Rede) →
      recarregue a página (F5) → clique na primeira linha (o endereço do site) → **Headers** (Cabeçalhos) →
      **Response Headers**: deve haver `content-security-policy` (com `frame-ancestors 'none'`),
      `x-frame-options: DENY` e `x-content-type-options: nosniff`. Na aba **Console** não deve haver erros
      vermelhos falando de "Content Security Policy".
- [ ] Uma implantação de **prévia** (de um branch que não é o `main`) abre, mas mostra erro de conexão com o
      servidor: é o esperado (seção 8).

Problemas? Veja a próxima seção ou abra um ticket para o grupo.

---

## 8. Como atualizar o site depois

Não há nada a fazer nos painéis no dia a dia:

1. O grupo trabalha num branch e abre um pull request no GitHub.
2. **Merge no `main` publica sozinho**: o Vercel remonta o site e o Render remonta a API (o Render normalmente só
   refaz a API quando algo dentro de `backend/` mudou). Mudanças no banco (migrations) são aplicadas
   automaticamente quando a API sobe.
3. Acompanhe: no Vercel, aba **Deployments**; no Render, aba **Events**/**Logs**. Se a versão nova da API falhar, o
   Render mantém a anterior no ar.

### Implantações de prévia (branches que não são o `main`)
- Para cada branch ou pull request, o Vercel cria um endereço de **prévia** (aparece como comentário no pull request).
- Essas prévias **não conseguem usar a API**: ela só aceita o endereço oficial. Na prévia, o site mostra erro de
  conexão; isso é esperado.
- Para testar uma prévia de verdade: copie o endereço fixo do branch (algo como
  `https://sala-web-git-NOME-DO-BRANCH-SEUNOME.vercel.app`), acrescente-o em `CORS_ORIGENS` no Render separado por
  vírgula (ex.: `https://sala-web.vercel.app,https://sala-web-git-...vercel.app`), salve, teste e **depois retire**.
- No plano Hobby, as prévias costumam pedir login do Vercel para abrir; só a sua conta tem acesso.

---

## 9. Problemas comuns

| O que aparece | Causa provável | O que fazer |
|---|---|---|
| Site carrega, mas mostra "Não foi possível conectar ao servidor" | `CORS_ORIGENS` diferente do endereço do site, ou `VITE_API_URL` errada | Confira o passo 5 (sem barra no fim, `https://`). Confira `VITE_API_URL` no Vercel; se mudou, faça **Redeploy**. Confira se `/saude` da API abre. |
| Site demora quase 1 minuto na primeira vez | API dormindo (normal no plano grátis) | Espere. Não use serviços de "ping" para mantê-la acordada: gastam as horas grátis do Render e do Neon. |
| Deploy no Render falha; nos Logs aparece `JWT_SECRET` | Segredo curto ou o de exemplo | Gere outro (passo 3, item 4) com 32+ caracteres. |
| Logs com `Can't load plugin` ou `Could not parse SQLAlchemy URL` | `DATABASE_URL` incompleta (não começa com `postgres`) | Copie de novo no Neon (passo 2) e cole a linha inteira. |
| Deploy no Render falha dizendo que não achou o `Dockerfile` | Pasta do Dockerfile | Render → serviço → **Settings** → **Build & Deploy**: **Root Directory** = `backend`. Se o campo **Dockerfile Path** não mostrar `backend/` antes do valor, use `backend/Dockerfile` e **Docker Build Context Directory** = `backend`; se mostrar, use `./Dockerfile` e `.`. Salve e faça **Manual Deploy**. |
| Montagem no Vercel falha com `VITE_API_URL` nos **Build Logs** | Variável vazia, sem `https://` ou com espaço | Corrija em **Settings → Environment Variables** (ex.: `https://sala-web-api.onrender.com`) e faça **Redeploy**. |
| Logs com `SSL`, `password authentication failed` ou `could not translate host name` | Endereço do banco copiado incompleto ou senha errada | Copie de novo no Neon (botão **Connect**) e refaça a troca do começo. |
| Logs com `CORS_ORIGENS` e a API não sobe | Valor com caminho (ex.: `/agenda`) ou `*` | Use só `https://endereco.vercel.app`. |
| `/saude` mostra `{"status":"erro"}` | A API não alcança o banco | Confira `DATABASE_URL`; no Neon, veja se o projeto está ativo e dentro dos limites. |
| Página em branco ou 404 ao abrir `/agenda` direto | Configuração do Vercel | Confira **Root Directory** = `frontend` e **Output Directory** = `dist`. Avise o grupo (arquivo `frontend/vercel.json`). |
| "Muitas tentativas" no login | 5 senhas erradas para o mesmo RM | Espere 5 minutos. |
| Esqueci a senha e não há outro admin | A API nunca altera uma conta que já existe | Render → **Environment**: troque `ADMIN_RM` para um RM novo (ex.: `admin2`) e crie de novo `ADMIN_SENHA` com uma senha provisória → **Save, rebuild, and deploy**. Entre com `admin2`, redefina a senha da conta antiga (**Admin** → **Professores** → **Redefinir senha** na linha dela) e depois apague `ADMIN_SENHA` de novo. |
| Uma foto aparece como "Foto indisponível" | Foto antiga que não foi encontrada ao passar para o banco | Exclua a foto e envie de novo pelo admin. |

Onde olhar: Render → serviço → **Logs**; Vercel → projeto → **Deployments** → clique na implantação → **Build Logs**.

---

## 10. Limites dos planos grátis (confira sempre nas páginas oficiais)

Valores aproximados de novembro de 2026; **podem mudar** sem aviso. Fontes: as páginas de preços citadas no início.

| Serviço | O que observar |
|---|---|
| **Vercel Hobby** | Uso pessoal e não comercial. Limites mensais de tráfego e de montagens (builds), folgados para este projeto. |
| **Render Free** | Dorme após 15 min sem tráfego; acorda em ~1 min. Cota mensal de horas de execução por conta (em torno de 750 h). Memória pequena (~512 MB). **Disco apagado** a cada sono, reinício ou deploy (por isso as fotos ficam no banco). |
| **Neon Free** | Espaço por projeto (informado ~1 GB; já foi 0,5 GB em outras épocas). Cota mensal de horas de computação; o banco "dorme" sozinho depois de alguns minutos parado e acorda na próxima consulta. Histórico de restauração curto. |

Estimativa de uso do banco: cerca de 30 ambientes com 6 fotos de ~300 KB cada dá uns 55 MB, mais os dados.
Acompanhe em Neon → projeto → **Monitoring**/**Usage**.

---

## 11. Se um segredo vazar

Vazou = apareceu num print, num commit, numa conversa, num arquivo compartilhado.

| Segredo | O que fazer |
|---|---|
| Endereço do banco (A) | Neon → projeto → **Roles** (ou **Branches → Roles**) → `neondb_owner` → **Reset password**. Copie a nova connection string (passo 2), atualize `DATABASE_URL` no Render e salve com deploy. |
| `JWT_SECRET` | Render → **Environment** → gere um novo valor → salve com deploy. Todos precisarão entrar de novo. |
| Senha de um admin | Troque pela tela **Minha conta**, ou peça ao outro admin para redefinir. |

Se o vazamento foi num commit, apagar o commit **não basta** (o histórico guarda): troque o segredo do mesmo jeito.

---

## 12. E o Docker Compose local?

Continua igual para o grupo: `docker compose up --build` na raiz do repositório, com o `.env` local
(veja `README.md` e `backend/README.md`). As fotos também ficam no banco local. Quem já tinha fotos na versão
antiga não perde nada: na primeira subida da versão nova, a API copia as fotos do volume antigo para o banco
sozinha (detalhes no `backend/README.md`).

Os dados do computador **não** vão para a internet, e vice-versa: o banco do Neon começa com os dados genéricos do
seed. Copiar dados de um para o outro não faz parte deste guia; peça ajuda ao grupo se precisar.
