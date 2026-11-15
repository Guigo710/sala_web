# 31: Limite de login por par (IP, RM) com teto por IP

Status: resolved
Responsável: Forge
Origem: Atlas
Prioridade: média
Blocked by: (nenhum)
Referências: **ADR-0007**; `docs/api-contrato.md` §4.2; ticket 29 (ponto 13); ticket 25 (Sentinela revisa)

## Problema
`LimiteLogin` (`backend/app/core/seguranca.py:112-153`) conta falhas só por IP, e `login`
(`backend/app/routers/auth.py:21-31`) usa `request.client.host`. Atrás do `docker-proxy`, de um proxy reverso ou
de um NAT da escola, muitos professores chegam com o mesmo IP: 5 erros de um deles bloqueiam o login de todos.
Além disso, `_falhas` nunca descarta entradas de IPs que não voltam, e cresce sem limite.

## O que fazer (ADR-0007)
- Duas contagens, cada uma com janela de 5 min e bloqueio de 5 min:
  - par `(ip, rm)`: bloqueia o par com 5 falhas;
  - `ip`: bloqueia o IP com 20 falhas, de qualquer RM.
- Checagem antes de conferir a senha: par ou IP bloqueado → `429 MUITAS_TENTATIVAS`, mesmo com a senha certa.
- Login certo zera só as falhas do par.
- RM usado na chave exatamente como digitado (o mesmo critério da busca, contrato §2.1).
- Descartar entradas vencidas: ao registrar uma falha, limpar timestamps fora da janela e bloqueios expirados;
  remover chaves vazias.
- Limites como constantes nomeadas (ou parâmetros do construtor), mantendo `limpar()` para os testes.
- Nada de ler `X-Forwarded-For` no código: o uvicorn já faz isso para os IPs de `FORWARDED_ALLOW_IPS`.
  Citar isso no `backend/README.md`, com link para `.env.example`.

## Critérios de aceite
- [x] 5 falhas de `rm=A` no IP X → `429` para `A` em X; `rm=B` no mesmo IP X ainda consegue logar.
- [x] 20 falhas no IP X, espalhadas por RMs diferentes → `429` para qualquer RM em X.
- [x] Bloqueio expira em 5 min (teste com relógio controlável, sem `sleep`).
- [x] Login certo durante o bloqueio do par → `429`; login certo fora do bloqueio zera as falhas do par.
- [x] Depois de N falhas com RMs aleatórios e de passada a janela, as estruturas internas não guardam entradas vencidas.
- [x] Testes do ticket 24 que dependem da regra antiga (5 falhas por IP) atualizados junto com o Sentinela.

## Comments

**Forge (15/11/2026):** feito (ADR-0007). `app/core/seguranca.py`: `LimiteLogin` com dois `_Contador` (par `(ip, rm)` 5 falhas; IP 20 falhas; janela e bloqueio de 300 s, constantes `MAX_FALHAS_PAR`, `MAX_FALHAS_IP`, `JANELA_S`, `BLOQUEIO_S`), relógio injetável, descarte de timestamps/bloqueios vencidos e chaves vazias a cada falha, `limpar()` e `tamanho()`. Checagem antes da senha (`services/auth.login`), sucesso zera só o par, RM como digitado. Sem leitura de `X-Forwarded-For`; `backend/README.md` explica `FORWARDED_ALLOW_IPS` com link para `.env.example`. Testes: `tests/test_limite_login.py` (12, relógio controlável, sem `sleep`); `test_auth_permissoes.py::test_rate_limit_de_login` e `test_fumaca.py::test_credenciais_invalidas_e_rate_limit` reescritos para a regra nova (par, vizinho no mesmo IP, teto de 20 no limite exato, outro IP livre).
