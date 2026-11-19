# 66: Interface para a API "dormindo" (Render Free acorda em cerca de 1 minuto)

Status: ready-for-agent
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
