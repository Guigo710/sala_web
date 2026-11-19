import { api, enviarFormulario } from './cliente';

/** GET /salas/{id}/fotos (§4.4) → Foto[] */
export const listarFotos = (salaId) => api.get(`/salas/${salaId}/fotos`);

/**
 * POST /salas/{id}/fotos (admin, multipart): uma foto por requisição → Foto
 * @param {(fracao: number) => void} [aoProgresso]
 */
export function enviarFoto(salaId, arquivo, legenda, aoProgresso) {
  const form = new FormData();
  form.append('arquivo', arquivo);
  if (legenda) form.append('legenda', legenda);
  return enviarFormulario(`/salas/${salaId}/fotos`, form, aoProgresso);
}

/** PATCH /salas/{id}/fotos/{foto_id} (admin) → Foto */
export const atualizarLegendaFoto = (salaId, fotoId, legenda) =>
  api.patch(`/salas/${salaId}/fotos/${fotoId}`, { legenda });

/** DELETE /salas/{id}/fotos/{foto_id} (admin) → 204 */
export const excluirFoto = (salaId, fotoId) => api.delete(`/salas/${salaId}/fotos/${fotoId}`);

/** PUT /salas/{id}/fotos/ordem (admin) → Foto[] */
export const reordenarFotos = (salaId, fotoIds) =>
  api.put(`/salas/${salaId}/fotos/ordem`, { foto_ids: fotoIds });
