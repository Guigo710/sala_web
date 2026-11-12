import { useState } from 'react';
import { trocarSenha } from '../api/auth';
import { useAuth } from '../auth/contexto';
import Alerta from '../components/Alerta';
import ErroApiAlerta from '../components/ErroApiAlerta';

export default function MinhaConta() {
  const { usuario } = useAuth();
  const [senhaAtual, setSenhaAtual] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmacao, setConfirmacao] = useState('');
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const erroLocal =
    novaSenha && novaSenha.length < 8
      ? 'A nova senha precisa ter pelo menos 8 caracteres.'
      : confirmacao && novaSenha !== confirmacao
        ? 'A confirmação não confere com a nova senha.'
        : '';

  const aoEnviar = async (e) => {
    e.preventDefault();
    if (erroLocal) return;
    setErro(null);
    setSucesso(false);
    setEnviando(true);
    try {
      await trocarSenha(senhaAtual, novaSenha);
      setSucesso(true);
      setSenhaAtual('');
      setNovaSenha('');
      setConfirmacao('');
    } catch (err) {
      setErro(err);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <section className="pagina pagina-estreita">
      <h1>Minha conta</h1>
      <dl className="dados-conta cartao">
        <div>
          <dt>Nome</dt>
          <dd>{usuario.nome}</dd>
        </div>
        <div>
          <dt>RM</dt>
          <dd>{usuario.rm}</dd>
        </div>
        <div>
          <dt>E-mail</dt>
          <dd>{usuario.email || '—'}</dd>
        </div>
        <div>
          <dt>Papel</dt>
          <dd>{usuario.papel === 'admin' ? 'Administrador' : 'Professor'}</dd>
        </div>
      </dl>

      <h2>Trocar senha</h2>
      <form className="formulario cartao" onSubmit={aoEnviar}>
        {sucesso && <Alerta tipo="sucesso">Senha alterada com sucesso.</Alerta>}
        <ErroApiAlerta erro={erro} />
        <div className="campo">
          <label htmlFor="senha-atual">Senha atual</label>
          <input
            id="senha-atual"
            type="password"
            autoComplete="current-password"
            required
            value={senhaAtual}
            onChange={(e) => setSenhaAtual(e.target.value)}
            aria-invalid={erro?.codigo === 'SENHA_ATUAL_INCORRETA' || undefined}
          />
        </div>
        <div className="campo">
          <label htmlFor="nova-senha">Nova senha</label>
          <input
            id="nova-senha"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={novaSenha}
            onChange={(e) => setNovaSenha(e.target.value)}
            aria-describedby="nova-senha-ajuda"
          />
          <small id="nova-senha-ajuda" className="ajuda">
            Mínimo de 8 caracteres.
          </small>
        </div>
        <div className="campo">
          <label htmlFor="confirmar-senha">Confirmar nova senha</label>
          <input
            id="confirmar-senha"
            type="password"
            autoComplete="new-password"
            required
            value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value)}
          />
        </div>
        {erroLocal && (
          <p className="erro-campo" role="alert">
            {erroLocal}
          </p>
        )}
        <div className="acoes">
          <button
            type="submit"
            className="botao"
            disabled={enviando || !senhaAtual || !novaSenha || !confirmacao || Boolean(erroLocal)}
          >
            {enviando ? 'Salvando…' : 'Trocar senha'}
          </button>
        </div>
      </form>
    </section>
  );
}
