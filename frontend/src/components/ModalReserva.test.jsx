import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErroApi } from '../api/cliente';
import { criarReserva, criarReservaRecorrente, previaRecorrencia } from '../api/reservas';
import { listarSalas, obterDisponibilidade } from '../api/salas';
import { renderizar } from '../testes/render';
import ModalReserva from './ModalReserva';

vi.mock('../api/salas', () => ({ listarSalas: vi.fn(), obterDisponibilidade: vi.fn() }));
vi.mock('../api/reservas', () => ({ criarReserva: vi.fn(), previaRecorrencia: vi.fn(), criarReservaRecorrente: vi.fn() }));
vi.mock('../api/professores', () => ({ listarProfessores: vi.fn().mockResolvedValue([]) }));

const DATA = '2030-03-05';
const aula = (id, turno, ordem, inicio, fim) => ({ id, turno, ordem, inicio, fim, dias_semana: [1, 2, 3, 4, 5], ativo: true });
const M1 = aula(1, 'manha', 1, '07:30', '08:20');
const M2 = aula(2, 'manha', 2, '08:20', '09:10');
const M3 = aula(3, 'manha', 3, '09:30', '10:20');
const M4 = aula(4, 'manha', 4, '10:20', '11:10');
const T1 = aula(6, 'tarde', 1, '13:00', '13:50');
const livre = (h) => ({ horario: h, livre: true, passou: false, reserva: null });
const ocupada = (h, nome = 'João Lima') => ({
  horario: h,
  livre: false,
  passou: false,
  reserva: { id: 88, professor: { id: 9, nome }, inicio: h.inicio, fim: h.fim },
});

const SALA = { id: 3, nome: 'Laboratório 03', tipo: 'lab_informatica', tipo_rotulo: 'Laboratório de informática', capacidade: 30 };
const CONFLITO = { data: DATA, inicio: '08:20', fim: '09:10', reserva_id: 88, sala_id: 3, professor: { id: 9, nome: 'João Lima' } };

function abrir(props = {}) {
  const aoFechar = vi.fn();
  const aoConcluir = vi.fn();
  renderizar(
    <ModalReserva aberto salaInicial={3} dataInicial={DATA} aoFechar={aoFechar} aoConcluir={aoConcluir} {...props} />,
  );
  return { aoFechar, aoConcluir, dialogo: () => screen.getByRole('dialog', { name: 'Nova reserva' }) };
}

const caixa = (rotulo) => screen.getByRole('checkbox', { name: new RegExp(rotulo) });
const marcadas = () => screen.getAllByRole('checkbox').filter((c) => c.checked).map((c) => c.closest('label').textContent);

beforeEach(() => {
  vi.clearAllMocks();
  listarSalas.mockResolvedValue([SALA]);
  obterDisponibilidade.mockResolvedValue({ sala_id: 3, data: DATA, dia_semana: 2, aulas: [livre(M1), livre(M2), livre(M3), livre(M4), livre(T1)] });
});

