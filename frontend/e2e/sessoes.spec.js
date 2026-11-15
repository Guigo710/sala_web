/*
 * E2E da revogação de sessões (ADR-0008, contrato 1.2, tickets 41 e 46) contra o backend real.
 * Cada teste usa dois contextos de navegador (duas "máquinas"): uma sessão age e a outra deve cair.
 *
 * "Cair" = a próxima rota protegida responde 401 e o app leva ao /login. Testamos os dois caminhos
 * do frontend: navegação dentro do app (aviso "Sua sessão expirou") e recarga da página
 * (verificação inicial com GET /auth/me).
 */
import { expect, test } from '@playwright/test';
import { ADMIN_RM, ADMIN_SENHA, API_URL, auth, criarProfessorApi, tela, tokenApi } from './apoio';

const sufixo = Date.now().toString(36).slice(-6);
const ctx = {};

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  ctx.tokenAdmin = await tokenApi(request, ADMIN_RM, ADMIN_SENHA);
});

/** Entra pela tela de login. Depois de uma sessão cair, o app volta para onde o usuário estava. */
async function entrar(page, rm, senha, destino = /\/agenda$/) {
  await page.goto('/login');
  await page.getByLabel('RM').fill(rm);
  await page.getByLabel('Senha').fill(senha);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(destino);
}

/** Navega dentro do app (sem recarregar) até uma rota protegida. */
async function irParaMinhasReservas(page) {
  await page.getByRole('link', { name: 'Minhas reservas' }).click();
}

async function esperarLoginComAviso(page) {
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('Sua sessão expirou. Entre novamente.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Entrar' })).toBeVisible();
}

/** Token gravado pelo app (auth/sessao.js). */
const tokenGravado = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('sala_web.sessao') || '{}').token || null);

async function sessaoSegueValendo(page) {
  await page.goto('/minhas-reservas');
  await expect(page).toHaveURL(/\/minhas-reservas$/);
  await expect(page.getByRole('heading', { name: 'Minhas reservas' })).toBeVisible();
}

async function novoProfessor(request, letra) {
  const dados = { rm: `e2e${letra}${sufixo}`, nome: `Prof ${letra.toUpperCase()} ${sufixo}`, senha: `senha${letra}Inicial1` };
  const criado = await criarProfessorApi(request, ctx.tokenAdmin, dados);
  return { ...dados, id: criado.id };
}

test('professor troca a própria senha e continua logado; a outra sessão dele cai', async ({ browser, request }) => {
  const prof = await novoProfessor(request, 's');
  const novaSenha = `novaSenha${sufixo}`;
  const c1 = await browser.newContext();
  const c2 = await browser.newContext();
  const p1 = await c1.newPage();
  const p2 = await c2.newPage();
  try {
    await entrar(p1, prof.rm, prof.senha);
    await entrar(p2, prof.rm, prof.senha);
    const tokenAntes = await tokenGravado(p1);
    expect(tokenAntes).toBeTruthy();

    await p1.goto('/minha-conta');
    await p1.getByLabel('Senha atual').fill(prof.senha);
    await p1.getByLabel('Nova senha', { exact: true }).fill(novaSenha);
    await p1.getByLabel('Confirmar nova senha').fill(novaSenha);
    await p1.getByRole('button', { name: 'Trocar senha' }).click();
    await expect(p1.getByText('Senha alterada com sucesso. As outras sessões foram encerradas.')).toBeVisible();
    await tela(p1, 'sessao1-senha-trocada');

    // Sessão 1: token novo gravado, navegação seguinte sem 401 (inclusive depois de recarregar).
    const tokenDepois = await tokenGravado(p1);
    expect(tokenDepois).toBeTruthy();
    expect(tokenDepois).not.toBe(tokenAntes);
    await irParaMinhasReservas(p1);
    await expect(p1).toHaveURL(/\/minhas-reservas$/);
    await sessaoSegueValendo(p1);
    await tela(p1, 'sessao1-continua-logada');

    // Sessão 2 (outro navegador, mesmo professor): cai para o login.
    await irParaMinhasReservas(p2);
    await esperarLoginComAviso(p2);
    await tela(p2, 'sessao2-caiu-para-login');

    // Senha antiga não entra mais; a nova sim.
    const antiga = await request.post(`${API_URL}/auth/login`, { data: { rm: prof.rm, senha: prof.senha } });
    expect(antiga.status()).toBe(401);
    await p2.getByLabel('RM').fill(prof.rm);
    await p2.getByLabel('Senha').fill(novaSenha);
    await p2.getByRole('button', { name: 'Entrar' }).click();
    await expect(p2).toHaveURL(/\/minhas-reservas$/); // volta para onde estava
    await sessaoSegueValendo(p2);
  } finally {
    await c1.close();
    await c2.close();
  }
});

