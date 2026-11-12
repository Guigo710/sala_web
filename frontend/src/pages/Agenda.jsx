import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import ptBrLocale from '@fullcalendar/core/locales/pt-br';
import { listarReservas } from '../api/reservas';
import { listarSalas } from '../api/salas';
import { listarHorarios } from '../api/horarios';
import { useAuth } from '../auth/contexto';
import { useTipos } from '../hooks/useTipos';
import { useAvisos } from '../components/avisos';
import DetalheReserva from '../components/DetalheReserva';
import DialogoCancelar from '../components/DialogoCancelar';
import ErroApiAlerta from '../components/ErroApiAlerta';
import ModalReserva from '../components/ModalReserva';
import {
  deMinutos,
  fullCalendarParaIso,
  hojeIso,
  intervaloParaConsulta,
  paraMinutos,
} from '../utils/datas';
import { corDoTipo } from '../utils/formatacao';

const PADRAO_MIN = '07:00:00';
const PADRAO_MAX = '23:00:00';

/** slotMinTime/slotMaxTime e dias ocultos derivados da grade (GET /horarios). */
function configuracaoDaGrade(horarios) {
  if (!horarios?.length) return { slotMinTime: PADRAO_MIN, slotMaxTime: PADRAO_MAX, hiddenDays: [] };
  const inicio = Math.min(...horarios.map((h) => paraMinutos(h.inicio)));
  const fim = Math.max(...horarios.map((h) => paraMinutos(h.fim)));
  const diasIso = new Set(horarios.flatMap((h) => h.dias_semana));
  const hiddenDays = [0, 1, 2, 3, 4, 5, 6].filter((d) => !diasIso.has(fullCalendarParaIso(d)));
  return {
    slotMinTime: deMinutos(Math.floor((inicio - 30) / 60) * 60),
    slotMaxTime: deMinutos(Math.ceil((fim + 30) / 60) * 60),
    hiddenDays: hiddenDays.length < 7 ? hiddenDays : [],
  };
}

function paraEvento(r) {
  const cor = corDoTipo(r.sala.tipo);
  return {
    id: String(r.id),
    title: `${r.sala.nome} · ${r.professor.nome}`,
    start: `${r.data}T${r.inicio}`,
    end: `${r.data}T${r.fim}`,
    backgroundColor: cor,
    borderColor: cor,
    textColor: '#fff',
    extendedProps: { reserva: r },
  };
}

function ConteudoEvento({ event, view }) {
  const r = event.extendedProps.reserva;
  const compacto = view.type === 'dayGridMonth';
  return (
    <div className={compacto ? 'evento evento-compacto' : 'evento'}>
      <span className="evento-hora">
        {r.inicio}
        {compacto ? '' : `–${r.fim}`}
      </span>{' '}
      <strong className="evento-sala">{r.sala.nome}</strong>
      <span className="evento-professor"> · {r.professor.nome}</span>
      {r.grupo_recorrencia_id && !compacto && <span className="evento-recorrente"> ↻</span>}
    </div>
  );
}

const telaEstreita = () => typeof window !== 'undefined' && window.matchMedia?.('(max-width: 640px)').matches;

