# 37: Alinhar o mock ao contrato 1.1 e validar a foto antes do upload

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Prioridade: baixa
Blocked by: (nenhum)
Referências: `docs/api-contrato.md` §1.6, §1.7, §4.4, §4.10 e §7 (histórico 1.1)

## Revisão do `src/api/` (resultado)
Os conectores batem com o contrato: rotas sem barra final, listas como parâmetro repetido, `Bearer`, envelope
de erro com `erros`/`conflitos`, `204 → null`, `ate = end - 1 dia` e `PUT` completos. Nenhuma divergência de
integração no código de produção. As suposições do Pixel foram confirmadas e escritas no contrato:
- `passou` ausente tratado como `false`: o backend envia `passou` **sempre** (§4.3). O fallback pode ficar, por defesa.
- Ativar/desativar lê o detalhe e manda o `PUT` completo: é o padrão oficial (§1.6). O `ativo` passa a ser
  obrigatório no `PUT` de salas e horários (ticket 32), e o Pixel já envia.
- "Já passou" com o relógio do navegador: permitido só como dica de interface; o servidor decide (§1.7).
  Isso vale também para a estimativa em `DialogoCancelar.jsx:26`, cuja mensagem final já usa `canceladas`.
- Na recorrência, a primeira data pode ser uma aula ocupada: confirmado (§4.10); `datas` não precisa conter `data_inicio`.

## O que fazer
1. **Mock** (`src/api/mock/servidor.js`):
   - `:715` aceita 63 dias (`(ate - de) / dia > 62`). O contrato conta as duas pontas: recusar quando
     `(ate - de) / dia + 1 > 62`.
   - `PUT /salas/{id}` e `PUT /horarios/{id}` sem `ativo` → `422 VALIDACAO` (§1.6).
2. **Upload de fotos** (`src/pages/admin/EditorFotos.jsx`): o `accept` do input (`:9`, `:174`) só filtra o
   diálogo do sistema, e o usuário pode escolher "todos os arquivos". Antes de enviar, recusar no próprio navegador
   o arquivo maior que `VITE_UPLOAD_MAX_MB` (padrão 5) ou com `file.type` fora de `TIPOS_ACEITOS`. Mostrar o erro por arquivo, igual ao `413`/`415`. O servidor continua sendo a referência: os
   erros `413`/`415` da API continuam tratados.
3. Documentar `VITE_UPLOAD_MAX_MB` no `.env.example` da raiz (seção Frontend, comentado) e no `frontend/README.md`.

## Critérios de aceite
- [ ] Mock: `de=2026-09-01&ate=2026-11-01` (62 dias) passa; `ate=2026-11-02` dá `422 INTERVALO_INVALIDO`.
- [ ] Mock: `PUT` de sala/horário sem `ativo` dá `422 VALIDACAO`.
- [ ] Arquivo de 6 MB ou `.gif` é recusado sem requisição à API, com mensagem por arquivo; arquivos válidos do mesmo lote seguem.
- [ ] Teste Vitest para a validação local de tamanho/tipo.

## Comments
