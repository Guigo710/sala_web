import { aoSessaoExpirada, definirToken, definirTransporte, ErroApi, montarQuery, requisitar } from './cliente';

const resposta = (status, corpo) =>
  new Response(corpo === null ? null : JSON.stringify(corpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

afterEach(() => {
  definirToken(null);
  definirTransporte(null);
  aoSessaoExpirada(null);
});

describe('montarQuery', () => {
  it('repete parâmetros de lista e omite vazios', () => {
    expect(montarQuery({ tipo: ['a', 'b'], capacidade_min: '', busca: null, horario_ids: [1, 2] })).toBe(
      '?tipo=a&tipo=b&horario_ids=1&horario_ids=2',
    );
    expect(montarQuery({})).toBe('');
  });
});

describe('requisitar', () => {
  it('envia o token como Bearer', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(resposta(200, { ok: true }));
    definirTransporte(fetchFalso);
    definirToken('abc');
    await requisitar('GET', '/auth/me');
    expect(fetchFalso.mock.calls[0][1].headers.Authorization).toBe('Bearer abc');
  });

  it('converte o envelope de erro em ErroApi', async () => {
    definirTransporte(() =>
      Promise.resolve(
        resposta(409, {
          detail: 'Sala não disponível neste horário.',
          codigo: 'CONFLITO_RESERVA',
          conflitos: [{ data: '2026-09-15', inicio: '08:20', fim: '09:10', reserva_id: 77, sala_id: 3, professor: null }],
        }),
      ),
    );
    const erro = await requisitar('POST', '/reservas', { corpo: {} }).catch((e) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro).toMatchObject({ status: 409, codigo: 'CONFLITO_RESERVA', detail: 'Sala não disponível neste horário.' });
    expect(erro.conflitos).toHaveLength(1);
  });

  it('avisa a sessão em 401 de rota protegida, mas não no login', async () => {
    const aoExpirar = vi.fn();
    aoSessaoExpirada(aoExpirar);
    definirToken('expirado');
    definirTransporte(() => Promise.resolve(resposta(401, { detail: 'x', codigo: 'NAO_AUTENTICADO' })));
    await expect(requisitar('GET', '/reservas/minhas')).rejects.toBeInstanceOf(ErroApi);
    expect(aoExpirar).toHaveBeenCalledTimes(1);

    definirTransporte(() => Promise.resolve(resposta(401, { detail: 'RM ou senha inválidos.', codigo: 'CREDENCIAIS_INVALIDAS' })));
    await expect(requisitar('POST', '/auth/login', { corpo: {} })).rejects.toMatchObject({ codigo: 'CREDENCIAIS_INVALIDAS' });
    expect(aoExpirar).toHaveBeenCalledTimes(1);
  });

  it('204 devolve null', async () => {
    definirTransporte(() => Promise.resolve(new Response(null, { status: 204 })));
    expect(await requisitar('DELETE', '/salas/1')).toBeNull();
  });
});
