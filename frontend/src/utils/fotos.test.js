import { limiteUploadMb, validarFoto } from './fotos';

const MB = 1024 * 1024;
const arquivo = (nome, tipo, tamanho) => {
  const f = new File(['x'], nome, { type: tipo });
  Object.defineProperty(f, 'size', { value: tamanho });
  return f;
};

describe('validarFoto', () => {
  it('aceita JPEG, PNG e WebP dentro do limite', () => {
    expect(validarFoto(arquivo('a.jpg', 'image/jpeg', 5 * MB), 5)).toBeNull();
    expect(validarFoto(arquivo('a.png', 'image/png', 10), 5)).toBeNull();
    expect(validarFoto(arquivo('a.webp', 'image/webp', 10), 5)).toBeNull();
  });

  it('recusa arquivo acima do limite com 413 ARQUIVO_GRANDE', () => {
    const erro = validarFoto(arquivo('grande.jpg', 'image/jpeg', 6 * MB), 5);
    expect(erro).toMatchObject({ status: 413, codigo: 'ARQUIVO_GRANDE' });
    expect(erro.detail).toContain('5 MB');
  });

  it('recusa tipo fora da lista (GIF, sem tipo) com 415 TIPO_ARQUIVO_INVALIDO', () => {
    expect(validarFoto(arquivo('a.gif', 'image/gif', 10), 5)).toMatchObject({ status: 415, codigo: 'TIPO_ARQUIVO_INVALIDO' });
    expect(validarFoto(arquivo('a.bin', '', 10), 5)).toMatchObject({ status: 415 });
  });

  it('limite vem de VITE_UPLOAD_MAX_MB, com padrão 5', () => {
    expect(limiteUploadMb(undefined)).toBe(5);
    expect(limiteUploadMb('')).toBe(5);
    expect(limiteUploadMb('abc')).toBe(5);
    expect(limiteUploadMb('8')).toBe(8);
  });
});
