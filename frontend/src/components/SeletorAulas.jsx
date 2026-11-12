import { useId } from 'react';
import { agruparPorTurno, alternarAula, intervaloDasAulas } from '../utils/aulas';
import { plural } from '../utils/formatacao';

/**
 * Seleção de aulas seguidas (RN03): mesmo turno, ordem consecutiva, sem buracos.
 * @param {{horario: object, livre?: boolean, passou?: boolean, reserva?: object}[]} itens
 * @param {number[]} selecionadas
 * @param {(ids: number[]) => void} aoMudar
 * @param {boolean} [permitirOcupadas] aulas ocupadas podem ser marcadas (recorrência: a prévia mostra o conflito)
 */
export default function SeletorAulas({
  itens,
  selecionadas,
  aoMudar,
  legenda = 'Aulas',
  desabilitado = false,
  permitirOcupadas = false,
}) {
  const idBase = useId();
  const horarios = itens.map((i) => i.horario);
  const porId = new Map(itens.map((i) => [i.horario.id, i]));
  const selecionavel = (item) => (permitirOcupadas || item.livre !== false) && !item.passou;
  const selecionaveis = itens.filter(selecionavel).map((i) => i.horario);
  const grupos = agruparPorTurno(horarios);
  const aulasSelecionadas = selecionadas.map((id) => porId.get(id)?.horario).filter(Boolean);
  const intervalo = intervaloDasAulas(aulasSelecionadas);

  return (
    <fieldset className="seletor-aulas" disabled={desabilitado}>
      <legend>{legenda}</legend>
      {grupos.length === 0 && <p className="texto-suave">Nenhuma aula neste dia.</p>}
      {grupos.map((grupo) => (
        <div key={grupo.valor} className="seletor-turno">
          <p className="seletor-turno-titulo" id={`${idBase}-${grupo.valor}`}>
            {grupo.rotulo}
          </p>
          <ul className="seletor-lista" aria-labelledby={`${idBase}-${grupo.valor}`}>
            {grupo.aulas.map((aula) => {
              const item = porId.get(aula.id);
              const pode = selecionavel(item);
              const marcada = selecionadas.includes(aula.id);
              const id = `${idBase}-aula-${aula.id}`;
              let situacao = null;
              if (item.livre === false) {
                situacao = item.reserva?.professor?.nome ? `ocupada · ${item.reserva.professor.nome}` : 'ocupada';
              } else if (item.passou) {
                situacao = 'já passou';
              }
              return (
                <li key={aula.id}>
                  <label
                    htmlFor={id}
                    className={[
                      'aula-chip',
                      marcada ? 'marcada' : '',
                      !pode ? 'indisponivel' : '',
                      item.livre === false ? 'ocupada' : '',
                    ].join(' ')}
                  >
                    <input
                      id={id}
                      type="checkbox"
                      checked={marcada}
                      disabled={!pode && !marcada}
                      onChange={() => aoMudar(alternarAula(selecionadas, aula, selecionaveis))}
                    />
                    <span className="aula-ordem">{aula.ordem}ª</span>
                    <span className="aula-hora">
                      {aula.inicio}–{aula.fim}
                    </span>
                    {situacao && <span className="aula-situacao">{situacao}</span>}
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <p className="ajuda" aria-live="polite">
        {intervalo
          ? `Selecionado: ${intervalo.inicio}–${intervalo.fim} (${plural(aulasSelecionadas.length, 'aula', 'aulas')}).`
          : 'Escolha uma ou mais aulas seguidas do mesmo turno.'}
      </p>
    </fieldset>
  );
}
