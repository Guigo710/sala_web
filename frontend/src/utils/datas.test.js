import {
  diaSemanaIso,
  fullCalendarParaIso,
  intervaloParaConsulta,
  isoParaFullCalendar,
  somarDias,
} from './datas';

describe('dia da semana ISO ↔ FullCalendar', () => {
  it('converte ISO (1..7) para FullCalendar (0..6)', () => {
    expect(isoParaFullCalendar(1)).toBe(1);
    expect(isoParaFullCalendar(6)).toBe(6);
    expect(isoParaFullCalendar(7)).toBe(0);
  });

  it('converte FullCalendar (0..6) para ISO (1..7)', () => {
    expect(fullCalendarParaIso(0)).toBe(7);
    expect(fullCalendarParaIso(1)).toBe(1);
    expect(fullCalendarParaIso(6)).toBe(6);
  });

  it('calcula o dia ISO de uma data', () => {
    expect(diaSemanaIso('2026-09-15')).toBe(2); // terça
    expect(diaSemanaIso('2026-09-20')).toBe(7); // domingo
  });
});

describe('intervaloParaConsulta', () => {
  it('usa ate = end - 1 dia (end do FullCalendar é exclusivo)', () => {
    expect(intervaloParaConsulta(new Date(2026, 8, 1), new Date(2026, 9, 1))).toEqual({
      de: '2026-09-01',
      ate: '2026-09-30',
    });
  });

  it('soma dias atravessando o mês', () => {
    expect(somarDias('2026-09-29', 7)).toBe('2026-10-06');
  });
});
