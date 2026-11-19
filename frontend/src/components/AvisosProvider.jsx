import { useCallback, useMemo, useState } from 'react';
import { AvisosContext } from './avisos';

let proximoId = 1;

export default function AvisosProvider({ children }) {
  const [avisos, setAvisos] = useState([]);

  const remover = useCallback((id) => setAvisos((lista) => lista.filter((a) => a.id !== id)), []);

  const avisar = useCallback(
    (texto, tipo = 'sucesso') => {
      const id = proximoId++;
      setAvisos((lista) => [...lista.slice(-3), { id, texto, tipo }]);
      setTimeout(() => remover(id), 6000);
    },
    [remover],
  );

  const valor = useMemo(() => ({ avisar }), [avisar]);

  return (
    <AvisosContext.Provider value={valor}>
      {children}
      <div className="avisos" aria-live="polite" aria-atomic="false">
        {avisos.map((a) => (
          <div key={a.id} className={`aviso aviso-${a.tipo}`} role="status">
            <span>{a.texto}</span>
            <button type="button" className="botao-icone" aria-label="Fechar aviso" onClick={() => remover(a.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </AvisosContext.Provider>
  );
}