describe('ModalReserva: reserva avulsa', () => {
  it('só permite aulas seguidas do mesmo turno e envia o bloco escolhido', async () => {
    const { aoFechar, aoConcluir } = abrir();
    await screen.findByText(/Aulas em/);
    const reservar = screen.getByRole('button', { name: 'Reservar' });
    expect(reservar).toBeDisabled();

    await userEvent.click(caixa('07:30–08:20'));
    await userEvent.click(caixa('09:30–10:20')); // pula a 2ª: o caminho é preenchido, sem buraco
    expect(marcadas()).toHaveLength(3);
    expect(screen.getByText('Selecionado: 07:30–10:20 (3 aulas).')).toBeInTheDocument();

    await userEvent.click(caixa('13:00–13:50')); // outro turno: recomeça
    expect(marcadas()).toEqual([expect.stringContaining('13:00–13:50')]);

    await userEvent.click(caixa('07:30–08:20'));
    await userEvent.click(caixa('08:20–09:10'));
    criarReserva.mockResolvedValue({ id: 101, sala: SALA, data: DATA, inicio: '07:30', fim: '09:10' });
    await userEvent.type(screen.getByLabelText('Observação (opcional)'), '  Programação I ');
    await userEvent.click(reservar);

    expect(criarReserva).toHaveBeenCalledWith({ sala_id: 3, data: DATA, horario_ids: [1, 2], observacao: 'Programação I' });
    expect(criarReserva.mock.calls[0][0]).not.toHaveProperty('professor_id');
    await waitFor(() => expect(aoFechar).toHaveBeenCalled());
    expect(aoConcluir).toHaveBeenCalledWith(expect.objectContaining({ id: 101 }));
  });

  it('aula ocupada não pode ser marcada e interrompe o bloco', async () => {
    obterDisponibilidade.mockResolvedValue({ sala_id: 3, data: DATA, dia_semana: 2, aulas: [livre(M1), ocupada(M2), livre(M3)] });
    abrir();
    await screen.findByText(/Aulas em/);
    expect(caixa('08:20–09:10')).toBeDisabled();
    expect(screen.getByText('ocupada · João Lima')).toBeInTheDocument();
    await userEvent.click(caixa('07:30–08:20'));
    await userEvent.click(caixa('09:30–10:20'));
    expect(marcadas()).toEqual([expect.stringContaining('09:30–10:20')]);
  });

  it('409 da API mostra os conflitos e recarrega a disponibilidade', async () => {
    abrir();
    await screen.findByText(/Aulas em/);
    await userEvent.click(caixa('08:20–09:10'));
    criarReserva.mockRejectedValue(
      new ErroApi({ status: 409, codigo: 'CONFLITO_RESERVA', detail: 'Sala não disponível neste horário.', conflitos: [CONFLITO] }),
    );
    obterDisponibilidade.mockResolvedValue({ sala_id: 3, data: DATA, dia_semana: 2, aulas: [livre(M1), ocupada(M2), livre(M3)] });
    await userEvent.click(screen.getByRole('button', { name: 'Reservar' }));

    const alerta = await screen.findByRole('alert');
    expect(within(alerta).getByText('Horário já reservado')).toBeInTheDocument();
    expect(within(alerta).getByText('Sala não disponível neste horário.')).toBeInTheDocument();
    expect(within(alerta).getByText(/reservado por João Lima/)).toHaveTextContent('08:20–09:10');
    await waitFor(() => expect(obterDisponibilidade).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('ocupada · João Lima')).toBeInTheDocument();
    expect(marcadas()).toHaveLength(0);
    expect(screen.getByRole('dialog', { name: 'Nova reserva' })).toBeInTheDocument();
  });
});

