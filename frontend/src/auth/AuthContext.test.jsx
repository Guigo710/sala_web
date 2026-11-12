import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { definirToken, definirTransporte, obterToken, requisitar } from '../api/cliente';
import Login from '../pages/Login';
import { LocalAtual } from '../testes/render';
import { AuthProvider } from './AuthContext';
import { useAuth } from './contexto';
import RotaProtegida from './RotaProtegida';

const CHAVE = 'sala_web.sessao';
const USUARIO = { id: 7, rm: '123456', nome: 'Maria Souza', email: null, papel: 'professor', ativo: true };

const json = (status, corpo) =>
  Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { 'Content-Type': 'application/json' } }));

/** Transporte falso: `rotas['METODO /caminho']` → função (init) que devolve a resposta. */
function servidor(rotas) {
  const chamadas = [];
  definirTransporte((url, init) => {
    const caminho = new URL(url).pathname;
    const chave = `${init.method} ${caminho}`;
    chamadas.push({ chave, init });
    const tratar = rotas[chave];
    return tratar ? tratar(init) : json(404, { detail: 'Não encontrado.', codigo: 'NAO_ENCONTRADO' });
  });
  return chamadas;
}

function Painel() {
  const { usuario } = useAuth();
  return <p>Olá, {usuario.nome}</p>;
}

function app(rota) {
  return render(
    <MemoryRouter initialEntries={[rota]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/agenda" element={<p>Agenda</p>} />
          <Route
            path="/minhas-reservas"
            element={
              <RotaProtegida>
                <Painel />
              </RotaProtegida>
            }
          />
        </Routes>
        <LocalAtual />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());
afterEach(() => {
  definirTransporte(null);
  definirToken(null);
});

describe('Login', () => {
  it('entra com RM e senha, guarda a sessão e volta para onde estava', async () => {
    const chamadas = servidor({
      'POST /auth/login': () =>
        json(200, { access_token: 'tok-123', token_type: 'bearer', expira_em: '2999-01-01T00:00:00-03:00', usuario: USUARIO }),
    });
    app('/minhas-reservas');
    await screen.findByRole('heading', { name: 'Entrar' });
    await userEvent.type(screen.getByLabelText('RM'), '  123456 ');
    await userEvent.type(screen.getByLabelText('Senha'), 'senha1234');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByText('Olá, Maria Souza')).toBeInTheDocument();
    expect(screen.getByTestId('local')).toHaveTextContent('/minhas-reservas');
    expect(JSON.parse(chamadas[0].init.body)).toEqual({ rm: '123456', senha: 'senha1234' });
    expect(JSON.parse(localStorage.getItem(CHAVE)).token).toBe('tok-123');
    expect(obterToken()).toBe('tok-123');
  });

  it('mostra a mensagem da API quando as credenciais são inválidas, sem guardar sessão', async () => {
    servidor({ 'POST /auth/login': () => json(401, { detail: 'RM ou senha inválidos.', codigo: 'CREDENCIAIS_INVALIDAS' }) });
    app('/login');
    await userEvent.type(screen.getByLabelText('RM'), '123456');
    await userEvent.type(screen.getByLabelText('Senha'), 'errada');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByText('RM ou senha inválidos.')).toBeInTheDocument();
    expect(localStorage.getItem(CHAVE)).toBeNull();
    expect(screen.getByTestId('local')).toHaveTextContent('/login');
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled();
  });

  it('mostra o bloqueio por muitas tentativas (429)', async () => {
    servidor({
      'POST /auth/login': () =>
        json(429, { detail: 'Muitas tentativas de login. Aguarde 5 minutos e tente novamente.', codigo: 'MUITAS_TENTATIVAS' }),
    });
    app('/login');
    await userEvent.type(screen.getByLabelText('RM'), '123456');
    await userEvent.type(screen.getByLabelText('Senha'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByText('Muitas tentativas')).toBeInTheDocument();
    expect(screen.getByText(/Aguarde 5 minutos/)).toBeInTheDocument();
  });
});

describe('sessão', () => {
  it('restaura a sessão do localStorage com GET /auth/me (Bearer)', async () => {
    localStorage.setItem(CHAVE, JSON.stringify({ token: 'salvo', expira_em: '2999-01-01T00:00:00Z' }));
    const chamadas = servidor({ 'GET /auth/me': () => json(200, USUARIO) });
    app('/minhas-reservas');
    expect(await screen.findByText('Olá, Maria Souza')).toBeInTheDocument();
    expect(chamadas[0].init.headers.Authorization).toBe('Bearer salvo');
  });

  it('token salvo e já vencido nem é enviado: vai para o login', async () => {
    localStorage.setItem(CHAVE, JSON.stringify({ token: 'velho', expira_em: '2000-01-01T00:00:00Z' }));
    const chamadas = servidor({});
    app('/minhas-reservas');
    await waitFor(() => expect(screen.getByTestId('local')).toHaveTextContent('/login'));
    expect(chamadas).toHaveLength(0);
    expect(localStorage.getItem(CHAVE)).toBeNull();
  });

  it('401 numa rota protegida limpa a sessão e leva ao login com aviso', async () => {
    localStorage.setItem(CHAVE, JSON.stringify({ token: 'tok', expira_em: '2999-01-01T00:00:00Z' }));
    servidor({
      'GET /auth/me': () => json(200, USUARIO),
      'GET /reservas/minhas': () => json(401, { detail: 'Faça login para continuar.', codigo: 'NAO_AUTENTICADO' }),
    });
    app('/minhas-reservas');
    await screen.findByText('Olá, Maria Souza');

    await act(async () => {
      await requisitar('GET', '/reservas/minhas').catch(() => {});
    });
    await waitFor(() => expect(screen.getByTestId('local')).toHaveTextContent('/login'));
    expect(localStorage.getItem(CHAVE)).toBeNull();
    expect(obterToken()).toBeNull();
    expect(screen.getByText('Sua sessão expirou. Entre novamente.')).toBeInTheDocument();
  });

  it('token recusado na verificação inicial só limpa a sessão (sem aviso de expiração)', async () => {
    localStorage.setItem(CHAVE, JSON.stringify({ token: 'revogado', expira_em: '2999-01-01T00:00:00Z' }));
    servidor({ 'GET /auth/me': () => json(401, { detail: 'Faça login para continuar.', codigo: 'NAO_AUTENTICADO' }) });
    app('/agenda');
    await waitFor(() => expect(localStorage.getItem(CHAVE)).toBeNull());
    expect(screen.getByText('Agenda')).toBeInTheDocument();
    expect(screen.queryByText('Sua sessão expirou. Entre novamente.')).not.toBeInTheDocument();
  });
});
