# ADR-0002: Reservas por aulas (slots) da grade, com cópia de início/fim

Status: aceito · Data: 2026-11-12 · Autor: Atlas

## Contexto
Na FATEC as aulas seguem uma grade fixa por turno (ex.: manhã 07:30–08:20, 08:20–09:10, intervalo
09:10–09:30, ...), inclusive aos sábados. O professor pensa em "1ª e 2ª aula", não em horários livres,
e pode reservar várias aulas seguidas. O admin precisa poder editar a grade.

Alternativas consideradas:
1. Horário livre (início/fim arbitrários): flexível, mas gera reservas desalinhadas da grade.
2. Uma linha de reserva por aula: conflito vira um UNIQUE simples, mas "3 aulas seguidas" vira 3 registros
   a manter juntos (cancelar, exibir) e editar a grade quebra o UNIQUE semântico.
3. **Uma linha por bloco de aulas seguidas, com início/fim copiados das aulas.**

## Decisão
Opção 3.
- Tabela `horarios_aula` (turno, ordem, início, fim, `dias_semana smallint[]` ISO 1..7, ativo), editável pelo admin.
- A API recebe `horario_ids`; o service exige mesmo turno, ordem consecutiva, aulas ativas e válidas no dia da semana.
- A reserva grava `inicio` = início da primeira aula, `fim` = fim da última (snapshot), `horario_inicio_id`,
  `horario_fim_id` e `quantidade_aulas`. O intervalo entre aulas fica dentro do bloco.
- O conflito é avaliado por **sobreposição de tempo** (`tsrange`), não por id de aula (ADR-0003).

## Consequências
- Editar a grade não altera reservas passadas nem futuras já feitas; elas mantêm o horário em que foram criadas.
  Se o admin mudar um horário, reservas antigas podem não coincidir com a nova grade; isso é aceitável e visível.
- Aulas com reserva não podem ser excluídas (FK RESTRICT → `409 HORARIO_EM_USO`); o admin as desativa.
- Blocos que atravessam turnos não são suportados na v1.
