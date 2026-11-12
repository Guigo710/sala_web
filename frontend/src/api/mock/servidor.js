/**
 * API simulada em memória, só para desenvolvimento (`VITE_USE_MOCK=true npm run dev`).
 * Segue docs/api-contrato.md o suficiente para navegar pelas telas sem o backend.
 * Não entra no build de produção (ver main.jsx). Contas: admin/admin1234, 123456/senha1234.
 */
import { API_URL, definirTransporte } from '../cliente';
import { criarDadosIniciais } from './dados';

let db = criarDadosIniciais();

/** Só para testes: volta aos dados iniciais e liga/desliga a latência simulada. */
export function reiniciarMock({ atraso = true } = {}) {
  db = criarDadosIniciais();
  comAtraso = atraso;
}
let comAtraso = true;
const TURNO_ORDEM = { manha: 0, tarde: 1, noite: 2 };

class Falha {
  constructor(status, codigo, detail, extra = {}) {
    Object.assign(this, { status, corpo: { detail, codigo, ...extra } });
  }
}
const falha = (status, codigo, detail, extra) => {
  throw new Falha(status, codigo, detail, extra);
};
const naoEncontrado = () => falha(404, 'NAO_ENCONTRADO', 'Não encontrado.');
const validacao = (campo, mensagem) =>
  falha(422, 'VALIDACAO', 'Dados inválidos.', { erros: [{ campo, mensagem }] });

// ---------- utilidades ----------
const dois = (n) => String(n).padStart(2, '0');
const isoData = (d) => `${d.getFullYear()}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}`;
const deIso = (t) => {
  const [a, m, d] = t.split('-').map(Number);
  return new Date(a, m - 1, d);
};
const somar = (t, n) => {
  const d = deIso(t);
  d.setDate(d.getDate() + n);
  return isoData(d);
};
const diaSemana = (t) => {
  const d = deIso(t).getDay();
  return d === 0 ? 7 : d;
};
const momento = (data, hora) => {
  const [h, m] = hora.split(':').map(Number);
  const d = deIso(data);
  d.setHours(h, m, 0, 0);
  return d;
};
const agoraIso = () => new Date().toISOString();
const sobrepoe = (a1, a2, b1, b2) => a1 < b2 && b1 < a2;
const textoOuNulo = (v) => (typeof v === 'string' && v.trim() ? v.trim() : null);
const porNome = (a, b) => a.nome.localeCompare(b.nome, 'pt-BR');

// ---------- serialização ----------
const rotuloTipo = (tipo) => db.tipos.find((t) => t.valor === tipo)?.rotulo ?? tipo;
const pessoa = (id) => {
  const p = db.professores.find((x) => x.id === id);
  return p ? { id: p.id, nome: p.nome } : null;
};
const usuarioJson = ({ senha: _senha, token_versao: _versao, ...resto }) => resto;
const fotosDaSala = (salaId) =>
  db.fotos.filter((f) => f.sala_id === salaId).sort((a, b) => a.ordem - b.ordem || a.id - b.id);
const salaResumo = (s) => ({
  id: s.id,
  nome: s.nome,
  tipo: s.tipo,
  tipo_rotulo: rotuloTipo(s.tipo),
  capacidade: s.capacidade,
  localizacao: s.localizacao,
  ativo: s.ativo,
  foto_capa_url: fotosDaSala(s.id)[0]?.url ?? null,
  equipamentos: s.equipamentos
    .map((e) => ({ ...e, nome: db.equipamentos.find((x) => x.id === e.equipamento_id)?.nome }))
    .filter((e) => e.nome)
    .sort(porNome)
    .map(({ equipamento_id, nome, quantidade, especificacao }) => ({ equipamento_id, nome, quantidade, especificacao })),
});
const salaDetalhe = (s) => ({
  ...salaResumo(s),
  descricao: s.descricao,
  fotos: fotosDaSala(s.id),
  softwares: db.softwares.filter((x) => s.softwares.includes(x.id)).sort(porNome),
  criado_em: s.criado_em,
  atualizado_em: s.atualizado_em,
});
const salaMini = (id) => {
  const s = db.salas.find((x) => x.id === id);
  return { id: s.id, nome: s.nome, tipo: s.tipo };
};
const podeCancelar = (r, u) => {
  if (!u || r.status !== 'ativa') return false;
  if (u.papel === 'admin') return true;
  return r.professor_id === u.id && new Date() < momento(r.data, r.inicio);
};
const reservaJson = (r, u) => ({
  id: r.id,
  sala: salaMini(r.sala_id),
  professor: pessoa(r.professor_id),
  data: r.data,
  inicio: r.inicio,
  fim: r.fim,
  horario_inicio_id: r.horario_inicio_id,
  horario_fim_id: r.horario_fim_id,
  quantidade_aulas: r.quantidade_aulas,
  status: r.status,
  observacao: r.observacao,
  grupo_recorrencia_id: r.grupo_recorrencia_id,
  criado_em: r.criado_em,
  cancelada_em: r.cancelada_em,
  cancelada_por: r.cancelada_por_id ? pessoa(r.cancelada_por_id) : null,
  motivo_cancelamento: r.motivo_cancelamento,
  pode_cancelar: podeCancelar(r, u),
});
const semestreJson = (s) => ({ ...s });
const grupoJson = (g) => {
  const ocorrencias = db.reservas.filter((r) => r.grupo_recorrencia_id === g.id);
  return {
    id: g.id,
    sala: salaMini(g.sala_id),
    professor: pessoa(g.professor_id),
    semestre: semestreJson(db.semestres.find((s) => s.id === g.semestre_id)),
    dia_semana: g.dia_semana,
    inicio: g.inicio,
    fim: g.fim,
    criado_em: g.criado_em,
    total_ocorrencias: ocorrencias.length,
    ocorrencias_ativas: ocorrencias.filter((r) => r.status === 'ativa').length,
  };
};
const conflitoJson = (r) => ({
  data: r.data,
  inicio: r.inicio,
  fim: r.fim,
  reserva_id: r.id,
  sala_id: r.sala_id,
  professor: pessoa(r.professor_id),
});
const ordenarHorarios = (lista) =>
  [...lista].sort((a, b) => TURNO_ORDEM[a.turno] - TURNO_ORDEM[b.turno] || a.ordem - b.ordem);

