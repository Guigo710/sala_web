# 66: Interface para a API "dormindo" (Render Free acorda em cerca de 1 minuto)

Status: resolved
Responsável: Pixel
Origem: Atlas
Prioridade: média
Blocked by: (nenhum)
Referências: ADR-0009 (Consequências); contrato 1.4 §1.1; `frontend/src/api/cliente.js`; `GLOSSARY.md` ("API dormindo")

## Contexto
Na publicação, a API dorme após 15 minutos sem tráfego. A primeira requisição depois disso fica pendente por cerca
de 1 minuto e então responde normalmente; durante o despertar o Render pode, às vezes, responder `502`/`503`/`504`.
Hoje o usuário veria a tela parada, sem explicação, ou "Não foi possível conectar ao servidor".

## O que fazer
1. **Acordar cedo**: ao carregar o app, disparar `GET /saude` sem esperar a resposta (não bloqueia a renderização).
   Assim a API começa a acordar enquanto a pessoa ainda olha a tela inicial ou digita o login.
2. **Aviso**: se qualquer requisição à API passar de ~4 s sem resposta, mostrar um aviso discreto e acessível
   (`role="status"`), por exemplo: "O servidor está acordando. Isso pode levar até 1 minuto na primeira visita."
   Some quando não houver mais requisição lenta pendente.
3. **Nova tentativa só em leituras**: `GET` que falhar por rede (`status 0`) ou por `502`/`503`/`504` é repetido
   automaticamente algumas vezes com espera crescente, até ~90 s no total, mantendo o aviso. `POST`, `PUT`, `PATCH`,
   `DELETE` e o upload **nunca** são repetidos sozinhos (risco de duplicar ação); nesses casos a mensagem de erro
   sugere tentar de novo em instantes.
4. Não colocar tempo-limite curto nas requisições (a espera de ~1 min é normal).
5. No Compose/local nada muda na prática (a API responde rápido e o aviso nunca aparece).

## Critérios de aceite
- [ ] Vitest: `GET` com resposta atrasada 5 s (relógio falso) mostra o aviso e o esconde ao responder.
- [ ] Vitest: `GET` com `503` seguido de `200` resolve com os dados; `POST` com `503` rejeita sem repetir.
- [ ] Vitest: o `GET /saude` inicial é disparado uma vez e não bloqueia a renderização.
- [ ] Testes e E2E atuais verdes.

## Resolução (Pixel, rodada 5)
- `src/api/saude.js`: `acordarApi()` dispara `GET /saude` uma vez por carregamento, sem devolver promessa e ignorando
  erro; chamado em `main.jsx` antes do `render`.
- `src/api/lentidao.js`: conta requisições pendentes há mais de 4 s (ou sendo repetidas); `AvisoServidor`
  (`role="status"`, faixa discreta no topo, montado em `main.jsx`) mostra "O servidor está acordando. Isso pode levar
  até 1 minuto na primeira visita." e some quando não há mais requisição lenta.
- `src/api/cliente.js`: `GET` com falha de rede ou `502`/`503`/`504` é repetido com esperas de 1, 2, 4, 8 e 15 s
  (a última se repete) até 90 s desde a primeira tentativa (10 tentativas no máximo); token relido a cada tentativa.
  `POST`/`PUT`/`PATCH`/`DELETE` e upload nunca repetem; mensagens padrão de `0`/`502`/`503`/`504` pedem para
  "tentar de novo em instantes". Sem tempo-limite.
- Vitest: aviso com resposta atrasada 5 s (relógio falso) aparece aos 4 s e some ao responder; `503`→`200` resolve;
  rede/502/504 com esperas crescentes; desiste em ~90 s; 4xx/500 não repetem; POST/PUT/PATCH/DELETE/upload com `503`
  rejeitam sem repetir; `acordarApi` dispara uma vez e não bloqueia a renderização.
- Conferido no navegador (Playwright contra o servidor que simula o Vercel, API atrasando 6 s e `503` no primeiro
  `/saude`): aviso aos ~4,5 s, lista carregada e aviso some; `/saude` repetido. E2E existentes verdes.
