# 68: Verificação final da rodada 5 (fotos no banco, publicação Vercel + Render + Neon)

Status: resolved (com tickets 70 e 71 abertos)
Responsável: Sentinela
Origem: Atlas
Prioridade: alta
Blocked by: 60, 61, 62, 63, 64, 65, 66, 67
Referências: ADR-0009, ADR-0010, ADR-0007 (adendos); contrato 1.4; `docs/publicacao.md`; `.github/workflows/ci.yml`

## O que verificar

### 1. Backend (pytest, contra Postgres real)
- Redução (ticket 60): orientação EXIF aplicada; EXIF/GPS removidos; lado maior ≤ 1600 sem ampliar; PNG com
  transparência → fundo branco; > 40 MP → `413` sem pico de memória; assinatura válida com corpo inválido → `415`;
  > 5 MB → `413`; saída sempre `image/jpeg`; tamanho típico ≤ 600 KB para foto de celular.
- `GET /uploads/...`: `200` com `Content-Type`, `Content-Length`, `ETag`, `Cache-Control: public, max-age=31536000, immutable`,
  CSP `sandbox`, `nosniff`; `304` com `If-None-Match`; `404` com envelope para nome inexistente, para foto com
  `conteudo` nulo e para tentativas de caminho (`../`, `%2e%2e`).
- Listas e detalhe não carregam `conteudo` (consulta emitida não seleciona a coluna).
- Importação (ticket 61): idempotente, foto ausente vira aviso, `../` recusado, nunca apaga nada.
- Ticket 62: `PORT`; `LOGIN_MAX_FALHAS_IP=0` desliga só o teto; `CORS_ORIGENS` com barra final aceita, `*` e caminho recusados.
- Ticket 63: fuso continua certo com `SET TIME ZONE`; reconexão após reinício do Postgres; `/saude` não pendura; senha fora dos logs.

### 2. Compose (quem já tem dados)
- Atualização a partir do commit anterior à rodada 5 com fotos no volume (incluindo uma PNG e uma linha órfã):
  fotos aparecem depois do `docker compose up --build`; segunda subida não reimporta; volume montado só leitura;
  backend com uid 10001; clone novo sobe limpo. Registrar o passo a passo usado nos comentários.

### 3. Ambiente "parecido com produção", sem contas externas
- Imagem do backend com `PORT=10000`, `LOGIN_MAX_FALHAS_IP=0`, `CORS_ORIGENS=https://exemplo.vercel.app` e
  `DATABASE_URL=...?sslmode=require` contra um Postgres local com SSL (certificado autoassinado): migrations, seed,
  importação (no-op), `/saude`, upload e leitura de foto.
- Frontend: `VERCEL=1 VITE_API_URL=https://api.exemplo.com npm run build` → meta CSP correta e sem `__CSP_NONCE__`;
  `vercel.json` válido; build sem `VERCEL` idêntico ao atual (job `imagens` verde).

### 4. Revisão de segurança
- CSP do Vercel (ADR-0009): `script-src 'self'` sem `unsafe-*`; nenhuma fonte de nonce/hash em `style-src` (anularia o
  `'unsafe-inline'`); intersecção cabeçalho + meta resulta em `img-src`/`connect-src` só `'self'` + API.
- `render.yaml`, `vercel.json`, `.env.example`, `docs/publicacao.md`: nenhum segredo real; `.gitignore` cobre `.env*`.
- `FORWARDED_ALLOW_IPS` nunca `*`; risco aceito do teto por IP desligado registrado (ADR-0009).
- Fotos: nenhum caminho de disco exposto; `Content-Type` vem do banco, nunca do nome; sem `Cross-Origin-Resource-Policy` restritivo.

### 5. CI
- Jobs atualizados (Pillow nas dependências; passo do build `VERCEL=1`; E2E com `importar_fotos`). Tudo verde.

