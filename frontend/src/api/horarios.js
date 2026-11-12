import { api } from './cliente';

/** GET /horarios (§4.8) → HorarioAula[] por turno e ordem */
export const listarHorarios = ({ dia_semana, turno, incluir_inativos } = {}) =>
  api.get('/horarios', { dia_semana, turno, incluir_inativos });
export const obterHorario = (id) => api.get(`/horarios/${id}`);
/** @param {{turno, ordem, inicio, fim, dias_semana: number[], ativo}} dados */
export const criarHorario = (dados) => api.post('/horarios', dados);
export const atualizarHorario = (id, dados) => api.put(`/horarios/${id}`, dados);
export const excluirHorario = (id) => api.delete(`/horarios/${id}`);
