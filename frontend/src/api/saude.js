import { api } from './cliente';

/** GET /saude (§4.1) */
export const verificarSaude = () => api.get('/saude');
