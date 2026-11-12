import { api } from './cliente';

/** GET /salas/tipos (§4.3) → [{ valor, rotulo }] */
export const listarTipos = () => api.get('/salas/tipos');

/**
 * GET /salas → SalaResumo[]
 * @param {{tipo?: string[], capacidade_min?: number, equipamento_id?: number[], software_id?: number[],
 *   busca?: string, data?: string, horario_ids?: number[], incluir_inativas?: boolean}} [filtros]
 */
export const listarSalas = (filtros = {}) => api.get('/salas', filtros);

/** GET /salas/{id} → SalaDetalhe */
export const obterSala = (id) => api.get(`/salas/${id}`);

/** GET /salas/{id}/disponibilidade?data= */
export const obterDisponibilidade = (id, data) => api.get(`/salas/${id}/disponibilidade`, { data });

/** POST /salas (admin) → SalaDetalhe */
export const criarSala = (dados) => api.post('/salas', dados);

/** PUT /salas/{id} (admin) → SalaDetalhe */
export const atualizarSala = (id, dados) => api.put(`/salas/${id}`, dados);

/** DELETE /salas/{id} (admin) → 204 */
export const excluirSala = (id) => api.delete(`/salas/${id}`);

/** PUT /salas/{id}/equipamentos (admin): substitui a lista → SalaDetalhe */
export const definirEquipamentosSala = (id, itens) => api.put(`/salas/${id}/equipamentos`, itens);

/** PUT /salas/{id}/softwares (admin): substitui a lista → SalaDetalhe */
export const definirSoftwaresSala = (id, softwareIds) =>
  api.put(`/salas/${id}/softwares`, { software_ids: softwareIds });