// ---------- autenticação ----------
// Token simulado `mock.<id>.<versão>`: como a claim `ver` do JWT (ADR-0008), só vale enquanto a
// versão for igual a `token_versao` da conta. Incrementar a versão derruba todas as sessões da conta.
const versaoDe = (u) => u.token_versao ?? 0;
const revogarTokens = (u) => {
  u.token_versao = versaoDe(u) + 1;
};
const emitirSessao = (u) => ({
  access_token: `mock.${u.id}.${versaoDe(u)}`,
  token_type: 'bearer',
  expira_em: new Date(Date.now() + 8 * 3600 * 1000).toISOString(),
  usuario: usuarioJson(u),
});
function usuarioDoToken(headers) {
  const auth = headers.Authorization || headers.authorization;
  const m = auth && /^Bearer mock\.(\d+)\.(\d+)$/.exec(auth);
  if (!m) return null;
  const u = db.professores.find((p) => p.id === Number(m[1]));
  return u && u.ativo && versaoDe(u) === Number(m[2]) ? u : null;
}
const exigirProfessor = (u) => u || falha(401, 'NAO_AUTENTICADO', 'Faça login para continuar.');
const exigirAdmin = (u) => {
  exigirProfessor(u);
  if (u.papel !== 'admin') falha(403, 'SEM_PERMISSAO', 'Você não tem permissão para esta ação.');
  return u;
};

// ---------- regras de reserva ----------
function validarAulas(horarioIds, data) {
  if (!Array.isArray(horarioIds) || horarioIds.length === 0) validacao('body.horario_ids', 'lista vazia');
  if (new Set(horarioIds).size !== horarioIds.length) validacao('body.horario_ids', 'aulas repetidas');
  const aulas = horarioIds.map((id) => db.horarios.find((h) => h.id === Number(id)) || naoEncontrado());
  const turno = aulas[0].turno;
  const ordens = aulas.map((a) => a.ordem).sort((a, b) => a - b);
  const seguidas =
    aulas.every((a) => a.ativo && a.turno === turno) && ordens.every((o, i) => i === 0 || o === ordens[i - 1] + 1);
  if (!seguidas) falha(422, 'AULAS_NAO_SEGUIDAS', 'Escolha aulas seguidas do mesmo turno.');
  const dia = diaSemana(data);
  if (aulas.some((a) => !a.dias_semana.includes(dia)))
    falha(422, 'AULA_INVALIDA_NO_DIA', 'Alguma aula escolhida não acontece neste dia da semana.');
  const ordenadas = ordenarHorarios(aulas);
  return { aulas: ordenadas, inicio: ordenadas[0].inicio, fim: ordenadas[ordenadas.length - 1].fim };
}

function salaParaReserva(salaId, u) {
  const sala = db.salas.find((s) => s.id === Number(salaId));
  if (!sala || (!sala.ativo && u?.papel !== 'admin')) naoEncontrado();
  if (!sala.ativo) falha(422, 'SALA_INATIVA', 'Este ambiente está inativo e não aceita reservas.');
  return sala;
}

function donoDaReserva(corpo, u) {
  if (corpo.professor_id === undefined || corpo.professor_id === null) return u.id;
  if (u.papel !== 'admin') falha(403, 'SEM_PERMISSAO', 'Apenas a administração pode reservar em nome de outro professor.');
  const p = db.professores.find((x) => x.id === Number(corpo.professor_id)) || naoEncontrado();
  if (!p.ativo) falha(422, 'PROFESSOR_INATIVO', 'A conta deste professor está inativa.');
  return p.id;
}

const conflitosEm = (salaId, data, inicio, fim) =>
  db.reservas.filter(
    (r) => r.status === 'ativa' && r.sala_id === salaId && r.data === data && sobrepoe(inicio, fim, r.inicio, r.fim),
  );

function criarRegistroReserva(sala, dono, u, data, bloco, observacao, grupoId = null) {
  const r = {
    id: db.seq.reserva++,
    sala_id: sala.id,
    professor_id: dono,
    data,
    inicio: bloco.inicio,
    fim: bloco.fim,
    horario_inicio_id: bloco.aulas[0].id,
    horario_fim_id: bloco.aulas[bloco.aulas.length - 1].id,
    quantidade_aulas: bloco.aulas.length,
    status: 'ativa',
    observacao: textoOuNulo(observacao),
    grupo_recorrencia_id: grupoId,
    criado_por_id: u.id,
    criado_em: agoraIso(),
    cancelada_em: null,
    cancelada_por_id: null,
    motivo_cancelamento: null,
  };
  db.reservas.push(r);
  return r;
}

