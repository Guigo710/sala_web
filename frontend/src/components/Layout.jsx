import { Outlet } from 'react-router-dom';
import Cabecalho from './Cabecalho';

export default function Layout() {
  return (
    <div className="app">
      <a href="#conteudo" className="pular-link">
        Pular para o conteúdo
      </a>
      <Cabecalho />
      <main id="conteudo" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="rodape">
        <p>sala_web · FATEC Indaiatuba · Reserva de salas e laboratórios</p>
      </footer>
    </div>
  );
}
