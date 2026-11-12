# 36: Dependências fixadas e configuração mais segura por padrão

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: baixa
Blocked by: (nenhum)
Referências: ADR-0001 (ambiente idêntico para todos), ADR-0004; ticket 25 (Sentinela)

## Problema
1. `backend/requirements.txt` só traz faixas (`fastapi>=0.115,<1.0`, `uvicorn[standard]>=0.30`, ...). O Starlette
   nem aparece: hoje entra como dependência transitiva na versão 1.7. Cada `docker compose build` pode trazer
   versões novas e diferentes das que foram testadas, o que contraria o "ambiente idêntico" do ADR-0001.
2. `pytest` e `httpx` estão no mesmo `requirements.txt` (`:15-17`) e vão para a imagem de produção.
3. `JWT_SECRET` só exige 16 caracteres (`backend/app/core/config.py:23`). O valor de exemplo do `.env.example`
   (`troque-por-um-segredo-longo-e-aleatorio`) passa nessa regra, então quem copia o `.env.example` sem editar sobe a API
   com um segredo público.

## O que fazer
- Fixar versões exatas (`==`) do que foi testado, incluindo `starlette`, num `requirements.txt` gerado (ex.:
  `pip freeze` filtrado ou `pip-compile` a partir de um `requirements.in` com as faixas atuais).
- Mover as dependências de teste para `requirements-dev.txt` (que inclui `-r requirements.txt`). O `Dockerfile`
  instala só o de produção; README e CI (ticket 28) usam o dev.
- Na validação de `Config`, recusar subir a API quando `JWT_SECRET` for igual ao valor de exemplo do `.env.example`,
  com mensagem clara. Se o Sentinela já tiver tratado isso no ticket 25, marcar este item como feito lá.

## Critérios de aceite
- [ ] `pip install -r requirements.txt` num ambiente limpo instala exatamente as versões listadas.
- [ ] A imagem do backend não contém `pytest` (`docker compose run --rm backend pip show pytest` falha).
- [ ] `pytest` continua rodando com `pip install -r requirements-dev.txt`; `backend/README.md` atualizado.
- [ ] Com `JWT_SECRET=troque-por-um-segredo-longo-e-aleatorio`, a API não sobe e o erro diz o que fazer.

## Comments
