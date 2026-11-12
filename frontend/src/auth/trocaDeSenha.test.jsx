/* Ticket 46 (contrato 1.2, ADR-0008): token novo na troca de senha e redefinição da própria senha pelo admin.
   Usa a API simulada (src/api/mock) como transporte, com a revogação por versão do token. */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router';
import { definirToken, definirTransporte, obterToken, requisitar } from '../api/cliente';
import { fetchMock, reiniciarMock } from '../api/mock/servidor';
import AvisosProvider from '../components/AvisosProvider';
import AdminProfessores from '../pages/admin/AdminProfessores';
import Login from '../pages/Login';
import MinhaConta from '../pages/MinhaConta';
import { LocalAtual } from '../testes/render';
import { AuthProvider } from './AuthContext';
import RotaAdmin from './RotaAdmin';
import RotaProtegida from './RotaProtegida';

const CHAVE = 'sala_web.sessao';
const tokenSalvo = () => JSON.parse(localStorage.getItem(CHAVE))?.token ?? null;

async function entrarNoMock(rm, senha) {
  const r = await fetchMock('http://localhost:8000/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rm, senha }),
  });
  const { access_token, expira_em } = await r.json();
  localStorage.setItem(CHAVE, JSON.stringify({ token: access_token, expira_em }));
  return access_token;
}

function app(rota) {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <AuthProvider>
        <AvisosProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/agenda" element={<p>Agenda</p>} />
            <Route
              path="/minha-conta"
              element={
                <RotaProtegida>
                  <MinhaConta />
                </RotaProtegida>
              }
            />
            <Route
              path="/admin/professores"
              element={
                <RotaAdmin>
                  <AdminProfessores />
                </RotaAdmin>
              }
            />
          </Routes>
          <LocalAtual />
        </AvisosProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  reiniciarMock({ atraso: false });
  definirTransporte(fetchMock);
});
afterEach(() => {
  definirTransporte(null);
  definirToken(null);
});

it('trocar a própria senha mantém o usuário logado com o token novo; o antigo deixa de valer', async () => {
  const antigo = await entrarNoMock('123456', 'senha1234');
  app('/minha-conta');
  await screen.findByRole('heading', { name: 'Minha conta' });

  await userEvent.type(screen.getByLabelText('Senha atual'), 'senha1234');
  await userEvent.type(screen.getByLabelText('Nova senha'), 'novaSenha456');
  await userEvent.type(screen.getByLabelText('Confirmar nova senha'), 'novaSenha456');
  await userEvent.click(screen.getByRole('button', { name: 'Trocar senha' }));

  expect(await screen.findByText(/Senha alterada com sucesso. As outras sessões foram encerradas./)).toBeInTheDocument();
  const novo = tokenSalvo();
  expect(novo).toBeTruthy();
  expect(novo).not.toBe(antigo);
  expect(obterToken()).toBe(novo);

  // A navegação seguinte usa o token novo e não dá 401; o antigo é recusado.
  await expect(requisitar('GET', '/auth/me')).resolves.toMatchObject({ rm: '123456' });
  expect(screen.getByTestId('local')).toHaveTextContent('/minha-conta');
  const comAntigo = await fetchMock('http://localhost:8000/auth/me', { headers: { Authorization: `Bearer ${antigo}` } });
  expect(comAntigo.status).toBe(401);
});

it('admin que redefine a própria senha é avisado antes e acaba no login com a mensagem', async () => {
  await entrarNoMock('admin', 'admin1234');
  app('/admin/professores');
  const linha = (await screen.findByText('admin', { selector: 'code' })).closest('tr');
  await userEvent.click(within(linha).getByRole('button', { name: 'Redefinir senha' }));

  // Confirmação antes de abrir o formulário.
  const confirmacao = await screen.findByRole('dialog', { name: 'Redefinir a sua própria senha' });
  expect(within(confirmacao).getByText(/Sua sessão será encerrada/)).toBeInTheDocument();
  expect(within(confirmacao).getByRole('link', { name: 'Trocar minha senha' })).toHaveAttribute('href', '/minha-conta');
  await userEvent.click(within(confirmacao).getByRole('button', { name: 'Continuar mesmo assim' }));

  const form = await screen.findByRole('dialog', { name: 'Redefinir senha' });
  await userEvent.type(within(form).getByLabelText('Nova senha'), 'outraSenha789');
  await userEvent.click(within(form).getByRole('button', { name: 'Redefinir e sair' }));

  await waitFor(() => expect(screen.getByTestId('local')).toHaveTextContent('/login'));
  expect(screen.getByText('Senha redefinida. Entre novamente.')).toBeInTheDocument();
  expect(localStorage.getItem(CHAVE)).toBeNull();
  expect(obterToken()).toBeNull();
});

it('admin que desiste na confirmação não redefine nada', async () => {
  const token = await entrarNoMock('admin', 'admin1234');
  app('/admin/professores');
  const linha = (await screen.findByText('admin', { selector: 'code' })).closest('tr');
  await userEvent.click(within(linha).getByRole('button', { name: 'Redefinir senha' }));
  const confirmacao = await screen.findByRole('dialog', { name: 'Redefinir a sua própria senha' });
  await userEvent.click(within(confirmacao).getByRole('button', { name: 'Voltar' }));

  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(tokenSalvo()).toBe(token);
});

it('redefinir a senha de outro professor não pede confirmação nem encerra a sessão do admin', async () => {
  const token = await entrarNoMock('admin', 'admin1234');
  app('/admin/professores');
  const linha = (await screen.findByText('Maria Souza')).closest('tr');
  await userEvent.click(within(linha).getByRole('button', { name: 'Redefinir senha' }));
  const form = await screen.findByRole('dialog', { name: 'Redefinir senha' });
  expect(within(form).queryByText(/Sua sessão será encerrada/)).not.toBeInTheDocument();
  await userEvent.type(within(form).getByLabelText('Nova senha'), 'outraSenha789');
  await userEvent.click(within(form).getByRole('button', { name: 'Redefinir senha' }));

  expect(await screen.findByText('Senha de Maria Souza redefinida.')).toBeInTheDocument();
  expect(screen.getByTestId('local')).toHaveTextContent('/admin/professores');
  expect(tokenSalvo()).toBe(token);
});
