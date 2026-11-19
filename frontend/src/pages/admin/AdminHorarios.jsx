import { useCallback, useState } from 'react';
import {
  atualizarHorario,
  criarHorario,
  excluirHorario,
  listarHorarios,
} from '../../api/horarios';
import { useCarregar } from '../../hooks/useCarregar';
import { useAvisos } from '../../components/avisos';
import { useConfirmar } from '../../components/useConfirmar';
import Carregando from '../../components/Carregando';
import EstadoVazio from '../../components/EstadoVazio';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import Modal from '../../components/Modal';
import { TURNOS, agruparPorTurno } from '../../utils/aulas';
import { DIAS_SEMANA } from '../../utils/datas';

const listar = () => listarHorarios({ incluir_inativos: true });

const diasTexto = (dias) =>
  DIAS_SEMANA.filter((d) => dias.includes(d.iso))
    .map((d) => d.curto)
    .join(', ');

function corpoDe(h) {
  return {
    turno: h.turno,
    ordem: Number(h.ordem),
    inicio: h.inicio,
    fim: h.fim,
    dias_semana: [...h.dias_semana].sort((a, b) => a - b),
    ativo: h.ativo,
  };
}

function FormHorario({ horario, sugestaoOrdem, aoSalvar, aoCancelar }) {
  const [v, setV] = useState(
    horario
      ? { ...horario }
      : { turno: 'manha', ordem: sugestaoOrdem('manha'), inicio: '', fim: '', dias_semana: [1, 2, 3, 4, 5], ativo: true },
  );
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const mudar = (k, valor) => setV((x) => ({ ...x, [k]: valor }));

  const alternarDia = (iso) =>
    mudar('dias_semana', v.dias_semana.includes(iso) ? v.dias_semana.filter((d) => d !== iso) : [...v.dias_semana, iso]);

  const erroLocal =
    v.inicio && v.fim && v.fim <= v.inicio
      ? 'O fim precisa ser depois do início.'
      : v.dias_semana.length === 0
        ? 'Escolha pelo menos um dia da semana.'
        : '';

  const enviar = async (e) => {
    e.preventDefault();
    if (erroLocal) return;
    setErro(null);
    setSalvando(true);
    try {
      if (horario) await atualizarHorario(horario.id, corpoDe(v));
      else await criarHorario(corpoDe(v));
      aoSalvar();
    } catch (err) {
      setErro(err);
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="formulario">
      <div className="modal-corpo-conteudo">
        <ErroApiAlerta erro={erro} />
        <div className="grade-campos">
          <div className="campo">
            <label htmlFor="hor-turno">Turno</label>
            <select
              id="hor-turno"
              value={v.turno}
              onChange={(e) => {
                const turno = e.target.value;
                setV((x) => ({ ...x, turno, ordem: horario ? x.ordem : sugestaoOrdem(turno) }));
              }}
              data-autofocus
            >
              {TURNOS.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.rotulo}
                </option>
              ))}
            </select>
          </div>
          <div className="campo">
            <label htmlFor="hor-ordem">Ordem no turno</label>
            <input
              id="hor-ordem"
              type="number"
              min="1"
              required
              value={v.ordem}
              onChange={(e) => mudar('ordem', e.target.value)}
            />
          </div>
          <div className="campo">
            <label htmlFor="hor-inicio">Início</label>
            <input id="hor-inicio" type="time" required value={v.inicio} onChange={(e) => mudar('inicio', e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="hor-fim">Fim</label>
            <input id="hor-fim" type="time" required value={v.fim} onChange={(e) => mudar('fim', e.target.value)} />
          </div>
        </div>
        <fieldset className="filtro-grupo">
          <legend>Dias da semana em que a aula vale</legend>
          <ul className="dias-semana">
            {DIAS_SEMANA.map((d) => (
              <li key={d.iso}>
                <label className="opcao opcao-dia">
                  <input type="checkbox" checked={v.dias_semana.includes(d.iso)} onChange={() => alternarDia(d.iso)} />
                  <span title={d.nome}>{d.curto}</span>
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
        <label className="opcao">
          <input type="checkbox" checked={v.ativo} onChange={(e) => mudar('ativo', e.target.checked)} />
          <span>Aula ativa (disponível para reservas)</span>
        </label>
        {horario && (
          <p className="ajuda">Alterar o horário não muda reservas já feitas: elas guardam o início e o fim originais.</p>
        )}
        {erroLocal && (
          <p className="erro-campo" role="alert">
            {erroLocal}
          </p>
        )}
      </div>
      <footer className="modal-rodape">
        <button type="button" className="botao botao-secundario" onClick={aoCancelar}>
          Cancelar
        </button>
        <button type="submit" className="botao" disabled={salvando || Boolean(erroLocal)}>
          {salvando ? 'Salvando…' : 'Salvar'}
        </button>
      </footer>
    </form>
  );
}

export default function AdminHorarios() {
  const { avisar } = useAvisos();
  const [confirmar, dialogo] = useConfirmar();
  const { dados: horarios, erro, carregando, recarregar } = useCarregar(listar);
  const [editando, setEditando] = useState(null);
  const [erroAcao, setErroAcao] = useState(null);

  const sugestaoOrdem = useCallback(
    (turno) => Math.max(0, ...(horarios || []).filter((h) => h.turno === turno).map((h) => h.ordem)) + 1,
    [horarios],
  );

  const alternarAtivo = async (h) => {
    setErroAcao(null);
    try {
      await atualizarHorario(h.id, { ...corpoDe(h), ativo: !h.ativo });
      avisar(h.ativo ? 'Aula desativada.' : 'Aula ativada.');
      recarregar();
    } catch (err) {
      setErroAcao(err);
    }
  };

  const remover = async (h) => {
    const ok = await confirmar({
      titulo: 'Excluir aula',
      mensagem: `Excluir a ${h.ordem}ª aula (${h.inicio}–${h.fim})? Aulas usadas em reservas não podem ser excluídas: desative-as.`,
      textoConfirmar: 'Excluir',
      perigo: true,
    });
    if (!ok) return;
    setErroAcao(null);
    try {
      await excluirHorario(h.id);
      avisar('Aula excluída.');
      recarregar();
    } catch (err) {
      setErroAcao(err);
    }
  };

  const grupos = agruparPorTurno(horarios || []);

  return (
    <div className="admin-secao">
      <div className="admin-secao-cabecalho">
        <div>
          <h2>Horários de aula</h2>
          <p className="texto-suave">A grade define as aulas que podem ser reservadas em cada turno e dia da semana.</p>
        </div>
        <button type="button" className="botao" onClick={() => setEditando({ horario: null })}>
          Nova aula
        </button>
      </div>

      <ErroApiAlerta erro={erro} />
      <ErroApiAlerta erro={erroAcao} />
      {carregando && !horarios && <Carregando />}
      {horarios && grupos.length === 0 && <EstadoVazio titulo="Nenhuma aula cadastrada." />}
      {grupos.map((g) => (
        <section key={g.valor} className="secao">
          <h3>{g.rotulo}</h3>
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col" className="num">
                    Ordem
                  </th>
                  <th scope="col">Início</th>
                  <th scope="col">Fim</th>
                  <th scope="col">Dias</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="acoes-col">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {g.aulas.map((h) => (
                  <tr key={h.id} className={h.ativo ? '' : 'linha-inativa'}>
                    <td className="num">{h.ordem}ª</td>
                    <td>{h.inicio}</td>
                    <td>{h.fim}</td>
                    <td>{diasTexto(h.dias_semana)}</td>
                    <td>
                      {h.ativo ? <span className="selo selo-ativa">Ativa</span> : <span className="selo selo-inativo">Inativa</span>}
                    </td>
                    <td className="acoes-col">
                      <div className="acoes-linha">
                        <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => setEditando({ horario: h })}>
                          Editar
                        </button>
                        <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => alternarAtivo(h)}>
                          {h.ativo ? 'Desativar' : 'Ativar'}
                        </button>
                        <button type="button" className="botao botao-perigo-leve botao-pequeno" onClick={() => remover(h)}>
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}

      <Modal
        aberto={Boolean(editando)}
        titulo={editando?.horario ? 'Editar aula' : 'Nova aula'}
        aoFechar={() => setEditando(null)}
      >
        {editando && (
          <FormHorario
            horario={editando.horario}
            sugestaoOrdem={sugestaoOrdem}
            aoCancelar={() => setEditando(null)}
            aoSalvar={() => {
              avisar(editando.horario ? 'Aula atualizada.' : 'Aula criada.');
              setEditando(null);
              recarregar();
            }}
          />
        )}
      </Modal>
      {dialogo}
    </div>
  );
}
