import { api } from './cliente';

/** GET /semestres (§4.9) → Semestre[] (data_inicio desc) */
export const listarSemestres = () => api.get('/semestres');
/** GET /semestres/atual → Semestre (404 se não houver) */
export const obterSemestreAtual = () => api.get('/semestres/atual');
export const obterSemestre = (id) => api.get(`/semestres/${id}`);
/** @param {{nome, data_inicio, data_fim}} dados */
export const criarSemestre = (dados) => api.post('/semestres', dados);
export const atualizarSemestre = (id, dados) => api.put(`/semestres/${id}`, dados);
export const excluirSemestre = (id) => api.delete(`/semestres/${id}`);
