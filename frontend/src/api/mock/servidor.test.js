import { API_URL } from '../cliente';
import { fetchMock, reiniciarMock } from './servidor';

/** Chama o mock como o cliente faria e devolve { status, corpo }. */
async function chamar(metodo, caminho, { token, corpo } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (corpo !== undefined) headers['Content-Type'] = 'application/json';
  const r = await fetchMock(`${API_URL}${caminho}`, {
    method: metodo,
    headers,
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const texto = await r.text();
  return { status: r.status, corpo: texto ? JSON.parse(texto) : null };
}

const entrar = async (rm, senha) => (await chamar('POST', '/auth/login', { corpo: { rm, senha } })).corpo.access_token;

beforeEach(() => reiniciarMock({ atraso: false }));

describe('mock: revogação de tokens (contrato 1.2, ADR-0008)', () => {
  it('PUT /auth/me/senha responde 200 com token novo e o antigo passa a dar 401', async () => {
    const antigo = await entrar('123456', 'senha1234');
    const r = await chamar('PUT', '/auth/me/senha', {
      token: antigo,
      corpo: { senha_atual: 'senha1234', nova_senha: 'novaSenha456' },
    });
    expect(r.status).toBe(200);
    expect(r.corpo).toMatchObject({ token_type: 'bearer', usuario: { rm: '123456' } });
    expect(r.corpo.access_token).not.toBe(antigo);
    expect(r.corpo.usuario).not.toHaveProperty('senha');
    expect(r.corpo.usuario).not.toHaveProperty('token_versao');

    expect((await chamar('GET', '/auth/me', { token: antigo })).status).toBe(401);
    expect((await chamar('GET', '/auth/me', { token: r.corpo.access_token })).status).toBe(200);
  });

  it('senha atual errada não muda nada: o token segue valendo', async () => {
    const token = await entrar('123456', 'senha1234');
    const r = await chamar('PUT', '/auth/me/senha', { token, corpo: { senha_atual: 'x', nova_senha: 'novaSenha456' } });
    expect(r.corpo.codigo).toBe('SENHA_ATUAL_INCORRETA');
    expect((await chamar('GET', '/auth/me', { token })).status).toBe(200);
  });

  it('redefinição pelo admin derruba as sessões da conta, inclusive a do próprio admin', async () => {
    const admin = await entrar('admin', 'admin1234');
    const prof = await entrar('123456', 'senha1234');
    expect((await chamar('PUT', '/professores/2/senha', { token: admin, corpo: { nova_senha: 'outraSenha1' } })).status).toBe(204);
    expect((await chamar('GET', '/auth/me', { token: prof })).status).toBe(401);
    expect((await chamar('GET', '/auth/me', { token: admin })).status).toBe(200);

    expect((await chamar('PUT', '/professores/1/senha', { token: admin, corpo: { nova_senha: 'outraSenha1' } })).status).toBe(204);
    expect((await chamar('GET', '/auth/me', { token: admin })).status).toBe(401);
  });

  it('mudança de papel e desativação derrubam; nome e reativação não', async () => {
    const admin = await entrar('admin', 'admin1234');
    let prof = await entrar('123456', 'senha1234');
    const put = (dados) => chamar('PUT', '/professores/2', { token: admin, corpo: { nome: 'Maria Souza', email: null, ...dados } });

    await put({ nome: 'Maria S.', papel: 'professor', ativo: true });
    expect((await chamar('GET', '/auth/me', { token: prof })).status).toBe(200);

    await put({ papel: 'admin', ativo: true });
    expect((await chamar('GET', '/auth/me', { token: prof })).status).toBe(401);

    prof = await entrar('123456', 'senha1234');
    await put({ papel: 'admin', ativo: false });
    await put({ papel: 'admin', ativo: true });
    expect((await chamar('GET', '/auth/me', { token: prof })).status).toBe(401);
  });
});

describe('mock: alinhamentos do contrato 1.1', () => {
  it('GET /reservas aceita 62 dias contando as duas pontas e recusa 63', async () => {
    expect((await chamar('GET', '/reservas?de=2026-09-01&ate=2026-11-01')).status).toBe(200);
    const r = await chamar('GET', '/reservas?de=2026-09-01&ate=2026-11-02');
    expect(r.status).toBe(422);
    expect(r.corpo.codigo).toBe('INTERVALO_INVALIDO');
  });

  it('PUT de sala e de horário sem `ativo` dá 422 VALIDACAO', async () => {
    const admin = await entrar('admin', 'admin1234');
    const sala = (await chamar('GET', '/salas/1')).corpo;
    const corpoSala = { nome: sala.nome, tipo: sala.tipo, descricao: sala.descricao, capacidade: sala.capacidade, localizacao: sala.localizacao };
    const semAtivo = await chamar('PUT', '/salas/1', { token: admin, corpo: corpoSala });
    expect(semAtivo.status).toBe(422);
    expect(semAtivo.corpo).toMatchObject({ codigo: 'VALIDACAO', erros: [{ campo: 'body.ativo' }] });
    expect((await chamar('PUT', '/salas/1', { token: admin, corpo: { ...corpoSala, ativo: true } })).status).toBe(200);

    const h = (await chamar('GET', '/horarios/1')).corpo;
    const corpoHorario = { turno: h.turno, ordem: h.ordem, inicio: h.inicio, fim: h.fim, dias_semana: h.dias_semana };
    const r = await chamar('PUT', '/horarios/1', { token: admin, corpo: corpoHorario });
    expect(r.status).toBe(422);
    expect(r.corpo.codigo).toBe('VALIDACAO');
    expect((await chamar('PUT', '/horarios/1', { token: admin, corpo: { ...corpoHorario, ativo: true } })).status).toBe(200);
  });
});
