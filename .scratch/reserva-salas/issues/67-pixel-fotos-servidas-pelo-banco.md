# 67: Fotos servidas pelo banco: substituto para imagem quebrada, textos do admin e mocks

Status: ready-for-agent
Responsável: Pixel
Origem: Atlas
Prioridade: média
Blocked by: (nenhum; pode ser feito em paralelo ao ticket 60, porque a `url` não muda de formato)
Referências: ADR-0010; contrato 1.4 §3.5, §4.4; `frontend/src/components/Galeria.jsx`, `CartaoSala.jsx`,
`frontend/src/pages/admin/EditorFotos.jsx`, `frontend/src/api/mock/*`, `frontend/src/utils/` (validação de fotos)

## Contexto
O contrato 1.4 mantém `Foto.url` no formato `/uploads/salas/{sala_id}/{uuid}.jpg`, então exibir fotos não muda.
Mudam três coisas visíveis: (a) toda foto guardada é JPEG de até 1600 px, (b) uma foto antiga cujo arquivo se perdeu
na importação responde `404` na `url`, (c) uploads acima de 40 megapixels são recusados com `413 ARQUIVO_GRANDE`.

## O que fazer
1. **Imagem quebrada**: em `Galeria`, `CartaoSala` e `EditorFotos`, `onError` troca por um substituto neutro
   (ex.: bloco cinza com "Foto indisponível"), sem laço de erro e mantendo o `alt`. No admin, o substituto deixa claro
   que a foto pode ser excluída.
2. **Textos do admin** (`EditorFotos`): informar que as fotos são reduzidas para até 1600 px e salvas em JPEG, e que a
   localização (GPS) da foto é removida. Limite de entrada continua `VITE_UPLOAD_MAX_MB` (5 MB).
   Erro `413` pela resolução: mostrar o `detail` da API (já é o comportamento padrão; conferir).
3. **Mocks e testes**: `url` de exemplo com `.jpg`; o mock de upload pode continuar com `blob:`.
4. Opcional, se simples: `decoding="async"` nas imagens da galeria (`loading="lazy"` já existe nas miniaturas).

## Critérios de aceite
- [ ] Vitest: imagem que dispara `error` mostra o substituto, uma vez só.
- [ ] Texto do admin presente; E2E de upload (`e2e/csp.spec.js`) segue verde contra a API nova.
- [ ] Nenhuma mudança necessária em `urlArquivo` (`/uploads/...` relativo continua funcionando).
