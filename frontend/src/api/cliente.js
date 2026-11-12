/**
 * Cliente HTTP da API sala_web (docs/api-contrato.md §1).
 * - Base em VITE_API_URL, rotas sem barra final.
 * - Envia `Authorization: Bearer <token>` quando há sessão.
 * - Converte o envelope de erro (§1.4) em `ErroApi`.
 * - 401 em rota protegida (com token enviado) avisa a sessão para limpar e ir ao login.
 */

export const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

export class ErroApi extends Error {
  constructor({ status, codigo, detail, erros = null, conflitos = null }) {
    super(detail);
    this.name = 'ErroApi';
    this.status = status;
    this.codigo = codigo;
    this.detail = detail;
    this.erros = erros;
    this.conflitos = conflitos;
  }
}

const MENSAGENS_PADRAO = {
  0: 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.',
  400: 'Requisição inválida.',
  401: 'Sua sessão expirou. Entre novamente.',
  403: 'Você não tem permissão para esta ação.',
  404: 'Não encontrado.',
  409: 'Conflito com dados existentes.',
  413: 'Arquivo grande demais.',
  415: 'Tipo de arquivo não aceito.',
  422: 'Dados inválidos.',
  429: 'Muitas tentativas. Aguarde alguns minutos.',
  500: 'Erro interno do servidor. Tente novamente mais tarde.',
};

let tokenAtual = null;
let aoNaoAutenticado = null;
let transporte = null; // fetch alternativo (mock de desenvolvimento ou testes)

export function definirToken(token) {
  tokenAtual = token || null;
}

export function obterToken() {
  return tokenAtual;
}

/** Registra a função chamada quando uma rota protegida responde 401. */
export function aoSessaoExpirada(funcao) {
  aoNaoAutenticado = funcao;
}

/** Troca o `fetch` usado pelo cliente (mock opcional em desenvolvimento, testes). */
export function definirTransporte(funcao) {
  transporte = funcao;
}

function buscar(url, opcoes) {
  return (transporte || globalThis.fetch)(url, opcoes);
}

/**
 * Monta a query string. Arrays viram parâmetro repetido (`tipo=a&tipo=b`);
 * `null`, `undefined`, `''` e arrays vazios são omitidos.
 */
export function montarQuery(params) {
  if (!params) return '';
  const qs = new URLSearchParams();
  for (const [chave, valor] of Object.entries(params)) {
    if (valor === null || valor === undefined || valor === '') continue;
    if (Array.isArray(valor)) {
      for (const item of valor) {
        if (item !== null && item !== undefined && item !== '') qs.append(chave, String(item));
      }
    } else {
      qs.append(chave, String(valor));
    }
  }
  const texto = qs.toString();
  return texto ? `?${texto}` : '';
}

/** URL absoluta de um arquivo servido pela API (ex.: `Foto.url`, §3.5). */
export function urlArquivo(url) {
  if (!url) return null;
  if (/^(https?:|data:|blob:)/.test(url)) return url;
  return `${API_URL}${url.startsWith('/') ? '' : '/'}${url}`;
}

function cabecalhos(extra = {}) {
  const h = { Accept: 'application/json', ...extra };
  if (tokenAtual) h.Authorization = `Bearer ${tokenAtual}`;
  return h;
}

/** Converte status + corpo de erro em `ErroApi` e trata o 401. */
export function criarErro(status, corpo, tokenEnviado) {
  const envelope = corpo && typeof corpo === 'object' ? corpo : {};
  const detail =
    typeof envelope.detail === 'string' && envelope.detail
      ? envelope.detail
      : MENSAGENS_PADRAO[status] || MENSAGENS_PADRAO[status >= 500 ? 500 : 400];
  const erro = new ErroApi({
    status,
    codigo: envelope.codigo || (status >= 500 ? 'ERRO_INTERNO' : `HTTP_${status}`),
    detail,
    erros: Array.isArray(envelope.erros) ? envelope.erros : null,
    conflitos: Array.isArray(envelope.conflitos) ? envelope.conflitos : null,
  });
  if (status === 401 && tokenEnviado && erro.codigo !== 'CREDENCIAIS_INVALIDAS' && aoNaoAutenticado) {
    aoNaoAutenticado(erro);
  }
  return erro;
}

async function lerCorpo(resposta) {
  if (resposta.status === 204) return null;
  const texto = await resposta.text();
  if (!texto) return null;
  try {
    return JSON.parse(texto);
  } catch {
    return texto;
  }
}

/**
 * Faz uma requisição à API.
 * @param {string} metodo GET, POST, PUT, PATCH, DELETE
 * @param {string} caminho ex.: `/salas/3`
 * @param {{query?: object, corpo?: any, formData?: FormData}} opcoes
 */
export async function requisitar(metodo, caminho, { query, corpo, formData } = {}) {
  const url = `${API_URL}${caminho}${montarQuery(query)}`;
  const tokenEnviado = Boolean(tokenAtual);
  const init = { method: metodo, headers: cabecalhos() };
  if (formData) {
    init.body = formData;
  } else if (corpo !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(corpo);
  }

  let resposta;
  try {
    resposta = await buscar(url, init);
  } catch {
    throw new ErroApi({ status: 0, codigo: 'SEM_CONEXAO', detail: MENSAGENS_PADRAO[0] });
  }

  const dados = await lerCorpo(resposta);
  if (!resposta.ok) throw criarErro(resposta.status, dados, tokenEnviado);
  return dados;
}

export const api = {
  get: (caminho, query) => requisitar('GET', caminho, { query }),
  post: (caminho, corpo, query) => requisitar('POST', caminho, { corpo, query }),
  put: (caminho, corpo) => requisitar('PUT', caminho, { corpo }),
  patch: (caminho, corpo) => requisitar('PATCH', caminho, { corpo }),
  delete: (caminho) => requisitar('DELETE', caminho),
};

/**
 * Envio `multipart/form-data` com progresso (XMLHttpRequest, pois `fetch` não informa
 * o progresso do upload). Com transporte alternativo ativo, usa `requisitar`.
 * @param {(fracao: number) => void} [aoProgresso] recebe valores de 0 a 1
 */
export function enviarFormulario(caminho, formData, aoProgresso) {
  if (transporte || typeof XMLHttpRequest === 'undefined') {
    aoProgresso?.(0);
    return requisitar('POST', caminho, { formData }).then((dados) => {
      aoProgresso?.(1);
      return dados;
    });
  }
  const tokenEnviado = Boolean(tokenAtual);
  return new Promise((resolver, rejeitar) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_URL}${caminho}`);
    const h = cabecalhos();
    for (const [k, v] of Object.entries(h)) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && aoProgresso) aoProgresso(e.loaded / e.total);
    };
    xhr.onerror = () =>
      rejeitar(new ErroApi({ status: 0, codigo: 'SEM_CONEXAO', detail: MENSAGENS_PADRAO[0] }));
    xhr.onload = () => {
      let dados = null;
      try {
        dados = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        dados = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        aoProgresso?.(1);
        resolver(dados);
      } else {
        rejeitar(criarErro(xhr.status, dados, tokenEnviado));
      }
    };
    xhr.send(formData);
  });
}
