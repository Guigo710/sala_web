import { Link } from 'react-router-dom';
import { urlArquivo } from '../api/cliente';
import { corDoTipo } from '../utils/formatacao';

function IconeTipo({ tipo }) {
  const lab = tipo?.startsWith('lab_');
  return (
    <svg viewBox="0 0 48 48" width="48" height="48" aria-hidden="true">
      {lab ? (
        <>
          <rect x="8" y="10" width="32" height="20" rx="2" fill="none" stroke="currentColor" strokeWidth="3" />
          <path d="M18 38h12M24 30v8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </>
      ) : (
        <>
          <rect x="6" y="8" width="36" height="22" rx="2" fill="none" stroke="currentColor" strokeWidth="3" />
          <path d="M12 38h24M16 30l-2 8M32 30l2 8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

/** Cartão de ambiente na listagem (SalaResumo §3.6). */
export default function CartaoSala({ sala }) {
  const capa = urlArquivo(sala.foto_capa_url);
  const equipamentos = sala.equipamentos || [];
  return (
    <article className="cartao-sala">
      <Link to={`/ambientes/${sala.id}`} className="cartao-sala-link">
        <div className="cartao-sala-capa" style={{ '--cor-tipo': corDoTipo(sala.tipo) }}>
          {capa ? (
            <img src={capa} alt="" loading="lazy" />
          ) : (
            <div className="capa-vazia">
              <IconeTipo tipo={sala.tipo} />
              <span>Sem foto</span>
            </div>
          )}
          <span className="selo-tipo">{sala.tipo_rotulo}</span>
        </div>
        <div className="cartao-sala-corpo">
          <h2 className="cartao-sala-nome">{sala.nome}</h2>
          <p className="cartao-sala-info">
            <span>
              <strong>{sala.capacidade}</strong> lugares
            </span>
            {sala.localizacao && <span>{sala.localizacao}</span>}
          </p>
          {!sala.ativo && <span className="selo selo-inativo">Inativo</span>}
          {equipamentos.length > 0 && (
            <ul className="cartao-sala-equip" aria-label="Equipamentos">
              {equipamentos.slice(0, 4).map((e) => (
                <li key={e.equipamento_id} title={e.especificacao || undefined}>
                  {e.quantidade > 1 ? `${e.quantidade}× ` : ''}
                  {e.nome}
                </li>
              ))}
              {equipamentos.length > 4 && <li>+{equipamentos.length - 4}</li>}
            </ul>
          )}
        </div>
      </Link>
    </article>
  );
}
