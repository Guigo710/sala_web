import { ErroApi } from '../api/cliente';

/** Tipos aceitos no upload de fotos (§4.4). O servidor confere de novo pelo conteúdo. */
export const TIPOS_FOTO = ['image/jpeg', 'image/png', 'image/webp'];

/** Limite em MB: `VITE_UPLOAD_MAX_MB` (deve acompanhar o `UPLOAD_MAX_MB` do backend), padrão 5. */
export function limiteUploadMb(valor = import.meta.env.VITE_UPLOAD_MAX_MB) {
  const n = Number(valor);
  return Number.isFinite(n) && n > 0 ? n : 5;
}

/**
 * Validação local, antes de enviar: só uma dica para não gastar a requisição.
 * Devolve um `ErroApi` igual ao que a API mandaria (413/415) ou `null` se o arquivo pode seguir.
 */
export function validarFoto(arquivo, maxMb = limiteUploadMb()) {
  if (!TIPOS_FOTO.includes(arquivo.type)) {
    return new ErroApi({
      status: 415,
      codigo: 'TIPO_ARQUIVO_INVALIDO',
      detail: 'Envie uma imagem JPEG, PNG ou WebP.',
    });
  }
  if (arquivo.size > maxMb * 1024 * 1024) {
    return new ErroApi({
      status: 413,
      codigo: 'ARQUIVO_GRANDE',
      detail: `A foto passa do limite de ${maxMb} MB.`,
    });
  }
  return null;
}
