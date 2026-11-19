import { Navigate, useLocation } from 'react-router';
import Carregando from '../components/Carregando';
import { useAuth } from './contexto';

/** Exige login (professor ou admin). Sem sessão → /login, voltando depois; após "Sair" → agenda. */
export default function RotaProtegida({ children }) {
  const { usuario, carregando, saiu } = useAuth();
  const location = useLocation();
  if (carregando) return <Carregando texto="Verificando sessão…" />;
  if (!usuario && saiu) return <Navigate to="/agenda" replace />;
  if (!usuario) return <Navigate to="/login" replace state={{ de: location }} />;
  return children;
}
