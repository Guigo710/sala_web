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
