import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErroApi } from '../api/cliente';
import {
  cancelarGrupoRecorrencia,
  cancelarReserva,
  listarMinhasReservas,
  obterGrupoRecorrencia,
} from '../api/reservas';
import { renderizar } from '../testes/render';
import MinhasReservas from './MinhasReservas';

vi.mock('../api/reservas', () => ({
  listarMinhasReservas: vi.fn(),
  cancelarReserva: vi.fn(),
  cancelarGrupoRecorrencia: vi.fn(),
  obterGrupoRecorrencia: vi.fn(),
}));

const reserva = (extra) => ({
  id: 101,
  sala: { id: 3, nome: 'Laboratório 03', tipo: 'lab_informatica' },
  professor: { id: 7, nome: 'Maria Souza' },
  data: '2030-03-05',
  inicio: '07:30',
  fim: '09:10',
  horario_inicio_id: 1,
  horario_fim_id: 2,
  quantidade_aulas: 2,
  status: 'ativa',
  observacao: null,
  grupo_recorrencia_id: null,
  criado_em: '2030-03-01T10:00:00-03:00',
  cancelada_em: null,
  cancelada_por: null,
  motivo_cancelamento: null,
  pode_cancelar: true,
  ...extra,
});

const AVULSA = reserva({});
const SEMANAL = reserva({ id: 120, data: '2030-03-12', grupo_recorrencia_id: 14 });
const INICIADA = reserva({ id: 130, data: '2030-03-04', pode_cancelar: false });

beforeEach(() => {
  vi.clearAllMocks();
  listarMinhasReservas.mockResolvedValue([AVULSA, SEMANAL, INICIADA]);
});

const item = (texto) => screen.getByText(texto).closest('li.reserva-item');

describe('Minhas reservas', () => {
  it('lista futuras ativas e só oferece cancelar onde a API permite', async () => {
    renderizar(<MinhasReservas />, { rota: '/minhas-reservas' });
    await screen.findByText(/05\/03\/2030/);
    expect(listarMinhasReservas).toHaveBeenCalledWith({ periodo: 'futuras', status: 'ativa' });
    expect(within(item(/05\/03\/2030/)).getByRole('button', { name: 'Cancelar' })).toBeInTheDocument();
    expect(within(item(/04\/03\/2030/)).queryByRole('button', { name: 'Cancelar' })).not.toBeInTheDocument();
    expect(within(item(/12\/03\/2030/)).getByText('↻ Semanal')).toBeInTheDocument();
  });

  it('cancela uma reserva com motivo e recarrega a lista', async () => {
    renderizar(<MinhasReservas />, { rota: '/minhas-reservas' });
    await screen.findByText(/05\/03\/2030/);
    await userEvent.click(within(item(/05\/03\/2030/)).getByRole('button', { name: 'Cancelar' }));
    const dialogo = screen.getByRole('dialog', { name: 'Cancelar reserva' });
    expect(dialogo).toHaveTextContent('Laboratório 03');
    await userEvent.type(within(dialogo).getByLabelText('Motivo (opcional)'), 'Aula remanejada');
    cancelarReserva.mockResolvedValue({ ...AVULSA, status: 'cancelada' });
    listarMinhasReservas.mockResolvedValue([SEMANAL]);
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar reserva' }));

    expect(cancelarReserva).toHaveBeenCalledWith(101, 'Aula remanejada');
    expect(await screen.findByText('Reserva cancelada.')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/05\/03\/2030/)).not.toBeInTheDocument());
    expect(listarMinhasReservas).toHaveBeenCalledTimes(2);
  });

  it('erro RESERVA_JA_INICIADA aparece no diálogo e atualiza a lista', async () => {
    renderizar(<MinhasReservas />, { rota: '/minhas-reservas' });
    await screen.findByText(/05\/03\/2030/);
    await userEvent.click(within(item(/05\/03\/2030/)).getByRole('button', { name: 'Cancelar' }));
    cancelarReserva.mockRejectedValue(
      new ErroApi({ status: 422, codigo: 'RESERVA_JA_INICIADA', detail: 'A aula já começou; não é mais possível cancelar.' }),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar reserva' }));
    expect(await screen.findByText('A aula já começou; não é mais possível cancelar.')).toBeInTheDocument();
    await waitFor(() => expect(listarMinhasReservas).toHaveBeenCalledTimes(2));
  });

  it('cancela todas as próximas ocorrências de uma recorrência', async () => {
    obterGrupoRecorrencia.mockResolvedValue({
      grupo: { id: 14 },
      reservas: [
        reserva({ id: 119, data: '2020-03-05', grupo_recorrencia_id: 14 }),
        SEMANAL,
        reserva({ id: 121, data: '2030-03-19', grupo_recorrencia_id: 14 }),
      ],
    });
    renderizar(<MinhasReservas />, { rota: '/minhas-reservas' });
    await screen.findByText(/12\/03\/2030/);
    await userEvent.click(within(item(/12\/03\/2030/)).getByRole('button', { name: 'Cancelar todas as próximas desta recorrência' }));
    const dialogo = screen.getByRole('dialog', { name: 'Cancelar recorrência' });
    expect(await within(dialogo).findByText(/Serão canceladas 2 reservas/)).toBeInTheDocument();
    cancelarGrupoRecorrencia.mockResolvedValue({ grupo_recorrencia_id: 14, canceladas: 2, reservas_ids: [120, 121] });
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar todas as próximas' }));
    expect(cancelarGrupoRecorrencia).toHaveBeenCalledWith(14, undefined);
    expect(await screen.findByText('2 reservas canceladas nesta recorrência.')).toBeInTheDocument();
  });

  it('troca de aba e de situação vira parâmetro da consulta', async () => {
    renderizar(<MinhasReservas />, { rota: '/minhas-reservas' });
    await screen.findByText(/05\/03\/2030/);
    await userEvent.click(screen.getByRole('tab', { name: 'Passadas' }));
    await waitFor(() => expect(listarMinhasReservas).toHaveBeenLastCalledWith({ periodo: 'passadas', status: 'ativa' }));
    await userEvent.selectOptions(screen.getByLabelText('Situação'), 'cancelada');
    await waitFor(() => expect(listarMinhasReservas).toHaveBeenLastCalledWith({ periodo: 'passadas', status: 'cancelada' }));
  });
});
