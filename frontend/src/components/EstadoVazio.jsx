export default function EstadoVazio({ titulo, children }) {
  return (
    <div className="estado-vazio">
      <p className="estado-vazio-titulo">{titulo}</p>
      {children && <div className="estado-vazio-texto">{children}</div>}
    </div>
  );
}