function serie(corpo, u) {
  const sala = salaParaReserva(corpo.sala_id, u);
  donoDaReserva(corpo, u);
  if (!corpo.data_inicio) validacao('body.data_inicio', 'obrigatório');
  const bloco = validarAulas(corpo.horario_ids, corpo.data_inicio);
  if (momento(corpo.data_inicio, bloco.inicio) <= new Date())
    falha(422, 'DATA_PASSADA', 'Não é possível reservar um horário que já começou.');
  const semestre = db.semestres.find((s) => s.data_inicio <= corpo.data_inicio && corpo.data_inicio <= s.data_fim);
  if (!semestre) falha(422, 'SEM_SEMESTRE', 'Não há semestre letivo cadastrado que contenha a data inicial.');
  const datas = [];
  for (let t = corpo.data_inicio; t <= semestre.data_fim; t = somar(t, 7)) datas.push(t);
  return { sala, bloco, semestre, datas };
}

function cancelar(r, u, motivo) {
  r.status = 'cancelada';
  r.cancelada_em = agoraIso();
  r.cancelada_por_id = u.id;
  r.motivo_cancelamento = textoOuNulo(motivo);
}

// ---------- rotas ----------
const rotas = [];
const rota = (metodo, padrao, fn) => {
  const chaves = [];
  const re = new RegExp(
    `^${padrao.replace(/\{(\w+)\}/g, (_, k) => {
      chaves.push(k);
      return '([^/]+)';
    })}$`,
  );
  rotas.push({ metodo, re, chaves, fn });
};

rota('GET', '/saude', () => ({ status: 'ok' }));

// Auth
rota('POST', '/auth/login', ({ corpo }) => {
  const u = db.professores.find((p) => p.rm === corpo?.rm);
  if (!u || u.senha !== corpo?.senha || !u.ativo) falha(401, 'CREDENCIAIS_INVALIDAS', 'RM ou senha inválidos.');
  return emitirSessao(u);
});
rota('GET', '/auth/me', ({ u }) => usuarioJson(exigirProfessor(u)));
rota('PUT', '/auth/me/senha', ({ u, corpo }) => {
  exigirProfessor(u);
  if (corpo.senha_atual !== u.senha) falha(422, 'SENHA_ATUAL_INCORRETA', 'A senha atual está incorreta.');
  if (!corpo.nova_senha || corpo.nova_senha.length < 8) validacao('body.nova_senha', 'mínimo de 8 caracteres');
  u.senha = corpo.nova_senha;
  revogarTokens(u);
  return emitirSessao(u); // 200 com token novo (contrato 1.2)
});

