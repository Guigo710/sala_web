/*
 * CSP do nginx (ticket 52): o app inteiro funciona sob a Content-Security-Policy, sem violações.
 * Passa por login, agenda (FullCalendar injeta um <style> com o nonce de <meta name="csp-nonce">),
 * detalhe do ambiente com foto vinda de /uploads da API e telas do admin (com foto também).
 *
 * Só faz sentido contra o nginx (imagem do frontend / Compose); o `vite preview` não manda CSP.
 * Sem cabeçalho CSP o teste é pulado, a menos que E2E_EXIGIR_CSP=1 (aí falha).
 *
 * Também roda contra o site do Vercel (ticket 65, ADR-0009), reconhecido pelo `'unsafe-inline'` em `style-src`
 * do cabeçalho: lá o cabeçalho é fixo (`vercel.json`, `https:` em img/connect) e a origem da API vem da
 * `<meta http-equiv="Content-Security-Policy">` gravada no build com VERCEL=1.
 */
import zlib from 'node:zlib';
import { expect, test } from '@playwright/test';
import { ADMIN_RM, ADMIN_SENHA, API_URL, auth, criarSalaApi, tokenApi } from './apoio';

// PNG 2x2 válido (vermelho), gerado na hora para não versionar binário.
const PNG_2X2 = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEElEQVR4nGP4z8AARAwQCgAf7gP9i18U1AAAAABJRU5ErkJggg==',
  'base64',
);

const sufixo = Date.now().toString(36).slice(-6);
const ctx = {};

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  ctx.token = await tokenApi(request, ADMIN_RM, ADMIN_SENHA);
  ctx.sala = await criarSalaApi(request, ctx.token, `Lab CSP ${sufixo}`);
  const r = await request.post(`${API_URL}/salas/${ctx.sala.id}/fotos`, {
    headers: auth(ctx.token),
    multipart: {
      arquivo: { name: 'csp.png', mimeType: 'image/png', buffer: PNG_2X2 },
      legenda: 'Foto do teste de CSP',
    },
  });
  expect(r.status(), await r.text()).toBe(201);
});

/** Registra violações (evento securitypolicyviolation) e mensagens de CSP do console. */
async function vigiarCsp(page) {
  const violacoes = [];
  await page.exposeFunction('__registrarViolacaoCsp', (v) => violacoes.push(v));
  await page.addInitScript(() => {
    document.addEventListener('securitypolicyviolation', (e) => {
      window.__registrarViolacaoCsp(`${e.violatedDirective} bloqueou ${e.blockedURI || '(inline)'}`);
    });
  });
  page.on('console', (msg) => {
    if (/content security policy|FullCalendar could not inject/i.test(msg.text())) violacoes.push(msg.text());
  });
  return violacoes;
}

test('o app roda sob a CSP (nginx ou Vercel) sem violações (login, agenda, detalhe com foto, admin)', async ({ page }) => {
  const violacoes = await vigiarCsp(page);

  const resposta = await page.goto('/login');
  const csp = resposta.headers()['content-security-policy'];
  if (!csp) {
    test.skip(!process.env.E2E_EXIGIR_CSP, 'Servidor sem CSP (vite preview?): rode contra a imagem nginx.');
    throw new Error('E2E_EXIGIR_CSP=1, mas a resposta não trouxe Content-Security-Policy.');
  }
  const origemApi = new URL(API_URL).origin;
  expect(csp).not.toContain("'unsafe-eval'");
  expect(csp).toMatch(/script-src 'self';/);
  if (csp.includes("style-src 'self' 'unsafe-inline'")) {
    // Vercel: cabeçalho fixo + meta do build com a origem da API; sem nonce.
    expect(csp).toContain("img-src 'self' https:;");
    expect(csp).toContain("connect-src 'self' https:;");
    expect(csp).toContain("frame-ancestors 'none'");
    const meta = await page.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content');
    expect(meta).toContain(`connect-src 'self' ${origemApi};`);
    expect(meta).toContain(`img-src 'self' ${origemApi};`);
    expect(meta).toMatch(/script-src 'self';/);
    expect(meta).not.toMatch(/unsafe-eval|nonce-/);
    expect(await page.locator('meta[name="csp-nonce"]').count()).toBe(0);
  } else {
    // nginx (Compose): origem da API no cabeçalho e nonce por resposta, sem 'unsafe-inline'.
    expect(csp).toContain(`connect-src 'self' ${origemApi}`);
    expect(csp).toContain(`img-src 'self' ${origemApi}`);
    expect(csp).not.toContain("'unsafe-inline'");
  }

  // Login (fetch para a API: connect-src).
  await page.getByLabel('RM').fill(ADMIN_RM);
  await page.getByLabel('Senha').fill(ADMIN_SENHA);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/agenda$/);

  // Agenda: os estilos injetados pelo FullCalendar foram aplicados (o <style> tem o nonce certo).
  await page.locator('.fc-daygrid-body').waitFor();
  const estiloFc = await page.evaluate(() => {
    const el = document.querySelector('style[data-fullcalendar]');
    return {
      regras: el?.sheet?.cssRules.length ?? 0,
      toolbar: getComputedStyle(document.querySelector('.fc-header-toolbar')).display,
    };
  });
  expect(estiloFc.regras).toBeGreaterThan(0);
  expect(estiloFc.toolbar).toBe('flex');

  // Detalhe do ambiente: a foto vem de API_URL/uploads (img-src) e carrega de fato.
  await page.goto(`/ambientes/${ctx.sala.id}`);
  const foto = page.locator('img[src*="/uploads/"]').first();
  await expect(foto).toBeVisible();
  await expect.poll(() => foto.evaluate((img) => img.complete && img.naturalWidth)).toBeGreaterThan(0);

  // Admin: lista de ambientes e edição com as fotos.
  await page.goto('/admin/ambientes');
  await expect(page.getByText(`Lab CSP ${sufixo}`).first()).toBeVisible();
  await page.goto(`/admin/ambientes/${ctx.sala.id}`);
  await expect(page.locator('img[src*="/uploads/"]').first()).toBeVisible();
  await page.goto('/admin/professores');
  await page.waitForLoadState('networkidle');

  expect(violacoes).toEqual([]);
});

