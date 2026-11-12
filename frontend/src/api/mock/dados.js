/**
 * Dados fictícios do mock de desenvolvimento (VITE_USE_MOCK=true). Nomes genéricos;
 * datas relativas a hoje para a agenda sempre ter conteúdo.
 */
import { DIAS_SEMANA } from '../../utils/datas';

const dois = (n) => String(n).padStart(2, '0');
const iso = (d) => `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}`;
const deIso = (t) => {
  const [a, m, d] = t.split('-').map(Number);
  return new Date(a, m - 1, d);
};
const somar = (t, n) => {
  const d = deIso(t);
  d.setDate(d.getDate() + n);
  return iso(d);
};

function svgFoto(titulo, legenda, cor1, cor2, variante) {
  const formas = [
    `<rect x="70" y="250" width="660" height="180" fill="#0002"/><rect x="110" y="200" width="120" height="70" rx="6" fill="#fff3"/><rect x="340" y="200" width="120" height="70" rx="6" fill="#fff3"/><rect x="570" y="200" width="120" height="70" rx="6" fill="#fff3"/>`,
    `<rect x="200" y="80" width="400" height="200" rx="8" fill="#fff2" stroke="#fff6" stroke-width="4"/><rect x="60" y="330" width="680" height="40" fill="#0003"/>`,
    `<circle cx="640" cy="120" r="70" fill="#fff2"/><rect x="60" y="300" width="300" height="110" rx="10" fill="#0002"/><rect x="420" y="300" width="300" height="110" rx="10" fill="#0002"/>`,
  ][variante % 3];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500" viewBox="0 0 800 500"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${cor1}"/><stop offset="1" stop-color="${cor2}"/></linearGradient></defs><rect width="800" height="500" fill="url(#g)"/>${formas}<text x="40" y="70" font-family="Arial, sans-serif" font-size="40" font-weight="700" fill="#fff">${titulo}</text><text x="40" y="470" font-family="Arial, sans-serif" font-size="26" fill="#ffffffd0">${legenda}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function criarDadosIniciais() {
  const hoje = iso(new Date());
  const ano = new Date().getFullYear();
  const agora = new Date().toISOString();

  const tipos = [
    { valor: 'sala', rotulo: 'Sala de aula' },
    { valor: 'lab_informatica', rotulo: 'Laboratório de informática' },
    { valor: 'lab_ciencias', rotulo: 'Laboratório de ciências' },
    { valor: 'lab_outro', rotulo: 'Outro laboratório' },
    { valor: 'auditorio', rotulo: 'Auditório' },
    { valor: 'outro', rotulo: 'Outro' },
  ];

  const professores = [
    { id: 1, rm: 'admin', nome: 'Administrador', email: null, papel: 'admin', ativo: true, senha: 'admin1234', criado_em: agora },
    { id: 2, rm: '123456', nome: 'Maria Souza', email: 'maria@example.com', papel: 'professor', ativo: true, senha: 'senha1234', criado_em: agora },
    { id: 3, rm: '654321', nome: 'João Lima', email: null, papel: 'professor', ativo: true, senha: 'senha1234', criado_em: agora },
    { id: 4, rm: '111222', nome: 'Ana Pereira', email: 'ana@example.com', papel: 'professor', ativo: false, senha: 'senha1234', criado_em: agora },
  ];

  const equipamentos = [
    { id: 1, nome: 'Computador', descricao: 'Desktop para alunos' },
    { id: 2, nome: 'Projetor', descricao: null },
    { id: 3, nome: 'Ar-condicionado', descricao: null },
    { id: 4, nome: 'Lousa digital', descricao: 'Tela interativa' },
    { id: 5, nome: 'Caixa de som', descricao: null },
    { id: 6, nome: 'Bancada', descricao: 'Bancada de experimentos' },
  ];

  const softwares = [
    { id: 1, nome: 'Visual Studio Code', versao: '1.95', categoria: 'IDE' },
    { id: 2, nome: 'PostgreSQL', versao: '16', categoria: 'Banco de dados' },
    { id: 3, nome: 'MySQL Workbench', versao: '8.0', categoria: 'Banco de dados' },
    { id: 4, nome: 'Python', versao: '3.12', categoria: 'Linguagem' },
    { id: 5, nome: 'Java JDK', versao: '21', categoria: 'Linguagem' },
    { id: 6, nome: 'Eclipse', versao: '2024-09', categoria: 'IDE' },
    { id: 7, nome: 'LibreOffice', versao: '24.8', categoria: 'Escritório' },
    { id: 8, nome: 'Packet Tracer', versao: '8.2', categoria: 'Redes' },
    { id: 9, nome: 'Git', versao: '2.47', categoria: 'Ferramentas' },
    { id: 10, nome: 'Node.js', versao: '22', categoria: 'Linguagem' },
  ];

  const base = [
    ['Sala 01', 'sala', 40, 'Bloco A, térreo', [[2, 1, null], [3, 1, null]], []],
    ['Sala 02', 'sala', 45, 'Bloco A, térreo', [[2, 1, null], [3, 2, null], [4, 1, '75"']], []],
    ['Sala 03', 'sala', 35, 'Bloco A, 1º andar', [[2, 1, null]], []],
    ['Sala 04', 'sala', 50, 'Bloco A, 1º andar', [[2, 1, null], [3, 2, null], [5, 2, null]], []],
    ['Laboratório 01', 'lab_informatica', 30, 'Bloco B, térreo', [[1, 30, 'i5 10ª geração, 16 GB RAM, SSD 256 GB'], [2, 1, null], [3, 2, null]], [1, 2, 4, 5, 9, 10]],
    ['Laboratório 02', 'lab_informatica', 25, 'Bloco B, térreo', [[1, 25, 'i5, 8 GB RAM'], [2, 1, null]], [1, 3, 4, 6, 7]],
    ['Laboratório 03', 'lab_informatica', 30, 'Bloco B, 1º andar', [[1, 30, 'i7, 32 GB RAM, SSD 512 GB'], [2, 1, null], [3, 1, null], [4, 1, null]], [1, 2, 3, 4, 5, 6, 9, 10]],
    ['Laboratório de Redes', 'lab_outro', 20, 'Bloco B, 1º andar', [[1, 20, 'i5, 16 GB RAM'], [2, 1, null]], [8, 9]],
    ['Laboratório de Química', 'lab_ciencias', 24, 'Bloco C, térreo', [[6, 6, 'Bancadas com pia e gás'], [2, 1, null]], []],
    ['Auditório', 'auditorio', 150, 'Bloco C, térreo', [[2, 2, 'Full HD'], [5, 4, null], [3, 4, null]], [7]],
    ['Sala 05', 'sala', 30, 'Bloco A, 2º andar', [[2, 1, null]], []],
  ];
  const cores = {
    sala: ['#1d4e89', '#3b82c4'],
    lab_informatica: ['#0f766e', '#2bb3a3'],
    lab_ciencias: ['#6d28d9', '#a78bfa'],
    lab_outro: ['#b45309', '#f59e0b'],
    auditorio: ['#9f1239', '#f43f5e'],
  };
  const legendas = ['Vista da porta', 'Vista do fundo', 'Detalhe dos equipamentos'];

  let fotoId = 1;
  const fotos = [];
  const salas = base.map(([nome, tipo, capacidade, localizacao, eqs, sws], i) => {
    const id = i + 1;
    const qtdFotos = id === 11 ? 0 : id <= 7 ? 3 : 1;
    for (let k = 0; k < qtdFotos; k += 1) {
      fotos.push({
        id: fotoId,
        sala_id: id,
        url: svgFoto(nome, legendas[k], cores[tipo][0], cores[tipo][1], k + i),
        legenda: legendas[k],
        ordem: k + 1,
        criado_em: agora,
      });
      fotoId += 1;
    }
    return {
      id,
      nome,
      tipo,
      capacidade,
      localizacao,
      descricao:
        tipo === 'lab_informatica'
          ? `${nome} usado pelas disciplinas de programação, banco de dados e redes.`
          : tipo === 'auditorio'
            ? 'Espaço para palestras, semanas acadêmicas e eventos.'
            : `Ambiente ${nome.toLowerCase()} para aulas teóricas.`,
      ativo: id !== 11,
      equipamentos: eqs.map(([equipamento_id, quantidade, especificacao]) => ({ equipamento_id, quantidade, especificacao })),
      softwares: sws,
      criado_em: agora,
      atualizado_em: agora,
    };
  });

  const todos = [1, 2, 3, 4, 5];
  const comSabado = [1, 2, 3, 4, 5, 6];
  const horarios = [
    ['manha', 1, '07:30', '08:20', comSabado],
    ['manha', 2, '08:20', '09:10', comSabado],
    ['manha', 3, '09:30', '10:20', comSabado],
    ['manha', 4, '10:20', '11:10', comSabado],
    ['manha', 5, '11:10', '12:00', todos],
    ['tarde', 1, '13:00', '13:50', todos],
    ['tarde', 2, '13:50', '14:40', todos],
    ['tarde', 3, '14:50', '15:40', todos],
    ['tarde', 4, '15:40', '16:30', todos],
    ['noite', 1, '19:00', '19:50', todos],
    ['noite', 2, '19:50', '20:40', todos],
    ['noite', 3, '20:50', '21:40', todos],
    ['noite', 4, '21:40', '22:30', todos],
  ].map(([turno, ordem, inicio, fim, dias_semana], i) => ({
    id: i + 1,
    turno,
    ordem,
    inicio,
    fim,
    dias_semana,
    ativo: true,
  }));

  const semestres = [
    { id: 1, nome: `${ano}-1`, data_inicio: `${ano}-02-02`, data_fim: `${ano}-06-30` },
    { id: 2, nome: `${ano}-2`, data_inicio: `${ano}-08-03`, data_fim: `${ano}-12-19` },
  ];

  // Reservas: algumas avulsas perto de hoje e uma recorrência semanal.
  const diaIso = (t) => {
    const d = deIso(t).getDay();
    return d === 0 ? 7 : d;
  };
  const proximoDia = (isoAlvo, aPartirDe) => {
    let t = aPartirDe;
    while (diaIso(t) !== isoAlvo) t = somar(t, 1);
    return t;
  };
  const h = (id) => horarios.find((x) => x.id === id);
  const reservas = [];
  let reservaId = 1;
  const nova = (salaId, profId, data, ids, extra = {}) => {
    const aulas = ids.map(h);
    reservas.push({
      id: reservaId++,
      sala_id: salaId,
      professor_id: profId,
      data,
      inicio: aulas[0].inicio,
      fim: aulas[aulas.length - 1].fim,
      horario_inicio_id: ids[0],
      horario_fim_id: ids[ids.length - 1],
      quantidade_aulas: ids.length,
      status: 'ativa',
      observacao: null,
      grupo_recorrencia_id: null,
      criado_por_id: profId,
      criado_em: agora,
      cancelada_em: null,
      cancelada_por_id: null,
      motivo_cancelamento: null,
      ...extra,
    });
  };

  const grupos = [];
  const semestreAtual = semestres.find((s) => s.data_inicio <= hoje && hoje <= s.data_fim) || semestres[1];
  const inicioGrupo = proximoDia(2, somar(hoje, -21));
  grupos.push({
    id: 1,
    sala_id: 5,
    professor_id: 2,
    semestre_id: semestreAtual.id,
    dia_semana: 2,
    inicio: '07:30',
    fim: '09:10',
    criado_por_id: 2,
    criado_em: agora,
  });
  for (let t = inicioGrupo; t <= semestreAtual.data_fim; t = somar(t, 7)) {
    nova(5, 2, t, [1, 2], { grupo_recorrencia_id: 1, observacao: 'Programação I - ADS 1º sem.' });
  }

  const seg = proximoDia(1, hoje);
  const qua = proximoDia(3, hoje);
  const qui = proximoDia(4, hoje);
  const sex = proximoDia(5, hoje);
  nova(7, 3, seg, [10, 11], { observacao: 'Banco de Dados - ADS 3º sem.' });
  nova(1, 2, qua, [6, 7, 8]);
  nova(10, 1, qui, [12, 13], { observacao: 'Palestra da semana acadêmica' });
  nova(6, 3, sex, [3, 4]);
  nova(7, 2, somar(hoje, -3), [1, 2], { observacao: 'Estrutura de Dados' });
  nova(2, 2, somar(qua, 7), [10, 11]);
  nova(8, 3, somar(seg, 1), [6, 7]);
  nova(6, 3, somar(sex, 14), [6, 7], { observacao: 'Reposição' }); // gera conflito na prévia de sextas à tarde
  nova(3, 2, somar(sex, 7), [1, 2, 3], {
    status: 'cancelada',
    cancelada_em: agora,
    cancelada_por_id: 2,
    motivo_cancelamento: 'Aula remanejada',
  });

  return {
    tipos,
    professores,
    equipamentos,
    softwares,
    salas,
    fotos,
    horarios,
    semestres,
    grupos,
    reservas,
    seq: { sala: 100, foto: 100, equipamento: 100, software: 100, professor: 100, horario: 100, semestre: 100, reserva: 1000, grupo: 100 },
    DIAS_SEMANA,
  };
}