// Salas
rota('GET', '/salas/tipos', () => db.tipos);
rota('GET', '/salas', ({ u, q }) => {
  const admin = u?.papel === 'admin';
  let lista = db.salas.filter((s) => s.ativo || (admin && q.get('incluir_inativas') === 'true'));
  const tipos = q.getAll('tipo');
  if (tipos.length) lista = lista.filter((s) => tipos.includes(s.tipo));
  if (q.get('capacidade_min')) lista = lista.filter((s) => s.capacidade >= Number(q.get('capacidade_min')));
  const eqs = q.getAll('equipamento_id').map(Number);
  if (eqs.length) lista = lista.filter((s) => eqs.every((id) => s.equipamentos.some((e) => e.equipamento_id === id)));
  const sws = q.getAll('software_id').map(Number);
  if (sws.length) lista = lista.filter((s) => sws.every((id) => s.softwares.includes(id)));
  const busca = q.get('busca')?.toLowerCase();
  if (busca)
    lista = lista.filter((s) => `${s.nome} ${s.descricao || ''} ${s.localizacao || ''}`.toLowerCase().includes(busca));
  const data = q.get('data');
  const ids = q.getAll('horario_ids').map(Number);
  if (Boolean(data) !== ids.length > 0) validacao('query.data', 'informe data e horario_ids juntos');
  if (data) {
    const bloco = validarAulas(ids, data);
    lista = lista.filter((s) => conflitosEm(s.id, data, bloco.inicio, bloco.fim).length === 0);
  }
  return lista.sort(porNome).map(salaResumo);
});
const acharSala = (id, u) => {
  const s = db.salas.find((x) => x.id === Number(id));
  if (!s || (!s.ativo && u?.papel !== 'admin')) naoEncontrado();
  return s;
};
rota('GET', '/salas/{id}', ({ p, u }) => salaDetalhe(acharSala(p.id, u)));
rota('GET', '/salas/{id}/disponibilidade', ({ p, u, q }) => {
  const s = acharSala(p.id, u);
  const data = q.get('data') || validacao('query.data', 'obrigatório');
  const dia = diaSemana(data);
  const aulas = ordenarHorarios(db.horarios.filter((h) => h.ativo && h.dias_semana.includes(dia))).map((h) => {
    const r = conflitosEm(s.id, data, h.inicio, h.fim)[0];
    return {
      horario: h,
      livre: !r,
      passou: momento(data, h.inicio) <= new Date(),
      reserva: r ? { id: r.id, professor: pessoa(r.professor_id), inicio: r.inicio, fim: r.fim } : null,
    };
  });
  return { sala_id: s.id, data, dia_semana: dia, aulas };
});
const dadosSala = (corpo, idAtual) => {
  if (!corpo.nome?.trim()) validacao('body.nome', 'obrigatório');
  if (!(Number(corpo.capacidade) > 0)) validacao('body.capacidade', 'deve ser maior que 0');
  if (db.salas.some((s) => s.nome === corpo.nome.trim() && s.id !== idAtual))
    falha(409, 'NOME_DUPLICADO', 'Já existe um ambiente com este nome.');
  return {
    nome: corpo.nome.trim(),
    tipo: corpo.tipo,
    descricao: textoOuNulo(corpo.descricao),
    capacidade: Number(corpo.capacidade),
    localizacao: textoOuNulo(corpo.localizacao),
    ativo: corpo.ativo ?? true,
  };
};
rota('POST', '/salas', ({ u, corpo }) => {
  exigirAdmin(u);
  const s = {
    id: db.seq.sala++,
    ...dadosSala(corpo, null),
    equipamentos: [],
    softwares: [],
    criado_em: agoraIso(),
    atualizado_em: agoraIso(),
  };
  db.salas.push(s);
  return [201, salaDetalhe(s)];
});
// §1.6: PUT é substituição; `ativo` é obrigatório em salas e horários.
const exigirAtivo = (corpo) => {
  if (typeof corpo?.ativo !== 'boolean') validacao('body.ativo', 'obrigatório');
};
rota('PUT', '/salas/{id}', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  exigirAtivo(corpo);
  Object.assign(s, dadosSala(corpo, s.id), { atualizado_em: agoraIso() });
  return salaDetalhe(s);
});
rota('DELETE', '/salas/{id}', ({ u, p }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  if (db.reservas.some((r) => r.sala_id === s.id))
    falha(409, 'SALA_COM_RESERVAS', 'Este ambiente tem reservas e não pode ser excluído. Desative-o.');
  db.salas = db.salas.filter((x) => x.id !== s.id);
  db.fotos = db.fotos.filter((f) => f.sala_id !== s.id);
  return null;
});
rota('PUT', '/salas/{id}/equipamentos', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  const ids = corpo.map((e) => e.equipamento_id);
  if (new Set(ids).size !== ids.length) validacao('body', 'equipamento repetido');
  corpo.forEach((e) => db.equipamentos.find((x) => x.id === e.equipamento_id) || naoEncontrado());
  s.equipamentos = corpo.map((e) => ({
    equipamento_id: e.equipamento_id,
    quantidade: e.quantidade ?? 1,
    especificacao: textoOuNulo(e.especificacao),
  }));
  s.atualizado_em = agoraIso();
  return salaDetalhe(s);
});
rota('PUT', '/salas/{id}/softwares', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  corpo.software_ids.forEach((id) => db.softwares.find((x) => x.id === id) || naoEncontrado());
  s.softwares = [...new Set(corpo.software_ids)];
  s.atualizado_em = agoraIso();
  return salaDetalhe(s);
});

// Fotos
rota('GET', '/salas/{id}/fotos', ({ p, u }) => fotosDaSala(acharSala(p.id, u).id));
rota('POST', '/salas/{id}/fotos', ({ u, p, form }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  const arquivo = form?.get('arquivo');
  if (!arquivo || typeof arquivo === 'string') validacao('body.arquivo', 'obrigatório');
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(arquivo.type))
    falha(415, 'TIPO_ARQUIVO_INVALIDO', 'Envie uma imagem JPEG, PNG ou WebP.');
  if (arquivo.size > 5 * 1024 * 1024) falha(413, 'ARQUIVO_GRANDE', 'A foto passa do limite de 5 MB.');
  const fotos = fotosDaSala(s.id);
  const foto = {
    id: db.seq.foto++,
    sala_id: s.id,
    url: URL.createObjectURL(arquivo),
    legenda: textoOuNulo(form.get('legenda')),
    ordem: Math.max(0, ...fotos.map((f) => f.ordem)) + 1,
    criado_em: agoraIso(),
  };
  db.fotos.push(foto);
  return [201, foto];
});
const acharFoto = (salaId, fotoId) =>
  db.fotos.find((f) => f.id === Number(fotoId) && f.sala_id === Number(salaId)) || naoEncontrado();
rota('PUT', '/salas/{id}/fotos/ordem', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const s = acharSala(p.id, u);
  const atuais = fotosDaSala(s.id).map((f) => f.id).sort();
  const enviados = [...corpo.foto_ids].sort();
  if (atuais.length !== enviados.length || atuais.some((id, i) => id !== enviados[i]))
    falha(422, 'ORDEM_FOTOS_INVALIDA', 'A lista não corresponde às fotos do ambiente.');
  corpo.foto_ids.forEach((id, i) => {
    acharFoto(s.id, id).ordem = i + 1;
  });
  return fotosDaSala(s.id);
});
rota('PATCH', '/salas/{id}/fotos/{foto}', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const f = acharFoto(p.id, p.foto);
  f.legenda = textoOuNulo(corpo.legenda);
  return f;
});
rota('DELETE', '/salas/{id}/fotos/{foto}', ({ u, p }) => {
  exigirAdmin(u);
  const f = acharFoto(p.id, p.foto);
  db.fotos = db.fotos.filter((x) => x.id !== f.id);
  return null;
});

