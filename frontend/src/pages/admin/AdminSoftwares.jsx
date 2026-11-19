import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  atualizarSoftware,
  criarSoftware,
  excluirSoftware,
  listarCategoriasSoftware,
  listarSoftwares,
} from '../../api/softwares';
import AdminCrud from './AdminCrud';

const listar = () => listarSoftwares();

const COLUNAS = [
  { rotulo: 'Nome', valor: (s) => <strong>{s.nome}</strong> },
  { rotulo: 'Versão', valor: (s) => s.versao || <span className="texto-suave">—</span> },
  {
    rotulo: 'Categoria',
    valor: (s) => (s.categoria ? <span className="selo selo-categoria">{s.categoria}</span> : <span className="texto-suave">—</span>),
  },
];

export default function AdminSoftwares() {
  const [categorias, setCategorias] = useState([]);

  const carregarCategorias = useCallback(() => {
    listarCategoriasSoftware().then(setCategorias, () => setCategorias([]));
  }, []);

  useEffect(() => {
    carregarCategorias();
  }, [carregarCategorias]);

  const campos = useMemo(
    () => [
      { nome: 'nome', rotulo: 'Nome', obrigatorio: true, maxLength: 80 },
      { nome: 'versao', rotulo: 'Versão', maxLength: 40 },
      {
        nome: 'categoria',
        rotulo: 'Categoria',
        maxLength: 60,
        sugestoes: categorias,
        ajuda: 'Escolha uma existente ou digite uma nova (ex.: IDE, Banco de dados).',
      },
    ],
    [categorias],
  );

  return (
    <AdminCrud
      titulo="Softwares"
      descricao="Catálogo de softwares. A instalação em cada ambiente é definida na edição do ambiente."
      nomeItem="Software"
      listar={listar}
      criar={criarSoftware}
      atualizar={atualizarSoftware}
      excluir={excluirSoftware}
      campos={campos}
      colunas={COLUNAS}
      rotuloItem={(s) => `${s.nome}${s.versao ? ` ${s.versao}` : ''}`}
      filtrar={(s, b) => `${s.nome} ${s.versao || ''} ${s.categoria || ''}`.toLowerCase().includes(b)}
      aoMudar={carregarCategorias}
    />
  );
}
