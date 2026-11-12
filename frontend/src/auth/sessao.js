/** Guarda o token JWT em localStorage (ADR-0004). */
const CHAVE = 'sala_web.sessao';

export function lerSessao() {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const sessao = JSON.parse(bruto);
    if (!sessao?.token) return null;
    if (sessao.expira_em && new Date(sessao.expira_em) <= new Date()) {
      limparSessao();
      return null;
    }
    return sessao;
  } catch {
    return null;
  }
}

export function salvarSessao(token, expiraEm) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify({ token, expira_em: expiraEm || null }));
  } catch {
    // sem armazenamento (modo privado): a sessão vale só enquanto a aba estiver aberta
  }
}

export function limparSessao() {
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    // ignorado
  }
}
