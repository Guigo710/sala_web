import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErroApi } from '../../api/cliente';
import { enviarFoto } from '../../api/fotos';
import { ADMIN, renderizar } from '../../testes/render';
import EditorFotos from './EditorFotos';

vi.mock('../../api/fotos', () => ({
  enviarFoto: vi.fn(),
  atualizarLegendaFoto: vi.fn(),
  excluirFoto: vi.fn(),
  reordenarFotos: vi.fn(),
}));

const MB = 1024 * 1024;
const arquivo = (nome, tipo, tamanho) => {
  const f = new File(['x'], nome, { type: tipo });
  Object.defineProperty(f, 'size', { value: tamanho });
  return f;
};

it('recusa no navegador foto grande demais ou GIF, por arquivo, e envia só as válidas', async () => {
  enviarFoto.mockResolvedValue({ id: 50, sala_id: 3, url: '/uploads/salas/3/x.jpg', legenda: null, ordem: 1 });
  // applyAccept: false simula o usuário escolhendo "todos os arquivos" no diálogo do sistema.
  const usuario = userEvent.setup({ applyAccept: false });
  renderizar(<EditorFotos sala={{ id: 3, fotos: [] }} />, { usuario: ADMIN });

  const valida = arquivo('sala.jpg', 'image/jpeg', 1 * MB);
  await usuario.upload(screen.getByLabelText('Enviar fotos…'), [
    arquivo('enorme.jpg', 'image/jpeg', 6 * MB),
    arquivo('animacao.gif', 'image/gif', 100),
    valida,
  ]);

  await waitFor(() => expect(enviarFoto).toHaveBeenCalledTimes(1));
  expect(enviarFoto.mock.calls[0][1]).toBe(valida);

  const itens = screen.getAllByRole('listitem');
  const item = (nome) => itens.find((li) => within(li).queryByText(nome));
  expect(within(item('enorme.jpg')).getByText(/413: A foto passa do limite de 5 MB/)).toBeInTheDocument();
  expect(within(item('animacao.gif')).getByText(/415: Envie uma imagem JPEG, PNG ou WebP/)).toBeInTheDocument();
  expect(await within(item('sala.jpg')).findByText('Enviada')).toBeInTheDocument();
});

it('explica a redução para 1600 px, o JPEG e a remoção do GPS (ADR-0010)', () => {
  renderizar(<EditorFotos sala={{ id: 3, fotos: [] }} />, { usuario: ADMIN });
  expect(screen.getByText(/até 5 MB cada/)).toHaveTextContent(/reduzidas para até 1600 px.*salvas em JPEG.*localização \(GPS\).*removidos/);
});

it('foto cujo arquivo se perdeu (404) vira substituto que sugere remover', () => {
  const sala = { id: 3, fotos: [{ id: 9, sala_id: 3, url: '/uploads/salas/3/perdida.jpg', legenda: 'Bancada', ordem: 1 }] };
  renderizar(<EditorFotos sala={sala} />, { usuario: ADMIN });
  fireEvent.error(screen.getByRole('img', { name: 'Bancada' }));
  expect(screen.getByRole('img', { name: /^Bancada\. Foto indisponível: o arquivo não foi encontrado\. Você pode remover esta foto\.$/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Remover foto 1' })).toBeEnabled();
});

it('413 por resolução (acima de 40 megapixels) mostra o detail da API', async () => {
  enviarFoto.mockReset();
  enviarFoto.mockRejectedValue(
    new ErroApi({ status: 413, codigo: 'ARQUIVO_GRANDE', detail: 'A imagem passa de 40 megapixels.' }),
  );
  const usuario = userEvent.setup();
  renderizar(<EditorFotos sala={{ id: 3, fotos: [] }} />, { usuario: ADMIN });
  await usuario.upload(screen.getByLabelText('Enviar fotos…'), arquivo('panorama.jpg', 'image/jpeg', 2 * MB));
  expect(await screen.findByText('413: A imagem passa de 40 megapixels.')).toBeInTheDocument();
});
