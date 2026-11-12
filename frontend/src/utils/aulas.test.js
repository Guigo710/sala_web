import { alternarAula, saoSeguidas } from './aulas';

const aula = (id, turno, ordem) => ({ id, turno, ordem, inicio: '00:00', fim: '00:00' });
const m1 = aula(1, 'manha', 1);
const m2 = aula(2, 'manha', 2);
const m3 = aula(3, 'manha', 3);
const m4 = aula(4, 'manha', 4);
const t1 = aula(5, 'tarde', 1);
const todas = [m1, m2, m3, m4, t1];

describe('alternarAula', () => {
  it('marca a primeira aula', () => {
    expect(alternarAula([], m2, todas)).toEqual([2]);
  });

  it('estende até a aula clicada preenchendo o caminho', () => {
    expect(alternarAula([1], m3, todas)).toEqual([1, 2, 3]);
  });

  it('recomeça ao trocar de turno', () => {
    expect(alternarAula([1, 2], t1, todas)).toEqual([5]);
  });

  it('não cria buracos quando uma aula do caminho não é selecionável', () => {
    expect(alternarAula([1], m3, [m1, m3, m4])).toEqual([3]);
  });

  it('desmarcar uma ponta tira só ela; desmarcar o meio corta a seleção', () => {
    expect(alternarAula([1, 2, 3], m3, todas)).toEqual([1, 2]);
    expect(alternarAula([1, 2, 3, 4], m3, todas)).toEqual([1, 2]);
  });
});

describe('saoSeguidas', () => {
  it('valida mesmo turno e ordem consecutiva', () => {
    expect(saoSeguidas([m2, m1])).toBe(true);
    expect(saoSeguidas([m1, m3])).toBe(false);
    expect(saoSeguidas([m1, t1])).toBe(false);
  });
});
