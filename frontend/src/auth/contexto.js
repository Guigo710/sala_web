import { createContext, useContext } from 'react';

export const AuthContext = createContext(null);

/** { usuario, carregando, ehAdmin, entrar, sair, saiu, mensagemSessao, trocarSenha, encerrarSessao } */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth precisa estar dentro de <AuthProvider>.');
  return ctx;
}