// Catálogos simples
function catalogo(caminho, colecao, seq, normalizar, chaveUnica, aoExcluir, ordenar = porNome) {
  rota('GET', caminho, ({ q }) => {
    const busca = q.get('busca')?.toLowerCase();
    const categoria = q.get('categoria');
    return db[colecao]
      .filter((x) => !busca || x.nome.toLowerCase().includes(busca))
      .filter((x) => !categoria || x.categoria === categoria)
      .sort(ordenar);
  });
  rota('GET', `${caminho}/{id}`, ({ p }) => db[colecao].find((x) => x.id === Number(p.id)) || naoEncontrado());
  const salvar = (corpo, atual) => {
    const dados = normalizar(corpo);
    if (db[colecao].some((x) => x.id !== atual?.id && chaveUnica(x) === chaveUnica(dados)))
      falha(409, 'NOME_DUPLICADO', 'Já existe um cadastro com este nome.');
    return dados;
  };
  rota('POST', caminho, ({ u, corpo }) => {
    exigirAdmin(u);
    const item = { id: db.seq[seq]++, ...salvar(corpo) };
    db[colecao].push(item);
    return [201, item];
  });
  rota('PUT', `${caminho}/{id}`, ({ u, p, corpo }) => {
    exigirAdmin(u);
    const item = db[colecao].find((x) => x.id === Number(p.id)) || naoEncontrado();
    return Object.assign(item, salvar(corpo, item));
  });
  rota('DELETE', `${caminho}/{id}`, ({ u, p }) => {
    exigirAdmin(u);
    const item = db[colecao].find((x) => x.id === Number(p.id)) || naoEncontrado();
    aoExcluir(item);
    db[colecao] = db[colecao].filter((x) => x.id !== item.id);
    return null;
  });
}

const exigirNome = (corpo) => (corpo.nome?.trim() ? corpo.nome.trim() : validacao('body.nome', 'obrigatório'));
catalogo(
  '/equipamentos',
  'equipamentos',
  'equipamento',
  (c) => ({ nome: exigirNome(c), descricao: textoOuNulo(c.descricao) }),
  (x) => x.nome,
  (item) => db.salas.forEach((s) => (s.equipamentos = s.equipamentos.filter((e) => e.equipamento_id !== item.id))),
);
rota('GET', '/softwares/categorias', () =>
  [...new Set(db.softwares.map((s) => s.categoria).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'pt-BR')),
);
catalogo(
  '/softwares',
  'softwares',
  'software',
  (c) => ({ nome: exigirNome(c), versao: textoOuNulo(c.versao), categoria: textoOuNulo(c.categoria) }),
  (x) => `${x.nome}|${x.versao ?? ''}`,
  (item) => db.salas.forEach((s) => (s.softwares = s.softwares.filter((id) => id !== item.id))),
  (a, b) => porNome(a, b) || (a.versao || '').localeCompare(b.versao || ''),
);

// Professores
rota('GET', '/professores', ({ u, q }) => {
  exigirAdmin(u);
  const busca = q.get('busca')?.toLowerCase();
  return db.professores
    .filter((p) => !busca || `${p.nome} ${p.rm}`.toLowerCase().includes(busca))
    .filter((p) => !q.get('papel') || p.papel === q.get('papel'))
    .filter((p) => !q.get('ativo') || String(p.ativo) === q.get('ativo'))
    .sort(porNome)
    .map(usuarioJson);
});
const acharProfessor = (id) => db.professores.find((x) => x.id === Number(id)) || naoEncontrado();
rota('GET', '/professores/{id}', ({ u, p }) => (exigirAdmin(u), usuarioJson(acharProfessor(p.id))));
rota('POST', '/professores', ({ u, corpo }) => {
  exigirAdmin(u);
  if (!/^[A-Za-z0-9]{3,20}$/.test(corpo.rm || '')) validacao('body.rm', 'de 3 a 20 letras ou números');
  if (!corpo.senha || corpo.senha.length < 8) validacao('body.senha', 'mínimo de 8 caracteres');
  if (db.professores.some((p) => p.rm === corpo.rm)) falha(409, 'RM_DUPLICADO', 'Já existe uma conta com este RM.');
  const novo = {
    id: db.seq.professor++,
    rm: corpo.rm,
    nome: exigirNome(corpo),
    email: textoOuNulo(corpo.email),
    papel: corpo.papel || 'professor',
    ativo: true,
    senha: corpo.senha,
    criado_em: agoraIso(),
  };
  db.professores.push(novo);
  return [201, usuarioJson(novo)];
});
rota('PUT', '/professores/{id}', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const alvo = acharProfessor(p.id);
  if (alvo.id === u.id && (corpo.ativo === false || corpo.papel !== 'admin'))
    falha(422, 'OPERACAO_EM_SI_MESMO', 'Você não pode desativar a própria conta nem remover seu papel de admin.');
  const derruba = corpo.papel !== alvo.papel || (alvo.ativo && corpo.ativo === false);
  Object.assign(alvo, { nome: exigirNome(corpo), email: textoOuNulo(corpo.email), papel: corpo.papel, ativo: corpo.ativo });
  if (derruba) revogarTokens(alvo);
  return usuarioJson(alvo);
});
rota('PUT', '/professores/{id}/senha', ({ u, p, corpo }) => {
  exigirAdmin(u);
  if (!corpo.nova_senha || corpo.nova_senha.length < 8) validacao('body.nova_senha', 'mínimo de 8 caracteres');
  const alvo = acharProfessor(p.id);
  alvo.senha = corpo.nova_senha;
  revogarTokens(alvo); // inclusive a sessão do próprio admin, se alvo for ele
  return null;
});
rota('DELETE', '/professores/{id}', ({ u, p }) => {
  exigirAdmin(u);
  const alvo = acharProfessor(p.id);
  if (alvo.id === u.id) falha(422, 'OPERACAO_EM_SI_MESMO', 'Você não pode excluir a própria conta.');
  if (db.reservas.some((r) => r.professor_id === alvo.id) || db.grupos.some((g) => g.professor_id === alvo.id))
    falha(409, 'PROFESSOR_COM_RESERVAS', 'Esta conta tem reservas e não pode ser excluída. Desative-a.');
  db.professores = db.professores.filter((x) => x.id !== alvo.id);
  return null;
});

