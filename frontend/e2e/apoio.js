/* Apoio dos testes E2E: chamadas diretas à API (preparação de dados) e datas no fuso da escola. */
import fs from 'node:fs';
import path from 'node:path';

export const API_URL = (process.env.E2E_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
export const ADMIN_RM = process.env.E2E_ADMIN_RM || process.env.ADMIN_RM || 'admin';
export const ADMIN_SENHA = process.env.E2E_ADMIN_SENHA || process.env.ADMIN_SENHA || 'senhaAdmin123';
const PASTA_TELAS = process.env.E2E_SCREENSHOTS || 'test-results/telas';

let contadorTela = 0;
/** Captura numerada do fluxo (sempre, não só em falha). */
export async function tela(page, nome) {
  fs.mkdirSync(PASTA_TELAS, { recursive: true });
  contadorTela += 1;
  const arquivo = path.join(PASTA_TELAS, `${String(contadorTela).padStart(2, '0')}-${nome}.png`);
  await page.screenshot({ path: arquivo, fullPage: true });
  return arquivo;
}

/** Hoje em America/Sao_Paulo, "YYYY-MM-DD". */
export function hojeSP() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date());
}

export function somarDias(iso, dias) {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

export function diaIso(iso) {
  const d = new Date(`${iso}T12:00:00Z`).getUTCDay();
  return d === 0 ? 7 : d;
}

/** Primeira data >= `de` (e > hoje) com o dia da semana ISO pedido. */
export function proximoDia(isoSemana, de = somarDias(hojeSP(), 1)) {
  let d = de <= hojeSP() ? somarDias(hojeSP(), 1) : de;
  while (diaIso(d) !== isoSemana) d = somarDias(d, 1);
  return d;
}

/** "2026-11-17" → "17/11" (como a interface mostra datas curtas, sem o dia da semana). */
export function ddmm(iso) {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
}

async function json(resposta, esperado) {
  const corpo = await resposta.json().catch(() => null);
  if (esperado && resposta.status() !== esperado) {
    throw new Error(`API ${resposta.url()} → ${resposta.status()} (esperado ${esperado}): ${JSON.stringify(corpo)}`);
  }
  return corpo;
}

export async function tokenApi(request, rm, senha) {
  const r = await request.post(`${API_URL}/auth/login`, { data: { rm, senha } });
  return (await json(r, 200)).access_token;
}

export const auth = (token) => ({ Authorization: `Bearer ${token}` });

export async function criarSalaApi(request, token, nome) {
  const r = await request.post(`${API_URL}/salas`, {
    headers: auth(token),
    data: { nome, tipo: 'lab_informatica', capacidade: 30, localizacao: 'Bloco E2E' },
  });
  return json(r, 201);
}

export async function criarProfessorApi(request, token, dados) {
  const r = await request.post(`${API_URL}/professores`, { headers: auth(token), data: { papel: 'professor', ...dados } });
  return json(r, 201);
}

export async function horariosManha(request) {
  const r = await request.get(`${API_URL}/horarios`, { params: { turno: 'manha' } });
  return json(r, 200);
}

export async function reservarApi(request, token, corpo, esperado = 201) {
  const r = await request.post(`${API_URL}/reservas`, { headers: auth(token), data: corpo });
  return json(r, esperado);
}

export async function agendaApi(request, params) {
  const r = await request.get(`${API_URL}/reservas`, { params });
  return json(r, 200);
}

/** Primeira quarta-feira (a partir da semana que vem) dentro de um semestre, com pelo menos 3 semanas até o fim. */
export async function quartaDeSemestre(request) {
  const semestres = await json(await request.get(`${API_URL}/semestres`), 200);
  const ordenados = [...semestres].sort((a, b) => a.data_inicio.localeCompare(b.data_inicio));
  for (const s of ordenados) {
    const candidata = proximoDia(3, s.data_inicio > somarDias(hojeSP(), 7) ? s.data_inicio : somarDias(hojeSP(), 7));
    if (candidata >= s.data_inicio && somarDias(candidata, 14) <= s.data_fim) return { semestre: s, data: candidata };
  }
  throw new Error('Nenhum semestre cadastrado comporta uma série de 3 semanas: rode o seed.');
}
