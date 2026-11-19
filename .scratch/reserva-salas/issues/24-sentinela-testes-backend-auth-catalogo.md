# 24: Testes backend: auth, permissões por rota, filtros e upload

Status: resolved
Responsável: Sentinela
Origem: Atlas
Blocked by: 03, 06, 07, 09
Referências: `docs/api-contrato.md` §1.3, §4.2–§4.9, §5

## Critérios de aceite
- [x] Teste parametrizado da matriz §5: cada rota de escrita com visitante (401), professor (403 quando admin), admin (ok).
- [x] Login: sucesso, senha errada, inativo, token expirado/adulterado, rate limit 429.
- [x] Respostas públicas sem `rm`/`senha_hash`.
- [x] Filtros de `GET /salas` (tipo, capacidade, equipamento E, software E, disponibilidade).
- [x] Upload: tipo falso (415), grande (413), nome malicioso (`../../x.jpg`) não escapa de `UPLOAD_DIR`.

## Comments

**Sentinela (12/11/2026):** feito.
- `backend/tests/test_auth_permissoes.py` (86 testes): matriz §5 parametrizada (27 rotas admin × visitante 401 /
  professor 403 / admin ok; 9 rotas de professor × sem token e token lixo → 401; 16 rotas públicas com token inválido →
  200), login (sucesso, claims, falhas com mensagem única, SQL injection no RM, conta inativa, papel lido do banco),
  tokens expirado/segredo errado/sem `exp`/sem `sub`/HS512/`alg=none`/adulterado → 401, rate limit 429, troca de senha,
  bcrypt, `OPERACAO_EM_SI_MESMO`, respostas públicas sem `rm`/`senha_hash`, `busca` com SQL/curingas, 500 sem stack trace,
  404/405 no envelope, CORS só para a origem configurada.
- `backend/tests/test_catalogo_upload.py` (33 testes): filtros de `/salas` (tipo, capacidade, equipamento E, software E,
  busca com `%`/`_`, disponibilidade data+aulas), inativas, catálogo, horários, semestres; upload JPEG/PNG/WebP pelo
  conteúdo, tipo falso (GIF, SVG, HTML, PDF, vazio, RIFF não-WebP) → 415 sem arquivo no disco, 413 pelos dois caminhos,
  nomes maliciosos (`../../x.jpg`, `\\`, `/etc/passwd`, `\x00`, `%2e%2e`) ficam em `UPLOAD_DIR/salas/{id}/{uuid}.jpg`,
  traversal em `/uploads/..` → 404, galeria (ordem, capa, exclusão apaga arquivos).
- **Atenção ticket 31:** `test_rate_limit_de_login` (aqui) e `test_credenciais_invalidas_e_rate_limit` (fumaça) codificam a
  regra atual (5 falhas por IP). Quando o 31 entrar, os dois precisam ser reescritos para a regra (IP, RM) + teto por IP.
