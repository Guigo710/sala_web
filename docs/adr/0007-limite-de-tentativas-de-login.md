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

## Adendo 1 (2026-11-19, ticket 53): limite na troca da própria senha
O ticket 50 estendeu a mesma ideia a `PUT /auth/me/senha` (Forge, rodada 4), registrado no contrato 1.4 (§4.2):
- 5 `SENHA_ATUAL_INCORRETA` da **mesma conta** (chave = id do professor, qualquer token dela) em 5 minutos
  bloqueiam a troca por 5 minutos; bloqueado → `429 MUITAS_TENTATIVAS` antes de conferir a senha (mesmo a certa);
- troca certa zera o contador; independente do contador do login; em memória, por processo (mesmas consequências acima).

Opção "mais forte" (revogar todas as sessões da conta ao estourar o limite): **não adotada na v1**.
- A favor: quem roubou um token perderia o acesso depois de 5 chutes.
- Contra: o dono que erra a senha atual 5 vezes seria derrubado de todos os dispositivos, inclusive no meio do
  formulário, e o ADR-0008 garante hoje que "erro não muda nada"; mudaria comportamento documentado do frontend.
- Risco que fica: com um token roubado, 5 chutes a cada 5 minutos durante a validade do token (8 h), cerca de 480
  chutes, contra senha de no mínimo 8 caracteres. Aceito. Reavaliar se houver contas com senhas fracas ou tokens mais longos.

## Adendo 2 (2026-11-19, ADR-0009): publicação no Render
- Os contadores em memória só são corretos porque o Render Free roda **uma instância** com **um worker**.
  Mais instâncias ou workers exigem armazenamento comum (ADR novo). Dormir/deploy zera os contadores (aceito).
- Atrás do balanceador do Render todos os clientes têm o mesmo `request.client.host`: o par (IP, RM) vira, na
  prática, contagem por RM, e o teto por IP viraria bloqueio global. O teto passa a ser configurável por
  `LOGIN_MAX_FALHAS_IP` (padrão 20; `0` desliga) e fica `0` na produção do Render. `FORWARDED_ALLOW_IPS=*` continua
  proibido (item 1). Detalhes e melhoria futura no ADR-0009.
