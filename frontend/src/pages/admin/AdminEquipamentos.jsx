import {
  atualizarEquipamento,
  criarEquipamento,
  excluirEquipamento,
  listarEquipamentos,
} from '../../api/equipamentos';
import AdminCrud from './AdminCrud';

const listar = () => listarEquipamentos();

const CAMPOS = [
  { nome: 'nome', rotulo: 'Nome', obrigatorio: true, maxLength: 80 },
  { nome: 'descricao', rotulo: 'Descrição', tipo: 'textarea' },
];

const COLUNAS = [
  { rotulo: 'Nome', valor: (e) => <strong>{e.nome}</strong> },
  { rotulo: 'Descrição', valor: (e) => e.descricao || <span className="texto-suave">—</span> },
];

export default function AdminEquipamentos() {
  return (
    <AdminCrud
      titulo="Equipamentos"
      descricao="Catálogo de equipamentos. A quantidade e a especificação de cada ambiente são definidas na edição do ambiente. Excluir um equipamento remove-o também dos ambientes."
      nomeItem="Equipamento"
      listar={listar}
      criar={criarEquipamento}
      atualizar={atualizarEquipamento}
      excluir={excluirEquipamento}
      campos={CAMPOS}
      colunas={COLUNAS}
      rotuloItem={(e) => e.nome}
      filtrar={(e, b) => `${e.nome} ${e.descricao || ''}`.toLowerCase().includes(b)}
    />
  );
}