/** PNG RGBA (largura × altura) com transparência, montado à mão (sem dependências), para o teste da redução. */
function pngGrande(largura, altura) {
  const crcTabela = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  const crc = (buf) => {
    let c = 0xffffffff;
    for (const b of buf) c = crcTabela[(c ^ b) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const bloco = (tipo, dados) => {
    const tam = Buffer.alloc(4);
    tam.writeUInt32BE(dados.length);
    const corpo = Buffer.concat([Buffer.from(tipo, 'ascii'), dados]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(corpo));
    return Buffer.concat([tam, corpo, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(largura, 0);
  ihdr.writeUInt32BE(altura, 4);
  ihdr.set([8, 6, 0, 0, 0], 8); // 8 bits, RGBA
  const linha = Buffer.alloc(1 + largura * 4);
  for (let x = 0; x < largura; x += 1) linha.set([x % 256, 80, 160, x < largura / 2 ? 255 : 0], 1 + x * 4);
  const bruto = Buffer.concat(Array.from({ length: altura }, () => linha));
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    bloco('IHDR', ihdr),
    bloco('IDAT', zlib.deflateSync(bruto)),
    bloco('IEND', Buffer.alloc(0)),
  ]);
}

/** Largura e altura de um JPEG (marcador SOF), e se ele tem APP1 (EXIF/XMP). */
function lerJpeg(buf) {
  expect([buf[0], buf[1]]).toEqual([0xff, 0xd8]);
  let i = 2;
  let app1 = false;
  while (i < buf.length) {
    const marcador = buf[i + 1];
    const tamanho = buf.readUInt16BE(i + 2);
    if (marcador === 0xe1) app1 = true;
    if (marcador >= 0xc0 && marcador <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marcador)) {
      return { altura: buf.readUInt16BE(i + 5), largura: buf.readUInt16BE(i + 7), app1 };
    }
    i += 2 + tamanho;
  }
  throw new Error('JPEG sem SOF');
}

// Ticket 68 (ADR-0010): foto grande enviada pelo admin é reduzida, guardada no banco e servida pela API com cache
// longo e ETag; o navegador a exibe sob a CSP (nginx ou Vercel) sem violação.
test('foto grande: reduzida, servida do banco com ETag/304 e exibida sob a CSP', async ({ page, request }) => {
  const violacoes = await vigiarCsp(page);
  const r = await request.post(`${API_URL}/salas/${ctx.sala.id}/fotos`, {
    headers: auth(ctx.token),
    multipart: {
      arquivo: { name: 'grande.png', mimeType: 'image/png', buffer: pngGrande(2400, 1800) },
      legenda: 'Foto grande',
    },
  });
  expect(r.status(), await r.text()).toBe(201);
  const { url } = await r.json();
  expect(url).toMatch(/^\/uploads\/salas\/\d+\/[0-9a-f-]{36}\.jpg$/);

  const g = await request.get(`${API_URL}${url}`);
  expect(g.status()).toBe(200);
  const cab = g.headers();
  expect(cab['content-type']).toBe('image/jpeg');
  expect(cab['cache-control']).toBe('public, max-age=31536000, immutable');
  expect(cab['content-security-policy']).toContain('sandbox');
  expect(cab['x-content-type-options']).toBe('nosniff');
  expect(cab.etag).toMatch(/^"[0-9a-f-]{36}"$/);
  const corpo = await g.body();
  expect(Number(cab['content-length'])).toBe(corpo.length);
  expect(lerJpeg(corpo)).toEqual({ largura: 1600, altura: 1200, app1: false });

  const r304 = await request.get(`${API_URL}${url}`, { headers: { 'If-None-Match': cab.etag } });
  expect(r304.status()).toBe(304);
  expect(r304.headers().etag).toBe(cab.etag);
  expect((await r304.body()).length).toBe(0);

  // No navegador: a foto aparece no detalhe (img-src da CSP libera a API) com o tamanho reduzido.
  await page.goto('/login');
  await page.getByLabel('RM').fill(ADMIN_RM);
  await page.getByLabel('Senha').fill(ADMIN_SENHA);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/agenda$/);
  const respostaFoto = page.waitForResponse((resp) => resp.url().endsWith(url));
  await page.goto(`/ambientes/${ctx.sala.id}`);
  expect((await respostaFoto).headers().etag).toBe(cab.etag);
  await page.getByRole('button', { name: 'Ver foto 2: Foto grande' }).click();
  const img = page.locator(`img[src$="${url}"]`).first();
  await expect(img).toBeAttached();
  await expect.poll(() => img.evaluate((el) => el.complete && el.naturalWidth)).toBe(1600);
  expect(violacoes).toEqual([]);
});
