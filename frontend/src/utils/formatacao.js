/** Mensagens de erro e textos reutilizáveis. */

/** Mensagem curta de um erro qualquer (ErroApi ou Error). */
export function mensagemDeErro(erro) {
  if (!erro) return '';
  return erro.detail || erro.message || 'Ocorreu um erro inesperado.';
}

/** Cores por tipo de ambiente (os rótulos vêm de GET /salas/tipos; aqui só a cor). */
export const CORES_TIPO = {
  sala: '#1d4e89',
  lab_informatica: '#0f766e',
  lab_ciencias: '#7c3aed',
  lab_outro: '#b45309',
  auditorio: '#be123c',
  outro: '#475569',
};

export const corDoTipo = (tipo) => CORES_TIPO[tipo] || CORES_TIPO.outro;

export const plural = (n, singular, pluralTexto) => `${n} ${n === 1 ? singular : pluralTexto}`;
