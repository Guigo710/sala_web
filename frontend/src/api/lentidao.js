/**
 * Requisições lentas à API (ticket 66, ADR-0009): na publicação a API dorme no Render Free e a primeira
 * requisição depois disso pode levar cerca de 1 minuto. Este módulo conta as requisições pendentes que já
 * passaram de `LIMITE_LENTA_MS` (ou que estão sendo repetidas) e avisa quem assinou, para a interface mostrar
 * "O servidor está acordando...". No Compose/local a API responde rápido e o aviso nunca aparece.
 */

export const LIMITE_LENTA_MS = 4000;

let lentas = 0;
const ouvintes = new Set();

function notificar() {
  for (const ouvinte of ouvintes) ouvinte();
}

/** `true` enquanto houver ao menos uma requisição lenta pendente. */
export function haLentidao() {
  return lentas > 0;
}

/** Assina mudanças (formato do `useSyncExternalStore`); devolve a função que cancela a assinatura. */
export function assinarLentidao(ouvinte) {
  ouvintes.add(ouvinte);
  return () => ouvintes.delete(ouvinte);
}

/**
 * Marca o início de uma requisição. Devolve `{ marcarLenta, terminar }`:
 * - depois de `LIMITE_LENTA_MS` sem `terminar()`, ela passa a contar como lenta;
 * - `marcarLenta()` antecipa isso (ex.: ao repetir um GET que falhou com 502/503/504);
 * - `terminar()` tira a requisição da contagem (pode ser chamada mais de uma vez).
 */
export function acompanharRequisicao() {
  let lenta = false;
  let terminada = false;
  const marcarLenta = () => {
    if (lenta || terminada) return;
    lenta = true;
    clearTimeout(relogio);
    lentas += 1;
    notificar();
  };
  const relogio = setTimeout(marcarLenta, LIMITE_LENTA_MS);
  const terminar = () => {
    if (terminada) return;
    terminada = true;
    clearTimeout(relogio);
    if (lenta) {
      lentas -= 1;
      notificar();
    }
  };
  return { marcarLenta, terminar };
}
