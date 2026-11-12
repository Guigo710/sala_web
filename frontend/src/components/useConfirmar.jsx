import { useCallback, useState } from 'react';
import Modal from './Modal';

/**
 * Diálogo de confirmação baseado em Promise.
 * const [confirmar, dialogo] = useConfirmar();
 * if (await confirmar({ titulo, mensagem, textoConfirmar, perigo: true })) { ... }
 * Renderize `{dialogo}` no componente.
 */
export function useConfirmar() {
  const [pedido, setPedido] = useState(null);

  const confirmar = useCallback(
    (opcoes) => new Promise((resolver) => setPedido({ ...opcoes, resolver })),
    [],
  );

  const responder = (resultado) => {
    pedido?.resolver(resultado);
    setPedido(null);
  };

  const dialogo = (
    <Modal
      aberto={Boolean(pedido)}
      titulo={pedido?.titulo ?? 'Confirmar'}
      aoFechar={() => responder(false)}
      tamanho="pequeno"
      rodape={
        <>
          <button type="button" className="botao botao-secundario" onClick={() => responder(false)}>
            {pedido?.textoCancelar ?? 'Voltar'}
          </button>
          <button
            type="button"
            className={pedido?.perigo ? 'botao botao-perigo' : 'botao'}
            onClick={() => responder(true)}
            data-autofocus
          >
            {pedido?.textoConfirmar ?? 'Confirmar'}
          </button>
        </>
      }
    >
      {typeof pedido?.mensagem === 'string' ? <p>{pedido.mensagem}</p> : pedido?.mensagem}
    </Modal>
  );

  return [confirmar, dialogo];
}
