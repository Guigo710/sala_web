# ADR-0010: Fotos reduzidas no upload e guardadas no próprio banco

Status: aceito · Data: 2026-11-19 · Autor: Atlas · Rodada 5 · **Substitui a parte de armazenamento e entrega do
ADR-0005** (pasta `UPLOAD_DIR`, volume `uploads`, `StaticFiles`). Continua valendo do ADR-0005: upload só por admin,
uma foto por requisição, assinatura JPEG/PNG/WebP, limite de entrada `UPLOAD_MAX_MB`, nome gerado pelo servidor.

## Contexto
Na publicação (ADR-0009) a API roda no Render Free, cujo **disco é efêmero**: arquivos gravados somem ao dormir,
reiniciar ou fazer deploy. Opções para guardar as fotos:

| Opção | Avaliação |
|---|---|
| Disco persistente do Render | Só em plano pago. Rejeitada. |
| Armazenamento de objetos (Cloudflare R2, Supabase Storage, Cloudinary...) | Mais uma conta, chaves de acesso, CORS e passos no guia para um dono não especialista; mais um fornecedor com limites próprios. Rejeitada por enquanto. |
| **Coluna `bytea` no PostgreSQL (Neon)** | Nenhuma conta nova; backup do banco já inclui as fotos; funciona igual no Compose. Viável porque as fotos são poucas (dezenas de ambientes, algumas fotos cada) e ficam pequenas depois de reduzidas. **Escolhida.** |

Estimativa: ~30 ambientes × ~6 fotos × ~300 KB ≈ 55 MB, folgado mesmo se o limite do Neon for 0,5 GB.

## Decisão

### Modelo (migration `0003_fotos_no_banco`)
Tabela `fotos_sala` ganha:
- `conteudo bytea` (nulo só em foto antiga cujo arquivo não foi achado na importação; ver abaixo);
- `tipo_mime varchar(30)` (hoje sempre `image/jpeg`);
- `tamanho integer` (bytes de `conteudo`).

`arquivo` continua `varchar(255) NOT NULL UNIQUE`, agora como **nome público** da foto (`salas/{sala_id}/{uuid4}.jpg`),
não mais caminho em disco. Recomendado `ALTER TABLE fotos_sala ALTER COLUMN conteudo SET STORAGE EXTERNAL` (JPEG não
comprime; evita o Postgres tentar comprimir à toa).

No ORM, `conteudo` é carregado **sob demanda** (`deferred`): listar salas, detalhe e galeria nunca trazem os bytes;
só a rota que entrega a imagem os lê.

### Redução no upload
Entrada: igual hoje (JPEG/PNG/WebP pela assinatura, até `UPLOAD_MAX_MB` = 5 MB, leitura em blocos). Processamento
com **Pillow**, nesta ordem:
1. Recusa imagens com mais de **40 megapixels** antes de decodificar (proteção contra "bomba de descompressão"):
   `413 ARQUIVO_GRANDE`. Arquivo com assinatura válida que o Pillow não consegue decodificar: `415 TIPO_ARQUIVO_INVALIDO`.
2. Aplica a orientação do EXIF (foto de celular "deitada" fica em pé).
3. Reduz para o **lado maior ≤ 1600 px**, mantendo a proporção; nunca amplia.
4. Converte para RGB; transparência (PNG/WebP) é composta sobre **fundo branco**.
5. Grava **JPEG**, qualidade 80, progressivo, otimizado. Se passar de **600 KB**, regrava uma vez com qualidade 70.
6. Remove todos os metadados (EXIF, inclusive **GPS**, XMP, comentários). Mantém só o perfil de cor ICC, se houver.

Por que JPEG e não WebP: o Render Free tem uma fração de CPU, e codificar JPEG é bem mais rápido; JPEG é aceito em
qualquer lugar; fotos de ambiente não precisam de transparência. Uma foto típica de celular fica entre 200 e 450 KB.

O nome público sempre termina em `.jpg`, coerente com o conteúdo.

