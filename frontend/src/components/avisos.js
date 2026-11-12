import { createContext, useContext } from 'react';

export const AvisosContext = createContext({ avisar: () => {} });

/** avisar(texto, tipo = 'sucesso'): mensagem temporária no canto da tela (aria-live). */
export const useAvisos = () => useContext(AvisosContext);
