import { useEffect, useState } from 'react';
import { listarSoftwares } from '../../api/softwares';
import { definirSoftwaresSala } from '../../api/salas';
import { useAvisos } from '../../components/avisos';
import ErroApiAlerta from '../../components/ErroApiAlerta';

/** Softwares instalados no ambiente (PUT /salas/{id}/softwares substitui a lista). */
export default function EditorSoftwares({ sala, aoAtualizar }) {
  const { avisar } = useAvisos();
  const [catalogo, setCatalogo] = useState([]);
  const [marcados, setMarcados] = useState(() => sala.softwares.map((s) => s.id));
  const [filtro, setFiltro] = useState('');
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [alterado, setAlterado] = useState(false);

  useEffect(() => {
    listarSoftwares().then(setCatalogo, () => setCatalogo([]));
  }, []);

  const alternar = (id) => {
    setMarcados((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));
    setAlterado(true);
  };

  const salvar = async () => {
    setErro(null);
    setSalvando(true);
    try {
      const atualizada = await definirSoftwaresSala(sala.id, marcados);
      setMarcados(atualizada.softwares.map((s) => s.id));
      setAlterado(false);
      aoAtualizar(atualizada);
      avisar('Softwares do ambiente salvos.');
    } catch (err) {
      setErro(err);
    } finally {
      setSalvando(false);
    }
  };

  const visiveis = catalogo.filter((s) =>
    `${s.nome} ${s.versao || ''} ${s.categoria || ''}`.toLowerCase().includes(filtro.toLowerCase()),
  );
  const categorias = [...new Set(visiveis.map((s) => s.categoria || 'Sem categoria'))].sort();

  return (
    <div>
      <ErroApiAlerta erro={erro} />
      <div className="campo campo-compacto campo-busca">
        <label htmlFor="sw-filtro">Filtrar softwares</label>
        <input id="sw-filtro" type="search" value={filtro} onChange={(e) => setFiltro(e.target.value)} />
      </div>
      {catalogo.length === 0 && <p className="texto-suave">Nenhum software no catálogo. Cadastre em Admin › Softwares.</p>}
      <div className="softwares-categorias">
        {categorias.map((cat) => (
          <fieldset key={cat} className="filtro-grupo">
            <legend>{cat}</legend>
            <ul className="lista-marcavel">
              {visiveis
                .filter((s) => (s.categoria || 'Sem categoria') === cat)
                .map((s) => (
                  <li key={s.id}>
                    <label className="opcao">
                      <input type="checkbox" checked={marcados.includes(s.id)} onChange={() => alternar(s.id)} />
                      <span>
                        {s.nome}
                        {s.versao ? ` ${s.versao}` : ''}
                      </span>
                    </label>
                  </li>
                ))}
            </ul>
          </fieldset>
        ))}
      </div>
      <div className="acoes">
        <span className="texto-suave">
          {marcados.length} {marcados.length === 1 ? 'software marcado' : 'softwares marcados'}
          {alterado ? ' · alterações não salvas' : ''}
        </span>
        <button type="button" className="botao" onClick={salvar} disabled={salvando || !alterado}>
          {salvando ? 'Salvando…' : 'Salvar softwares'}
        </button>
      </div>
    </div>
  );
}
