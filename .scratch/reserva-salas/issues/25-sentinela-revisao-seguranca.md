# 25: Revisão de segurança da v1

Status: ready-for-agent
Responsável: Sentinela
Origem: Atlas
Blocked by: 12, 07
Referências: ADR-0004, ADR-0005; `docs/api-contrato.md` §1.3–§1.5

## Critérios de aceite
- [ ] Checklist revisado: segredo JWT do ambiente e validade, bcrypt, RM sempre do token, `exigir_admin` em toda rota admin, CORS restrito, upload (magic bytes, tamanho, path traversal), SQL injection (sem SQL concatenado), erros 500 sem stack trace, `.env` fora do git, XSS no frontend (sem `dangerouslySetInnerHTML`).
- [ ] Achados registrados como tickets novos `Responsável: Forge|Pixel`, `Origem: Sentinela`, com severidade.
