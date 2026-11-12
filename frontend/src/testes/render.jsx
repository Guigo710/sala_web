/* Renderização com os provedores do app (rotas, sessão e avisos) para testes de componentes. */
import { render } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router';
import { AuthContext } from '../auth/contexto';
import AvisosProvider from '../components/AvisosProvider';

export const PROFESSOR = { id: 7, rm: '123456', nome: 'Maria Souza', email: null, papel: 'professor', ativo: true };
export const ADMIN = { id: 1, rm: 'admin', nome: 'Administrador', email: null, papel: 'admin', ativo: true };

export function authFalso(usuario = PROFESSOR, extra = {}) {
  return {
    usuario,
    carregando: false,
    ehAdmin: usuario?.papel === 'admin',
    entrar: vi.fn(),
    sair: vi.fn(),
    saiu: false,
    mensagemSessao: '',
    trocarSenha: vi.fn(),
    encerrarSessao: vi.fn(),
    ...extra,
  };
}

/** Mostra o caminho atual (para conferir redirecionamentos). */
export function LocalAtual() {
  const { pathname } = useLocation();
  return <output data-testid="local">{pathname}</output>;
}

export function renderizar(ui, { usuario = PROFESSOR, auth, rota = '/', caminho = '*' } = {}) {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <AuthContext.Provider value={auth || authFalso(usuario)}>
        <AvisosProvider>
          <Routes>
            <Route path={caminho} element={ui} />
          </Routes>
          <LocalAtual />
        </AvisosProvider>
      </AuthContext.Provider>
    </MemoryRouter>,
  );
}
