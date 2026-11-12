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

describe('requisitar: casos extras (Sentinela)', () => {
  it('sem token não envia Authorization; corpo JSON com Content-Type', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(resposta(201, { id: 1 }));
    definirTransporte(fetchFalso);
    await requisitar('POST', '/reservas', { corpo: { sala_id: 3 } });
    const [url, init] = fetchFalso.mock.calls[0];
    expect(url).toMatch(/\/reservas$/);
    expect(init.headers.Authorization).toBeUndefined();
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body)).toEqual({ sala_id: 3 });
  });

  it('422 VALIDACAO traz a lista `erros`', async () => {
    definirTransporte(() =>
      Promise.resolve(
        resposta(422, {
          detail: 'Dados inválidos: body.capacidade deve ser maior que 0.',
          codigo: 'VALIDACAO',
          erros: [{ campo: 'body.capacidade', mensagem: 'deve ser maior que 0' }],
        }),
      ),
    );
    const erro = await requisitar('POST', '/salas', { corpo: {} }).catch((e) => e);
    expect(erro).toMatchObject({ status: 422, codigo: 'VALIDACAO', erros: [{ campo: 'body.capacidade' }], conflitos: null });
  });

  it('falha de rede vira SEM_CONEXAO; corpo não-JSON usa mensagem padrão', async () => {
    definirTransporte(() => Promise.reject(new TypeError('Failed to fetch')));
    await expect(requisitar('GET', '/salas')).rejects.toMatchObject({ status: 0, codigo: 'SEM_CONEXAO' });
    definirTransporte(() => Promise.resolve(new Response('<html>Bad Gateway</html>', { status: 502 })));
    await expect(requisitar('GET', '/salas')).rejects.toMatchObject({
      status: 502,
      codigo: 'ERRO_INTERNO',
      detail: 'Erro interno do servidor. Tente novamente mais tarde.',
    });
  });

  it('401 sem token enviado (visitante) não dispara o fim de sessão', async () => {
    const aoExpirar = vi.fn();
    aoSessaoExpirada(aoExpirar);
    definirTransporte(() => Promise.resolve(resposta(401, { detail: 'x', codigo: 'NAO_AUTENTICADO' })));
    await expect(requisitar('GET', '/reservas/minhas')).rejects.toBeInstanceOf(ErroApi);
    expect(aoExpirar).not.toHaveBeenCalled();
  });
});
