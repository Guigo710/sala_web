import { Link } from 'react-router-dom';

export default function NaoEncontrada() {
  return (
    <section className="pagina pagina-estreita">
      <h1>Página não encontrada</h1>
      <p>O endereço acessado não existe.</p>
      <p>
        <Link to="/agenda">Ir para a agenda</Link> ou <Link to="/ambientes">ver os ambientes</Link>.
      </p>
    </section>
  );
}