### Entrega
- A URL **continua no mesmo formato**: `Foto.url = "/uploads/" + arquivo`, ex.: `/uploads/salas/3/<uuid>.jpg`.
  Rota `GET /uploads/{arquivo}` que busca pelo nome em `fotos_sala` e devolve `conteudo`. O frontend não muda
  (`urlArquivo` monta `${VITE_API_URL}${url}`), a CSP do nginx continua cobrindo a origem da API, e os cabeçalhos
  de `/uploads` do contrato §1.9 seguem valendo.
  Rejeitado: `/fotos/{id}/arquivo`. Com o id na URL, um banco recriado (seed, ambiente novo) reaproveita ids e um
  navegador com cache de um ano mostraria a foto antiga; o UUID nunca se repete.
- Cabeçalhos: `Content-Type` da coluna, `Content-Length`, `Cache-Control: public, max-age=31536000, immutable`
  (o conteúdo de um nome nunca muda: não existe "trocar o arquivo" de uma foto, só excluir e enviar outra),
  `ETag` forte com o UUID; `If-None-Match` igual → `304` sem corpo. Mais os de segurança do §1.9.
- Inexistente, ou foto sem `conteudo` → `404 NAO_ENCONTRADO` (envelope JSON). Sem `Cross-Origin-Resource-Policy`
  restritivo: o frontend (Vercel) e a API (Render) têm origens diferentes.

### Exclusão
Excluir foto ou sala só apaga registros (cascata). Nenhum arquivo em disco é tocado.

### Fotos já gravadas em disco (quem usa o Compose desde antes)
- Comando idempotente `python -m app.importar_fotos`, rodado no `CMD` depois do seed e antes do `uvicorn`:
  para cada foto com `conteudo IS NULL`, lê `UPLOAD_DIR/<arquivo>`, passa pela mesma redução, grava `conteudo`,
  `tipo_mime`, `tamanho` e um **nome novo** `salas/{sala_id}/{uuid4}.jpg` (o conteúdo mudou de formato; o nome antigo
  deixa de existir). Um commit por foto, então uma falha no meio não perde o que já foi importado.
- Arquivo não encontrado ou ilegível: registra aviso no log e deixa a linha com `conteudo` nulo (a foto já estava
  quebrada antes; o admin a exclui pela tela). Nada é apagado automaticamente.
- Os arquivos do volume **não são apagados** pela importação.
- Compose desta rodada: o volume `uploads` continua declarado e montado **só leitura** no backend (`:ro`), só para a
  importação; o serviço `uploads-permissoes` sai (ninguém mais grava lá). Quem quiser liberar espaço depois de
  conferir as fotos pode remover o volume (instrução no `backend/README.md`). Retirar a montagem do Compose fica
  para uma rodada futura.
- Na nuvem (Render) não há `UPLOAD_DIR` nem fotos antigas: o comando não encontra nada a fazer.

## Consequências
- Funciona igual no Compose e no Render; nenhuma conta ou chave nova.
- Backup e restauração do banco incluem as fotos. O banco cresce (~55 MB estimados); acompanhar o uso no painel do Neon.
- As fotos passam pela API: cada imagem não cacheada é uma requisição ao Render (e acorda a API, se estiver dormindo).
  O cache de um ano com `immutable` faz cada navegador baixar cada foto uma vez só.
- Upload fica mais lento (decodificar e codificar) e usa mais memória por alguns instantes; aceitável para um admin
  enviando uma foto por vez. O limite de 40 MP segura o pior caso.
- Privacidade melhor: a localização GPS das fotos de celular deixa de ser publicada.
- Fotos antigas mudam de URL uma única vez (importação). Nada externo guarda essas URLs.
- Sem miniaturas nesta rodada: a galeria e o cartão usam a mesma imagem de 1600 px. Se pesar, ADR novo.
- Implementação: tickets 60 e 61 (Forge), 67 (Pixel), 68 (Sentinela). Contrato 1.4: §1.9, §2, §3.5, §4.1, §4.4.
