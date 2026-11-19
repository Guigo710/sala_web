import { useCallback, useState } from 'react';
import { useCarregar } from '../../hooks/useCarregar';
import { useAvisos } from '../../components/avisos';
import { useConfirmar } from '../../components/useConfirmar';
import Carregando from '../../components/Carregando';
import EstadoVazio from '../../components/EstadoVazio';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import Modal from '../../components/Modal';

/**
 * Cadastro simples (lista + criar/editar em modal + excluir com confirmação).
 * `campos`: [{ nome, rotulo, tipo = 'text', obrigatorio, maxLength, sugestoes, ajuda }]
 * `colunas`: [{ rotulo, valor: (item) => ReactNode, classe }]
 * `validar(valores)`: mensagem de erro local ou ''.
 */
export default function AdminCrud({
  titulo,
  descricao,
  nomeItem,
  listar,
  criar,
  atualizar,
  excluir,
  campos,
  colunas,
  rotuloItem,
  filtrar,
  validar,
  aoMudar,
}) {
  const { avisar } = useAvisos();
  const [confirmar, dialogo] = useConfirmar();
  const { dados: itens, erro, carregando, recarregar } = useCarregar(listar);
  const [editando, setEditando] = useState(null); // { item|null, valores }
  const [erroForm, setErroForm] = useState(null);
  const [erroAcao, setErroAcao] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [busca, setBusca] = useState('');

  const valoresIniciais = useCallback(
    (item) => Object.fromEntries(campos.map((c) => [c.nome, item?.[c.nome] ?? ''])),
    [campos],
  );

  const abrir = (item = null) => {
    setErroForm(null);
    setEditando({ item, valores: valoresIniciais(item) });
  };

  const mudarValor = (nome, valor) =>
    setEditando((e) => ({ ...e, valores: { ...e.valores, [nome]: valor } }));

  const erroLocal = editando && validar ? validar(editando.valores) : '';

  const salvar = async (e) => {
    e.preventDefault();
    if (erroLocal) return;
    setErroForm(null);
    setSalvando(true);
    const corpo = Object.fromEntries(
      campos.map((c) => {
        const v = editando.valores[c.nome];
        const texto = typeof v === 'string' ? v.trim() : v;
        return [c.nome, texto === '' ? null : texto];
      }),
    );
    try {
      if (editando.item) {
        await atualizar(editando.item.id, corpo);
        avisar(`${nomeItem} atualizado.`);
      } else {
        await criar(corpo);
        avisar(`${nomeItem} criado.`);
      }
      setEditando(null);
      recarregar();
      aoMudar?.();
    } catch (err) {
      setErroForm(err);
    } finally {
      setSalvando(false);
    }
  };

  const remover = async (item) => {
    const ok = await confirmar({
      titulo: `Excluir ${nomeItem.toLowerCase()}`,
      mensagem: `Excluir “${rotuloItem(item)}”? Esta ação não pode ser desfeita.`,
      textoConfirmar: 'Excluir',
      perigo: true,
    });
    if (!ok) return;
    setErroAcao(null);
    try {
      await excluir(item.id);
      avisar(`${nomeItem} excluído.`);
      recarregar();
      aoMudar?.();
    } catch (err) {
      setErroAcao(err);
    }
  };

  const visiveis = (itens || []).filter((i) => !busca || filtrar?.(i, busca.toLowerCase()));

  return (
    <div className="admin-secao">
      <div className="admin-secao-cabecalho">
        <div>
          <h2>{titulo}</h2>
          {descricao && <p className="texto-suave">{descricao}</p>}
        </div>
        <button type="button" className="botao" onClick={() => abrir()}>
          Novo {nomeItem.toLowerCase()}
        </button>
      </div>

      {filtrar && (
        <div className="campo campo-compacto campo-busca">
          <label htmlFor={`busca-${titulo}`}>Buscar</label>
          <input id={`busca-${titulo}`} type="search" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </div>
      )}

      <ErroApiAlerta erro={erro} />
      <ErroApiAlerta erro={erroAcao} />
      {carregando && !itens && <Carregando />}
      {itens &&
        (visiveis.length === 0 ? (
          <EstadoVazio titulo={busca ? 'Nada encontrado.' : 'Nenhum cadastro ainda.'} />
        ) : (
          <div className="tabela-rolavel">
            <table className="tabela">
              <thead>
                <tr>
                  {colunas.map((c) => (
                    <th key={c.rotulo} scope="col" className={c.classe}>
                      {c.rotulo}
                    </th>
                  ))}
                  <th scope="col" className="acoes-col">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((item) => (
                  <tr key={item.id}>
                    {colunas.map((c) => (
                      <td key={c.rotulo} className={c.classe}>
                        {c.valor(item)}
                      </td>
                    ))}
                    <td className="acoes-col">
                      <div className="acoes-linha">
                        <button
                          type="button"
                          className="botao botao-secundario botao-pequeno"
                          onClick={() => abrir(item)}
                          aria-label={`Editar ${rotuloItem(item)}`}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="botao botao-perigo-leve botao-pequeno"
                          onClick={() => remover(item)}
                          aria-label={`Excluir ${rotuloItem(item)}`}
                        >
                          Excluir
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

      <Modal
        aberto={Boolean(editando)}
        titulo={editando?.item ? `Editar ${nomeItem.toLowerCase()}` : `Novo ${nomeItem.toLowerCase()}`}
        aoFechar={() => setEditando(null)}
      >
        {editando && (
          <form onSubmit={salvar} className="formulario">
            <div className="modal-corpo-conteudo">
              <ErroApiAlerta erro={erroForm} />
              {campos.map((c, i) => {
                const id = `crud-${c.nome}`;
                const listaId = c.sugestoes ? `${id}-sugestoes` : undefined;
                return (
                  <div className="campo" key={c.nome}>
                    <label htmlFor={id}>
                      {c.rotulo}
                      {!c.obrigatorio && <span className="texto-suave"> (opcional)</span>}
                    </label>
                    {c.tipo === 'textarea' ? (
                      <textarea
                        id={id}
                        rows={3}
                        value={editando.valores[c.nome]}
                        maxLength={c.maxLength}
                        onChange={(e) => mudarValor(c.nome, e.target.value)}
                        data-autofocus={i === 0 || undefined}
                      />
                    ) : (
                      <input
                        id={id}
                        type={c.tipo || 'text'}
                        required={c.obrigatorio}
                        maxLength={c.maxLength}
                        list={listaId}
                        value={editando.valores[c.nome]}
                        onChange={(e) => mudarValor(c.nome, e.target.value)}
                        data-autofocus={i === 0 || undefined}
                      />
                    )}
                    {c.sugestoes && (
                      <datalist id={listaId}>
                        {c.sugestoes.map((s) => (
                          <option key={s} value={s} />
                        ))}
                      </datalist>
                    )}
                    {c.ajuda && <small className="ajuda">{c.ajuda}</small>}
                  </div>
                );
              })}
              {erroLocal && (
                <p className="erro-campo" role="alert">
                  {erroLocal}
                </p>
              )}
            </div>
            <footer className="modal-rodape">
              <button type="button" className="botao botao-secundario" onClick={() => setEditando(null)}>
                Cancelar
              </button>
              <button type="submit" className="botao" disabled={salvando || Boolean(erroLocal)}>
                {salvando ? 'Salvando…' : 'Salvar'}
              </button>
            </footer>
          </form>
        )}
      </Modal>
      {dialogo}
    </div>
  );
}
