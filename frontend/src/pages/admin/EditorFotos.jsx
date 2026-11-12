import { useRef, useState } from 'react';
import { urlArquivo } from '../../api/cliente';
import { atualizarLegendaFoto, enviarFoto, excluirFoto, reordenarFotos } from '../../api/fotos';
import { useAvisos } from '../../components/avisos';
import { useConfirmar } from '../../components/useConfirmar';
import ErroApiAlerta from '../../components/ErroApiAlerta';
import { mensagemDeErro } from '../../utils/formatacao';
import { TIPOS_FOTO, limiteUploadMb, validarFoto } from '../../utils/fotos';

let proximaChave = 1;

function ItemFoto({ foto, indice, total, salaId, aoMover, aoRemover, aoAtualizar }) {
  const [legenda, setLegenda] = useState(foto.legenda ?? '');
  const [erro, setErro] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const alterada = legenda !== (foto.legenda ?? '');

  const salvar = async (e) => {
    e.preventDefault();
    if (!alterada) return;
    setErro(null);
    setSalvando(true);
    try {
      const atualizada = await atualizarLegendaFoto(salaId, foto.id, legenda.trim() || null);
      aoAtualizar(atualizada);
      setLegenda(atualizada.legenda ?? '');
    } catch (err) {
      setErro(err);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <li className="foto-item">
      <img src={urlArquivo(foto.url)} alt={foto.legenda || `Foto ${indice + 1}`} />
      <div className="foto-item-corpo">
        <span className="foto-ordem">{indice === 0 ? 'Capa' : `#${indice + 1}`}</span>
        <form onSubmit={salvar} className="foto-legenda">
          <label htmlFor={`legenda-${foto.id}`} className="sr-only">
            Legenda da foto {indice + 1}
          </label>
          <input
            id={`legenda-${foto.id}`}
            maxLength={200}
            placeholder="Legenda (opcional)"
            value={legenda}
            onChange={(e) => setLegenda(e.target.value)}
          />
          <button type="submit" className="botao botao-secundario botao-pequeno" disabled={!alterada || salvando}>
            {salvando ? 'Salvando…' : 'Salvar'}
          </button>
        </form>
        {erro && <p className="erro-campo">{mensagemDeErro(erro)}</p>}
        <div className="acoes-linha">
          <button
            type="button"
            className="botao botao-secundario botao-pequeno"
            onClick={() => aoMover(indice, -1)}
            disabled={indice === 0}
            aria-label={`Mover foto ${indice + 1} para antes`}
          >
            ↑
          </button>
          <button
            type="button"
            className="botao botao-secundario botao-pequeno"
            onClick={() => aoMover(indice, 1)}
            disabled={indice === total - 1}
            aria-label={`Mover foto ${indice + 1} para depois`}
          >
            ↓
          </button>
          <button
            type="button"
            className="botao botao-perigo-leve botao-pequeno"
            onClick={() => aoRemover(foto)}
            aria-label={`Remover foto ${indice + 1}`}
          >
            Remover
          </button>
        </div>
      </div>
    </li>
  );
}

/** Galeria do ambiente: upload múltiplo (1 requisição por arquivo), legenda, ordem e remoção. */
export default function EditorFotos({ sala }) {
  const { avisar } = useAvisos();
  const [confirmar, dialogo] = useConfirmar();
  const [fotos, setFotos] = useState(sala.fotos);
  const [envios, setEnvios] = useState([]);
  const [erro, setErro] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const entrada = useRef(null);

  const atualizarEnvio = (chave, mudancas) =>
    setEnvios((lista) => lista.map((e) => (e.chave === chave ? { ...e, ...mudancas } : e)));

  const aoEscolher = async (e) => {
    const arquivos = [...e.target.files];
    e.target.value = '';
    if (arquivos.length === 0) return;
    // O `accept` só filtra o diálogo; arquivo fora do tipo ou do tamanho nem vai para a API.
    const novos = arquivos.map((arquivo) => {
      const erroLocal = validarFoto(arquivo);
      return {
        chave: proximaChave++,
        arquivo,
        nome: arquivo.name,
        progresso: 0,
        estado: erroLocal ? 'erro' : 'aguardando',
        erro: erroLocal,
      };
    });
    setEnvios((lista) => [...lista.filter((x) => x.estado !== 'ok'), ...novos]);
    setEnviando(true);
    let enviadas = 0;
    for (const item of novos) {
      if (item.erro) continue;
      atualizarEnvio(item.chave, { estado: 'enviando' });
      try {
        const foto = await enviarFoto(sala.id, item.arquivo, null, (p) =>
          atualizarEnvio(item.chave, { progresso: p }),
        );
        setFotos((f) => [...f, foto]);
        atualizarEnvio(item.chave, { estado: 'ok', progresso: 1 });
        enviadas += 1;
      } catch (err) {
        atualizarEnvio(item.chave, { estado: 'erro', erro: err });
      }
    }
    setEnviando(false);
    if (enviadas > 0) avisar(enviadas === 1 ? '1 foto enviada.' : `${enviadas} fotos enviadas.`);
  };

  const mover = async (indice, delta) => {
    const destino = indice + delta;
    if (destino < 0 || destino >= fotos.length) return;
    const anterior = fotos;
    const nova = [...fotos];
    [nova[indice], nova[destino]] = [nova[destino], nova[indice]];
    setFotos(nova);
    setErro(null);
    try {
      setFotos(await reordenarFotos(sala.id, nova.map((f) => f.id)));
    } catch (err) {
      setFotos(anterior);
      setErro(err);
    }
  };

  const remover = async (foto) => {
    const ok = await confirmar({
      titulo: 'Remover foto',
      mensagem: `Remover esta foto${foto.legenda ? ` (“${foto.legenda}”)` : ''}? O arquivo será apagado.`,
      textoConfirmar: 'Remover',
      perigo: true,
    });
    if (!ok) return;
    setErro(null);
    try {
      await excluirFoto(sala.id, foto.id);
      setFotos((f) => f.filter((x) => x.id !== foto.id));
      avisar('Foto removida.');
    } catch (err) {
      setErro(err);
    }
  };

  return (
    <div>
      <div className="upload-area">
        <input
          ref={entrada}
          id="fotos-arquivos"
          type="file"
          accept={TIPOS_FOTO.join(',')}
          multiple
          className="sr-only"
          onChange={aoEscolher}
          disabled={enviando}
        />
        <label htmlFor="fotos-arquivos" className={enviando ? 'botao desabilitado' : 'botao'}>
          Enviar fotos…
        </label>
        <span className="texto-suave">JPEG, PNG ou WebP, até {limiteUploadMb()} MB cada. Você pode escolher várias de uma vez.</span>
      </div>

      {envios.length > 0 && (
        <ul className="lista-envios" aria-live="polite">
          {envios.map((e) => (
            <li key={e.chave} className={`envio envio-${e.estado}`}>
              <span className="envio-nome">{e.nome}</span>
              {e.estado === 'erro' ? (
                <span className="envio-erro">
                  {e.erro?.status === 413 || e.erro?.status === 415 ? `${e.erro.status}: ` : ''}
                  {mensagemDeErro(e.erro)}
                </span>
              ) : (
                <>
                  <progress max="1" value={e.progresso} aria-label={`Progresso de ${e.nome}`} />
                  <span className="envio-estado">
                    {e.estado === 'ok' ? 'Enviada' : e.estado === 'aguardando' ? 'Na fila' : `${Math.round(e.progresso * 100)}%`}
                  </span>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <ErroApiAlerta erro={erro} />

      {fotos.length === 0 ? (
        <p className="texto-suave">Nenhuma foto. A primeira foto da lista é a capa do ambiente.</p>
      ) : (
        <ol className="lista-fotos">
          {fotos.map((f, i) => (
            <ItemFoto
              key={f.id}
              foto={f}
              indice={i}
              total={fotos.length}
              salaId={sala.id}
              aoMover={mover}
              aoRemover={remover}
              aoAtualizar={(atualizada) => setFotos((lista) => lista.map((x) => (x.id === atualizada.id ? atualizada : x)))}
            />
          ))}
        </ol>
      )}
      {dialogo}
    </div>
  );
}