test('admin redefine a senha de um professor e a sessão desse professor cai', async ({ browser, request }) => {
  const prof = await novoProfessor(request, 'r');
  const cProf = await browser.newContext();
  const cAdmin = await browser.newContext();
  const pProf = await cProf.newPage();
  const pAdmin = await cAdmin.newPage();
  try {
    await entrar(pProf, prof.rm, prof.senha);
    await sessaoSegueValendo(pProf);

    await entrar(pAdmin, ADMIN_RM, ADMIN_SENHA);
    await pAdmin.goto('/admin/professores');
    const linha = pAdmin.getByRole('row').filter({ hasText: prof.rm });
    await linha.getByRole('button', { name: 'Redefinir senha' }).click();
    const dialogo = pAdmin.getByRole('dialog', { name: 'Redefinir senha' });
    await dialogo.getByLabel('Nova senha').fill(`redefinida${sufixo}`);
    await dialogo.getByRole('button', { name: 'Redefinir senha' }).click();
    await expect(dialogo).toBeHidden();
    await expect(pAdmin.getByText(`Senha de ${prof.nome} redefinida.`)).toBeVisible();
    await tela(pAdmin, 'admin-redefiniu-senha');

    // A sessão do professor cai: navegação no app → login com aviso.
    // A aba do professor ficou aberta: navega dentro do app (sem recarregar).
    await pProf.getByRole('link', { name: 'Agenda', exact: true }).click();
    await irParaMinhasReservas(pProf);
    await esperarLoginComAviso(pProf);
    await tela(pProf, 'professor-caiu-apos-redefinicao');

    // A sessão do admin (outra conta) segue valendo.
    await sessaoSegueValendo(pAdmin);
    await pProf.getByLabel('RM').fill(prof.rm);
    await pProf.getByLabel('Senha').fill(`redefinida${sufixo}`);
    await pProf.getByRole('button', { name: 'Entrar' }).click();
    await expect(pProf).toHaveURL(/\/minhas-reservas$/);
  } finally {
    await cProf.close();
    await cAdmin.close();
  }
});

test('admin desativa um professor e a sessão dele cai (e não volta ao reativar)', async ({ browser, request }) => {
  const prof = await novoProfessor(request, 'd');
  const cProf = await browser.newContext();
  const cAdmin = await browser.newContext();
  const pProf = await cProf.newPage();
  const pAdmin = await cAdmin.newPage();
  try {
    await entrar(pProf, prof.rm, prof.senha);
    await sessaoSegueValendo(pProf);
    const tokenProf = await tokenGravado(pProf);
    expect(tokenProf).toBeTruthy();

    await entrar(pAdmin, ADMIN_RM, ADMIN_SENHA);
    await pAdmin.goto('/admin/professores');
    const linha = pAdmin.getByRole('row').filter({ hasText: prof.rm });
    await linha.getByRole('button', { name: 'Desativar' }).click();
    await expect(pAdmin.getByText(`Conta de ${prof.nome} desativada.`)).toBeVisible();
    await expect(linha).toContainText('Inativa');
    await tela(pAdmin, 'admin-desativou-professor');

    // Caminho da recarga: GET /auth/me → 401 → login.
    await pProf.goto('/minhas-reservas');
    await expect(pProf).toHaveURL(/\/login$/);
    await expect(pProf.getByRole('button', { name: 'Entrar' })).toBeVisible();
    await tela(pProf, 'professor-desativado-caiu');

    // Conta inativa não entra.
    await pProf.getByLabel('RM').fill(prof.rm);
    await pProf.getByLabel('Senha').fill(prof.senha);
    await pProf.getByRole('button', { name: 'Entrar' }).click();
    await expect(pProf.getByRole('alert')).toBeVisible();
    await expect(pProf).toHaveURL(/\/login$/);
    await tela(pProf, 'professor-desativado-login-recusado');

    // Reativar não revive o token antigo (ADR-0008).
    await linha.getByRole('button', { name: 'Ativar' }).click();
    await expect(pAdmin.getByText(`Conta de ${prof.nome} ativada.`)).toBeVisible();
    const me = await request.get(`${API_URL}/auth/me`, { headers: auth(tokenProf) });
    expect(me.status()).toBe(401);
    // Já está em /login (vindo de /minhas-reservas): depois de entrar, volta para lá.
    await entrar(pProf, prof.rm, prof.senha, /\/(agenda|minhas-reservas)$/);
    await sessaoSegueValendo(pProf);
  } finally {
    await cProf.close();
    await cAdmin.close();
  }
});
