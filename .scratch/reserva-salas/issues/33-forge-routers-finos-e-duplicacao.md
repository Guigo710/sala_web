# 33: Routers finos e menos duplicação nos CRUDs

Status: ready-for-agent
Responsável: Forge
Origem: Atlas
Prioridade: média
Blocked by: 23, 24 (testes de regressão antes do refactor), 31, 32 (mexem nos mesmos arquivos)
Referências: `backend/README.md` (estrutura: regra de negócio em `services/`); spec RN01, RN02, RN08, RN09

## Problema
Reservas e recorrência estão bem separadas (`services/reservas.py`, `services/recorrencia.py`), mas os demais
recursos têm consulta, regra de negócio e transação **dentro dos routers**:

| Router | Regra/transação no router |
|---|---|
| `routers/salas.py:25-38`, `:88-148` | checagem de nome, commit, substituição de equipamentos e softwares com `delete`/`insert` |
| `routers/fotos.py:34-94` | coordenação disco + banco no upload, regra `ORDEM_FOTOS_INVALIDA`, exclusão |
| `routers/horarios.py:29-62`, `:105-118` | RN02 (`HORARIO_SOBREPOSTO`), `ORDEM_DUPLICADA`, `HORARIO_EM_USO` |
| `routers/professores.py:58-120` | `RM_DUPLICADO`, RN08 `OPERACAO_EM_SI_MESMO`, vínculos de `PROFESSOR_COM_RESERVAS` |
| `routers/semestres.py:30-103` | sobreposição, "semestre atual", `SEMESTRE_EM_USO` |
| `routers/auth.py:20-46` | fluxo de login com limite de tentativas, troca de senha |
| `routers/equipamentos.py:17-74`, `routers/softwares.py:17-85` | CRUD com checagem de duplicidade |

Há também duplicação e um problema de correção:
- Sete cópias de `_obter` (busca por id ou `404`), seis de `_salvar`/`_commit_nome` e quatro de `_checar_nome`/`_checar_duplicado`.
- **A tradução de `IntegrityError` ignora qual constraint falhou.** `routers/horarios.py:55-62` transforma
  qualquer `IntegrityError` em `409 ORDEM_DUPLICADA`; `routers/semestres.py:41-50` transforma tudo que não é a
  exclusão em `NOME_DUPLICADO`; em salas, equipamentos, softwares e professores acontece o mesmo. Uma violação
  inesperada (FK, CHECK) vira um 409 com mensagem errada, em vez de 500 com log.
- `escapar_like` mora em `services/salas.py:30-31` e é importado pelos routers de equipamentos, softwares e professores.

## O que fazer
- Criar um service por recurso (`services/equipamentos.py`, `softwares.py`, `horarios.py`, `semestres.py`,
  `professores.py`, `fotos.py`, `auth.py`) e completar `services/salas.py` (criar, atualizar, definir
  equipamentos e softwares). Toda regra de negócio, consulta e `commit` vai para lá.
- O router fica com: declarar a rota e as dependências, chamar **uma** função de service e converter a saída
  (via `apresentacao` ou `model_validate`).
- Helpers comuns num módulo neutro (ex.: `app/services/comum.py`):
  - `obter_ou_404(db, Modelo, id, mensagem)`;
  - `commit_traduzindo(db, {nome_constraint: ErroApi, ...})`: faz rollback e devolve o `ErroApi` da constraint
    conhecida; **constraint desconhecida → relança** (vira 500 com log);
  - `escapar_like`.
- Manter as pré-checagens que geram mensagens amigáveis; a constraint do banco continua sendo a garantia final.
- **Sem mudança de comportamento**: o contrato, os status e as mensagens continuam iguais.

## Critérios de aceite
- [ ] `grep -nE "db\.(commit|execute|scalar|scalars|add|delete)|select\(" backend/app/routers` não encontra nada.
- [ ] Nenhum router importa de `sqlalchemy` (exceto tipos, se precisar) nem de outro router.
- [ ] Um único `obter_ou_404` e um único helper de commit com tradução por nome de constraint.
- [ ] `IntegrityError` de constraint não mapeada → `500 ERRO_INTERNO` (teste: forçar uma violação de CHECK via monkeypatch).
- [ ] Os testes do Sentinela (tickets 23 e 24) e os de fumaça passam antes e depois, sem alteração.

## Comments
