import { api } from './cliente';

/** GET /professores (§4.7, admin) → Usuario[] */
export const listarProfessores = ({ busca, papel, ativo } = {}) =>
  api.get('/professores', { busca, papel, ativo });
export const obterProfessor = (id) => api.get(`/professores/${id}`);
/** @param {{rm, nome, email, senha, papel}} dados */
export const criarProfessor = (dados) => api.post('/professores', dados);
/** @param {{nome, email, papel, ativo}} dados (RM não é editável) */
export const atualizarProfessor = (id, dados) => api.put(`/professores/${id}`, dados);
export const redefinirSenhaProfessor = (id, novaSenha) =>
  api.put(`/professores/${id}/senha`, { nova_senha: novaSenha });
export const excluirProfessor = (id) => api.delete(`/professores/${id}`);
