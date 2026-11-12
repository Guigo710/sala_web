import { api } from './cliente';

/** POST /auth/login (§4.2) → { access_token, token_type, expira_em, usuario } */
export const login = (rm, senha) => api.post('/auth/login', { rm, senha });

/** GET /auth/me → Usuario */
export const obterUsuarioAtual = () => api.get('/auth/me');

/** PUT /auth/me/senha → 204 */
export const trocarSenha = (senhaAtual, novaSenha) =>
  api.put('/auth/me/senha', { senha_atual: senhaAtual, nova_senha: novaSenha });