// Horários
rota('GET', '/horarios', ({ u, q }) => {
  const inativos = u?.papel === 'admin' && q.get('incluir_inativos') === 'true';
  return ordenarHorarios(
    db.horarios
      .filter((h) => h.ativo || inativos)
      .filter((h) => !q.get('dia_semana') || h.dias_semana.includes(Number(q.get('dia_semana'))))
      .filter((h) => !q.get('turno') || h.turno === q.get('turno')),
  );
});
rota('GET', '/horarios/{id}', ({ p }) => db.horarios.find((h) => h.id === Number(p.id)) || naoEncontrado());
const dadosHorario = (c, idAtual) => {
  const inicio = String(c.inicio).slice(0, 5);
  const fim = String(c.fim).slice(0, 5);
  if (!(fim > inicio)) validacao('body.fim', 'deve ser depois do início');
  if (!c.dias_semana?.length) validacao('body.dias_semana', 'lista vazia');
  const dados = { turno: c.turno, ordem: Number(c.ordem), inicio, fim, dias_semana: c.dias_semana, ativo: c.ativo ?? true };
  if (db.horarios.some((h) => h.id !== idAtual && h.turno === dados.turno && h.ordem === dados.ordem))
    falha(409, 'ORDEM_DUPLICADA', 'Já existe uma aula com esta ordem neste turno.');
  if (
    dados.ativo &&
    db.horarios.some(
      (h) =>
        h.id !== idAtual &&
        h.ativo &&
        h.dias_semana.some((d) => dados.dias_semana.includes(d)) &&
        sobrepoe(dados.inicio, dados.fim, h.inicio, h.fim),
    )
  )
    falha(409, 'HORARIO_SOBREPOSTO', 'Este horário se sobrepõe a outra aula ativa em algum dia em comum.');
  return dados;
};
rota('POST', '/horarios', ({ u, corpo }) => {
  exigirAdmin(u);
  const h = { id: db.seq.horario++, ...dadosHorario(corpo, null) };
  db.horarios.push(h);
  return [201, h];
});
rota('PUT', '/horarios/{id}', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const h = db.horarios.find((x) => x.id === Number(p.id)) || naoEncontrado();
  exigirAtivo(corpo);
  return Object.assign(h, dadosHorario(corpo, h.id));
});
rota('DELETE', '/horarios/{id}', ({ u, p }) => {
  exigirAdmin(u);
  const h = db.horarios.find((x) => x.id === Number(p.id)) || naoEncontrado();
  if (db.reservas.some((r) => r.horario_inicio_id === h.id || r.horario_fim_id === h.id))
    falha(409, 'HORARIO_EM_USO', 'Esta aula é usada em reservas. Desative-a em vez de excluir.');
  db.horarios = db.horarios.filter((x) => x.id !== h.id);
  return null;
});

// Semestres
const ordenarSemestres = (lista) => [...lista].sort((a, b) => b.data_inicio.localeCompare(a.data_inicio));
rota('GET', '/semestres', () => ordenarSemestres(db.semestres));
rota('GET', '/semestres/atual', () => {
  const hoje = isoData(new Date());
  return (
    db.semestres.find((s) => s.data_inicio <= hoje && hoje <= s.data_fim) ||
    [...db.semestres].sort((a, b) => a.data_inicio.localeCompare(b.data_inicio)).find((s) => s.data_inicio > hoje) ||
    naoEncontrado()
  );
});
rota('GET', '/semestres/{id}', ({ p }) => db.semestres.find((s) => s.id === Number(p.id)) || naoEncontrado());
const dadosSemestre = (c, idAtual) => {
  const dados = { nome: exigirNome(c), data_inicio: c.data_inicio, data_fim: c.data_fim };
  if (!(dados.data_fim > dados.data_inicio)) validacao('body.data_fim', 'deve ser depois do início');
  if (db.semestres.some((s) => s.id !== idAtual && s.nome === dados.nome))
    falha(409, 'NOME_DUPLICADO', 'Já existe um semestre com este nome.');
  if (db.semestres.some((s) => s.id !== idAtual && s.data_inicio <= dados.data_fim && dados.data_inicio <= s.data_fim))
    falha(409, 'SEMESTRE_SOBREPOSTO', 'As datas se sobrepõem a outro semestre.');
  return dados;
};
rota('POST', '/semestres', ({ u, corpo }) => {
  exigirAdmin(u);
  const s = { id: db.seq.semestre++, ...dadosSemestre(corpo, null) };
  db.semestres.push(s);
  return [201, s];
});
rota('PUT', '/semestres/{id}', ({ u, p, corpo }) => {
  exigirAdmin(u);
  const s = db.semestres.find((x) => x.id === Number(p.id)) || naoEncontrado();
  return Object.assign(s, dadosSemestre(corpo, s.id));
});
rota('DELETE', '/semestres/{id}', ({ u, p }) => {
  exigirAdmin(u);
  const s = db.semestres.find((x) => x.id === Number(p.id)) || naoEncontrado();
  if (db.grupos.some((g) => g.semestre_id === s.id))
    falha(409, 'SEMESTRE_EM_USO', 'Há reservas semanais neste semestre; ele não pode ser excluído.');
  db.semestres = db.semestres.filter((x) => x.id !== s.id);
  return null;
});

