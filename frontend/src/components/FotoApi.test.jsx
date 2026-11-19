import { fireEvent, render, screen } from '@testing-library/react';
import FotoApi from './FotoApi';
import Galeria from './Galeria';

describe('FotoApi (ticket 67)', () => {
  it('imagem que dispara error mostra o substituto, uma vez só, mantendo o alt', () => {
    const { container, rerender } = render(<FotoApi src="http://api/uploads/salas/3/a.jpg" alt="Lab 1: vista da porta" />);
    const img = screen.getByRole('img', { name: 'Lab 1: vista da porta' });
    expect(img.tagName).toBe('IMG');

    fireEvent.error(img);
    const substituto = screen.getByRole('img', { name: 'Lab 1: vista da porta. Foto indisponível' });
    expect(substituto.tagName).toBe('SPAN');
    expect(substituto).toHaveTextContent('Foto indisponível');
    // Sem laço: nenhum <img> sobra para falhar de novo.
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelectorAll('[data-foto-indisponivel]')).toHaveLength(1);

    rerender(<FotoApi src="http://api/uploads/salas/3/a.jpg" alt="Lab 1: vista da porta" />);
    expect(container.querySelectorAll('[data-foto-indisponivel]')).toHaveLength(1);

    // Outra foto (src novo) é tentada normalmente.
    rerender(<FotoApi src="http://api/uploads/salas/3/b.jpg" alt="Lab 1: vista do fundo" />);
    expect(screen.getByRole('img', { name: 'Lab 1: vista do fundo' }).tagName).toBe('IMG');
  });

  it('foto decorativa (alt vazio) vira substituto oculto ao leitor de tela', () => {
    const { container } = render(<FotoApi src="/x.jpg" alt="" />);
    fireEvent.error(container.querySelector('img'));
    expect(container.querySelector('[data-foto-indisponivel]')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('na galeria, só a foto quebrada vira substituto', () => {
    const fotos = [
      { id: 1, url: '/uploads/salas/3/a.jpg', legenda: 'Vista da porta', ordem: 1 },
      { id: 2, url: '/uploads/salas/3/b.jpg', legenda: null, ordem: 2 },
    ];
    const { container } = render(<Galeria fotos={fotos} nomeSala="Lab 1" />);
    const principal = screen.getByRole('img', { name: 'Vista da porta' });
    expect(principal).toHaveAttribute('decoding', 'async');
    fireEvent.error(principal);
    expect(screen.getByRole('img', { name: 'Vista da porta. Foto indisponível' })).toBeInTheDocument();
    // Miniaturas continuam como <img> (a primeira miniatura é outro elemento e carrega à parte).
    expect(container.querySelectorAll('.galeria-miniaturas img')).toHaveLength(2);
  });
});