### 6. Guia e primeira publicação
- Ler `docs/publicacao.md` como o dono (Windows, sem terminal) e apontar passos ambíguos ou desatualizados em
  comentário neste ticket, ou abrir ticket `Responsável: Atlas`.
- Lista de conferência para a primeira publicação real, que o dono executa e reporta: `/saude` com `{"status":"ok"}`;
  login do admin pelo site do Vercel; troca de senha; upload de foto; **a foto continua aparecendo depois de
  "Manual Deploy → Restart service" no Render** (prova de que está no banco); `curl -I` (ou DevTools) mostrando a CSP e
  os cabeçalhos no site do Vercel; implantação de prévia **sem** acesso à API (erro esperado de conexão).

## Critérios de aceite
- [ ] Itens 1 a 5 conferidos, com evidências (saídas de comando, testes novos) nos comentários.
- [ ] Achados abertos como tickets ao responsável (Forge/Pixel) ou ao Atlas (guia/contrato).
- [ ] Lista de conferência do item 6 comparada com a seção 7 ("Conferência final") de `docs/publicacao.md`;
      itens faltando ou errados vão em ticket `Responsável: Atlas` (o guia é do Atlas).

## Resolução (Sentinela, rodada 5)

### Suítes
- Backend: `405 passed` (365 antes + 2 da trava por sala + 38 em `tests/test_sentinela_rodada5.py`), Postgres 16 real.
- Frontend: Vitest `93 passed` (13 arquivos), `npm run lint` ok, `npm run build` ok (sem VERCEL mantém `__CSP_NONCE__`).
- E2E (Playwright) contra o ambiente "de produção" abaixo: `10 passed` (9 antigos + 1 novo em `e2e/csp.spec.js`).

### Teste instável (`test_concorrencia_mesmo_bloco_exatamente_um_sucesso`)
- Causa achada no log do Postgres (19/11 11:47): 7 × `deadlock detected ... while checking exclusion constraint on
  tuple (0,1) in relation "reservas"`, entre os 8 INSERTs do teste. Na restrição de exclusão, dois INSERTs que se
  sobrepõem gravam a entrada no índice GiST e depois cada um espera a transação do outro. O erro é `40P01`
  (`OperationalError`, não `IntegrityError`) e virava `500 ERRO_INTERNO`. Reproduzido de forma determinística
  direto no banco (duas transações com duas linhas em ordem cruzada → `DeadlockDetected sqlstate=40P01`).
- Antes da correção: 30/30 isolado, 3/3 no arquivo e 500 rodadas de estresse (8 POST simultâneos cada, com e sem
  CPU saturada) passaram, sem deadlock: a janela é rara, mas real (o pool 5+5 não tem relação).
- Correção: `travar_sala` (`pg_advisory_xact_lock(0x5A1A, sala_id)`) antes de `buscar_conflitos` em
  `reservas.criar_avulsa` e `recorrencia.confirmar`. Testes novos determinísticos (falham sem a trava): a criação
  espera a trava e depois responde 409 com o conflito de quem terminou antes; outra sala não espera; a recorrente espera.
- Depois: 30/30 isolado, 30/30 no arquivo (41 testes), 0 deadlocks no log.

### Ambiente "de produção" (sem contas externas)
- Postgres 16 em container **só com SSL** (`hostnossl ... reject`, certificado autoassinado), usuário `neondb_owner`;
  `DATABASE_URL=...?sslmode=require&channel_binding=require`; `pg_stat_ssl`: `sala_web | t | TLSv1.3`.
- Imagem do backend (Dockerfile do repo; só o `pip install` recebeu o CA do proxy da sessão), `PORT=10000`,
  `LOGIN_MAX_FALHAS_IP=0`, `CORS_ORIGENS=https://localhost:4443/` (barra final aceita), uid 10001: migrations, seed,
  importação (no-op) e `Uvicorn running on http://0.0.0.0:10000`; segunda subida sem reimportar.
