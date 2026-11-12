import { api } from './cliente';

/** POST /auth/login (§4.2) → { access_token, token_type, expira_em, usuario } */
export const login = (rm, senha) => api.post('/auth/login', { rm, senha });

/** GET /auth/me → Usuario */
export const obterUsuarioAtual = () => api.get('/auth/me');

/**
 * PUT /auth/me/senha (contrato 1.2) → 200 com o corpo do login (`access_token`, `expira_em`, `usuario`).
 * O token usado na requisição deixa de valer: grave o novo (ver AuthContext.trocarSenha).
 */
export const trocarSenha = (senhaAtual, novaSenha) =>
  api.put('/auth/me/senha', { senha_atual: senhaAtual, nova_senha: novaSenha });
