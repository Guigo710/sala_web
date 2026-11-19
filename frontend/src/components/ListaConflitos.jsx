import { formatarDataCurta } from '../utils/datas';

/** Lista de `Conflito` (§3.12). */
export default function ListaConflitos({ conflitos }) {
  if (!conflitos?.length) return null;
  return (
    <ul className="lista-conflitos">
      {conflitos.map((c, i) => (
        <li key={`${c.reserva_id}-${c.data}-${i}`}>
          <strong>{formatarDataCurta(c.data)}</strong>, {c.inicio}–{c.fim}
          {c.professor?.nome ? <> · reservado por {c.professor.nome}</> : null}
        </li>
      ))}
    </ul>
  );
}