- "Render": TLS em `https://localhost:8443` → API; "Vercel": `VERCEL=1 VITE_API_URL=https://localhost:8443` +
  servidor HTTPS que aplica o `vercel.json` (arquivos primeiro, depois `rewrites`; `headers` por `source`).
  `/agenda`, `/ambientes/3`, `/admin/ambientes` → 200; `/src/main.jsx`, `/assets/nao-existe.js`, `/.env` → 404;
  cabeçalhos e CSP presentes; `/assets/*` com cache imutável.
- Foto de 2400×1800 RGBA enviada pelo E2E: JPEG 1600×1200 sem APP1, `ETag`, `Cache-Control` imutável, CSP
  `sandbox`, `nosniff`, `304` com `If-None-Match`; exibida no site sem violação de CSP. Foto continua servida
  depois de trocar o container da API (prova de que está no banco).
- Banco reiniciado com a API no ar → próximas 8 requisições 200; banco parado → `/saude` 503 em 0,01 s
  (conexão recusada); nenhum log com a senha do banco, do admin ou o `JWT_SECRET`.

### Segurança
- Upload: 4000×3000 orientação 6 com GPS/comentário → 1200×1600 sem EXIF/GPS/comentário; nome enviado
  (`../../../etc/passwd.jpg`) descartado; 41 MP, bomba de 400 MP (1,2 MB), SOF de JPEG 65000×65000 → 413;
  IHDR 2^31 → 415; SVG, HTML, HTML com assinatura JPEG, GIF, TIFF, BMP, WebP falso → 415; poliglota PNG+ZIP
  recodificado (ZIP some); > 5 MB → 413.
- `/uploads`: `../`, `%2e%2e`, `..%2f`, nomes enormes, CRLF → 404 envelope sem cabeçalhos de foto; CORS só para a
  origem do site; sem CORP; POST/DELETE → 405.
- `CORS_ORIGENS`: preflight do site aceito, outra origem e origem parecida recusadas; `*` e caminho impedem subir.
- `render.yaml`, `vercel.json`, `.env.example`: sem segredo real; `.gitignore` cobre `.env*`; `FORWARDED_ALLOW_IPS`
  nunca `*`.
- Corrigido direto: `NUL` em texto e ids além do `integer` davam `500` (ex.: `/salas/99999999999`,
  `/salas?busca=%00`, login com `\u0000` no RM, `/uploads/...%00.jpg`) → agora `422 VALIDACAO` (handler de
  `DataError`) e `404` em `/uploads`; `hide_parameters=True` no engine (log de erro do banco sem valores);
  `hide_input_in_errors=True` na config (um `JWT_SECRET` curto aparecia inteiro no log do Render);
  `DATABASE_URL` copiada do Neon com `postgresql://`/`postgres://` passa a funcionar; build do Vercel recusa
  `VITE_API_URL` em `http://`.
- Aberto: ticket 70 (PNG/WebP perto de 40 MP chega a 577 MB de pico; Render Free tem 512 MB).

### Guia (`docs/publicacao.md`)
Corrigido: troca de senha (o link é o nome do usuário no topo, página "Minha conta" → "Trocar senha"); aviso
esperado no log depois de apagar `ADMIN_SENHA`; opção A como recomendada e o que fazer se o Blueprint der erro
(apagar serviço e Blueprint e usar o formulário); Dockerfile não encontrado (as duas leituras do campo);
`VITE_API_URL` errada no build do Vercel; recuperação quando o único admin esquece a senha (`ADMIN_RM` novo);
`postgresql://` agora aceito; conferência final com cabeçalhos/CSP pelo F12 e a prévia sem API.
Pendente (ticket 71, Atlas): conferir `render.yaml` na documentação oficial; registrar no contrato/ADR-0003.

### Compose (item 2)
Não refeito nesta verificação: a atualização com fotos antigas (PNG e órfã), a segunda subida e o volume `:ro`
foram conferidos com Docker pelo Forge no ticket 61, com saídas no próprio ticket.
