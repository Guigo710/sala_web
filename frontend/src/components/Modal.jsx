import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';

const SELETOR_FOCAVEIS =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

let abertos = 0;

/**
 * Diálogo modal acessível: role="dialog", foco preso dentro, Esc fecha, foco volta ao elemento de origem.
 * Elemento com `data-autofocus` recebe o foco inicial.
 */
export default function Modal({ aberto, titulo, aoFechar, children, rodape, tamanho = 'medio' }) {
  const ref = useRef(null);
  const aoFecharRef = useRef(aoFechar);
  const idTitulo = useId();

  useEffect(() => {
    aoFecharRef.current = aoFechar;
  }, [aoFechar]);

  useEffect(() => {
    if (!aberto) return undefined;
    const anterior = document.activeElement;
    const el = ref.current;
    const focaveis = () => [...el.querySelectorAll(SELETOR_FOCAVEIS)];
    (el.querySelector('[data-autofocus]') || el).focus();
    abertos += 1;
    document.body.classList.add('com-modal');

    const aoTeclar = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        aoFecharRef.current?.();
        return;
      }
      if (e.key !== 'Tab') return;
      const lista = focaveis();
      if (lista.length === 0) {
        e.preventDefault();
        return;
      }
      const primeiro = lista[0];
      const ultimo = lista[lista.length - 1];
      if (e.shiftKey && (document.activeElement === primeiro || document.activeElement === el)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primeiro.focus();
      }
    };
    el.addEventListener('keydown', aoTeclar);
    return () => {
      el.removeEventListener('keydown', aoTeclar);
      abertos -= 1;
      if (abertos <= 0) {
        abertos = 0;
        document.body.classList.remove('com-modal');
      }
      if (anterior && typeof anterior.focus === 'function') anterior.focus();
    };
  }, [aberto]);

  if (!aberto) return null;

  return createPortal(
    <div
      className="modal-fundo"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) aoFechar?.();
      }}
    >
      <div
        className={`modal modal-${tamanho}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        ref={ref}
        tabIndex={-1}
      >
        <header className="modal-cabecalho">
          <h2 id={idTitulo}>{titulo}</h2>
          <button type="button" className="botao-icone" aria-label="Fechar" onClick={aoFechar}>
            ×
          </button>
        </header>
        <div className="modal-corpo">{children}</div>
        {rodape && <footer className="modal-rodape">{rodape}</footer>}
      </div>
    </div>,
    document.body,
  );
}
