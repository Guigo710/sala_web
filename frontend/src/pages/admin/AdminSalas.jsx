import { useState } from 'react';
import { Link } from 'react-router-dom';
import { atualizarSala, excluirSala, listarSalas, obterSala } from '../../api/salas';
import { useCarregar } from '../../hooks/useCarregar';
import { useAvisos } from '../../components/avisos';
import { useConfirmar } from '../../components/useConfirmar';
import Carregando from '../../components/Carregando';
import EstadoVazio from '../../components/EstadoVazio';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import { corpoSala } from '../../utils/salas';

const listar = () => listarSalas({ incluir_inativas: true });

export default function AdminSalas() {
  const { avisar } = useAvisos();
  const [confirmar, dialogo] = useConfirmar();
  const { dados: salas, erro, carregando, recarregar } = useCarregar(listar);
  const [erroAcao, setErroAcao] = useState(null);
  const [busca, setBusca] = useState('');

  const alternarAtivo = async (resumo) => {
    setErroAcao(null);
    try {
      // PUT substitui todos os campos básicos: busca o detalhe para não perder a descrição.
      const sala = await obterSala(resumo.id);
      await atualizarSala(sala.id, { ...corpoSala(sala), ativo: !sala.ativo });
      avisar(sala.ativo ? `${sala.nome} desativado.` : `${sala.nome} ativado.`);
      recarregar();
    } catch (err) {
      setErroAcao(err);
    }
  };

  const remover = async (sala) => {
    const ok = await confirmar({
      titulo: 'Excluir ambiente',
      mensagem: `Excluir “${sala.nome}”, com suas fotos e associações? Ambientes com reservas não podem ser excluídos: desative-os.`,
      textoConfirmar: 'Excluir',
      perigo: true,
    });
    if (!ok) return;
    setErroAcao(null);
    try {
      await excluirSala(sala.id);
      avisar(`${sala.nome} excluído.`);
      recarregar();
    } catch (err) {
      setErroAcao(Object.assign(err, { alvo: sala }));
    }
  };

  const visiveis = (salas || []).filter(
    (s) => !busca || `${s.nome} ${s.localizacao || ''} ${s.tipo_rotulo}`.toLowerCase().includes(busca.toLowerCase()),
  );

  return (
    <div className="admin-secao">
      <div className="admin-secao-cabecalho">
        <div>
          <h2>Ambientes</h2>
          <p className="texto-suave">Salas, laboratórios e outros espaços, incluindo os inativos.</p>
        </div>
        <Link to="novo" className="botao">
          Novo ambiente
        </Link>
      </div>

      <div className="campo campo-compacto campo-busca">
        <label htmlFor="admin-salas-busca">Buscar</label>
        <input id="admin-salas-busca" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
      </div>

      <ErroApiAlerta erro={erro} />
      {erroAcao && (
        <ErroApiAlerta
          erro={erroAcao}
          acao={
            erroAcao.codigo === 'SALA_COM_RESERVAS' && erroAcao.alvo?.ativo ? (
              <button type="button" className="botao botao-pequeno" onClick={() => alternarAtivo(erroAcao.alvo)}>
                Desativar ambiente
              </button>
            ) : null
          }
        />
      )}
      {carregando && !salas && <Carregando />}
      {salas &&
        (visiveis.length === 0 ? (
          <EstadoVazio titulo="Nenhum ambiente encontrado." />
        ) : (
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">Nome</th>
                  <th scope="col">Tipo</th>
                  <th scope="col" className="num">
                    Capacidade
                  </th>
                  <th scope="col">Localização</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="acoes-col">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((s) => (
                  <tr key={s.id} className={s.ativo ? '' : 'linha-inativa'}>
                    <td>
                      <Link to={String(s.id)}>
                        <strong>{s.nome}</strong>
                      </Link>
                    </td>
                    <td>{s.tipo_rotulo}</td>
                    <td className="num">{s.capacidade}</td>
                    <td>{s.localizacao || <span className="texto-suave">—</span>}</td>
                    <td>
                      {s.ativo ? <span className="selo selo-ativa">Ativo</span> : <span className="selo selo-inativo">Inativo</span>}
                    </td>
                    <td className="acoes-col">
                      <div className="acoes-linha">
                        <Link to={String(s.id)} className="botao botao-secundario botao-pequeno">
                          Editar
                        </Link>
                        <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => alternarAtivo(s)}>
                          {s.ativo ? 'Desativar' : 'Ativar'}
                        </button>
                        <button type="button" className="botao botao-perigo-leve botao-pequeno" onClick={() => remover(s)}>
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      {dialogo}
    </div>
  );
}
