import { useEffect, useState } from 'react';
import { listarEquipamentos } from '../../api/equipamentos';
import { definirEquipamentosSala } from '../../api/salas';
import { useAvisos } from '../../components/avisos';
import ErroApiAlerta from '../../components/ErroApiAlerta';

const deSala = (sala) =>
  sala.equipamentos.map((e) => ({
    equipamento_id: e.equipamento_id,
    nome: e.nome,
    quantidade: String(e.quantidade),
    especificacao: e.especificacao ?? '',
  }));

/** Equipamentos do ambiente (PUT /salas/{id}/equipamentos substitui a lista). */
export default function EditorEquipamentos({ sala, aoAtualizar }) {
  const { avisar } = useAvisos();
  const [catalogo, setCatalogo] = useState([]);
  const [linhas, setLinhas] = useState(() => deSala(sala));
  const [novo, setNovo] = useState('');
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [alterado, setAlterado] = useState(false);

  useEffect(() => {
    listarEquipamentos().then(setCatalogo, () => setCatalogo([]));
  }, []);

  const mudar = (i, campo, valor) => {
    setLinhas((ls) => ls.map((l, j) => (j === i ? { ...l, [campo]: valor } : l)));
    setAlterado(true);
  };

  const adicionar = () => {
    const eq = catalogo.find((c) => String(c.id) === novo);
    if (!eq) return;
    setLinhas((ls) => [...ls, { equipamento_id: eq.id, nome: eq.nome, quantidade: '1', especificacao: '' }]);
    setNovo('');
    setAlterado(true);
  };

  const remover = (i) => {
    setLinhas((ls) => ls.filter((_, j) => j !== i));
    setAlterado(true);
  };

  const invalida = linhas.some((l) => !(Number(l.quantidade) >= 1));

  const salvar = async () => {
    setErro(null);
    setSalvando(true);
    try {
      const atualizada = await definirEquipamentosSala(
        sala.id,
        linhas.map((l) => ({
          equipamento_id: l.equipamento_id,
          quantidade: Number(l.quantidade),
          especificacao: l.especificacao.trim() || null,
        })),
      );
      setLinhas(deSala(atualizada));
      setAlterado(false);
      aoAtualizar(atualizada);
      avisar('Equipamentos do ambiente salvos.');
    } catch (err) {
      setErro(err);
    } finally {
      setSalvando(false);
    }
  };

  const disponiveis = catalogo.filter((c) => !linhas.some((l) => l.equipamento_id === c.id));

  return (
    <div>
      <ErroApiAlerta erro={erro} />
      {linhas.length === 0 ? (
        <p className="texto-suave">Nenhum equipamento neste ambiente.</p>
      ) : (
        <div className="tabela-rolavel">
          <table className="tabela tabela-editavel">
            <thead>
              <tr>
                <th scope="col">Equipamento</th>
                <th scope="col">Quantidade</th>
                <th scope="col">Especificação</th>
                <th scope="col" className="acoes-col">
                  <span className="sr-only">Ações</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((l, i) => (
                <tr key={l.equipamento_id}>
                  <td>{l.nome}</td>
                  <td>
                    <label className="sr-only" htmlFor={`eq-qtd-${l.equipamento_id}`}>
                      Quantidade de {l.nome}
                    </label>
                    <input
                      id={`eq-qtd-${l.equipamento_id}`}
                      type="number"
                      min="1"
                      className="input-numero"
                      value={l.quantidade}
                      onChange={(e) => mudar(i, 'quantidade', e.target.value)}
                    />
                  </td>
                  <td>
                    <label className="sr-only" htmlFor={`eq-spec-${l.equipamento_id}`}>
                      Especificação de {l.nome}
                    </label>
                    <input
                      id={`eq-spec-${l.equipamento_id}`}
                      maxLength={255}
                      placeholder="Ex.: i5, 16 GB RAM"
                      value={l.especificacao}
                      onChange={(e) => mudar(i, 'especificacao', e.target.value)}
                    />
                  </td>
                  <td className="acoes-col">
                    <button
                      type="button"
                      className="botao botao-perigo-leve botao-pequeno"
                      onClick={() => remover(i)}
                      aria-label={`Remover ${l.nome}`}
                    >
                      Remover
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="linha-adicionar">
        <div className="campo campo-compacto">
          <label htmlFor="eq-novo">Adicionar equipamento</label>
          <select id="eq-novo" value={novo} onChange={(e) => setNovo(e.target.value)}>
            <option value="">Selecione…</option>
            {disponiveis.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </select>
        </div>
        <button type="button" className="botao botao-secundario" onClick={adicionar} disabled={!novo}>
          Adicionar
        </button>
      </div>

      <div className="acoes">
        {alterado && <span className="texto-suave">Alterações não salvas</span>}
        <button type="button" className="botao" onClick={salvar} disabled={salvando || invalida || !alterado}>
          {salvando ? 'Salvando…' : 'Salvar equipamentos'}
        </button>
      </div>
    </div>
  );
}
