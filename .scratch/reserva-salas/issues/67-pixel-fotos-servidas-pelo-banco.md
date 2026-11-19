# 67: Fotos servidas pelo banco: substituto para imagem quebrada, textos do admin e mocks

Status: resolved
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

## Resolução (Pixel, rodada 5)
- `src/components/FotoApi.jsx`: `<img>` que, no `error`, vira um `<span class="foto-indisponivel">` (ícone +
  "Foto indisponível"), sem laço (o substituto não carrega nada; tenta de novo só se o `src` mudar), com
  `role="img"` e nome = `alt` + texto; com `alt=""` fica `aria-hidden`. Usado em `Galeria` (principal, miniaturas,
  ampliada; `decoding="async"`), `CartaoSala` e `EditorFotos` (texto "o arquivo não foi encontrado. Você pode remover
  esta foto.").
- `EditorFotos`: texto sobre redução para até 1600 px, JPEG e remoção da localização (GPS); `413` continua mostrando o
  `detail` da API (teste com "40 megapixels"); confirmação de remoção diz "A foto será apagada".
- Mocks/testes: exemplos com `.jpg`; o mock de desenvolvimento ganhou na sala 8 uma foto `/uploads/...jpg` inexistente
  (mostra o substituto); upload do mock continua `blob:`. `urlArquivo` sem mudança.
- Vitest: substituto aparece uma vez só, mantém o alt, troca de `src` tenta de novo; galeria; admin (texto, substituto,
  413). Conferido no navegador: foto com arquivo apagado (404) mostra o substituto no detalhe, no cartão e no admin,
  sem violação de CSP. `e2e/csp.spec.js` verde (contra a API do `HEAD`; a API nova do Forge ainda estava em edição).
