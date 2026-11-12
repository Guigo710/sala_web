import { formatarData, formatarDataCurta, DIAS_SEMANA } from '../utils/datas';
import { plural } from '../utils/formatacao';

/**
 * Prévia da recorrência semanal (POST /reservas/recorrentes/previa).
 * Datas livres podem ser desmarcadas; datas em conflito não podem ser marcadas.
 */
export default function PreviaRecorrencia({ previa, selecionadas, aoMudar }) {
  const diaNome = DIAS_SEMANA.find((d) => d.iso === previa.dia_semana)?.nome ?? '';
  const livres = previa.ocorrencias.filter((o) => o.livre).map((o) => o.data);

  const alternar = (data) =>
    aoMudar(selecionadas.includes(data) ? selecionadas.filter((d) => d !== data) : [...selecionadas, data].sort());

  return (
    <div className="previa">
      <div className="previa-resumo">
        <p>
          <strong>{previa.sala.nome}</strong> · toda {diaNome.toLowerCase()}, {previa.inicio}–{previa.fim}
        </p>
        <p className="texto-suave">
          Semestre {previa.semestre.nome} ({formatarData(previa.semestre.data_inicio)} a{' '}
          {formatarData(previa.semestre.data_fim)})
        </p>
        <ul className="previa-totais">
          <li>
            <strong>{previa.total}</strong> {previa.total === 1 ? 'data' : 'datas'}
          </li>
          <li className="total-livre">
            <strong>{previa.livres}</strong> {previa.livres === 1 ? 'livre' : 'livres'}
          </li>
          <li className="total-conflito">
            <strong>{previa.em_conflito}</strong> em conflito
          </li>
        </ul>
      </div>

      <fieldset className="previa-datas">
        <legend>Datas da série</legend>
        <div className="previa-acoes-rapidas">
          <button type="button" className="botao-link" onClick={() => aoMudar(livres)}>
            Marcar todas as livres
          </button>
          <button type="button" className="botao-link" onClick={() => aoMudar([])}>
            Desmarcar todas
          </button>
        </div>
        <ul>
          {previa.ocorrencias.map((o) => {
            const id = `previa-${o.data}`;
            return (
              <li key={o.data} className={o.livre ? 'ocorrencia livre' : 'ocorrencia conflito'}>
                <input
                  id={id}
                  type="checkbox"
                  checked={o.livre && selecionadas.includes(o.data)}
                  disabled={!o.livre}
                  onChange={() => alternar(o.data)}
                />
                <label htmlFor={id}>
                  <span className="ocorrencia-data">{formatarDataCurta(o.data)}</span>
                  {o.livre ? (
                    <span className="ocorrencia-status">Livre</span>
                  ) : (
                    <span className="ocorrencia-status">
                      Em conflito
                      {o.conflitos?.length > 0 &&
                        ` · ${o.conflitos
                          .map((c) => `${c.inicio}–${c.fim}${c.professor?.nome ? ` (${c.professor.nome})` : ''}`)
                          .join(', ')}`}
                    </span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>
      <p className="ajuda" aria-live="polite">
        {plural(selecionadas.length, 'data selecionada', 'datas selecionadas')} para reservar.
      </p>
    </div>
  );
}
