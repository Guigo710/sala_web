/*
 * E2E do fluxo principal contra o backend real (ticket 27, spec H05–H08).
 * Cada execução cria um ambiente e dois professores com nomes únicos, então pode rodar
 * várias vezes no mesmo banco sem limpar nada.
 */
import { expect, test } from '@playwright/test';
import {
  ADMIN_RM,
  ADMIN_SENHA,
  agendaApi,
  criarProfessorApi,
  criarSalaApi,
  ddmm,
  horariosManha,
  proximoDia,
  quartaDeSemestre,
  reservarApi,
  somarDias,
  tela,
  tokenApi,
} from './apoio';

const sufixo = Date.now().toString(36).slice(-6);
const SALA = `Lab E2E ${sufixo}`;
const PROF_A = { rm: `e2ea${sufixo}`, nome: `Ana E2E ${sufixo}`, senha: 'senhaAna123' };
const PROF_B = { rm: `e2eb${sufixo}`, nome: `Bruno E2E ${sufixo}`, senha: 'senhaBruno123' };

const ctx = {};

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  ctx.tokenAdmin = await tokenApi(request, ADMIN_RM, ADMIN_SENHA);
  ctx.sala = await criarSalaApi(request, ctx.tokenAdmin, SALA);
  ctx.manha = await horariosManha(request); // 1ª 07:30–08:20, 2ª 08:20–09:10, 3ª 09:30–10:20 ...
  await criarProfessorApi(request, ctx.tokenAdmin, PROF_B);
  ctx.terca = proximoDia(2, somarDias(new Date().toISOString().slice(0, 10), 2));
});

async function entrar(page, rm, senha) {
  await page.goto('/login');
  await page.getByLabel('RM').fill(rm);
  await page.getByLabel('Senha').fill(senha);
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page).toHaveURL(/\/agenda$/);
}

async function abrirModalReserva(page, data) {
  await page.goto('/agenda');
  await page.getByRole('button', { name: 'Nova reserva' }).click();
  const dialogo = page.getByRole('dialog', { name: 'Nova reserva' });
  await dialogo.getByLabel('Ambiente').selectOption(String(ctx.sala.id));
  await dialogo.getByLabel(/^Data/).fill(data);
  await expect(dialogo.getByText(/Aulas em/)).toBeVisible();
  return dialogo;
}

/** Na agenda (mês), avança até achar um evento com o texto; devolve o locator. */
async function eventoNaAgenda(page, texto) {
  const evento = page.locator('.fc-event', { hasText: texto });
  for (let i = 0; i < 3; i += 1) {
    await page.locator('.fc-daygrid-body').waitFor();
    await page.waitForLoadState('networkidle');
    if (await evento.count()) return evento;
    await page.locator('.fc-next-button').click();
  }
  return evento;
}

test('admin entra e cadastra um professor pela interface', async ({ page }) => {
  await entrar(page, ADMIN_RM, ADMIN_SENHA);
  await tela(page, 'admin-logado-agenda');

  await page.goto('/admin/professores');
  await page.getByRole('button', { name: 'Novo professor' }).click();
  const dialogo = page.getByRole('dialog');
  await dialogo.getByLabel('RM').fill(PROF_A.rm);
  await dialogo.getByLabel('Nome').fill(PROF_A.nome);
  await dialogo.getByLabel('Senha inicial').fill(PROF_A.senha);
  await tela(page, 'admin-novo-professor');
  await dialogo.getByRole('button', { name: 'Salvar' }).click();
  await expect(dialogo).toBeHidden();
  await expect(page.getByRole('cell', { name: PROF_A.rm })).toBeVisible();
  await tela(page, 'admin-professor-criado');
});

test('professor reserva 2 aulas seguidas e vê a reserva na agenda', async ({ page }) => {
  await entrar(page, PROF_A.rm, PROF_A.senha);
  const dialogo = await abrirModalReserva(page, ctx.terca);
  await dialogo.getByLabel(/07:30–08:20/).check();
  await dialogo.getByLabel(/08:20–09:10/).check();
  await expect(dialogo.getByText('Selecionado: 07:30–09:10 (2 aulas).')).toBeVisible();
  await tela(page, 'professor-modal-reserva');
  await dialogo.getByRole('button', { name: 'Reservar', exact: true }).click();
  await expect(dialogo).toBeHidden();
  await expect(page.getByText(/Reserva criada:/)).toBeVisible();

  const evento = await eventoNaAgenda(page, SALA);
  await expect(evento).toHaveCount(1);
  await expect(evento).toContainText(PROF_A.nome);
  await tela(page, 'professor-reserva-na-agenda');

  const [reserva] = await agendaApi(page.request, { data: ctx.terca, sala_id: ctx.sala.id });
  expect(reserva).toMatchObject({ inicio: '07:30', fim: '09:10', quantidade_aulas: 2, professor: { nome: PROF_A.nome } });
  expect(reserva.professor).not.toHaveProperty('rm');
  ctx.reservaA = reserva;
});

