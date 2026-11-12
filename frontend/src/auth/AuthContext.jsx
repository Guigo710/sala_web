import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { login, obterUsuarioAtual } from '../api/auth';
import { aoSessaoExpirada, definirToken } from '../api/cliente';
import { AuthContext } from './contexto';
import { lerSessao, limparSessao, salvarSessao } from './sessao';

/**
 * Sessão do usuário: token em localStorage, `GET /auth/me` ao abrir o app.
 * 401 em rota protegida limpa a sessão e leva a /login (voltando depois para onde estava).
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [carregando, setCarregando] = useState(() => Boolean(lerSessao()));
  const [mensagemSessao, setMensagemSessao] = useState('');
  // true depois de "Sair": páginas protegidas levam à agenda, não ao login.
  const [saiu, setSaiu] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const locationRef = useRef(location);
  locationRef.current = location;
  // Durante a verificação inicial (GET /auth/me), token vencido só limpa a sessão, sem redirecionar.
  const verificandoRef = useRef(true);

  const sair = useCallback(() => {
    limparSessao();
    definirToken(null);
    setUsuario(null);
    setSaiu(true);
  }, []);

  useEffect(() => {
    aoSessaoExpirada(() => {
      limparSessao();
      definirToken(null);
      setUsuario(null);
      if (verificandoRef.current) return;
      setMensagemSessao('Sua sessão expirou. Entre novamente.');
      const atual = locationRef.current;
      if (atual.pathname !== '/login') {
        navigate('/login', { replace: true, state: { de: atual } });
      }
    });
    return () => aoSessaoExpirada(null);
  }, [navigate]);

  useEffect(() => {
    const sessao = lerSessao();
    if (!sessao) {
      verificandoRef.current = false;
      return undefined;
    }
    let ativo = true;
    verificandoRef.current = true;
    definirToken(sessao.token);
    obterUsuarioAtual()
      .then((u) => ativo && setUsuario(u))
      .catch((erro) => {
        if (!ativo) return;
        // 401 já tratado pelo cliente; outros erros (rede) mantêm o token para tentar depois.
        if (erro.status === 401) {
          limparSessao();
          definirToken(null);
          setUsuario(null);
        }
      })
      .finally(() => {
        if (!ativo) return;
        verificandoRef.current = false;
        setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, []);

  const entrar = useCallback(async (rm, senha) => {
    const resposta = await login(rm, senha);
    salvarSessao(resposta.access_token, resposta.expira_em);
    definirToken(resposta.access_token);
    setUsuario(resposta.usuario);
    setMensagemSessao('');
    setSaiu(false);
    return resposta.usuario;
  }, []);

  const valor = useMemo(
    () => ({
      usuario,
      carregando,
      ehAdmin: usuario?.papel === 'admin',
      entrar,
      sair,
      saiu,
      mensagemSessao,
    }),
    [usuario, carregando, entrar, sair, saiu, mensagemSessao],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
