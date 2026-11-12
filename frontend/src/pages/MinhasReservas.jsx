import { useCallback, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { listarMinhasReservas } from '../api/reservas';
import { useCarregar } from '../hooks/useCarregar';
import Carregando from '../components/Carregando';
import DialogoCancelar from '../components/DialogoCancelar';
import ErroApiAlerta from '../components/ErroApiAlerta';
import EstadoVazio from '../components/EstadoVazio';
import { formatarDataCurta, formatarDataHora } from '../utils/datas';
import { corDoTipo, plural } from '../utils/formatacao';

const ABAS = [
  { valor: 'futuras', rotulo: 'Futuras' },
  { valor: 'passadas', rotulo: 'Passadas' },
];

const STATUS = [
  { valor: 'ativa', rotulo: 'Ativas' },
  { valor: 'cancelada', rotulo: 'Canceladas' },
  { valor: 'todas', rotulo: 'Todas' },
];

function ItemReserva({ reserva, aoCancelar, aoCancelarGrupo, mostrarGrupo }) {
  const cancelada = reserva.status === 'cancelada';
  return (
    <li className={cancelada ? 'reserva-item cancelada' : 'reserva-item'} style={{ '--cor-tipo': corDoTipo(reserva.sala.tipo) }}>
      <div className="reserva-quando">
        <span className="reserva-data">{formatarDataCurta(reserva.data)}</span>
        <span className="reserva-hora">
          {reserva.inicio}–{reserva.fim}
        </span>
      </div>
      <div className="reserva-o-que">
        <Link to={`/ambientes/${reserva.sala.id}`} className="reserva-sala">
          {reserva.sala.nome}
        </Link>
        <span className="texto-suave"> · {plural(reserva.quantidade_aulas, 'aula', 'aulas')}</span>
        <div className="reserva-selos">
          {reserva.grupo_recorrencia_id && <span className="selo selo-recorrente">↻ Semanal</span>}
          {cancelada && <span className="selo selo-cancelada">Cancelada</span>}
        </div>
        {reserva.observacao && <p className="reserva-obs">{reserva.observacao}</p>}
        {cancelada && (
          <p className="reserva-obs texto-suave">
            Cancelada em {formatarDataHora(reserva.cancelada_em)}
            {reserva.cancelada_por ? ` por ${reserva.cancelada_por.nome}` : ''}
            {reserva.motivo_cancelamento ? `: ${reserva.motivo_cancelamento}` : ''}
          </p>
        )}
      </div>
      <div className="reserva-acoes">
        {reserva.pode_cancelar && (
          <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => aoCancelar(reserva)}>
            Cancelar
          </button>
        )}
        {mostrarGrupo && reserva.grupo_recorrencia_id && reserva.status === 'ativa' && (
          <button type="button" className="botao-link" onClick={() => aoCancelarGrupo(reserva)}>
            Cancelar todas as próximas desta recorrência
          </button>
        )}
      </div>
    </li>
  );
}

export default function MinhasReservas() {
  const [params, setParams] = useSearchParams();
  const periodo = params.get('periodo') === 'passadas' ? 'passadas' : 'futuras';
  const status = STATUS.some((s) => s.valor === params.get('status')) ? params.get('status') : 'ativa';
  const [cancelando, setCancelando] = useState(null);

  const carregar = useCallback(() => listarMinhasReservas({ periodo, status }), [periodo, status]);
  const { dados: reservas, erro, carregando, recarregar } = useCarregar(carregar);

  const mudar = (chave, valor) => {
    const novo = new URLSearchParams(params);
    novo.set(chave, valor);
    setParams(novo, { replace: true });
  };

  const aoTeclarAba = (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    const proxima = periodo === 'futuras' ? 'passadas' : 'futuras';
    mudar('periodo', proxima);
    document.getElementById(`aba-${proxima}`)?.focus();
  };

  return (
    <section className="pagina">
      <div className="pagina-titulo pagina-titulo-com-acoes">
        <div>
          <h1>Minhas reservas</h1>
          <p className="texto-suave">Suas reservas avulsas e semanais. Você pode cancelar até o início da aula.</p>
        </div>
        <Link to="/agenda" className="botao">
          Nova reserva
        </Link>
      </div>

      <div className="barra-ferramentas">
        <div role="tablist" aria-label="Período" className="abas">
          {ABAS.map((a) => (
            <button
              key={a.valor}
              id={`aba-${a.valor}`}
              type="button"
              role="tab"
              aria-selected={periodo === a.valor}
              aria-controls="painel-reservas"
              tabIndex={periodo === a.valor ? 0 : -1}
              className={periodo === a.valor ? 'aba ativa' : 'aba'}
              onClick={() => mudar('periodo', a.valor)}
              onKeyDown={aoTeclarAba}
            >
              {a.rotulo}
            </button>
          ))}
        </div>
        <div className="campo campo-compacto campo-inline">
          <label htmlFor="filtro-status">Situação</label>
          <select id="filtro-status" value={status} onChange={(e) => mudar('status', e.target.value)}>
            {STATUS.map((s) => (
              <option key={s.valor} value={s.valor}>
                {s.rotulo}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div id="painel-reservas" role="tabpanel" aria-labelledby={`aba-${periodo}`}>
        <ErroApiAlerta erro={erro} />
        {carregando && !reservas && <Carregando texto="Carregando reservas…" />}
        {reservas &&
          (reservas.length === 0 ? (
            <EstadoVazio
              titulo={periodo === 'futuras' ? 'Você não tem reservas futuras.' : 'Nenhuma reserva passada.'}
            >
              {periodo === 'futuras' && status !== 'cancelada' && (
                <p>
                  Veja os <Link to="/ambientes">ambientes</Link> ou use a <Link to="/agenda">agenda</Link> para
                  reservar.
                </p>
              )}
            </EstadoVazio>
          ) : (
            <ul className="lista-reservas" aria-busy={carregando}>
              {reservas.map((r) => (
                <ItemReserva
                  key={r.id}
                  reserva={r}
                  mostrarGrupo={periodo === 'futuras'}
                  aoCancelar={(res) => setCancelando({ reserva: res, modo: 'uma' })}
                  aoCancelarGrupo={(res) => setCancelando({ reserva: res, modo: 'grupo' })}
                />
              ))}
            </ul>
          ))}
      </div>

      <DialogoCancelar
        reserva={cancelando?.reserva}
        modo={cancelando?.modo}
        aoFechar={() => setCancelando(null)}
        aoConcluir={recarregar}
      />
    </section>
  );
}
