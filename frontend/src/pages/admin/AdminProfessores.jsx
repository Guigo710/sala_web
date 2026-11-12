import { useCallback, useEffect, useState } from 'react';
import {
  atualizarProfessor,
  criarProfessor,
  excluirProfessor,
  listarProfessores,
  redefinirSenhaProfessor,
} from '../../api/professores';
import { useAuth } from '../../auth/contexto';
import { useCarregar } from '../../hooks/useCarregar';
import { useAvisos } from '../../components/avisos';
import { useConfirmar } from '../../components/useConfirmar';
import Alerta from '../../components/Alerta';
import Carregando from '../../components/Carregando';
import EstadoVazio from '../../components/EstadoVazio';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import Modal from '../../components/Modal';

const RM_REGEX = /^[A-Za-z0-9]{3,20}$/;

function FormProfessor({ professor, aoSalvar, aoCancelar, ehVoceMesmo }) {
  const novo = !professor;
  const [v, setV] = useState({
    rm: professor?.rm ?? '',
    nome: professor?.nome ?? '',
    email: professor?.email ?? '',
    senha: '',
    papel: professor?.papel ?? 'professor',
    ativo: professor?.ativo ?? true,
  });
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const mudar = (k, valor) => setV((x) => ({ ...x, [k]: valor }));

  const erroLocal =
    novo && v.rm && !RM_REGEX.test(v.rm)
      ? 'O RM deve ter de 3 a 20 letras ou números.'
      : novo && v.senha && v.senha.length < 8
        ? 'A senha inicial precisa ter pelo menos 8 caracteres.'
        : '';

  const enviar = async (e) => {
    e.preventDefault();
    if (erroLocal) return;
    setErro(null);
    setSalvando(true);
    try {
      const email = v.email.trim() || null;
      if (novo) {
        await criarProfessor({ rm: v.rm.trim(), nome: v.nome.trim(), email, senha: v.senha, papel: v.papel });
      } else {
        await atualizarProfessor(professor.id, { nome: v.nome.trim(), email, papel: v.papel, ativo: v.ativo });
      }
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
            <label htmlFor="prof-rm">RM</label>
            <input
              id="prof-rm"
              required
              value={v.rm}
              disabled={!novo}
              maxLength={20}
              autoComplete="off"
              onChange={(e) => mudar('rm', e.target.value)}
              data-autofocus={novo || undefined}
            />
            {!novo && <small className="ajuda">O RM não pode ser alterado.</small>}
          </div>
          <div className="campo">
            <label htmlFor="prof-papel">Papel</label>
            <select
              id="prof-papel"
              value={v.papel}
              onChange={(e) => mudar('papel', e.target.value)}
              disabled={ehVoceMesmo}
            >
              <option value="professor">Professor</option>
              <option value="admin">Administrador</option>
            </select>
            {ehVoceMesmo && <small className="ajuda">Você não pode remover seu próprio papel de admin.</small>}
          </div>
        </div>
        <div className="campo">
          <label htmlFor="prof-nome">Nome</label>
          <input
            id="prof-nome"
            required
            maxLength={120}
            value={v.nome}
            onChange={(e) => mudar('nome', e.target.value)}
            data-autofocus={!novo || undefined}
          />
        </div>
        <div className="campo">
          <label htmlFor="prof-email">
            E-mail <span className="texto-suave">(opcional)</span>
          </label>
          <input id="prof-email" type="email" maxLength={160} value={v.email} onChange={(e) => mudar('email', e.target.value)} />
        </div>
        {novo ? (
          <div className="campo">
            <label htmlFor="prof-senha">Senha inicial</label>
            <input
              id="prof-senha"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={v.senha}
              onChange={(e) => mudar('senha', e.target.value)}
            />
            <small className="ajuda">Mínimo de 8 caracteres. O professor pode trocá-la em “Minha conta”.</small>
          </div>
        ) : (
          <label className="opcao">
            <input type="checkbox" checked={v.ativo} disabled={ehVoceMesmo} onChange={(e) => mudar('ativo', e.target.checked)} />
            <span>Conta ativa</span>
          </label>
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

function FormSenha({ professor, aoSalvar, aoCancelar }) {
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const curta = senha && senha.length < 8;

  const enviar = async (e) => {
    e.preventDefault();
    if (curta) return;
    setErro(null);
    setSalvando(true);
    try {
      await redefinirSenhaProfessor(professor.id, senha);
      aoSalvar();
    } catch (err) {
      setErro(err);
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="formulario">
      <div className="modal-corpo-conteudo">
        <p>
          Nova senha para <strong>{professor.nome}</strong> (RM {professor.rm}).
        </p>
        <ErroApiAlerta erro={erro} />
        <div className="campo">
          <label htmlFor="nova-senha-prof">Nova senha</label>
          <input
            id="nova-senha-prof"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            data-autofocus
          />
          <small className="ajuda">Mínimo de 8 caracteres.</small>
        </div>
        {curta && (
          <p className="erro-campo" role="alert">
            A senha precisa ter pelo menos 8 caracteres.
          </p>
        )}
      </div>
      <footer className="modal-rodape">
        <button type="button" className="botao botao-secundario" onClick={aoCancelar}>
          Cancelar
        </button>
        <button type="submit" className="botao" disabled={salvando || !senha || curta}>
          {salvando ? 'Salvando…' : 'Redefinir senha'}
        </button>
      </footer>
    </form>
  );
}

export default function AdminProfessores() {
  const { usuario } = useAuth();
  const { avisar } = useAvisos();
  const [confirmar, dialogo] = useConfirmar();
  const [busca, setBusca] = useState('');
  const [buscaAplicada, setBuscaAplicada] = useState('');
  const [papel, setPapel] = useState('');
  const [ativo, setAtivo] = useState('');
  const [editando, setEditando] = useState(null); // { professor|null }
  const [senhaDe, setSenhaDe] = useState(null);
  const [erroAcao, setErroAcao] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => setBuscaAplicada(busca.trim()), 350);
    return () => clearTimeout(t);
  }, [busca]);

  const carregar = useCallback(
    () => listarProfessores({ busca: buscaAplicada, papel, ativo }),
    [buscaAplicada, papel, ativo],
  );
  const { dados: professores, erro, carregando, recarregar } = useCarregar(carregar);

  const alternarAtivo = async (p) => {
    setErroAcao(null);
    try {
      await atualizarProfessor(p.id, { nome: p.nome, email: p.email, papel: p.papel, ativo: !p.ativo });
      avisar(p.ativo ? `Conta de ${p.nome} desativada.` : `Conta de ${p.nome} ativada.`);
      recarregar();
    } catch (err) {
      setErroAcao(err);
    }
  };

  const remover = async (p) => {
    const ok = await confirmar({
      titulo: 'Excluir conta',
      mensagem: `Excluir a conta de ${p.nome} (RM ${p.rm})? Contas com reservas não podem ser excluídas: desative-as.`,
      textoConfirmar: 'Excluir',
      perigo: true,
    });
    if (!ok) return;
    setErroAcao(null);
    try {
      await excluirProfessor(p.id);
      avisar('Conta excluída.');
      recarregar();
    } catch (err) {
      setErroAcao({ ...err, detail: err.detail, alvo: p });
    }
  };

  return (
    <div className="admin-secao">
      <div className="admin-secao-cabecalho">
        <div>
          <h2>Professores</h2>
          <p className="texto-suave">Só a administração cria contas. O RM e a senha são usados no login.</p>
        </div>
        <button type="button" className="botao" onClick={() => setEditando({ professor: null })}>
          Novo professor
        </button>
      </div>

      <div className="barra-filtros">
        <div className="campo campo-compacto">
          <label htmlFor="prof-busca">Buscar (nome ou RM)</label>
          <input id="prof-busca" type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
        <div className="campo campo-compacto">
          <label htmlFor="prof-filtro-papel">Papel</label>
          <select id="prof-filtro-papel" value={papel} onChange={(e) => setPapel(e.target.value)}>
            <option value="">Todos</option>
            <option value="professor">Professor</option>
            <option value="admin">Administrador</option>
          </select>
        </div>
        <div className="campo campo-compacto">
          <label htmlFor="prof-filtro-ativo">Situação</label>
          <select id="prof-filtro-ativo" value={ativo} onChange={(e) => setAtivo(e.target.value)}>
            <option value="">Todas</option>
            <option value="true">Ativas</option>
            <option value="false">Inativas</option>
          </select>
        </div>
      </div>

      <ErroApiAlerta erro={erro} />
      {erroAcao && (
        <ErroApiAlerta
          erro={erroAcao}
          acao={
            erroAcao.codigo === 'PROFESSOR_COM_RESERVAS' && erroAcao.alvo?.ativo ? (
              <button type="button" className="botao botao-pequeno" onClick={() => alternarAtivo(erroAcao.alvo)}>
                Desativar conta
              </button>
            ) : null
          }
        />
      )}
      {carregando && !professores && <Carregando />}
      {professores &&
        (professores.length === 0 ? (
          <EstadoVazio titulo="Nenhuma conta encontrada." />
        ) : (
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  <th scope="col">RM</th>
                  <th scope="col">Nome</th>
                  <th scope="col">E-mail</th>
                  <th scope="col">Papel</th>
                  <th scope="col">Situação</th>
                  <th scope="col" className="acoes-col">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {professores.map((p) => {
                  const voce = p.id === usuario.id;
                  return (
                    <tr key={p.id} className={p.ativo ? '' : 'linha-inativa'}>
                      <td>
                        <code>{p.rm}</code>
                      </td>
                      <td>
                        {p.nome}
                        {voce && <span className="selo">você</span>}
                      </td>
                      <td>{p.email || <span className="texto-suave">—</span>}</td>
                      <td>{p.papel === 'admin' ? <span className="selo selo-admin">admin</span> : 'Professor'}</td>
                      <td>
                        {p.ativo ? <span className="selo selo-ativa">Ativa</span> : <span className="selo selo-inativo">Inativa</span>}
                      </td>
                      <td className="acoes-col">
                        <div className="acoes-linha">
                          <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => setEditando({ professor: p })}>
                            Editar
                          </button>
                          <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => setSenhaDe(p)}>
                            Redefinir senha
                          </button>
                          {!voce && (
                            <>
                              <button type="button" className="botao botao-secundario botao-pequeno" onClick={() => alternarAtivo(p)}>
                                {p.ativo ? 'Desativar' : 'Ativar'}
                              </button>
                              <button type="button" className="botao botao-perigo-leve botao-pequeno" onClick={() => remover(p)}>
                                Excluir
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ))}

      <Modal
        aberto={Boolean(editando)}
        titulo={editando?.professor ? 'Editar conta' : 'Nova conta'}
        aoFechar={() => setEditando(null)}
      >
        {editando && (
          <FormProfessor
            professor={editando.professor}
            ehVoceMesmo={editando.professor?.id === usuario.id}
            aoCancelar={() => setEditando(null)}
            aoSalvar={() => {
              avisar(editando.professor ? 'Conta atualizada.' : 'Conta criada.');
              setEditando(null);
              recarregar();
            }}
          />
        )}
      </Modal>

      <Modal aberto={Boolean(senhaDe)} titulo="Redefinir senha" aoFechar={() => setSenhaDe(null)} tamanho="pequeno">
        {senhaDe && (
          <FormSenha
            professor={senhaDe}
            aoCancelar={() => setSenhaDe(null)}
            aoSalvar={() => {
              avisar(`Senha de ${senhaDe.nome} redefinida.`);
              setSenhaDe(null);
            }}
          />
        )}
      </Modal>
      {dialogo}
      {!carregando && professores && <Alerta tipo="info">Contas desativadas não conseguem entrar, mas o histórico de reservas é mantido.</Alerta>}
    </div>
  );
}
