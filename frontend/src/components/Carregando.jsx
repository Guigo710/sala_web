export default function Carregando({ texto = 'Carregando…', compacto = false }) {
  return (
    <div className={compacto ? 'carregando carregando-compacto' : 'carregando'} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{texto}</span>
    </div>
  );
}
