# ADR-0005: Fotos em volume Docker servidas como estáticos pelo backend

Status: aceito · Data: 2026-11-12 · Autor: Atlas

## Contexto
Cada ambiente tem uma galeria (várias fotos, com ordem e legenda). Custo zero: sem S3 ou serviço externo.

## Decisão
- Tabela `fotos_sala` (sala_id, arquivo, legenda, ordem). O banco guarda só o caminho relativo.
- Arquivos em `UPLOAD_DIR` (padrão `/app/uploads`), volume Docker nomeado `uploads`, no layout
  `salas/{sala_id}/{uuid4}.{ext}`. O nome original enviado é descartado (evita path traversal e colisão).
- Upload `multipart/form-data`, uma foto por requisição, só admin. Aceita JPEG/PNG/WebP verificados pela
  assinatura do conteúdo (magic bytes); limite `UPLOAD_MAX_MB` (padrão 5). Leitura em blocos, abortando ao passar do limite.
- O FastAPI monta `StaticFiles` em `/uploads`. A API devolve `url` relativa (`/uploads/salas/3/<uuid>.jpg`).
- Excluir foto ou sala apaga também os arquivos (o service remove após o commit).
- Sem redimensionamento/miniaturas na v1.

## Consequências
- Backup das fotos = backup do volume `uploads` (além do banco).
- Se a API trocar de host, as URLs relativas continuam válidas.
- Migrar para armazenamento externo no futuro só muda o service de fotos e a forma de montar `url`.
