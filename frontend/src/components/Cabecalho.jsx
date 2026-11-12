import { useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router';
import { useAuth } from '../auth/contexto';

export default function Cabecalho() {
  const { usuario, ehAdmin, sair } = useAuth();
  const [menuAberto, setMenuAberto] = useState(false);
  const [caminhoMenu, setCaminhoMenu] = useState(null);
  const location = useLocation();

  // Fecha o menu móvel ao trocar de página.
  if (menuAberto && caminhoMenu !== location.pathname) {
    setMenuAberto(false);
  }

  const alternarMenu = () => {
    setCaminhoMenu(location.pathname);
    setMenuAberto((v) => !v);
  };

  const classeLink = ({ isActive }) => (isActive ? 'nav-link ativo' : 'nav-link');

  return (
    <header className="cabecalho">
      <div className="cabecalho-interno">
        <Link to="/agenda" className="marca">
          <span className="marca-icone" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="28" height="28">
              <rect width="32" height="32" rx="6" fill="currentColor" />
              <rect x="7" y="9" width="18" height="16" rx="2" fill="none" stroke="#fff" strokeWidth="2" />
              <path d="M7 14h18M12 6v5M20 6v5" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </span>
          <span>
            Reserva de salas
            <small>FATEC Indaiatuba</small>
          </span>
        </Link>

        <button
          type="button"
          className="menu-botao"
          aria-expanded={menuAberto}
          aria-controls="menu-principal"
          onClick={alternarMenu}
        >
          <span aria-hidden="true">☰</span>
          <span className="sr-only">Menu</span>
        </button>

        <nav id="menu-principal" className={menuAberto ? 'nav aberto' : 'nav'} aria-label="Principal">
          <ul className="nav-lista">
            <li>
              <NavLink to="/agenda" className={classeLink}>
                Agenda
              </NavLink>
            </li>
            <li>
              <NavLink to="/ambientes" className={classeLink}>
                Ambientes
              </NavLink>
            </li>
            {usuario && (
              <li>
                <NavLink to="/minhas-reservas" className={classeLink}>
                  Minhas reservas
                </NavLink>
              </li>
            )}
            {ehAdmin && (
              <li>
                <NavLink to="/admin" className={classeLink}>
                  Admin
                </NavLink>
              </li>
            )}
          </ul>
          <div className="nav-conta">
            {usuario ? (
              <>
                <NavLink to="/minha-conta" className={classeLink} title="Minha conta">
                  {usuario.nome.split(' ')[0]}
                  {ehAdmin && <span className="selo selo-admin">admin</span>}
                </NavLink>
                <button type="button" className="botao botao-secundario botao-pequeno" onClick={sair}>
                  Sair
                </button>
              </>
            ) : (
              <Link to="/login" state={{ de: location }} className="botao botao-pequeno">
                Entrar
              </Link>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
}
