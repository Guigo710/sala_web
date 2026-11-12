import { useEffect, useState } from 'react';
import { urlArquivo } from '../api/cliente';
import Modal from './Modal';

/** Galeria de fotos (§3.5): miniaturas + visualização ampliada (setas, Esc). */
export default function Galeria({ fotos, nomeSala }) {
  const [indice, setIndice] = useState(0);
  const [ampliada, setAmpliada] = useState(false);
  const total = fotos.length;
  const atual = fotos[Math.min(indice, total - 1)];
  const textoAlt = (foto, i) => foto.legenda || `${nomeSala}: foto ${i + 1} de ${total}`;

  const anterior = () => setIndice((i) => (i - 1 + total) % total);
  const proxima = () => setIndice((i) => (i + 1) % total);

  useEffect(() => {
    if (!ampliada) return undefined;
    const aoTeclar = (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        setIndice((i) => (i - 1 + total) % total);
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        setIndice((i) => (i + 1) % total);
      }
    };
    document.addEventListener('keydown', aoTeclar);
    return () => document.removeEventListener('keydown', aoTeclar);
  }, [ampliada, total]);

  if (total === 0) {
    return (
      <div className="galeria galeria-vazia">
        <p>Este ambiente ainda não tem fotos.</p>
      </div>
    );
  }

  return (
    <div className="galeria">
      <figure className="galeria-principal">
        <button
          type="button"
          className="galeria-ampliar"
          onClick={() => setAmpliada(true)}
          aria-label={`Ampliar foto: ${textoAlt(atual, indice)}`}
        >
          <img src={urlArquivo(atual.url)} alt={textoAlt(atual, indice)} />
        </button>
        {atual.legenda && <figcaption>{atual.legenda}</figcaption>}
      </figure>

      {total > 1 && (
        <ul className="galeria-miniaturas" aria-label="Miniaturas">
          {fotos.map((foto, i) => (
            <li key={foto.id}>
              <button
                type="button"
                className={i === indice ? 'miniatura ativa' : 'miniatura'}
                onClick={() => setIndice(i)}
                aria-label={`Ver foto ${i + 1}${foto.legenda ? `: ${foto.legenda}` : ''}`}
                aria-current={i === indice ? 'true' : undefined}
              >
                <img src={urlArquivo(foto.url)} alt="" loading="lazy" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <Modal aberto={ampliada} titulo={`${nomeSala} · foto ${indice + 1} de ${total}`} aoFechar={() => setAmpliada(false)} tamanho="galeria">
        <figure className="galeria-ampliada">
          <img src={urlArquivo(atual.url)} alt={textoAlt(atual, indice)} />
          {atual.legenda && <figcaption>{atual.legenda}</figcaption>}
        </figure>
        {total > 1 && (
          <div className="galeria-navegacao">
            <button type="button" className="botao botao-secundario" onClick={anterior} aria-label="Foto anterior">
              ← Anterior
            </button>
            <span className="texto-suave">Use as setas do teclado · Esc fecha</span>
            <button type="button" className="botao botao-secundario" onClick={proxima} aria-label="Próxima foto" data-autofocus>
              Próxima →
            </button>
          </div>
        )}
      </Modal>
    </div>
  );
}
