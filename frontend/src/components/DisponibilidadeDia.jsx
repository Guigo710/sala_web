import { useCallback } from 'react';
import { obterDisponibilidade } from '../api/salas';
import { useCarregar } from '../hooks/useCarregar';
import { agruparPorTurno } from '../utils/aulas';
import Carregando from './Carregando';
import ErroApiAlerta from './ErroApiAlerta';

/** Grade do dia de uma sala: livre / ocupada (professor) / passou. `versao` força recarregar. */
export default function DisponibilidadeDia({ salaId, data, versao = 0 }) {
  const carregar = useCallback(
    () => (versao >= 0 ? obterDisponibilidade(salaId, data) : null),
    [salaId, data, versao],
  );
  const { dados, erro, carregando } = useCarregar(carregar);

  if (carregando && !dados) return <Carregando compacto texto="Consultando disponibilidade…" />;
  if (erro) return <ErroApiAlerta erro={erro} />;
  if (!dados) return null;

  if (dados.aulas.length === 0) {
    return <p className="texto-suave">Não há aulas na grade neste dia.</p>;
  }

  const porId = new Map(dados.aulas.map((a) => [a.horario.id, a]));
  const grupos = agruparPorTurno(dados.aulas.map((a) => a.horario));

  return (
    <div className="disponibilidade" aria-busy={carregando}>
      {grupos.map((g) => (
        <div key={g.valor} className="disponibilidade-turno">
          <h3>{g.rotulo}</h3>
          <ul>
            {g.aulas.map((h) => {
              const item = porId.get(h.id);
              let classe = 'livre';
              let texto = 'Livre';
              if (!item.livre) {
                classe = 'ocupada';
                texto = item.reserva?.professor?.nome ? `Ocupada · ${item.reserva.professor.nome}` : 'Ocupada';
              } else if (item.passou) {
                classe = 'passou';
                texto = 'Já passou';
              }
              return (
                <li key={h.id} className={`disp-item disp-${classe}`}>
                  <span className="disp-aula">
                    {h.ordem}ª · {h.inicio}–{h.fim}
                  </span>
                  <span className="disp-status">{texto}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
