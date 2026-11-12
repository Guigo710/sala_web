import { NavLink, Outlet } from 'react-router';

const SECOES = [
  { para: 'ambientes', rotulo: 'Ambientes' },
  { para: 'equipamentos', rotulo: 'Equipamentos' },
  { para: 'softwares', rotulo: 'Softwares' },
  { para: 'professores', rotulo: 'Professores' },
  { para: 'horarios', rotulo: 'Horários' },
  { para: 'semestres', rotulo: 'Semestres' },
];

export default function AdminLayout() {
  return (
    <section className="pagina">
      <div className="pagina-titulo">
        <h1>Administração</h1>
      </div>
      <nav className="admin-nav" aria-label="Seções da administração">
        <ul>
          {SECOES.map((s) => (
            <li key={s.para}>
              <NavLink to={s.para} className={({ isActive }) => (isActive ? 'admin-nav-link ativo' : 'admin-nav-link')}>
                {s.rotulo}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="admin-conteudo">
        <Outlet />
      </div>
    </section>
  );
}