export default function Agenda() {
  const { usuario } = useAuth();
  const { avisar } = useAvisos();
  const tipos = useTipos();
  const calendario = useRef(null);
  const [params, setParams] = useSearchParams();
  const salaFiltro = params.get('sala') || '';
  const [salas, setSalas] = useState([]);
  const [horarios, setHorarios] = useState(null);
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [novaReserva, setNovaReserva] = useState(null);
  const [detalhe, setDetalhe] = useState(null);
  const [cancelando, setCancelando] = useState(null);

  useEffect(() => {
    listarSalas().then(setSalas, () => setSalas([]));
    listarHorarios().then(setHorarios, () => setHorarios([]));
  }, []);

  const grade = useMemo(() => configuracaoDaGrade(horarios), [horarios]);

  const buscarEventos = useCallback(
    (info, sucesso, falha) => {
      const { de, ate } = intervaloParaConsulta(info.start, info.end);
      listarReservas({ de, ate, sala_id: salaFiltro || undefined }).then(
        (lista) => {
          setErro(null);
          sucesso(lista.map(paraEvento));
        },
        (err) => {
          setErro(err);
          falha(err);
        },
      );
    },
    [salaFiltro],
  );

  const atualizarAgenda = () => calendario.current?.getApi().refetchEvents();

  const aoClicarDia = (info) => {
    const data = info.dateStr.slice(0, 10);
    if (!usuario) {
      avisar('Entre com seu RM para reservar.', 'info');
      return;
    }
    if (data < hojeIso()) {
      avisar('Não é possível reservar em uma data que já passou.', 'info');
      return;
    }
    setNovaReserva({ data });
  };

  const mudarFiltroSala = (valor) => {
    const novo = new URLSearchParams(params);
    if (valor) novo.set('sala', valor);
    else novo.delete('sala');
    setParams(novo, { replace: true });
  };

  const tiposUsados = tipos.filter((t) =>
    salas.some((s) => s.tipo === t.valor && (!salaFiltro || String(s.id) === salaFiltro)),
  );

  return (
    <section className="pagina pagina-larga">
      <div className="pagina-titulo pagina-titulo-com-acoes">
        <div>
          <h1>Agenda</h1>
          <p className="texto-suave">
            {usuario
              ? 'Clique num dia para reservar ou numa reserva para ver detalhes.'
              : 'Reservas de todos os ambientes. Entre para reservar.'}
          </p>
        </div>
        <div className="agenda-acoes">
          <div className="campo campo-compacto">
            <label htmlFor="agenda-sala">Ambiente</label>
            <select id="agenda-sala" value={salaFiltro} onChange={(e) => mudarFiltroSala(e.target.value)}>
              <option value="">Todos os ambientes</option>
              {salas.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
          </div>
          {usuario && (
            <button type="button" className="botao" onClick={() => setNovaReserva({ data: hojeIso() })}>
              Nova reserva
            </button>
          )}
        </div>
      </div>

      {tiposUsados.length > 0 && (
        <ul className="legenda-tipos" aria-label="Legenda de cores">
          {tiposUsados.map((t) => (
            <li key={t.valor}>
              <span className="legenda-cor" style={{ background: corDoTipo(t.valor) }} aria-hidden="true" />
              {t.rotulo}
            </li>
          ))}
        </ul>
      )}

      <ErroApiAlerta erro={erro} titulo="Não foi possível carregar as reservas" />

      <div className="agenda-calendario" aria-busy={carregando}>
        {carregando && (
          <span className="agenda-carregando" role="status">
            Atualizando…
          </span>
        )}
        {horarios !== null && (
          <FullCalendar
            ref={calendario}
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            locale={ptBrLocale}
            initialView={telaEstreita() ? 'timeGridDay' : 'dayGridMonth'}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay',
            }}
            buttonText={{ today: 'Hoje', month: 'Mês', week: 'Semana', day: 'Dia' }}
            events={buscarEventos}
            eventContent={(arg) => <ConteudoEvento event={arg.event} view={arg.view} />}
            eventClick={(info) => setDetalhe(info.event.extendedProps.reserva)}
            dateClick={aoClicarDia}
            loading={setCarregando}
            slotMinTime={grade.slotMinTime}
            slotMaxTime={grade.slotMaxTime}
            hiddenDays={grade.hiddenDays}
            allDaySlot={false}
            nowIndicator
            eventDisplay="block"
            dayMaxEvents={4}
            height="auto"
            slotDuration="00:30:00"
            slotLabelFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
            eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
          />
        )}
      </div>

      <ModalReserva
        aberto={Boolean(novaReserva)}
        aoFechar={() => setNovaReserva(null)}
        aoConcluir={atualizarAgenda}
        dataInicial={novaReserva?.data}
        salaInicial={salaFiltro || undefined}
      />

      <DetalheReserva
        reserva={cancelando ? null : detalhe}
        aoFechar={() => setDetalhe(null)}
        aoCancelar={(r) => setCancelando({ reserva: r, modo: 'uma' })}
        aoCancelarGrupo={(r) => setCancelando({ reserva: r, modo: 'grupo' })}
      />

      <DialogoCancelar
        reserva={cancelando?.reserva}
        modo={cancelando?.modo}
        aoFechar={() => setCancelando(null)}
        aoConcluir={() => {
          setDetalhe(null);
          atualizarAgenda();
        }}
      />
    </section>
  );
}
