import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { listarSalas } from '../api/salas';
import { listarEquipamentos } from '../api/equipamentos';
import { listarSoftwares } from '../api/softwares';
import { listarHorarios } from '../api/horarios';
import { useCarregar } from '../hooks/useCarregar';
import { useTipos } from '../hooks/useTipos';
import CartaoSala from '../components/CartaoSala';
import Carregando from '../components/Carregando';
import EstadoVazio from '../components/EstadoVazio';
import ErroApiAlerta from '../components/ErroApiAlerta';
import SeletorAulas from '../components/SeletorAulas';
import { diaSemanaIso, formatarDataLonga } from '../utils/datas';
import { plural } from '../utils/formatacao';

const CHAVES_LISTA = ['tipo', 'equipamento_id', 'software_id', 'horario_ids'];

function lerFiltros(params) {
  return {
    tipo: params.getAll('tipo'),
    capacidade_min: params.get('capacidade_min') || '',
    equipamento_id: params.getAll('equipamento_id').map(Number),
    software_id: params.getAll('software_id').map(Number),
    busca: params.get('busca') || '',
    data: params.get('data') || '',
    horario_ids: params.getAll('horario_ids').map(Number),
  };
}

function ListaMarcavel({ legenda, itens, marcados, aoAlternar, vazio, rotulo }) {
  return (
    <fieldset className="filtro-grupo">
      <legend>{legenda}</legend>
      {itens.length === 0 && <p className="texto-suave texto-pequeno">{vazio}</p>}
      <ul className="lista-marcavel">
        {itens.map((item) => (
          <li key={item.id}>
            <label className="opcao">
              <input type="checkbox" checked={marcados.includes(item.id)} onChange={() => aoAlternar(item.id)} />
              <span>{rotulo(item)}</span>
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}

export default function Salas() {
  const [params, setParams] = useSearchParams();
  const chave = params.toString();
  const filtros = useMemo(() => lerFiltros(new URLSearchParams(chave)), [chave]);
  const tipos = useTipos();
  const [equipamentos, setEquipamentos] = useState([]);
  const [softwares, setSoftwares] = useState([]);
  const [filtroSoftware, setFiltroSoftware] = useState('');
  const [aulasDoDia, setAulasDoDia] = useState([]);
  const [busca, setBusca] = useState(filtros.busca);
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);

  useEffect(() => {
    listarEquipamentos().then(setEquipamentos, () => setEquipamentos([]));
    listarSoftwares().then(setSoftwares, () => setSoftwares([]));
  }, []);

  useEffect(() => {
    if (!filtros.data) {
      setAulasDoDia([]);
      return undefined;
    }
    let ativo = true;
    listarHorarios({ dia_semana: diaSemanaIso(filtros.data) }).then(
      (lista) => ativo && setAulasDoDia(lista),
      () => ativo && setAulasDoDia([]),
    );
    return () => {
      ativo = false;
    };
  }, [filtros.data]);

  const atualizar = useCallback(
    (mudancas) => {
      setParams(
        (atual) => {
          const novo = new URLSearchParams(atual);
          for (const [k, v] of Object.entries(mudancas)) {
            novo.delete(k);
            if (Array.isArray(v)) v.forEach((x) => novo.append(k, String(x)));
            else if (v !== '' && v !== null && v !== undefined) novo.set(k, String(v));
          }
          return novo;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  // Busca com atraso para não consultar a cada tecla.
  useEffect(() => {
    if (busca === filtros.busca) return undefined;
    const t = setTimeout(() => atualizar({ busca: busca.trim() }), 400);
    return () => clearTimeout(t);
  }, [busca, filtros.busca, atualizar]);

  const consultaDisponibilidade = filtros.data && filtros.horario_ids.length > 0;

  const carregar = useCallback(() => {
    const f = lerFiltros(new URLSearchParams(chave));
    const query = {
      tipo: f.tipo,
      capacidade_min: f.capacidade_min,
      equipamento_id: f.equipamento_id,
      software_id: f.software_id,
      busca: f.busca,
    };
    if (f.data && f.horario_ids.length > 0) {
      query.data = f.data;
      query.horario_ids = f.horario_ids;
    }
    return listarSalas(query);
  }, [chave]);

  const { dados: salas, erro, carregando } = useCarregar(carregar);

  const alternarLista = (nome, valor) => {
    const atual = filtros[nome];
    atualizar({ [nome]: atual.includes(valor) ? atual.filter((v) => v !== valor) : [...atual, valor] });
  };

  const limpar = () => {
    setBusca('');
    setParams(new URLSearchParams(), { replace: true });
  };

  const totalFiltros =
    CHAVES_LISTA.reduce((n, k) => n + (k === 'horario_ids' ? 0 : filtros[k].length), 0) +
    (filtros.capacidade_min ? 1 : 0) +
    (filtros.busca ? 1 : 0) +
    (filtros.data ? 1 : 0);

  const softwaresVisiveis = softwares.filter((s) =>
    `${s.nome} ${s.versao || ''} ${s.categoria || ''}`.toLowerCase().includes(filtroSoftware.toLowerCase()),
  );

  return (
    <section className="pagina">
      <div className="pagina-titulo">
        <h1>Ambientes</h1>
        <p className="texto-suave">Salas de aula, laboratórios e outros espaços disponíveis para reserva.</p>
      </div>

      <div className="layout-filtros">
        <aside className={filtrosAbertos ? 'painel-filtros aberto' : 'painel-filtros'} aria-label="Filtros">
          <button
            type="button"
            className="botao botao-secundario filtros-alternar"
            aria-expanded={filtrosAbertos}
            onClick={() => setFiltrosAbertos((v) => !v)}
          >
            Filtros{totalFiltros > 0 ? ` (${totalFiltros})` : ''}
          </button>
          <div className="painel-filtros-conteudo">
            <div className="campo">
              <label htmlFor="filtro-busca">Buscar</label>
              <input
                id="filtro-busca"
                type="search"
                placeholder="Nome, descrição ou local"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
              />
            </div>

            <fieldset className="filtro-grupo">
              <legend>Tipo</legend>
              <ul className="lista-marcavel">
                {tipos.map((t) => (
                  <li key={t.valor}>
                    <label className="opcao">
                      <input
                        type="checkbox"
                        checked={filtros.tipo.includes(t.valor)}
                        onChange={() => alternarLista('tipo', t.valor)}
                      />
                      <span>{t.rotulo}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </fieldset>

            <div className="campo">
              <label htmlFor="filtro-capacidade">Capacidade mínima</label>
              <input
                id="filtro-capacidade"
                type="number"
                min="1"
                inputMode="numeric"
                placeholder="Ex.: 30"
                value={filtros.capacidade_min}
                onChange={(e) => atualizar({ capacidade_min: e.target.value })}
              />
            </div>

            <fieldset className="filtro-grupo filtro-livre">
              <legend>Livre em</legend>
              <div className="campo">
                <label htmlFor="filtro-data">Data</label>
                <input
                  id="filtro-data"
                  type="date"
                  value={filtros.data}
                  onChange={(e) => atualizar({ data: e.target.value, horario_ids: [] })}
                />
              </div>
              {filtros.data && (
                <SeletorAulas
                  legenda="Aulas seguidas"
                  itens={aulasDoDia.map((h) => ({ horario: h }))}
                  selecionadas={filtros.horario_ids}
                  aoMudar={(ids) => atualizar({ horario_ids: ids })}
                />
              )}
            </fieldset>

            <ListaMarcavel
              legenda="Equipamentos"
              itens={equipamentos}
              marcados={filtros.equipamento_id}
              aoAlternar={(id) => alternarLista('equipamento_id', id)}
              vazio="Nenhum equipamento cadastrado."
              rotulo={(e) => e.nome}
            />

            <fieldset className="filtro-grupo">
              <legend>Softwares</legend>
              {softwares.length > 6 && (
                <div className="campo campo-compacto">
                  <label htmlFor="filtro-software-busca" className="sr-only">
                    Filtrar lista de softwares
                  </label>
                  <input
                    id="filtro-software-busca"
                    type="search"
                    placeholder="Filtrar softwares"
                    value={filtroSoftware}
                    onChange={(e) => setFiltroSoftware(e.target.value)}
                  />
                </div>
              )}
              <ul className="lista-marcavel lista-rolavel">
                {softwaresVisiveis.map((s) => (
                  <li key={s.id}>
                    <label className="opcao">
                      <input
                        type="checkbox"
                        checked={filtros.software_id.includes(s.id)}
                        onChange={() => alternarLista('software_id', s.id)}
                      />
                      <span>
                        {s.nome}
                        {s.versao ? ` ${s.versao}` : ''}
                        {s.categoria && <small className="texto-suave"> · {s.categoria}</small>}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
              {softwares.length === 0 && <p className="texto-suave texto-pequeno">Nenhum software cadastrado.</p>}
            </fieldset>

            {totalFiltros > 0 && (
              <button type="button" className="botao botao-secundario botao-bloco" onClick={limpar}>
                Limpar filtros
              </button>
            )}
          </div>
        </aside>

        <div className="resultados">
          {filtros.data && filtros.horario_ids.length === 0 && (
            <p className="dica">Escolha as aulas para ver só os ambientes livres em {formatarDataLonga(filtros.data)}.</p>
          )}
          {consultaDisponibilidade && !erro && (
            <p className="dica dica-destaque">
              Mostrando ambientes livres em {formatarDataLonga(filtros.data)} nas aulas escolhidas.
            </p>
          )}
          <ErroApiAlerta erro={erro} titulo="Não foi possível aplicar os filtros" />
          {carregando && <Carregando texto="Buscando ambientes…" />}
          {!carregando && salas && (
            <>
              <p className="contagem" aria-live="polite">
                {plural(salas.length, 'ambiente encontrado', 'ambientes encontrados')}
              </p>
              {salas.length === 0 ? (
                <EstadoVazio titulo="Nenhum ambiente atende aos filtros.">
                  {totalFiltros > 0 && (
                    <button type="button" className="botao botao-secundario" onClick={limpar}>
                      Limpar filtros
                    </button>
                  )}
                </EstadoVazio>
              ) : (
                <div className="grade-salas">
                  {salas.map((s) => (
                    <CartaoSala key={s.id} sala={s} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
