import { useState } from 'react';

function IconeFotoQuebrada() {
  return (
    <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M3 16l5-5 4 4 3-3 6 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M4 4l16 16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

/**
 * `<img>` de uma foto servida pela API, com substituto quando ela não carrega (ticket 67, ADR-0010): uma foto
 * antiga cujo arquivo se perdeu na importação responde 404 na `url`. No `error` o `<img>` sai de cena (sem laço
 * de erro: o substituto não tenta carregar nada) e entra um bloco neutro com "Foto indisponível", mantendo o
 * `alt` como nome acessível. Se o `src` mudar, a nova foto é tentada normalmente. É um `<span>` (conteúdo
 * permitido dentro de `<button>` e `<a>`, onde as fotos da galeria e do cartão ficam).
 *
 * @param {string} src URL absoluta (use `urlArquivo`)
 * @param {string} alt texto alternativo; `""` = decorativa (o substituto também fica oculto ao leitor de tela)
 * @param {string} [substituto] texto do substituto (padrão "Foto indisponível"); entra também no nome acessível
 */
export default function FotoApi({ src, alt, substituto = 'Foto indisponível', ...resto }) {
  const [srcComErro, setSrcComErro] = useState(null);

  if (src && srcComErro === src) {
    const acessivel = alt ? { role: 'img', 'aria-label': `${alt}. ${substituto}` } : { 'aria-hidden': true };
    return (
      <span className="foto-indisponivel" data-foto-indisponivel="" {...acessivel}>
        <IconeFotoQuebrada />
        <span>{substituto}</span>
      </span>
    );
  }

  return <img src={src} alt={alt} onError={() => setSrcComErro(src)} {...resto} />;
}
