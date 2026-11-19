import {
  aoSessaoExpirada,
  definirToken,
  definirTransporte,
  enviarFormulario,
  ErroApi,
  montarQuery,
  PRAZO_REPETICAO_MS,
  requisitar,
} from './cliente';
import { haLentidao } from './lentidao';

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

  // POST: falhas de rede e 502 não são repetidas (ticket 66), então o erro chega na hora.
  it('falha de rede vira SEM_CONEXAO; corpo não-JSON usa mensagem padrão', async () => {
    definirTransporte(() => Promise.reject(new TypeError('Failed to fetch')));
    await expect(requisitar('POST', '/salas', { corpo: {} })).rejects.toMatchObject({ status: 0, codigo: 'SEM_CONEXAO' });
    definirTransporte(() => Promise.resolve(new Response('<html>Bad Gateway</html>', { status: 502 })));
    await expect(requisitar('POST', '/salas', { corpo: {} })).rejects.toMatchObject({
      status: 502,
      codigo: 'ERRO_INTERNO',
      detail: 'O servidor está indisponível no momento (pode estar acordando). Tente de novo em instantes.',
    });
    definirTransporte(() => Promise.resolve(new Response('<html>Erro</html>', { status: 500 })));
    await expect(requisitar('POST', '/salas', { corpo: {} })).rejects.toMatchObject({
      status: 500,
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

describe('API dormindo (ticket 66): nova tentativa só em GET', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('GET com 503 seguido de 200 resolve com os dados (e marca lentidão enquanto repete)', async () => {
    const fetchFalso = vi
      .fn()
      .mockResolvedValueOnce(new Response('<html>Service Unavailable</html>', { status: 503 }))
      .mockResolvedValueOnce(resposta(200, [{ id: 3 }]));
    definirTransporte(fetchFalso);
    const promessa = requisitar('GET', '/salas');
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    expect(haLentidao()).toBe(true);
    await vi.advanceTimersByTimeAsync(1000);
    await expect(promessa).resolves.toEqual([{ id: 3 }]);
    expect(fetchFalso).toHaveBeenCalledTimes(2);
    expect(haLentidao()).toBe(false);
  });

  it('GET repete falha de rede, 502 e 504 com espera crescente', async () => {
    const fetchFalso = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(new Response('', { status: 502 }))
      .mockResolvedValueOnce(new Response('', { status: 504 }))
      .mockResolvedValueOnce(resposta(200, { status: 'ok' }));
    definirTransporte(fetchFalso);
    const promessa = requisitar('GET', '/saude');
    await vi.advanceTimersByTimeAsync(999);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1); // +1 s
    expect(fetchFalso).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(2000); // +2 s
    expect(fetchFalso).toHaveBeenCalledTimes(3);
    await vi.advanceTimersByTimeAsync(4000); // +4 s
    await expect(promessa).resolves.toEqual({ status: 'ok' });
    expect(fetchFalso).toHaveBeenCalledTimes(4);
  });

  it('GET desiste depois de ~90 s e rejeita com o último erro', async () => {
    const fetchFalso = vi.fn().mockImplementation(() => Promise.resolve(new Response('', { status: 503 })));
    definirTransporte(fetchFalso);
    const promessa = requisitar('GET', '/salas');
    const resultado = expect(promessa).rejects.toMatchObject({ status: 503 });
    await vi.advanceTimersByTimeAsync(PRAZO_REPETICAO_MS + 1000);
    await resultado;
    // 1 + 2 + 4 + 8 + 15×5 = 90 s de espera: 10 tentativas no total.
    expect(fetchFalso).toHaveBeenCalledTimes(10);
    expect(haLentidao()).toBe(false);
  });

  it('GET não repete 4xx nem 500', async () => {
    for (const status of [400, 401, 404, 409, 500]) {
      const fetchFalso = vi.fn().mockResolvedValue(resposta(status, { detail: 'x', codigo: 'X' }));
      definirTransporte(fetchFalso);
      await expect(requisitar('GET', '/salas/1')).rejects.toMatchObject({ status });
      expect(fetchFalso).toHaveBeenCalledTimes(1);
    }
  });

  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])('%s com 503 rejeita sem repetir', async (metodo) => {
    const fetchFalso = vi.fn().mockResolvedValue(new Response('', { status: 503 }));
    definirTransporte(fetchFalso);
    const erro = await requisitar(metodo, '/reservas', { corpo: {} }).catch((e) => e);
    expect(erro).toMatchObject({ status: 503, detail: expect.stringMatching(/Tente de novo em instantes/) });
    await vi.advanceTimersByTimeAsync(PRAZO_REPETICAO_MS);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  it('POST com falha de rede rejeita sem repetir', async () => {
    const fetchFalso = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    definirTransporte(fetchFalso);
    await expect(requisitar('POST', '/auth/login', { corpo: {} })).rejects.toMatchObject({ status: 0 });
    await vi.advanceTimersByTimeAsync(PRAZO_REPETICAO_MS);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  it('upload (multipart) com 503 rejeita sem repetir', async () => {
    const fetchFalso = vi.fn().mockResolvedValue(new Response('', { status: 503 }));
    definirTransporte(fetchFalso);
    await expect(enviarFormulario('/salas/3/fotos', new FormData())).rejects.toMatchObject({ status: 503 });
    await vi.advanceTimersByTimeAsync(PRAZO_REPETICAO_MS);
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });
});
