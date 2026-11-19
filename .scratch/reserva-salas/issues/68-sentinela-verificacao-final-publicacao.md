# 68: Verificação final da rodada 5 (fotos no banco, publicação Vercel + Render + Neon)

Status: ready-for-agent
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
