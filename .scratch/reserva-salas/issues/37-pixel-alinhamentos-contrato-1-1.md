# 37: Alinhar o mock ao contrato 1.1 e validar a foto antes do upload

Status: resolved
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
- [x] Mock: `de=2026-09-01&ate=2026-11-01` (62 dias) passa; `ate=2026-11-02` dá `422 INTERVALO_INVALIDO`.
- [x] Mock: `PUT` de sala/horário sem `ativo` dá `422 VALIDACAO`.
- [x] Arquivo de 6 MB ou `.gif` é recusado sem requisição à API, com mensagem por arquivo; arquivos válidos do mesmo lote seguem.
- [x] Teste Vitest para a validação local de tamanho/tipo.

## Comments

**Pixel (2026-11-12):** Mock: `GET /reservas?de&ate` conta as duas pontas (`dias + 1 > 62` → `422 INTERVALO_INVALIDO`); `PUT /salas/{id}` e `PUT /horarios/{id}` sem `ativo` booleano → `422 VALIDACAO` (`body.ativo`). Upload: `src/utils/fotos.js` (`validarFoto`, `limiteUploadMb`) recusa no navegador tipo fora de JPEG/PNG/WebP (415) e arquivo acima de `VITE_UPLOAD_MAX_MB` (padrão 5; 413) sem chamar a API; o erro aparece na linha do arquivo, igual ao da API, e os válidos do lote seguem. `413`/`415` do servidor continuam tratados. `VITE_UPLOAD_MAX_MB` documentado no `.env.example` (comentado) e no `frontend/README.md`; o Compose passa `UPLOAD_MAX_MB` como padrão. Testes: `src/utils/fotos.test.js`, `src/pages/admin/EditorFotos.test.jsx`, `src/api/mock/servidor.test.js`.
