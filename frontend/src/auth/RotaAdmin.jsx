import { Link } from 'react-router';
import RotaProtegida from './RotaProtegida';
import { useAuth } from './contexto';

function SoAdmin({ children }) {
  const { ehAdmin } = useAuth();
  if (!ehAdmin) {
    return (
      <section className="pagina pagina-estreita">
        <h1>Acesso restrito</h1>
        <p>Esta área é exclusiva da administração.</p>
        <p>
          <Link to="/agenda">Voltar para a agenda</Link>
        </p>
      </section>
    );
  }
  return children;
}

/** Exige papel admin. Visitante → /login; professor → aviso de acesso restrito. */
export default function RotaAdmin({ children }) {
  return (
    <RotaProtegida>
      <SoAdmin>{children}</SoAdmin>
    </RotaProtegida>
  );
}
