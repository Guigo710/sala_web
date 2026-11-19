import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router';
import { useAuth } from '../auth/contexto';
import Alerta from '../components/Alerta';
import { mensagemDeErro } from '../utils/formatacao';

function destinoDepoisDoLogin(state) {
  const de = state?.de;
  if (!de?.pathname || de.pathname === '/login') return '/agenda';
  return `${de.pathname}${de.search || ''}${de.hash || ''}`;
}

export default function Login() {
  const { usuario, entrar, mensagemSessao } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [rm, setRm] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);

  const destino = destinoDepoisDoLogin(location.state);

  if (usuario && !enviando) return <Navigate to={destino} replace />;

  const aoEnviar = async (e) => {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(rm.trim(), senha);
      navigate(destino, { replace: true });
    } catch (err) {
      setErro(err);
      setEnviando(false);
    }
  };

  return (
    <section className="pagina pagina-login">
      <div className="cartao cartao-login">
        <h1>Entrar</h1>
        <p className="texto-suave">Use seu RM e a senha fornecida pela administração.</p>

        {mensagemSessao && !erro && <Alerta tipo="aviso">{mensagemSessao}</Alerta>}
        {erro && (
          <Alerta tipo="erro" titulo={erro.codigo === 'MUITAS_TENTATIVAS' ? 'Muitas tentativas' : undefined}>
            {mensagemDeErro(erro)}
          </Alerta>
        )}

        <form onSubmit={aoEnviar} className="formulario" noValidate={false}>
          <div className="campo">
            <label htmlFor="login-rm">RM</label>
            <input
              id="login-rm"
              name="rm"
              autoComplete="username"
              required
              value={rm}
              onChange={(e) => setRm(e.target.value)}
              autoFocus
            />
          </div>
          <div className="campo">
            <label htmlFor="login-senha">Senha</label>
            <input
              id="login-senha"
              name="senha"
              type="password"
              autoComplete="current-password"
              required
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
            />
          </div>
          <button type="submit" className="botao botao-bloco" disabled={enviando || !rm || !senha}>
            {enviando ? 'Entrando…' : 'Entrar'}
          </button>
        </form>
        <p className="texto-suave texto-pequeno">
          Não tem conta ou esqueceu a senha? Procure a administração: só ela cria contas e redefine senhas.
        </p>
      </div>
    </section>
  );
}
