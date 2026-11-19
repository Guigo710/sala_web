import { useEffect, useState } from 'react';
import { listarTipos } from '../api/salas';

let cache = null;

/** Tipos de ambiente de GET /salas/tipos (rótulos vêm da API, nunca fixos no código). */
export function useTipos() {
  const [tipos, setTipos] = useState(() => (Array.isArray(cache) ? cache : []));
  useEffect(() => {
    if (Array.isArray(cache)) return undefined;
    let ativo = true;
    if (!cache) cache = listarTipos().catch((e) => {
      cache = null;
      throw e;
    });
    cache.then(
      (lista) => {
        cache = lista;
        if (ativo) setTipos(lista);
      },
      () => {},
    );
    return () => {
      ativo = false;
    };
  }, []);
  return tipos;
}

/** Rótulo de um tipo (usa `tipo_rotulo` quando o objeto já traz). */
export function rotuloDoTipo(tipos, valor) {
  return tipos.find((t) => t.valor === valor)?.rotulo ?? valor;
}
