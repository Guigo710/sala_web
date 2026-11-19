import { act, render, screen } from '@testing-library/react';
import { definirTransporte, requisitar } from '../api/cliente';
import { acordarApi, reiniciarAcordarApi } from '../api/saude';
import AvisoServidor from './AvisoServidor';

const TEXTO = /O servidor está acordando/;
const json = (corpo) => new Response(JSON.stringify(corpo), { status: 200, headers: { 'Content-Type': 'application/json' } });

afterEach(() => {
  definirTransporte(null);
  reiniciarAcordarApi();
  vi.useRealTimers();
});

describe('AvisoServidor (ticket 66)', () => {
  it('GET que demora 5 s mostra o aviso depois de ~4 s e o esconde ao responder', async () => {
    vi.useFakeTimers();
    definirTransporte(() => new Promise((resolver) => setTimeout(() => resolver(json([{ id: 1 }])), 5000)));
    render(<AvisoServidor />);
    const regiao = screen.getByRole('status');
    expect(regiao).toBeEmptyDOMElement();

    let dados;
    act(() => {
      requisitar('GET', '/salas').then((d) => (dados = d));
    });
    await act(() => vi.advanceTimersByTimeAsync(3900));
    expect(screen.queryByText(TEXTO)).not.toBeInTheDocument();

    await act(() => vi.advanceTimersByTimeAsync(200));
    expect(screen.getByRole('status')).toHaveTextContent(TEXTO);

    await act(() => vi.advanceTimersByTimeAsync(1000));
    expect(dados).toEqual([{ id: 1 }]);
    expect(screen.queryByText(TEXTO)).not.toBeInTheDocument();
  });

  it('resposta rápida nunca mostra o aviso', async () => {
    vi.useFakeTimers();
    definirTransporte(() => Promise.resolve(json({ status: 'ok' })));
    render(<AvisoServidor />);
    await act(() => requisitar('GET', '/saude'));
    await act(() => vi.advanceTimersByTimeAsync(10_000));
    expect(screen.queryByText(TEXTO)).not.toBeInTheDocument();
  });
});

describe('acordarApi (ticket 66)', () => {
  it('dispara GET /saude uma vez só, sem esperar a resposta nem bloquear a renderização', () => {
    const fetchFalso = vi.fn(() => new Promise(() => {})); // API dormindo: nunca responde
    definirTransporte(fetchFalso);

    expect(acordarApi()).toBeUndefined(); // não devolve promessa para ninguém esperar
    acordarApi();
    render(<p>Tela inicial</p>);

    expect(screen.getByText('Tela inicial')).toBeInTheDocument();
    expect(fetchFalso).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFalso.mock.calls[0];
    expect(url).toMatch(/\/saude$/);
    expect(init.method).toBe('GET');
  });

  it('erro no /saude é ignorado (não vira rejeição sem tratamento)', async () => {
    definirTransporte(() => Promise.resolve(new Response('', { status: 404 })));
    acordarApi();
    await new Promise((r) => setTimeout(r, 0));
  });
});
