import { api } from './cliente';

/** GET /equipamentos (§4.5) → Equipamento[] */
export const listarEquipamentos = (busca) => api.get('/equipamentos', { busca });
export const obterEquipamento = (id) => api.get(`/equipamentos/${id}`);
/** @param {{nome: string, descricao: string|null}} dados */
export const criarEquipamento = (dados) => api.post('/equipamentos', dados);
export const atualizarEquipamento = (id, dados) => api.put(`/equipamentos/${id}`, dados);
export const excluirEquipamento = (id) => api.delete(`/equipamentos/${id}`);
