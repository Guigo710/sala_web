# ADR-0005: Fotos em volume Docker servidas como estáticos pelo backend

Status: **parcialmente substituído pelo ADR-0010** (2026-11-19) · Data: 2026-11-12 · Autor: Atlas

> **Atenção (rodada 5):** o armazenamento em disco (`UPLOAD_DIR`, volume `uploads`, `StaticFiles`) e a entrega dos
> arquivos foram substituídos pelo ADR-0010: as fotos são reduzidas no upload e guardadas no banco, e a rota
> `GET /uploads/...` lê do banco. Continuam valendo daqui: upload só por admin, uma foto por requisição,
> assinatura JPEG/PNG/WebP, limite de entrada `UPLOAD_MAX_MB`, nome gerado pelo servidor (UUID).
> Os itens substituídos estão marcados com ~~riscado~~.

## Contexto
Cada ambiente tem uma galeria (várias fotos, com ordem e legenda). Custo zero: sem S3 ou serviço externo.

## Decisão
- Tabela `fotos_sala` (sala_id, arquivo, legenda, ordem). ~~O banco guarda só o caminho relativo.~~ (ADR-0010: guarda o conteúdo.)
- ~~Arquivos em `UPLOAD_DIR` (padrão `/app/uploads`), volume Docker nomeado `uploads`, no layout
  `salas/{sala_id}/{uuid4}.{ext}`.~~ O nome original enviado é descartado (evita path traversal e colisão).
- Upload `multipart/form-data`, uma foto por requisição, só admin. Aceita JPEG/PNG/WebP verificados pela
  assinatura do conteúdo (magic bytes); limite `UPLOAD_MAX_MB` (padrão 5). Leitura em blocos, abortando ao passar do limite.
- ~~O FastAPI monta `StaticFiles` em `/uploads`.~~ A API devolve `url` relativa (`/uploads/salas/3/<uuid>.jpg`); o formato se mantém no ADR-0010.
- ~~Excluir foto ou sala apaga também os arquivos (o service remove após o commit).~~
- ~~Sem redimensionamento/miniaturas na v1.~~ (ADR-0010: reduz para 1600 px em JPEG; segue sem miniaturas.)

## Consequências
- ~~Backup das fotos = backup do volume `uploads` (além do banco).~~ (ADR-0010: o backup do banco inclui as fotos.)
- Se a API trocar de host, as URLs relativas continuam válidas.
- Migrar para armazenamento externo no futuro só muda o service de fotos e a forma de montar `url`.