describe('ModalReserva: recorrência com prévia', () => {
  const PREVIA = {
    sala: { id: 3, nome: 'Laboratório 03', tipo: 'lab_informatica' },
    semestre: { id: 2, nome: '2030-1', data_inicio: '2030-02-04', data_fim: '2030-06-25' },
    dia_semana: 2,
    inicio: '07:30',
    fim: '09:10',
    horario_ids: [1, 2],
    ocorrencias: [
      { data: '2030-03-05', livre: true, conflitos: [] },
      { data: '2030-03-12', livre: false, conflitos: [{ ...CONFLITO, data: '2030-03-12' }] },
      { data: '2030-03-19', livre: true, conflitos: [] },
      { data: '2030-03-26', livre: true, conflitos: [] },
    ],
    total: 4,
    livres: 3,
    em_conflito: 1,
  };

  async function irParaPrevia() {
    const ctx = abrir();
    await screen.findByText(/Aulas em/);
    await userEvent.click(screen.getByRole('checkbox', { name: /Repetir toda semana/ }));
    await userEvent.click(caixa('07:30–08:20'));
    await userEvent.click(caixa('08:20–09:10'));
    previaRecorrencia.mockResolvedValue(PREVIA);
    await userEvent.click(screen.getByRole('button', { name: 'Ver datas da série' }));
    await screen.findByText('Datas da série');
    return ctx;
  }

  const caixaData = (ddmm) => screen.getByRole('checkbox', { name: new RegExp(ddmm) });

  it('mostra a prévia, não deixa marcar conflito e reserva só as livres selecionadas', async () => {
    const { aoFechar } = await irParaPrevia();
    expect(previaRecorrencia).toHaveBeenCalledWith({ sala_id: 3, horario_ids: [1, 2], data_inicio: DATA });
    expect(criarReservaRecorrente).not.toHaveBeenCalled();
    expect(screen.getByText(/toda terça-feira, 07:30–09:10/)).toBeInTheDocument();

    expect(caixaData('12/03/2030')).toBeDisabled();
    expect(caixaData('12/03/2030')).not.toBeChecked();
    expect(screen.getByText(/Em conflito · 08:20–09:10 \(João Lima\)/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reservar só as livres selecionadas (3)' })).toBeEnabled();

    await userEvent.click(caixaData('26/03/2030')); // desmarca uma livre
    criarReservaRecorrente.mockResolvedValue({ grupo: { id: 14 }, reservas: [{}, {}] });
    await userEvent.click(screen.getByRole('button', { name: 'Reservar só as livres selecionadas (2)' }));

    expect(criarReservaRecorrente).toHaveBeenCalledWith({
      sala_id: 3,
      horario_ids: [1, 2],
      data_inicio: DATA,
      datas: ['2030-03-05', '2030-03-19'],
    });
    await waitFor(() => expect(aoFechar).toHaveBeenCalled());
  });

  it('desmarcar todas desabilita a confirmação; "marcar todas as livres" volta às livres', async () => {
    await irParaPrevia();
    await userEvent.click(screen.getByRole('button', { name: 'Desmarcar todas' }));
    expect(screen.getByRole('button', { name: /Reservar só as livres selecionadas \(0\)/ })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Marcar todas as livres' }));
    expect(screen.getByRole('button', { name: 'Reservar só as livres selecionadas (3)' })).toBeEnabled();
  });

  it('conflito surgido entre prévia e confirmação refaz a prévia mantendo a seleção ainda livre', async () => {
    await irParaPrevia();
    await userEvent.click(caixaData('26/03/2030'));
    criarReservaRecorrente.mockRejectedValue(new ErroApi({ status: 409, codigo: 'CONFLITO_RESERVA', detail: 'x', conflitos: [] }));
    const nova = {
      ...PREVIA,
      ocorrencias: PREVIA.ocorrencias.map((o) => (o.data === '2030-03-19' ? { ...o, livre: false, conflitos: [{ ...CONFLITO, data: o.data }] } : o)),
      livres: 2,
      em_conflito: 2,
    };
    previaRecorrencia.mockResolvedValue(nova);
    await userEvent.click(screen.getByRole('button', { name: 'Reservar só as livres selecionadas (2)' }));

    expect(await screen.findByText(/foram ocupadas enquanto você decidia/)).toBeInTheDocument();
    expect(previaRecorrencia).toHaveBeenCalledTimes(2);
    // 19/03 ficou ocupada e 26/03 continua desmarcada: só 05/03 segue selecionada
    expect(screen.getByRole('button', { name: 'Reservar só as livres selecionadas (1)' })).toBeEnabled();
    expect(caixaData('19/03/2030')).toBeDisabled();
  });

  it('sem semestre: explica o erro no formulário', async () => {
    abrir();
    await screen.findByText(/Aulas em/);
    await userEvent.click(screen.getByRole('checkbox', { name: /Repetir toda semana/ }));
    await userEvent.click(caixa('07:30–08:20'));
    previaRecorrencia.mockRejectedValue(
      new ErroApi({ status: 422, codigo: 'SEM_SEMESTRE', detail: 'Não há semestre letivo cadastrado que contenha a data inicial.' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Ver datas da série' }));
    expect(await screen.findByText('Não há semestre letivo para esta data')).toBeInTheDocument();
  });

  it('na recorrência uma aula ocupada na data inicial pode ser escolhida (a prévia mostra o conflito)', async () => {
    obterDisponibilidade.mockResolvedValue({ sala_id: 3, data: DATA, dia_semana: 2, aulas: [livre(M1), ocupada(M2)] });
    abrir();
    await screen.findByText(/Aulas em/);
    expect(caixa('08:20–09:10')).toBeDisabled();
    await userEvent.click(screen.getByRole('checkbox', { name: /Repetir toda semana/ }));
    expect(caixa('08:20–09:10')).toBeEnabled();
  });
});
