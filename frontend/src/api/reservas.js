import { api } from './cliente';

/**
 * POST /reservas (§4.10): reserva avulsa → Reserva
 * @param {{sala_id: number, data: string, horario_ids: number[], observacao?: string, professor_id?: number}} dados
 */
export const criarReserva = (dados) => api.post('/reservas', dados);

/** POST /reservas/recorrentes/previa: não grava nada */
export const previaRecorrencia = (dados) => api.post('/reservas/recorrentes/previa', dados);

/** POST /reservas/recorrentes → { grupo, reservas } */
export const criarReservaRecorrente = (dados) => api.post('/reservas/recorrentes', dados);

/**
 * GET /reservas (agenda pública). Exatamente um modo de período: `mes`, `data` ou `de`+`ate`.
 * @param {{mes?: string, data?: string, de?: string, ate?: string, sala_id?: number[]|number,
 *   professor_id?: number, status?: 'ativa'|'cancelada'|'todas'}} params
 */
export const listarReservas = (params) => api.get('/reservas', params);

/** GET /reservas/minhas */
export const listarMinhasReservas = ({ periodo, status } = {}) =>
  api.get('/reservas/minhas', { periodo, status });

export const obterReserva = (id) => api.get(`/reservas/${id}`);

/** GET /reservas/grupos/{grupo_id} → { grupo, reservas } */
export const obterGrupoRecorrencia = (grupoId) => api.get(`/reservas/grupos/${grupoId}`);

/** POST /reservas/{id}/cancelar → Reserva */
export const cancelarReserva = (id, motivo) =>
  api.post(`/reservas/${id}/cancelar`, motivo ? { motivo } : {});

/** POST /reservas/grupos/{grupo_id}/cancelar → { grupo_recorrencia_id, canceladas, reservas_ids } */
export const cancelarGrupoRecorrencia = (grupoId, motivo) =>
  api.post(`/reservas/grupos/${grupoId}/cancelar`, motivo ? { motivo } : {});
