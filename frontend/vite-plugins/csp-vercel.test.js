import fs from 'node:fs';
import path from 'node:path';
import cspVercel, { aplicarCspVercel, origemDaApi, politicaVercel } from './csp-vercel';

const INDEX = fs.readFileSync(path.resolve(__dirname, '../index.html'), 'utf8');
const VERCEL_JSON = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../vercel.json'), 'utf8'));

describe('origemDaApi (mesma regra do Dockerfile)', () => {
  it('aceita http(s)://host[:porta][/caminho] e devolve a origem', () => {
    expect(origemDaApi('https://sala-web-api.onrender.com')).toBe('https://sala-web-api.onrender.com');
    expect(origemDaApi('https://api.exemplo.com/')).toBe('https://api.exemplo.com');
    expect(origemDaApi('http://localhost:8000/v1/api')).toBe('http://localhost:8000');
  });

  it.each([undefined, '', 'sala-web-api.onrender.com', 'https://a.com; script-src *', "https://a.com'", 'ftp://a.com', 'https://a.com?x=1'])(
    'recusa %j com mensagem clara',
    (valor) => {
      expect(() => origemDaApi(valor)).toThrow(/VITE_API_URL inválida para a CSP do Vercel/);
    },
  );
});

describe('aplicarCspVercel', () => {
  const html = aplicarCspVercel(INDEX, 'https://api.exemplo.com');

  it('põe a meta CSP como primeiro elemento do <head>', () => {
    const head = html.slice(html.indexOf('<head>') + '<head>'.length).trimStart();
    expect(head.startsWith(`<meta http-equiv="Content-Security-Policy" content="${politicaVercel('https://api.exemplo.com')}" />`)).toBe(true);
  });

  it('tira o marcador do nonce e mantém o resto', () => {
    expect(html).not.toContain('__CSP_NONCE__');
    expect(html).not.toContain('csp-nonce');
    expect(html).toContain('<meta charset="UTF-8" />');
    expect(html).toContain('<title>Reserva de salas</title>');
  });

  it('política: unsafe-inline só em style-src, sem nonce, sem unsafe-eval, API em img/connect', () => {
    const p = politicaVercel('https://api.exemplo.com');
    expect(p).toContain("script-src 'self';");
    expect(p).toContain("style-src 'self' 'unsafe-inline';");
    expect(p).toContain("img-src 'self' https://api.exemplo.com;");
    expect(p).toContain("connect-src 'self' https://api.exemplo.com;");
    expect(p).not.toMatch(/nonce-|sha256-|unsafe-eval|frame-ancestors/);
  });
});

describe('plugin', () => {
  const executar = (ambiente, env) => {
    const plugin = cspVercel({ ambiente });
    plugin.configResolved({ env, logger: { info: () => {} } });
    return plugin.transformIndexHtml.handler(INDEX);
  };

  it('sem VERCEL o index.html sai idêntico (Compose/nginx com nonce)', () => {
    expect(executar({}, { VITE_API_URL: 'https://api.exemplo.com' })).toBe(INDEX);
  });

  it('com VERCEL=1 grava a CSP da API', () => {
    expect(executar({ VERCEL: '1' }, { VITE_API_URL: 'https://api.exemplo.com' })).toContain(
      "connect-src 'self' https://api.exemplo.com",
    );
  });

  it('com VERCEL=1 e VITE_API_URL ausente ou inválida, o build falha', () => {
    expect(() => executar({ VERCEL: '1' }, {})).toThrow(/VITE_API_URL/);
    expect(() => executar({ VERCEL: '1' }, { VITE_API_URL: 'api.exemplo.com' })).toThrow(/VITE_API_URL/);
  });
});

describe('vercel.json', () => {
  const cabecalhos = Object.fromEntries(
    VERCEL_JSON.headers.find((h) => h.source === '/(.*)').headers.map((h) => [h.key, h.value]),
  );

  it('cabeçalhos de segurança e CSP do ADR-0009', () => {
    expect(cabecalhos).toMatchObject({
      'X-Content-Type-Options': 'nosniff',
      'X-Frame-Options': 'DENY',
      'Referrer-Policy': 'strict-origin-when-cross-origin',
      'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
      'Content-Security-Policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https:; connect-src 'self' https:; font-src 'self' data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
    });
  });

  it('cache longo só em /assets e nada de buildCommand/outputDirectory', () => {
    const assets = VERCEL_JSON.headers.find((h) => h.source === '/assets/(.*)');
    expect(assets.headers).toEqual([{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }]);
    expect(VERCEL_JSON).not.toHaveProperty('buildCommand');
    expect(VERCEL_JSON).not.toHaveProperty('outputDirectory');
  });

  it('fallback de SPA só para caminhos sem extensão', () => {
    const [regra] = VERCEL_JSON.rewrites;
    expect(regra.destination).toBe('/index.html');
    // O Vercel usa path-to-regexp; o grupo entre parênteses é uma expressão regular comum.
    const grupo = new RegExp(`^${regra.source.replace(/^\/\(/, '/(?:')}$`);
    for (const rota of ['/agenda', '/ambientes/3', '/admin/ambientes', '/admin/ambientes/novo', '/minhas-reservas', '/']) {
      expect(grupo.test(rota), rota).toBe(true);
    }
    for (const arquivo of ['/src/main.jsx', '/assets/nao-existe.js', '/.env', '/favicon.ico', '/package.json']) {
      expect(grupo.test(arquivo), arquivo).toBe(false);
    }
  });
});
