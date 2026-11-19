import Alerta from './Alerta';
import ListaConflitos from './ListaConflitos';
import { mensagemDeErro } from '../utils/formatacao';

/** Mostra um ErroApi: `detail`, lista `erros` (422 VALIDACAO) e `conflitos` (409). */
export default function ErroApiAlerta({ erro, titulo, acao }) {
  if (!erro) return null;
  return (
    <Alerta tipo="erro" titulo={titulo} acao={acao}>
      <p>{mensagemDeErro(erro)}</p>
      {erro.erros?.length > 0 && (
        <ul className="lista-erros">
          {erro.erros.map((e, i) => (
            <li key={`${e.campo}-${i}`}>
              {e.campo ? <code>{String(e.campo).replace(/^(body|query|path)\./, '')}</code> : null}
              {e.campo ? ': ' : ''}
              {e.mensagem}
            </li>
          ))}
        </ul>
      )}
      {erro.conflitos?.length > 0 && <ListaConflitos conflitos={erro.conflitos} />}
    </Alerta>
  );
}
