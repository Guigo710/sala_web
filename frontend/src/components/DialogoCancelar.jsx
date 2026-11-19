import { useEffect, useState } from 'react';
import { cancelarGrupoRecorrencia, cancelarReserva, obterGrupoRecorrencia } from '../api/reservas';
import { formatarDataLonga, jaPassou } from '../utils/datas';
import { plural } from '../utils/formatacao';
import ErroApiAlerta from './ErroApiAlerta';
import Modal from './Modal';
import { useAvisos } from './avisos';

const MAX_MOTIVO = 200;
const ERROS_QUE_ATUALIZAM = ['RESERVA_JA_INICIADA', 'RESERVA_JA_CANCELADA', 'NAO_ENCONTRADO'];

function Conteudo({ reserva, modo, aoFechar, aoConcluir }) {
  const { avisar } = useAvisos();
  const [motivo, setMotivo] = useState('');
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [aCancelar, setACancelar] = useState(null);
  const grupoId = reserva.grupo_recorrencia_id;

  useEffect(() => {
    if (modo !== 'grupo') return undefined;
    let ativo = true;
    obterGrupoRecorrencia(grupoId).then(
      ({ reservas }) =>
        ativo &&
        setACancelar(reservas.filter((r) => r.status === 'ativa' && !jaPassou(r.data, r.inicio)).length),
      () => ativo && setACancelar(null),
    );
    return () => {
      ativo = false;
    };
  }, [modo, grupoId]);

  const confirmar = async () => {
    setErro(null);
    setEnviando(true);
    try {
      const m = motivo.trim() || undefined;
      if (modo === 'grupo') {
        const r = await cancelarGrupoRecorrencia(grupoId, m);
        avisar(
          r.canceladas > 0
            ? `${plural(r.canceladas, 'reserva cancelada', 'reservas canceladas')} nesta recorrência.`
            : 'Nenhuma reserva futura ativa para cancelar nesta recorrência.',
          r.canceladas > 0 ? 'sucesso' : 'info',
        );
        aoConcluir?.(r);
      } else {
        const r = await cancelarReserva(reserva.id, m);
        avisar('Reserva cancelada.');
        aoConcluir?.(r);
      }
      aoFechar();
    } catch (err) {
      setErro(err);
      setEnviando(false);
      if (ERROS_QUE_ATUALIZAM.includes(err.codigo)) aoConcluir?.(null);
    }
  };

  return (
    <>
      <div className="modal-corpo-conteudo">
        {modo === 'grupo' ? (
          <p>
            Cancelar <strong>todas as próximas ocorrências</strong> desta reserva semanal em{' '}
            <strong>{reserva.sala.nome}</strong> ({reserva.inicio}–{reserva.fim})?
            {aCancelar !== null && <> Serão canceladas {plural(aCancelar, 'reserva', 'reservas')}.</>} As
            ocorrências que já passaram ficam no histórico.
          </p>
        ) : (
          <p>
            Cancelar a reserva de <strong>{reserva.sala.nome}</strong> em {formatarDataLonga(reserva.data)},{' '}
            {reserva.inicio}–{reserva.fim}?
          </p>
        )}
        <ErroApiAlerta erro={erro} />
        <div className="campo">
          <label htmlFor="cancelar-motivo">Motivo (opcional)</label>
          <textarea
            id="cancelar-motivo"
            rows={2}
            maxLength={MAX_MOTIVO}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            data-autofocus
          />
          <small className="ajuda contador">
            {motivo.length}/{MAX_MOTIVO}
          </small>
        </div>
      </div>
      <footer className="modal-rodape">
        <button type="button" className="botao botao-secundario" onClick={aoFechar} disabled={enviando}>
          Voltar
        </button>
        <button type="button" className="botao botao-perigo" onClick={confirmar} disabled={enviando}>
          {enviando ? 'Cancelando…' : modo === 'grupo' ? 'Cancelar todas as próximas' : 'Cancelar reserva'}
        </button>
      </footer>
    </>
  );
}

/**
 * Confirmação de cancelamento (uma reserva ou o grupo de recorrência), com motivo opcional.
 * `aoConcluir(resultado)` é chamado no sucesso e também (com null) quando a lista precisa ser atualizada.
 */
export default function DialogoCancelar({ reserva, modo = 'uma', aoFechar, aoConcluir }) {
  return (
    <Modal
      aberto={Boolean(reserva)}
      titulo={modo === 'grupo' ? 'Cancelar recorrência' : 'Cancelar reserva'}
      aoFechar={aoFechar}
      tamanho="pequeno"
    >
      {reserva && <Conteudo reserva={reserva} modo={modo} aoFechar={aoFechar} aoConcluir={aoConcluir} />}
    </Modal>
  );
}
