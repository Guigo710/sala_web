import { Link } from 'react-router';
import { formatarDataHora, formatarDataLonga } from '../utils/datas';
import { plural } from '../utils/formatacao';
import Modal from './Modal';

/** Detalhes de uma reserva (clique num evento da agenda). */
export default function DetalheReserva({ reserva, aoFechar, aoCancelar, aoCancelarGrupo }) {
  return (
    <Modal aberto={Boolean(reserva)} titulo="Reserva" aoFechar={aoFechar} tamanho="pequeno">
      {reserva && (
        <>
          <div className="modal-corpo-conteudo">
            <dl className="lista-definicoes">
              <div>
                <dt>Ambiente</dt>
                <dd>
                  <Link to={`/ambientes/${reserva.sala.id}`}>{reserva.sala.nome}</Link>
                </dd>
              </div>
              <div>
                <dt>Data</dt>
                <dd>{formatarDataLonga(reserva.data)}</dd>
              </div>
              <div>
                <dt>Horário</dt>
                <dd>
                  {reserva.inicio}–{reserva.fim} ({plural(reserva.quantidade_aulas, 'aula', 'aulas')})
                </dd>
              </div>
              <div>
                <dt>Professor</dt>
                <dd>{reserva.professor.nome}</dd>
              </div>
              {reserva.observacao && (
                <div>
                  <dt>Observação</dt>
                  <dd>{reserva.observacao}</dd>
                </div>
              )}
              {reserva.grupo_recorrencia_id && (
                <div>
                  <dt>Tipo</dt>
                  <dd>Reserva semanal (recorrente)</dd>
                </div>
              )}
              <div>
                <dt>Situação</dt>
                <dd>
                  {reserva.status === 'ativa' ? (
                    <span className="selo selo-ativa">Ativa</span>
                  ) : (
                    <span className="selo selo-cancelada">Cancelada</span>
                  )}
                  {reserva.cancelada_em && (
                    <small className="texto-suave">
                      {' '}
                      em {formatarDataHora(reserva.cancelada_em)}
                      {reserva.cancelada_por ? ` por ${reserva.cancelada_por.nome}` : ''}
                    </small>
                  )}
                </dd>
              </div>
              {reserva.motivo_cancelamento && (
                <div>
                  <dt>Motivo</dt>
                  <dd>{reserva.motivo_cancelamento}</dd>
                </div>
              )}
            </dl>
          </div>
          <footer className="modal-rodape">
            {reserva.pode_cancelar && reserva.grupo_recorrencia_id && (
              <button type="button" className="botao botao-secundario" onClick={() => aoCancelarGrupo(reserva)}>
                Cancelar todas as próximas
              </button>
            )}
            {reserva.pode_cancelar && (
              <button type="button" className="botao botao-perigo" onClick={() => aoCancelar(reserva)}>
                Cancelar reserva
              </button>
            )}
            <button type="button" className="botao" onClick={aoFechar} data-autofocus>
              Fechar
            </button>
          </footer>
        </>
      )}
    </Modal>
  );
}