// Reservas
rota('POST', '/reservas', ({ u, corpo }) => {
  exigirProfessor(u);
  const sala = salaParaReserva(corpo.sala_id, u);
  const dono = donoDaReserva(corpo, u);
  const bloco = validarAulas(corpo.horario_ids, corpo.data);
  if (momento(corpo.data, bloco.inicio) <= new Date())
    falha(422, 'DATA_PASSADA', 'Não é possível reservar um horário que já começou.');
  const conflitos = conflitosEm(sala.id, corpo.data, bloco.inicio, bloco.fim);
  if (conflitos.length)
    falha(409, 'CONFLITO_RESERVA', 'Sala não disponível neste horário.', { conflitos: conflitos.map(conflitoJson) });
  return [201, reservaJson(criarRegistroReserva(sala, dono, u, corpo.data, bloco, corpo.observacao), u)];
});
rota('POST', '/reservas/recorrentes/previa', ({ u, corpo }) => {
  exigirProfessor(u);
  const { sala, bloco, semestre, datas } = serie(corpo, u);
  const ocorrencias = datas.map((data) => {
    const c = conflitosEm(sala.id, data, bloco.inicio, bloco.fim);
    return { data, livre: c.length === 0, conflitos: c.map(conflitoJson) };
  });
  const livres = ocorrencias.filter((o) => o.livre).length;
  return {
    sala: salaMini(sala.id),
    semestre: semestreJson(semestre),
    dia_semana: diaSemana(corpo.data_inicio),
    inicio: bloco.inicio,
    fim: bloco.fim,
    horario_ids: bloco.aulas.map((a) => a.id),
    ocorrencias,
    total: ocorrencias.length,
    livres,
    em_conflito: ocorrencias.length - livres,
  };
});
rota('POST', '/reservas/recorrentes', ({ u, corpo }) => {
  exigirProfessor(u);
  const { sala, bloco, semestre, datas } = serie(corpo, u);
  const dono = donoDaReserva(corpo, u);
  if (!corpo.datas?.length) validacao('body.datas', 'lista vazia');
  if (corpo.datas.some((d) => !datas.includes(d)))
    falha(422, 'DATA_FORA_DA_SERIE', 'Alguma data enviada não pertence à série semanal.');
  const conflitos = corpo.datas.flatMap((d) => conflitosEm(sala.id, d, bloco.inicio, bloco.fim));
  if (conflitos.length)
    falha(409, 'CONFLITO_RESERVA', 'Algumas datas ficaram ocupadas.', { conflitos: conflitos.map(conflitoJson) });
  const grupo = {
    id: db.seq.grupo++,
    sala_id: sala.id,
    professor_id: dono,
    semestre_id: semestre.id,
    dia_semana: diaSemana(corpo.data_inicio),
    inicio: bloco.inicio,
    fim: bloco.fim,
    criado_por_id: u.id,
    criado_em: agoraIso(),
  };
  db.grupos.push(grupo);
  const criadas = [...corpo.datas]
    .sort()
    .map((d) => criarRegistroReserva(sala, dono, u, d, bloco, corpo.observacao, grupo.id));
  return [201, { grupo: grupoJson(grupo), reservas: criadas.map((r) => reservaJson(r, u)) }];
});
const ordenarReservas = (lista, desc = false) =>
  [...lista].sort((a, b) => {
    const c =
      a.data.localeCompare(b.data) || a.inicio.localeCompare(b.inicio) || salaMini(a.sala_id).nome.localeCompare(salaMini(b.sala_id).nome);
    return desc ? -c : c;
  });
