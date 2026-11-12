/** Caixa de mensagem. `tipo`: erro | aviso | sucesso | info. */
export default function Alerta({ tipo = 'info', titulo, children, acao }) {
  const papel = tipo === 'erro' || tipo === 'aviso' ? 'alert' : 'status';
  return (
    <div className={`alerta alerta-${tipo}`} role={papel}>
      <div className="alerta-texto">
        {titulo && <strong className="alerta-titulo">{titulo}</strong>}
        {children}
      </div>
      {acao && <div className="alerta-acao">{acao}</div>}
    </div>
  );
}