test('outro professor vê o bloco ocupado e recebe o conflito ao tentar reservar', async ({ page }) => {
  await entrar(page, PROF_B.rm, PROF_B.senha);
  const dialogo = await abrirModalReserva(page, ctx.terca);

  // A interface já mostra as aulas ocupadas e não deixa marcá-las.
  const ocupada = dialogo.getByLabel(/08:20–09:10/);
  await expect(ocupada).toBeDisabled();
  await expect(dialogo.getByText(`ocupada · ${PROF_A.nome}`).first()).toBeVisible();

  // Corrida real: B escolhe a 3ª aula, mas o admin a reserva antes de B confirmar → 409 do backend.
  await dialogo.getByLabel(/09:30–10:20/).check();
  await reservarApi(page.request, ctx.tokenAdmin, { sala_id: ctx.sala.id, data: ctx.terca, horario_ids: [ctx.manha[2].id] });
  await dialogo.getByRole('button', { name: 'Reservar', exact: true }).click();
  const alerta = dialogo.getByRole('alert').filter({ hasText: 'Horário já reservado' });
  await expect(alerta).toBeVisible();
  await expect(alerta).toContainText('Sala não disponível neste horário.');
  await expect(alerta).toContainText('09:30–10:20');
  await tela(page, 'conflito-409-no-modal');
  // A disponibilidade é recarregada: agora a 3ª aula aparece ocupada.
  await expect(dialogo.getByLabel(/09:30–10:20/)).toBeDisabled();
});

test('recorrência: prévia lista o conflito e reserva só as datas livres', async ({ page }) => {
  const { data: quarta } = await quartaDeSemestre(page.request);
  const ocupada = somarDias(quarta, 7);
  await reservarApi(page.request, ctx.tokenAdmin, { sala_id: ctx.sala.id, data: ocupada, horario_ids: [ctx.manha[0].id] });

  await entrar(page, PROF_A.rm, PROF_A.senha);
  const dialogo = await abrirModalReserva(page, quarta);
  await dialogo.getByText('Repetir toda semana').click();
  await dialogo.getByLabel(/07:30–08:20/).check();
  await dialogo.getByLabel(/08:20–09:10/).check();
  await dialogo.getByRole('button', { name: 'Ver datas da série' }).click();

  await expect(dialogo.getByText('Datas da série')).toBeVisible();
  const linhaOcupada = dialogo.locator('li.ocorrencia', { hasText: ddmm(ocupada) });
  await expect(linhaOcupada).toHaveClass(/conflito/);
  await expect(linhaOcupada.getByRole('checkbox')).toBeDisabled();
  await expect(linhaOcupada).toContainText('07:30–08:20');
  const total = await dialogo.locator('li.ocorrencia').count();
  const livres = await dialogo.locator('li.ocorrencia.livre').count();
  expect(total).toBeGreaterThanOrEqual(3);
  expect(livres).toBe(total - 1);

  // Desmarca a última data livre: só as demais devem ser gravadas.
  const ultimaLivre = dialogo.locator('li.ocorrencia.livre').last().getByRole('checkbox');
  await ultimaLivre.uncheck();
  await tela(page, 'recorrencia-previa');
  await dialogo.getByRole('button', { name: `Reservar só as livres selecionadas (${livres - 1})` }).click();
  await expect(dialogo).toBeHidden();
  await expect(page.getByText(new RegExp(`Reserva semanal criada: ${livres - 1} datas reservadas`))).toBeVisible();
  await tela(page, 'recorrencia-confirmada');

  const minhas = await page.request
    .get(`${process.env.E2E_API_URL || 'http://localhost:8000'}/reservas/minhas`, {
      headers: { Authorization: `Bearer ${await tokenApi(page.request, PROF_A.rm, PROF_A.senha)}` },
    })
    .then((r) => r.json());
  const daSerie = minhas.filter((r) => r.grupo_recorrencia_id);
  expect(daSerie).toHaveLength(livres - 1);
  expect(daSerie.map((r) => r.data)).not.toContain(ocupada);
  ctx.quarta = quarta;
});

test('professor cancela em Minhas reservas e a reserva some da agenda; depois cancela a série', async ({ page }) => {
  await entrar(page, PROF_A.rm, PROF_A.senha);
  await page.goto('/minhas-reservas');
  const item = page.locator('li.reserva-item', { hasText: ddmm(ctx.terca) }).filter({ hasText: SALA });
  await expect(item).toHaveCount(1);
  await tela(page, 'minhas-reservas');
  await item.getByRole('button', { name: 'Cancelar' }).click();
  const dialogo = page.getByRole('dialog', { name: 'Cancelar reserva' });
  await dialogo.getByLabel('Motivo (opcional)').fill('Teste E2E');
  await dialogo.getByRole('button', { name: 'Cancelar reserva' }).click();
  await expect(page.getByText('Reserva cancelada.')).toBeVisible();
  await expect(item).toHaveCount(0);

  const ativas = await agendaApi(page.request, { data: ctx.terca, sala_id: ctx.sala.id });
  expect(ativas.map((r) => r.id)).not.toContain(ctx.reservaA.id);
  await page.goto(`/agenda?sala=${ctx.sala.id}`);
  await page.waitForLoadState('networkidle');
  // Na terça só resta a reserva do admin (09:30); a de Ana sumiu.
  await eventoNaAgenda(page, SALA);
  const terca = page.locator(`td[data-date="${ctx.terca}"] .fc-event`);
  await expect(terca.filter({ hasText: PROF_A.nome })).toHaveCount(0);
  await tela(page, 'agenda-apos-cancelar');

  // Cancelar toda a série semanal.
  await page.goto('/minhas-reservas');
  await page.getByRole('button', { name: 'Cancelar todas as próximas desta recorrência' }).first().click();
  const dialogoGrupo = page.getByRole('dialog', { name: 'Cancelar recorrência' });
  await expect(dialogoGrupo).toContainText('Serão canceladas');
  await dialogoGrupo.getByRole('button', { name: 'Cancelar todas as próximas' }).click();
  await expect(page.getByText(/reservas? canceladas? nesta recorrência/)).toBeVisible();
  await expect(page.getByText('Você não tem reservas futuras.')).toBeVisible();
  await tela(page, 'minhas-reservas-vazia');
});
