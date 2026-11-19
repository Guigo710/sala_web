/**
 * CSP do build no Vercel (ticket 65, ADR-0009 "Cabeçalhos e CSP do frontend no Vercel").
 *
 * No Vercel o site é servido como arquivos estáticos: não há nginx para gerar um nonce por resposta. Lá a política é:
 * - no cabeçalho (`vercel.json`, fixo): `img-src`/`connect-src` com `https:` e `frame-ancestors 'none'`;
 * - nesta `<meta http-equiv="Content-Security-Policy">`, gravada no `index.html` só quando `VERCEL` está definido
 *   (o Vercel define `VERCEL=1` no build): `img-src`/`connect-src` restritos à origem de `VITE_API_URL`.
 * O navegador aplica as duas e só permite o que ambas permitem. `style-src 'unsafe-inline'` (sem nonce nem hash,
 * que fariam o navegador ignorar o `'unsafe-inline'`) só aqui; `script-src 'self'` continua estrito.
 * A `<meta name="csp-nonce">` (marcador `__CSP_NONCE__` que o nginx troca) sai deste build.
 *
 * Fora do Vercel (`npm run build` local, Dockerfile/nginx) o plugin não faz nada: o `index.html` sai igual.
 */

/** Mesma regra do Dockerfile: `http(s)://host[:porta][/caminho]`; devolve a origem (sem o caminho). */
const URL_API = /^(https?:\/\/[A-Za-z0-9.-]+(:[0-9]+)?)(\/[A-Za-z0-9._~/-]*)?$/;

export function origemDaApi(url) {
  const m = URL_API.exec(url ?? '');
  if (!m) {
    throw new Error(
      `VITE_API_URL inválida para a CSP do Vercel: '${url ?? ''}'. Use o endereço da API no formato ` +
        'https://nome-da-api.onrender.com (sem barra no fim), em Settings → Environment Variables do projeto no Vercel, ' +
        'e refaça a implantação (docs/publicacao.md, passo 4).',
    );
  }
  return m[1];
}

/** Política da `<meta>` (sem `frame-ancestors`, que não vale em meta: fica no cabeçalho do `vercel.json`). */
export function politicaVercel(origemApi) {
  return [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' ${origemApi}`,
    `connect-src 'self' ${origemApi}`,
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
}

/** Tira a meta do nonce (e o comentário logo acima dela) e põe a meta CSP como primeiro elemento do `<head>`. */
export function aplicarCspVercel(html, origemApi) {
  const semNonce = html
    .replace(/[ \t]*<!--(?:(?!-->)[\s\S])*?-->[ \t]*\r?\n(?=[ \t]*<meta name="csp-nonce")/, '')
    .replace(/[ \t]*<meta name="csp-nonce" content="__CSP_NONCE__"\s*\/?>[ \t]*\r?\n?/, '');
  if (semNonce.includes('__CSP_NONCE__')) {
    throw new Error('index.html: não consegui remover a <meta name="csp-nonce"> para o build do Vercel.');
  }
  const meta = `<meta http-equiv="Content-Security-Policy" content="${politicaVercel(origemApi)}" />`;
  const abertura = /<head(\s[^>]*)?>/i;
  if (!abertura.test(semNonce)) throw new Error('index.html sem <head>: não há onde pôr a CSP do Vercel.');
  return semNonce.replace(abertura, (tag) => `${tag}\n    ${meta}`);
}

/** Plugin do Vite: só age em `vite build` com `VERCEL` definido no ambiente. */
export default function cspVercel({ ambiente = process.env } = {}) {
  let origemApi = null;
  return {
    name: 'sala-web-csp-vercel',
    apply: 'build',
    configResolved(config) {
      if (!ambiente.VERCEL) return;
      // config.env tem as VITE_* do ambiente e dos arquivos .env, como o Vite as grava no JavaScript.
      origemApi = origemDaApi(config.env.VITE_API_URL);
      // O site do Vercel é https: uma API em http seria bloqueada (conteúdo misto e `connect-src ... https:` do
      // cabeçalho). Melhor falhar o build com a explicação do que publicar um site que não fala com a API (ticket 68).
      if (!origemApi.startsWith('https://')) {
        throw new Error(
          `VITE_API_URL precisa começar com https:// no Vercel (recebido '${config.env.VITE_API_URL}'). Copie o ` +
            'endereço da API do topo da página do serviço no Render (https://nome-da-api.onrender.com) e refaça a ' +
            'implantação (docs/publicacao.md, passo 4).',
        );
      }
      config.logger.info(`[csp-vercel] CSP do Vercel: img-src/connect-src 'self' ${origemApi}`);
    },
    transformIndexHtml: {
      order: 'post',
      handler: (html) => (origemApi ? aplicarCspVercel(html, origemApi) : html),
    },
  };
}
