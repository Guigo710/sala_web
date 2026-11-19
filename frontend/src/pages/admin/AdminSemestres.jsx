import {
  atualizarSemestre,
  criarSemestre,
  excluirSemestre,
  listarSemestres,
} from '../../api/semestres';
import { formatarData } from '../../utils/datas';
import AdminCrud from './AdminCrud';

const listar = () => listarSemestres();

const CAMPOS = [
  { nome: 'nome', rotulo: 'Nome', obrigatorio: true, maxLength: 20, ajuda: 'Ex.: 2026-2' },
  { nome: 'data_inicio', rotulo: 'Início', tipo: 'date', obrigatorio: true },
  { nome: 'data_fim', rotulo: 'Fim', tipo: 'date', obrigatorio: true },
];

const COLUNAS = [
  { rotulo: 'Nome', valor: (s) => <strong>{s.nome}</strong> },
  { rotulo: 'Início', valor: (s) => formatarData(s.data_inicio) },
  { rotulo: 'Fim', valor: (s) => formatarData(s.data_fim) },
];

const validar = (v) =>
  v.data_inicio && v.data_fim && v.data_fim <= v.data_inicio ? 'O fim precisa ser depois do início.' : '';

export default function AdminSemestres() {
  return (
    <AdminCrud
      titulo="Semestres letivos"
      descricao="A reserva semanal vai da data escolhida até o fim do semestre que a contém. Semestres não podem se sobrepor."
      nomeItem="Semestre"
      listar={listar}
      criar={criarSemestre}
      atualizar={atualizarSemestre}
      excluir={excluirSemestre}
      campos={CAMPOS}
      colunas={COLUNAS}
      rotuloItem={(s) => s.nome}
      validar={validar}
    />
  );
}
