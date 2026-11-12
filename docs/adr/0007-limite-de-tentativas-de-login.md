# ADR-0007: Limite de tentativas de login por (IP, RM) com teto por IP

Status: aceito · Data: 2026-11-12 · Autor: Atlas · Origem: ticket 29 (ponto 13) · Substitui o item
"Login com limite simples em memória" do ADR-0004

## Contexto
O ADR-0004 definiu: 5 falhas do mesmo IP em 5 minutos bloqueiam o IP por 5 minutos, usando
`request.client.host`. Na prática, o IP visto pela API pode ser o mesmo para muitos usuários:
- no Docker, conexões que passam pelo `docker-proxy` (ex.: acesso por `localhost`) chegam com o IP do gateway da rede;
- atrás de um proxy reverso (nginx) todas chegam com o IP do proxy;
- na escola, vários computadores podem sair por um mesmo NAT.

Com a chave só por IP, um professor que erra a senha 5 vezes (ou um atacante) bloqueia o login de todos que
compartilham aquele IP.

## Decisão
1. **IP do cliente**: `request.client.host`, como hoje. O uvicorn só troca esse valor pelo de `X-Forwarded-For`
   quando a conexão vem de um IP listado em `FORWARDED_ALLOW_IPS` (padrão do uvicorn: `127.0.0.1`).
   Sem proxy reverso, não configurar nada. Com proxy reverso, definir `FORWARDED_ALLOW_IPS` com o IP do proxy.
   **Nunca** usar `*` (qualquer cliente poderia forjar o IP).
2. **Duas contagens**, ambas com janela de 5 minutos e bloqueio de 5 minutos:
   - por **par (IP, RM digitado)**: 5 falhas bloqueiam o par;
   - por **IP**: 20 falhas (qualquer RM) bloqueiam o IP, contra varredura de muitos RMs.
3. Bloqueado → `429 MUITAS_TENTATIVAS` antes de conferir a senha (mesmo com a senha certa).
   Login certo zera as falhas daquele par (não as do IP).
4. Continua em memória, por processo (sem Redis na v1). As estruturas descartam entradas vencidas, para não
   crescer sem limite com RMs ou IPs inventados.

## Consequências
- Um usuário que erra a própria senha não bloqueia os colegas no mesmo IP.
- Um atacante atrás do mesmo NAT ainda pode, com 20 falhas, bloquear aquele IP por 5 minutos; aceito na v1.
- Reiniciar o backend zera os contadores; com mais de um worker, cada um conta separado (como no ADR-0004).
- Implementação: ticket 31 (Forge). Revisão: Sentinela (ticket 25).
