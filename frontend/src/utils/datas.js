/**
 * Datas e dias da semana.
 * API: dia da semana ISO (1 = segunda … 7 = domingo). FullCalendar/JS: 0 = domingo … 6 = sábado.
 */

export const DIAS_SEMANA = [
  { iso: 1, curto: 'Seg', nome: 'Segunda-feira' },
  { iso: 2, curto: 'Ter', nome: 'Terça-feira' },
  { iso: 3, curto: 'Qua', nome: 'Quarta-feira' },
  { iso: 4, curto: 'Qui', nome: 'Quinta-feira' },
  { iso: 5, curto: 'Sex', nome: 'Sexta-feira' },
  { iso: 6, curto: 'Sáb', nome: 'Sábado' },
  { iso: 7, curto: 'Dom', nome: 'Domingo' },
];

/** ISO (1..7) → FullCalendar/JS (0..6). */
export const isoParaFullCalendar = (iso) => iso % 7;

/** FullCalendar/JS (0..6) → ISO (1..7). */
export const fullCalendarParaIso = (dia) => (dia === 0 ? 7 : dia);

const dois = (n) => String(n).padStart(2, '0');

/** Date → "YYYY-MM-DD" no fuso local. */
export function paraDataIso(date) {
  return `${date.getFullYear()}-${dois(date.getMonth() + 1)}-${dois(date.getDate())}`;
}

/** "YYYY-MM-DD" → Date à meia-noite local. */
export function deDataIso(texto) {
  const [a, m, d] = texto.split('-').map(Number);
  return new Date(a, m - 1, d);
}

export const hojeIso = () => paraDataIso(new Date());

/** Dia da semana ISO de uma data "YYYY-MM-DD". */
export const diaSemanaIso = (texto) => fullCalendarParaIso(deDataIso(texto).getDay());

export function somarDias(texto, dias) {
  const d = deDataIso(texto);
  d.setDate(d.getDate() + dias);
  return paraDataIso(d);
}

/** Data + hora locais ("YYYY-MM-DD", "HH:MM") → Date. */
export function dataHora(data, hora) {
  const [h, min] = hora.split(':').map(Number);
  const d = deDataIso(data);
  d.setHours(h, min, 0, 0);
  return d;
}

/** true se `data + hora` já passou (relógio do navegador). */
export const jaPassou = (data, hora, agora = new Date()) => dataHora(data, hora) <= agora;

const fmtLonga = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'long',
  day: '2-digit',
  month: 'long',
  year: 'numeric',
});
const fmtCurta = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
});
const fmtSimples = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
const fmtDataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

/** "2026-09-15" → "terça-feira, 15 de setembro de 2026" */
export const formatarDataLonga = (texto) => (texto ? fmtLonga.format(deDataIso(texto)) : '');
/** "2026-09-15" → "ter., 15/09/2026" */
export const formatarDataCurta = (texto) => (texto ? fmtCurta.format(deDataIso(texto)) : '');
/** "2026-09-15" → "15/09/2026" */
export const formatarData = (texto) => (texto ? fmtSimples.format(deDataIso(texto)) : '');
/** ISO 8601 com fuso → "15/09/2026 10:15" */
export const formatarDataHora = (texto) => (texto ? fmtDataHora.format(new Date(texto)) : '');

/**
 * Intervalo visível do FullCalendar → parâmetros `de`/`ate` de GET /reservas.
 * FullCalendar entrega `end` exclusivo: `ate = end - 1 dia`.
 */
export function intervaloParaConsulta(inicio, fimExclusivo) {
  const fim = new Date(fimExclusivo);
  fim.setDate(fim.getDate() - 1);
  return { de: paraDataIso(inicio), ate: paraDataIso(fim) };
}

/** "HH:MM" → minutos desde 00:00. */
export function paraMinutos(hora) {
  const [h, m] = hora.split(':').map(Number);
  return h * 60 + m;
}

/** minutos → "HH:MM:SS" (formato aceito pelo FullCalendar em slotMinTime/slotMaxTime). */
export function deMinutos(minutos) {
  const limitado = Math.max(0, Math.min(24 * 60, minutos));
  return `${dois(Math.floor(limitado / 60))}:${dois(limitado % 60)}:00`;
}