const filtrarStatus = (lista, status = 'ativa') => (status === 'todas' ? lista : lista.filter((r) => r.status === status));
rota('GET', '/reservas', ({ u, q }) => {
  const modos = ['mes', 'data', 'de'].filter((k) => q.get(k));
  if (modos.length !== 1) falha(422, 'INTERVALO_INVALIDO', 'Informe exatamente um período: mes, data ou de/ate.');
  let de;
  let ate;
  if (q.get('mes')) {
    const [a, m] = q.get('mes').split('-').map(Number);
    de = `${a}-${dois(m)}-01`;
    ate = isoData(new Date(a, m, 0));
  } else if (q.get('data')) {
    de = q.get('data');
    ate = de;
  } else {
    de = q.get('de');
    ate = q.get('ate');
    if (!ate || ate < de || Math.round((deIso(ate) - deIso(de)) / 86400000) + 1 > 62)
      falha(422, 'INTERVALO_INVALIDO', 'Intervalo inválido (até 62 dias).');
  }
  const salas = q.getAll('sala_id').map(Number);
  let lista = db.reservas.filter((r) => r.data >= de && r.data <= ate);
  if (salas.length) lista = lista.filter((r) => salas.includes(r.sala_id));
  if (q.get('professor_id')) lista = lista.filter((r) => r.professor_id === Number(q.get('professor_id')));
  return ordenarReservas(filtrarStatus(lista, q.get('status') || 'ativa')).map((r) => reservaJson(r, u));
});
rota('GET', '/reservas/minhas', ({ u, q }) => {
  exigirProfessor(u);
  const periodo = q.get('periodo') || 'futuras';
  const agora = new Date();
  let lista = db.reservas.filter((r) => r.professor_id === u.id);
  if (periodo === 'futuras') lista = lista.filter((r) => momento(r.data, r.fim) > agora);
  if (periodo === 'passadas') lista = lista.filter((r) => momento(r.data, r.fim) <= agora);
  lista = filtrarStatus(lista, q.get('status') || 'ativa');
  return ordenarReservas(lista, periodo !== 'futuras').map((r) => reservaJson(r, u));
});
const acharGrupo = (id, u) => {
  const g = db.grupos.find((x) => x.id === Number(id)) || naoEncontrado();
  if (u.papel !== 'admin' && g.professor_id !== u.id) falha(403, 'SEM_PERMISSAO', 'Esta recorrência é de outro professor.');
  return g;
};
rota('GET', '/reservas/grupos/{id}', ({ u, p }) => {
  exigirProfessor(u);
  const g = acharGrupo(p.id, u);
  return {
    grupo: grupoJson(g),
    reservas: ordenarReservas(db.reservas.filter((r) => r.grupo_recorrencia_id === g.id)).map((r) => reservaJson(r, u)),
  };
});
rota('POST', '/reservas/grupos/{id}/cancelar', ({ u, p, corpo }) => {
  exigirProfessor(u);
  const g = acharGrupo(p.id, u);
  const agora = new Date();
  const alvo = db.reservas.filter(
    (r) => r.grupo_recorrencia_id === g.id && r.status === 'ativa' && momento(r.data, r.inicio) > agora,
  );
  alvo.forEach((r) => cancelar(r, u, corpo?.motivo));
  return { grupo_recorrencia_id: g.id, canceladas: alvo.length, reservas_ids: alvo.map((r) => r.id) };
});
rota('GET', '/reservas/{id}', ({ u, p }) =>
  reservaJson(db.reservas.find((r) => r.id === Number(p.id)) || naoEncontrado(), u),
);
rota('POST', '/reservas/{id}/cancelar', ({ u, p, corpo }) => {
  exigirProfessor(u);
  const r = db.reservas.find((x) => x.id === Number(p.id)) || naoEncontrado();
  if (u.papel !== 'admin' && r.professor_id !== u.id) falha(403, 'SEM_PERMISSAO', 'Esta reserva é de outro professor.');
  if (r.status === 'cancelada') falha(409, 'RESERVA_JA_CANCELADA', 'Esta reserva já foi cancelada.');
  if (u.papel !== 'admin' && momento(r.data, r.inicio) <= new Date())
    falha(422, 'RESERVA_JA_INICIADA', 'A aula já começou; não é mais possível cancelar.');
  cancelar(r, u, corpo?.motivo);
  return reservaJson(r, u);
});

// ---------- transporte ----------
const esperar = (ms) => new Promise((r) => setTimeout(r, ms));

export async function fetchMock(url, init = {}) {
  if (comAtraso) await esperar(120 + Math.random() * 180);
  const endereco = new URL(url);
  const base = new URL(API_URL);
  const caminho = endereco.pathname.slice(base.pathname.replace(/\/$/, '').length) || '/';
  const metodo = (init.method || 'GET').toUpperCase();
  const headers = init.headers || {};
  const form = init.body instanceof FormData ? init.body : null;
  let corpo = null;
  if (!form && typeof init.body === 'string') corpo = JSON.parse(init.body);
  const u = usuarioDoToken(headers);

  const json = (status, dados) =>
    new Response(dados === null ? null : JSON.stringify(dados), {
      status,
      headers: { 'Content-Type': 'application/json' },
    });

  for (const r of rotas) {
    if (r.metodo !== metodo) continue;
    const m = r.re.exec(caminho);
    if (!m) continue;
    const p = Object.fromEntries(r.chaves.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
    try {
      const resultado = r.fn({ u, p, q: endereco.searchParams, corpo, form });
      if (Array.isArray(resultado) && typeof resultado[0] === 'number' && resultado.length === 2)
        return json(resultado[0], resultado[1]);
      if (resultado === null) return new Response(null, { status: 204 });
      return json(200, resultado);
    } catch (e) {
      if (e instanceof Falha) return json(e.status, e.corpo);
      console.error('[mock]', e);
      return json(500, { detail: 'Erro interno do servidor.', codigo: 'ERRO_INTERNO' });
    }
  }
  return json(404, { detail: 'Rota não encontrada.', codigo: 'NAO_ENCONTRADO' });
}

export function instalarMock() {
  definirTransporte(fetchMock);
  console.info('[sala_web] API simulada ativa (VITE_USE_MOCK=true). Contas: admin/admin1234, 123456/senha1234.');
}
