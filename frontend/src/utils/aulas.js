/** Regras de aulas seguidas (spec RN03) aplicadas na interface. */

export const TURNOS = [
  { valor: 'manha', rotulo: 'Manhã' },
  { valor: 'tarde', rotulo: 'Tarde' },
  { valor: 'noite', rotulo: 'Noite' },
];

const ORDEM_TURNO = { manha: 0, tarde: 1, noite: 2 };

export const rotuloTurno = (valor) => TURNOS.find((t) => t.valor === valor)?.rotulo ?? valor;

export function ordenarAulas(aulas) {
  return [...aulas].sort(
    (a, b) => ORDEM_TURNO[a.turno] - ORDEM_TURNO[b.turno] || a.ordem - b.ordem,
  );
}

/** Agrupa HorarioAula[] por turno, na ordem manhã, tarde, noite (só turnos com aulas). */
export function agruparPorTurno(aulas) {
  return TURNOS.map((t) => ({
    ...t,
    aulas: ordenarAulas(aulas.filter((a) => a.turno === t.valor)),
  })).filter((g) => g.aulas.length > 0);
}

/** true se as aulas são do mesmo turno e de ordem consecutiva, sem repetição. */
export function saoSeguidas(aulas) {
  if (aulas.length === 0) return false;
  const turno = aulas[0].turno;
  if (aulas.some((a) => a.turno !== turno)) return false;
  const ordens = aulas.map((a) => a.ordem).sort((x, y) => x - y);
  return ordens.every((o, i) => i === 0 || o === ordens[i - 1] + 1);
}

/**
 * Atualiza a seleção ao clicar numa aula, garantindo aulas seguidas do mesmo turno.
 * - Aula já marcada: se é uma ponta, sai; se está no meio, a seleção é cortada antes dela.
 * - Aula nova do mesmo turno: estende a seleção até ela, se todas as aulas do caminho
 *   forem selecionáveis; senão a seleção recomeça nela.
 * - Aula de outro turno: a seleção recomeça nela.
 * @param {number[]} selecionadas ids marcados
 * @param {object} aula HorarioAula clicada
 * @param {object[]} selecionaveis HorarioAula[] que podem ser marcadas (livres, não passadas)
 * @returns {number[]} nova lista de ids, ordenada por ordem
 */
export function alternarAula(selecionadas, aula, selecionaveis) {
  const porId = new Map(selecionaveis.map((a) => [a.id, a]));
  const atuais = selecionadas.map((id) => porId.get(id)).filter(Boolean);
  const ids = (lista) => ordenarAulas(lista).map((a) => a.id);

  if (selecionadas.includes(aula.id)) {
    const ordens = atuais.map((a) => a.ordem);
    const min = Math.min(...ordens);
    const max = Math.max(...ordens);
    if (aula.ordem === min || aula.ordem === max) return ids(atuais.filter((a) => a.id !== aula.id));
    return ids(atuais.filter((a) => a.ordem < aula.ordem));
  }

  if (!porId.has(aula.id)) return ids(atuais);
  if (atuais.length === 0 || atuais[0].turno !== aula.turno) return [aula.id];

  const ordens = [...atuais.map((a) => a.ordem), aula.ordem];
  const min = Math.min(...ordens);
  const max = Math.max(...ordens);
  const doTurno = selecionaveis.filter((a) => a.turno === aula.turno);
  const caminho = [];
  for (let o = min; o <= max; o += 1) {
    const encontrada = doTurno.find((a) => a.ordem === o);
    if (!encontrada) return [aula.id];
    caminho.push(encontrada);
  }
  return ids(caminho);
}

/** Intervalo { inicio, fim } ocupado pelas aulas selecionadas. */
export function intervaloDasAulas(aulas) {
  if (aulas.length === 0) return null;
  const ordenadas = ordenarAulas(aulas);
  return { inicio: ordenadas[0].inicio, fim: ordenadas[ordenadas.length - 1].fim };
}

export const rotuloAula = (aula) => `${aula.ordem}ª aula · ${aula.inicio}–${aula.fim}`;
