import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { atualizarSala, criarSala, obterSala } from '../../api/salas';
import { useCarregar } from '../../hooks/useCarregar';
import { useTipos } from '../../hooks/useTipos';
import { useAvisos } from '../../components/avisos';
import Carregando from '../../components/Carregando';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import { corpoSala } from '../../utils/salas';
import EditorEquipamentos from './EditorEquipamentos';
import EditorFotos from './EditorFotos';
import EditorSoftwares from './EditorSoftwares';

const VAZIA = { nome: '', tipo: 'sala', descricao: '', capacidade: '', localizacao: '', ativo: true };

function FormDados({ sala, aoSalvo }) {
  const tipos = useTipos();
  const { avisar } = useAvisos();
  const [v, setV] = useState(() =>
    sala
      ? {
          nome: sala.nome,
          tipo: sala.tipo,
          descricao: sala.descricao ?? '',
          capacidade: String(sala.capacidade),
          localizacao: sala.localizacao ?? '',
          ativo: sala.ativo,
        }
      : VAZIA,
  );
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const mudar = (k, valor) => setV((x) => ({ ...x, [k]: valor }));

  const enviar = async (e) => {
    e.preventDefault();
    setErro(null);
    setSalvando(true);
    try {
      const resposta = sala ? await atualizarSala(sala.id, corpoSala(v)) : await criarSala(corpoSala(v));
      avisar(sala ? 'Dados do ambiente salvos.' : 'Ambiente criado. Agora adicione equipamentos, softwares e fotos.');
      aoSalvo(resposta);
    } catch (err) {
      setErro(err);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="formulario">
      <ErroApiAlerta erro={erro} />
      <div className="grade-campos">
        <div className="campo">
          <label htmlFor="sala-nome">Nome</label>
          <input id="sala-nome" required maxLength={80} value={v.nome} onChange={(e) => mudar('nome', e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="sala-tipo">Tipo</label>
          <select id="sala-tipo" required value={v.tipo} onChange={(e) => mudar('tipo', e.target.value)}>
            {tipos.length === 0 && <option value={v.tipo}>{v.tipo}</option>}
            {tipos.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="sala-capacidade">Capacidade (lugares)</label>
          <input
            id="sala-capacidade"
            type="number"
            min="1"
            required
            value={v.capacidade}
            onChange={(e) => mudar('capacidade', e.target.value)}
          />
        </div>
        <div className="campo">
          <label htmlFor="sala-localizacao">
            Localização <span className="texto-suave">(opcional)</span>
          </label>
          <input
            id="sala-localizacao"
            maxLength={120}
            placeholder="Ex.: Bloco A, 2º andar"
            value={v.localizacao}
            onChange={(e) => mudar('localizacao', e.target.value)}
          />
        </div>
      </div>
      <div className="campo">
        <label htmlFor="sala-descricao">
          Descrição <span className="texto-suave">(opcional)</span>
        </label>
        <textarea id="sala-descricao" rows={4} value={v.descricao} onChange={(e) => mudar('descricao', e.target.value)} />
      </div>
      <label className="opcao">
        <input type="checkbox" checked={v.ativo} onChange={(e) => mudar('ativo', e.target.checked)} />
        <span>Ativo (aparece para professores e aceita reservas)</span>
      </label>
      <div className="acoes">
        <button type="submit" className="botao" disabled={salvando}>
          {salvando ? 'Salvando…' : sala ? 'Salvar dados' : 'Criar ambiente'}
        </button>
      </div>
    </form>
  );
}

function Edicao({ id }) {
  const carregar = useCallback(() => obterSala(id), [id]);
  const { dados: sala, erro, carregando, setDados } = useCarregar(carregar);

  if (carregando && !sala) return <Carregando />;
  if (erro) return <ErroApiAlerta erro={erro} titulo="Não foi possível carregar o ambiente" />;

  return (
    <>
      <div className="admin-secao-cabecalho">
        <div>
          <p className="migalhas">
            <Link to="/admin/ambientes">Ambientes</Link> <span aria-hidden="true">›</span> {sala.nome}
          </p>
          <h2>
            {sala.nome} {!sala.ativo && <span className="selo selo-inativo">Inativo</span>}
          </h2>
        </div>
        <Link to={`/ambientes/${sala.id}`} className="botao botao-secundario">
          Ver página pública
        </Link>
      </div>
      <nav className="ancoras" aria-label="Seções do ambiente">
        <a href="#secao-dados">Dados</a>
        <a href="#secao-equipamentos">Equipamentos</a>
        <a href="#secao-softwares">Softwares</a>
        <a href="#secao-fotos">Fotos</a>
      </nav>
      <section id="secao-dados" className="secao cartao">
        <h3>Dados</h3>
        <FormDados sala={sala} aoSalvo={setDados} />
      </section>
      <section id="secao-equipamentos" className="secao cartao">
        <h3>Equipamentos</h3>
        <EditorEquipamentos sala={sala} aoAtualizar={setDados} />
      </section>
      <section id="secao-softwares" className="secao cartao">
        <h3>Softwares instalados</h3>
        <EditorSoftwares sala={sala} aoAtualizar={setDados} />
      </section>
      <section id="secao-fotos" className="secao cartao">
        <h3>Fotos</h3>
        <EditorFotos sala={sala} />
      </section>
    </>
  );
}

export default function AdminSalaEditar() {
  const { id } = useParams();
  const navigate = useNavigate();

  if (id) return <Edicao key={id} id={id} />;

  return (
    <div className="admin-secao">
      <div className="admin-secao-cabecalho">
        <div>
          <p className="migalhas">
            <Link to="/admin/ambientes">Ambientes</Link> <span aria-hidden="true">›</span> Novo
          </p>
          <h2>Novo ambiente</h2>
        </div>
      </div>
      <section className="secao cartao">
        <FormDados sala={null} aoSalvo={(nova) => navigate(`/admin/ambientes/${nova.id}`, { replace: true })} />
      </section>
    </div>
  );
}
