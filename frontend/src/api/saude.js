import { api } from './cliente';

/** GET /saude (§4.1) */
export const verificarSaude = () => api.get('/saude');

let acordando = null;

/**
 * Acorda a API assim que o app abre (ticket 66, ADR-0009): dispara um `GET /saude` sem esperar a resposta,
 * para a API do Render começar a acordar enquanto a pessoa olha a tela inicial ou digita o login.
 * Só dispara uma vez por carregamento da página; erros são ignorados (as telas mostram os seus).
 */
export function acordarApi() {
  if (!acordando) acordando = verificarSaude().catch(() => null);
}

/** Só para testes: permite disparar de novo. */
export function reiniciarAcordarApi() {
  acordando = null;
}
