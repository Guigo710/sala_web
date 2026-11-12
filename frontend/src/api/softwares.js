import { api } from './cliente';

/** GET /softwares (§4.6) → Software[] */
export const listarSoftwares = ({ busca, categoria } = {}) => api.get('/softwares', { busca, categoria });
/** GET /softwares/categorias → string[] */
export const listarCategoriasSoftware = () => api.get('/softwares/categorias');
export const obterSoftware = (id) => api.get(`/softwares/${id}`);
/** @param {{nome: string, versao: string|null, categoria: string|null}} dados */
export const criarSoftware = (dados) => api.post('/softwares', dados);
export const atualizarSoftware = (id, dados) => api.put(`/softwares/${id}`, dados);
export const excluirSoftware = (id) => api.delete(`/softwares/${id}`);
