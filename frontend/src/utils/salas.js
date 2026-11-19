/** Corpo do POST/PUT /salas a partir de um SalaDetalhe ou dos valores do formulário (§4.3). */
export function corpoSala(sala) {
  const texto = (v) => (typeof v === 'string' && v.trim() ? v.trim() : null);
  return {
    nome: String(sala.nome ?? '').trim(),
    tipo: sala.tipo,
    descricao: texto(sala.descricao),
    capacidade: Number(sala.capacidade),
    localizacao: texto(sala.localizacao),
    ativo: Boolean(sala.ativo),
  };
}
