import { useCallback, useEffect, useState } from 'react';

/**
 * Executa `carregar()` (memoize com useCallback) e expõe { dados, erro, carregando, recarregar, setDados }.
 * Reexecuta quando `carregar` muda. Respostas antigas são descartadas.
 */
export function useCarregar(carregar) {
  const [estado, setEstado] = useState({ dados: null, erro: null, carregando: true });
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let ativo = true;
    setEstado((e) => ({ ...e, carregando: true, erro: null }));
    Promise.resolve()
      .then(carregar)
      .then(
        (dados) => ativo && setEstado({ dados, erro: null, carregando: false }),
        (erro) => ativo && setEstado({ dados: null, erro, carregando: false }),
      );
    return () => {
      ativo = false;
    };
  }, [carregar, versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const setDados = useCallback(
    (atualizar) =>
      setEstado((e) => ({
        ...e,
        dados: typeof atualizar === 'function' ? atualizar(e.dados) : atualizar,
      })),
    [],
  );

  return { ...estado, recarregar, setDados };
}
