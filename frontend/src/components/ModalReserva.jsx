import { useCallback, useEffect, useState } from 'react';
import { listarSalas, obterDisponibilidade } from '../api/salas';
import { listarProfessores } from '../api/professores';
import { criarReserva, criarReservaRecorrente, previaRecorrencia } from '../api/reservas';
import { useAuth } from '../auth/contexto';
import { hojeIso, formatarDataLonga } from '../utils/datas';
import { plural } from '../utils/formatacao';
import Alerta from './Alerta';
import Carregando from './Carregando';
import ErroApiAlerta from './ErroApiAlerta';
import Modal from './Modal';
import PreviaRecorrencia from './PreviaRecorrencia';
import SeletorAulas from './SeletorAulas';
import { useAvisos } from './avisos';

const MAX_OBSERVACAO = 200;

function corpoBase({ salaId, horarioIds, professorId }) {
  const corpo = { sala_id: Number(salaId), horario_ids: horarioIds };
  if (professorId) corpo.professor_id = Number(professorId);
  return corpo;
}

/**
 * Reserva avulsa (aulas seguidas) e, com "Repetir toda semana", reserva recorrente com prévia.
 * O RM nunca é pedido: o dono vem do token. Admin pode reservar em nome de um professor.
 */
function ConteudoModalReserva({ salaInicial, dataInicial, aoFechar, aoConcluir }) {
  const { usuario, ehAdmin } = useAuth();
  const { avisar } = useAvisos();
  const [salas, setSalas] = useState(null);
  const [professores, setProfessores] = useState([]);
  const [salaId, setSalaId] = useState(salaInicial ? String(salaInicial) : '');
  const [data, setData] = useState(dataInicial && dataInicial >= hojeIso() ? dataInicial : hojeIso());
  const [disponibilidade, setDisponibilidade] = useState(null);
  const [erroDisp, setErroDisp] = useState(null);
  const [carregandoDisp, setCarregandoDisp] = useState(false);
  const [versaoDisp, setVersaoDisp] = useState(0);
  const [horarioIds, setHorarioIds] = useState([]);
  const [observacao, setObservacao] = useState('');
  const [professorId, setProfessorId] = useState('');
  const [repetir, setRepetir] = useState(false);
  const [etapa, setEtapa] = useState('formulario');
  const [previa, setPrevia] = useState(null);
  const [datasEscolhidas, setDatasEscolhidas] = useState([]);
  const [erro, setErro] = useState(null);
  const [aviso, setAviso] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    listarSalas().then(setSalas, (e) => {
      setSalas([]);
      setErro(e);
    });
    if (ehAdmin) listarProfessores({ ativo: true }).then(setProfessores, () => setProfessores([]));
  }, [ehAdmin]);

  useEffect(() => {
    if (!salaId || !data) {
      setDisponibilidade(null);
      return undefined;
    }
    let ativo = true;
    setCarregandoDisp(true);
    setErroDisp(null);
    obterDisponibilidade(salaId, data)
      .then(
        (d) => ativo && setDisponibilidade(d),
        (e) => {
          if (!ativo) return;
          setDisponibilidade(null);
          setErroDisp(e);
        },
      )
      .finally(() => ativo && setCarregandoDisp(false));
    return () => {
      ativo = false;
    };
  }, [salaId, data, versaoDisp]);

  const mudarSala = (valor) => {
    setSalaId(valor);
    setHorarioIds([]);
    setErro(null);
  };
  const mudarData = (valor) => {
    setData(valor);
    setHorarioIds([]);
    setErro(null);
  };

  const buscarPrevia = useCallback(
    async (manterSelecao) => {
      const resposta = await previaRecorrencia({
        ...corpoBase({ salaId, horarioIds, professorId }),
        data_inicio: data,
      });
      setPrevia(resposta);
      const livres = resposta.ocorrencias.filter((o) => o.livre).map((o) => o.data);
      setDatasEscolhidas(manterSelecao ? manterSelecao.filter((d) => livres.includes(d)) : livres);
      setEtapa('previa');
      return resposta;
    },
    [salaId, horarioIds, professorId, data],
  );

  const aoEnviarFormulario = async (e) => {
    e.preventDefault();
    if (!salaId || !data || horarioIds.length === 0) return;
    setErro(null);
    setAviso('');
    setEnviando(true);
    try {
      if (repetir) {
        await buscarPrevia();
      } else {
        const corpo = { ...corpoBase({ salaId, horarioIds, professorId }), data };
        if (observacao.trim()) corpo.observacao = observacao.trim();
        const reserva = await criarReserva(corpo);
        avisar(`Reserva criada: ${reserva.sala.nome}, ${formatarDataLonga(reserva.data)}, ${reserva.inicio}–${reserva.fim}.`);
        aoConcluir?.(reserva);
        aoFechar();
      }
    } catch (err) {
      setErro(err);
      if (err.codigo === 'CONFLITO_RESERVA' || err.codigo === 'DATA_PASSADA') {
        setHorarioIds([]);
        setVersaoDisp((v) => v + 1);
      }
    } finally {
      setEnviando(false);
    }
  };

  const confirmarRecorrencia = async () => {
    if (datasEscolhidas.length === 0) return;
    setErro(null);
    setAviso('');
    setEnviando(true);
    try {
      const corpo = {
        ...corpoBase({ salaId, horarioIds, professorId }),
        data_inicio: data,
        datas: datasEscolhidas,
      };
      if (observacao.trim()) corpo.observacao = observacao.trim();
      const resultado = await criarReservaRecorrente(corpo);
      avisar(`Reserva semanal criada: ${plural(resultado.reservas.length, 'data reservada', 'datas reservadas')}.`);
      aoConcluir?.(resultado);
      aoFechar();
    } catch (err) {
      if (err.codigo === 'CONFLITO_RESERVA') {
        setAviso(
          'Algumas datas foram ocupadas enquanto você decidia. A prévia foi atualizada: confira e confirme de novo.',
        );
        try {
          await buscarPrevia(datasEscolhidas);
        } catch (err2) {
          setErro(err2);
        }
      } else {
        setErro(err);
      }
    } finally {
      setEnviando(false);
    }
  };

  if (etapa === 'previa' && previa) {
    return (
      <>
        <div className="modal-corpo-conteudo">
          {aviso && <Alerta tipo="aviso">{aviso}</Alerta>}
          <ErroApiAlerta erro={erro} />
          <PreviaRecorrencia previa={previa} selecionadas={datasEscolhidas} aoMudar={setDatasEscolhidas} />
        </div>
        <footer className="modal-rodape">
          <button type="button" className="botao botao-secundario" onClick={aoFechar} disabled={enviando}>
            Desistir
          </button>
          <button
            type="button"
            className="botao botao-secundario"
            onClick={() => {
              setEtapa('formulario');
              setErro(null);
              setAviso('');
            }}
            disabled={enviando}
          >
            Voltar
          </button>
          <button
            type="button"
            className="botao"
            onClick={confirmarRecorrencia}
            disabled={enviando || datasEscolhidas.length === 0}
          >
            {enviando ? 'Reservando…' : `Reservar só as livres selecionadas (${datasEscolhidas.length})`}
          </button>
        </footer>
      </>
    );
  }

  const erroSemSemestre = erro?.codigo === 'SEM_SEMESTRE';

  return (
    <form onSubmit={aoEnviarFormulario} className="formulario">
      <div className="modal-corpo-conteudo">
        {erroSemSemestre ? (
          <Alerta tipo="erro" titulo="Não há semestre letivo para esta data">
            <p>{erro.detail}</p>
            <p>A reserva semanal vai até o fim do semestre. Escolha outra data ou peça à administração para cadastrar o semestre.</p>
          </Alerta>
        ) : (
          <ErroApiAlerta erro={erro} titulo={erro?.codigo === 'CONFLITO_RESERVA' ? 'Horário já reservado' : undefined} />
        )}

        <div className="grade-campos">
          <div className="campo">
            <label htmlFor="reserva-sala">Ambiente</label>
            {salas === null ? (
              <Carregando compacto />
            ) : (
              <select id="reserva-sala" required value={salaId} onChange={(e) => mudarSala(e.target.value)}>
                <option value="">Selecione…</option>
                {salas.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome} ({s.tipo_rotulo}, {s.capacidade} lugares)
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="campo">
            <label htmlFor="reserva-data">{repetir ? 'Data inicial' : 'Data'}</label>
            <input
              id="reserva-data"
              type="date"
              required
              min={hojeIso()}
              value={data}
              onChange={(e) => mudarData(e.target.value)}
            />
          </div>
        </div>

        {salaId && data && (
          <>
            {carregandoDisp && <Carregando compacto texto="Consultando aulas livres…" />}
            <ErroApiAlerta erro={erroDisp} />
            {disponibilidade && !carregandoDisp && (
              <SeletorAulas
                legenda={`Aulas em ${formatarDataLonga(data)}`}
                itens={disponibilidade.aulas}
                selecionadas={horarioIds}
                aoMudar={setHorarioIds}
                permitirOcupadas={repetir}
              />
            )}
            {repetir && disponibilidade?.aulas.some((a) => !a.livre) && (
              <p className="ajuda">Aulas ocupadas nesta data podem ser escolhidas: a prévia mostra as datas em conflito.</p>
            )}
          </>
        )}

        {ehAdmin && (
          <div className="campo">
            <label htmlFor="reserva-professor">Reservar em nome de</label>
            <select id="reserva-professor" value={professorId} onChange={(e) => setProfessorId(e.target.value)}>
              <option value="">Eu mesmo ({usuario.nome})</option>
              {professores
                .filter((p) => p.id !== usuario.id)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nome} ({p.rm})
                  </option>
                ))}
            </select>
          </div>
        )}

        <div className="campo">
          <label htmlFor="reserva-observacao">Observação (opcional)</label>
          <textarea
            id="reserva-observacao"
            rows={2}
            maxLength={MAX_OBSERVACAO}
            placeholder="Ex.: Programação I - ADS 1º sem."
            value={observacao}
            onChange={(e) => setObservacao(e.target.value)}
            aria-describedby="reserva-observacao-contador"
          />
          <small id="reserva-observacao-contador" className="ajuda contador">
            {observacao.length}/{MAX_OBSERVACAO}
          </small>
        </div>

        <label className="opcao opcao-destaque">
          <input
            type="checkbox"
            checked={repetir}
            onChange={(e) => {
              setRepetir(e.target.checked);
              setErro(null);
              if (!e.target.checked) setHorarioIds([]);
            }}
          />
          <span>
            Repetir toda semana até o fim do semestre
            <small className="texto-suave"> · você verá as datas em conflito antes de confirmar</small>
          </span>
        </label>
      </div>
      <footer className="modal-rodape">
        <button type="button" className="botao botao-secundario" onClick={aoFechar} disabled={enviando}>
          Cancelar
        </button>
        <button type="submit" className="botao" disabled={enviando || !salaId || !data || horarioIds.length === 0}>
          {enviando ? (repetir ? 'Calculando…' : 'Reservando…') : repetir ? 'Ver datas da série' : 'Reservar'}
        </button>
      </footer>
    </form>
  );
}

export default function ModalReserva({ aberto, aoFechar, aoConcluir, salaInicial, dataInicial }) {
  return (
    <Modal aberto={aberto} titulo="Nova reserva" aoFechar={aoFechar} tamanho="grande">
      {aberto && (
        <ConteudoModalReserva
          salaInicial={salaInicial}
          dataInicial={dataInicial}
          aoFechar={aoFechar}
          aoConcluir={aoConcluir}
        />
      )}
    </Modal>
  );
}
