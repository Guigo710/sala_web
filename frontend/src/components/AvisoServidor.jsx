import { useSyncExternalStore } from 'react';
import { assinarLentidao, haLentidao } from '../api/lentidao';

/**
 * Aviso discreto de "servidor acordando" (ticket 66): aparece enquanto alguma requisição à API passa de ~4 s
 * ou está sendo repetida, e some sozinho. A região `role="status"` fica sempre no DOM para o leitor de tela
 * anunciar o texto quando ele surgir.
 */
export default function AvisoServidor() {
  const lento = useSyncExternalStore(assinarLentidao, haLentidao, haLentidao);
  return (
    <div className={lento ? 'aviso-servidor visivel' : 'aviso-servidor'} role="status" aria-live="polite">
      {lento && (
        <>
          <span className="aviso-servidor-icone" aria-hidden="true" />
          <span>O servidor está acordando. Isso pode levar até 1 minuto na primeira visita.</span>
        </>
      )}
    </div>
  );
}
