import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { login, obterUsuarioAtual, trocarSenha as trocarSenhaApi } from '../api/auth';
import { aoSessaoExpirada, definirToken } from '../api/cliente';
import { AuthContext } from './contexto';
import { lerSessao, limparSessao, salvarSessao } from './sessao';

/**
 * Sessão do usuário: token em localStorage, `GET /auth/me` ao abrir o app.
 * 401 em rota protegida limpa a sessão e leva a /login (voltando depois para onde estava).
 * Troca da própria senha devolve token novo (contrato 1.2, ADR-0008): grava como num login.
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

  /** Grava a sessão a partir do corpo do login (`access_token`, `expira_em`, `usuario`). */
  const iniciarSessao = useCallback((resposta) => {
    salvarSessao(resposta.access_token, resposta.expira_em);
    definirToken(resposta.access_token);
    setUsuario(resposta.usuario);
    setMensagemSessao('');
    setSaiu(false);
    return resposta.usuario;
  }, []);

  const entrar = useCallback(
    async (rm, senha) => iniciarSessao(await login(rm, senha)),
    [iniciarSessao],
  );

  /** PUT /auth/me/senha → 200 com token novo; o anterior deixa de valer (§4.2). */
  const trocarSenha = useCallback(
    async (senhaAtual, novaSenha) => iniciarSessao(await trocarSenhaApi(senhaAtual, novaSenha)),
    [iniciarSessao],
  );

  /** Encerra a sessão local (token já revogado no servidor) e leva ao login com aviso. */
  const encerrarSessao = useCallback(
    (mensagem) => {
      limparSessao();
      definirToken(null);
      setUsuario(null);
      setMensagemSessao(mensagem || '');
      navigate('/login', { replace: true });
    },
    [navigate],
  );

  const valor = useMemo(
    () => ({
      usuario,
      carregando,
      ehAdmin: usuario?.papel === 'admin',
      entrar,
      sair,
      saiu,
      mensagemSessao,
      trocarSenha,
      encerrarSessao,
    }),
    [usuario, carregando, entrar, sair, saiu, mensagemSessao, trocarSenha, encerrarSessao],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}
