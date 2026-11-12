import { useCallback, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router';
import { obterSala } from '../api/salas';
import { useAuth } from '../auth/contexto';
import { useCarregar } from '../hooks/useCarregar';
import Carregando from '../components/Carregando';
import DisponibilidadeDia from '../components/DisponibilidadeDia';
import ErroApiAlerta from '../components/ErroApiAlerta';
import Galeria from '../components/Galeria';
import ModalReserva from '../components/ModalReserva';
import { hojeIso } from '../utils/datas';
import { corDoTipo } from '../utils/formatacao';

export default function SalaDetalhe() {
  const { id } = useParams();
  const { usuario } = useAuth();
  const location = useLocation();
  const [data, setData] = useState(hojeIso());
  const [reservando, setReservando] = useState(false);
  const [versao, setVersao] = useState(0);

  const carregar = useCallback(() => obterSala(id), [id]);
  const { dados: sala, erro, carregando } = useCarregar(carregar);

  if (carregando) return <Carregando texto="Carregando ambiente…" />;
  if (erro) {
    return (
      <section className="pagina">
        <p>
          <Link to="/ambientes">← Ambientes</Link>
        </p>
        <ErroApiAlerta
          erro={erro}
          titulo={erro.status === 404 ? 'Ambiente não encontrado' : 'Não foi possível carregar o ambiente'}
        />
      </section>
    );
  }

  return (
    <section className="pagina">
      <nav className="migalhas" aria-label="Você está em">
        <Link to="/ambientes">Ambientes</Link> <span aria-hidden="true">›</span> <span>{sala.nome}</span>
      </nav>

      <header className="sala-cabecalho">
        <div>
          <span className="selo-tipo selo-tipo-inline" style={{ '--cor-tipo': corDoTipo(sala.tipo) }}>
            {sala.tipo_rotulo}
          </span>
          {!sala.ativo && <span className="selo selo-inativo">Inativo</span>}
          <h1>{sala.nome}</h1>
          <p className="sala-meta">
            <span>
              <strong>{sala.capacidade}</strong> lugares
            </span>
            {sala.localizacao && <span>{sala.localizacao}</span>}
          </p>
        </div>
        <div className="sala-cabecalho-acoes">
          {usuario ? (
            <button type="button" className="botao" onClick={() => setReservando(true)} disabled={!sala.ativo}>
              Reservar
            </button>
          ) : (
            <Link to="/login" state={{ de: location }} className="botao botao-secundario">
              Entre para reservar
            </Link>
          )}
        </div>
      </header>

      <div className="sala-grade">
        <div className="sala-coluna-principal">
          <Galeria fotos={sala.fotos} nomeSala={sala.nome} />

          {sala.descricao && (
            <section className="secao">
              <h2>Descrição</h2>
              <p className="texto-pre">{sala.descricao}</p>
            </section>
          )}

          <section className="secao">
            <h2>Equipamentos</h2>
            {sala.equipamentos.length === 0 ? (
              <p className="texto-suave">Nenhum equipamento cadastrado.</p>
            ) : (
              <div className="tabela-rolavel">
                <table className="tabela">
                  <thead>
                    <tr>
                      <th scope="col">Equipamento</th>
                      <th scope="col" className="num">
                        Qtd.
                      </th>
                      <th scope="col">Especificação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sala.equipamentos.map((e) => (
                      <tr key={e.equipamento_id}>
                        <td>{e.nome}</td>
                        <td className="num">{e.quantidade}</td>
                        <td>{e.especificacao || <span className="texto-suave">—</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="secao">
            <h2>Softwares instalados</h2>
            {sala.softwares.length === 0 ? (
              <p className="texto-suave">Nenhum software cadastrado.</p>
            ) : (
              <ul className="lista-softwares">
                {sala.softwares.map((s) => (
                  <li key={s.id}>
                    <span className="software-nome">
                      {s.nome}
                      {s.versao && <span className="software-versao"> {s.versao}</span>}
                    </span>
                    {s.categoria && <span className="selo selo-categoria">{s.categoria}</span>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="sala-coluna-lateral">
          <section className="secao cartao">
            <h2>Disponibilidade</h2>
            <div className="campo">
              <label htmlFor="disp-data">Data</label>
              <input id="disp-data" type="date" value={data} onChange={(e) => e.target.value && setData(e.target.value)} />
            </div>
            <DisponibilidadeDia salaId={sala.id} data={data} versao={versao} />
            {usuario && sala.ativo && (
              <button type="button" className="botao botao-bloco" onClick={() => setReservando(true)}>
                Reservar nesta data
              </button>
            )}
          </section>
        </aside>
      </div>

      <ModalReserva
        aberto={reservando}
        aoFechar={() => setReservando(false)}
        aoConcluir={() => setVersao((v) => v + 1)}
        salaInicial={sala.id}
        dataInicial={data}
      />
    </section>
  );
}
