# Spec: Reserva de salas e laboratórios (v1)

Status: ready-for-agent
Responsável: Atlas
Fonte da verdade: `decisoes.md` (se algo aqui contradiz, vale `decisoes.md`).
Contrato da API: `docs/api-contrato.md`. Termos: `GLOSSARY.md`. Decisões técnicas: `docs/adr/`.

## 1. Problema

Na FATEC Indaiatuba, professores reservam salas e laboratórios de forma informal (planilha, recado,
secretaria). Isso gera reservas duplicadas, falta de visibilidade sobre o que cada ambiente oferece
(equipamentos, softwares instalados, capacidade) e retrabalho a cada semestre para repetir as mesmas
reservas semanais.

O sistema web resolve isso com: catálogo de ambientes com fotos, equipamentos e softwares; agenda
visível; reserva por aulas (slots da grade) com bloqueio de conflito garantido no banco; reserva
semanal recorrente até o fim do semestre com prévia de conflitos.

## 2. Usuários

| Perfil | Quem é | O que faz |
|---|---|---|
| **Visitante** (sem login) | Qualquer pessoa na rede da escola | Consulta ambientes, fotos, equipamentos, softwares, grade de horários e agenda (sem ver RM). |
| **Professor** (`papel = professor`) | Docente com conta criada pelo admin | Tudo do visitante + reserva (avulsa e recorrente), vê e cancela as próprias reservas, troca a própria senha. |
| **Admin** (`papel = admin`) | Coordenação/secretaria | Tudo do professor + CRUD de ambientes, fotos, equipamentos, softwares, professores, horários e semestres; cancela qualquer reserva; pode reservar em nome de um professor. |

Não há autocadastro: só o admin cria contas. O primeiro admin vem de variáveis de ambiente no seed.

## 3. Histórias de usuário

### Consulta
- **H01** Como visitante, quero listar os ambientes filtrando por tipo, capacidade mínima, equipamento e software, para achar um lugar adequado à aula.
- **H02** Como visitante, quero filtrar ambientes livres numa data e num conjunto de aulas seguidas, para saber onde ainda posso reservar.
- **H03** Como visitante, quero abrir um ambiente e ver descrição, capacidade, galeria de fotos, equipamentos (quantidade + especificação) e softwares instalados.
- **H04** Como visitante, quero ver a agenda em visão mensal e em visão de semana/dia, filtrando por ambiente.

### Reserva
- **H05** Como professor, quero entrar com RM e senha.
- **H06** Como professor, quero reservar um ambiente numa data escolhendo uma ou várias aulas seguidas do mesmo turno.
- **H07** Como professor, quero reservar um ambiente toda semana (mesmo dia da semana e mesmas aulas) até o fim do semestre, vendo antes quais datas estão em conflito, e escolher reservar só as livres ou desistir.
- **H08** Como professor, quero ver "Minhas reservas" (futuras e passadas) e cancelar uma ocorrência ou todas as ocorrências futuras de uma recorrência.
- **H09** Como professor, quero trocar minha senha.

### Administração
- **H10** Como admin, quero cadastrar, editar, desativar e excluir ambientes.
- **H11** Como admin, quero enviar várias fotos de um ambiente, com legenda, reordenar e remover.
- **H12** Como admin, quero manter o catálogo de equipamentos e dizer quantos/quais existem em cada ambiente.
- **H13** Como admin, quero manter o catálogo de softwares (nome, versão, categoria) e dizer em quais ambientes estão instalados.
- **H14** Como admin, quero criar e editar contas de professores (inclusive outros admins), redefinir senha e desativar contas.
- **H15** Como admin, quero editar a grade de aulas (turno, ordem, início, fim, dias da semana).
- **H16** Como admin, quero cadastrar semestres letivos (nome, início, fim).
- **H17** Como admin, quero cancelar qualquer reserva a qualquer momento e reservar em nome de um professor.

## 4. Regras de negócio

### RN01 Ambientes
- Um ambiente (`salas`) tem `tipo` de uma lista fechada: `sala`, `lab_informatica`, `lab_ciencias`, `lab_outro`, `auditorio`, `outro` (lista em `docs/api-contrato.md` §2.3).
- Ambiente inativo (`ativo = false`) não aparece para visitante/professor e não aceita reservas novas; reservas existentes continuam.
- Ambiente com reservas (qualquer status) não pode ser excluído: o admin desativa.

### RN02 Grade de horários (aulas)
- Reservas são feitas **por aula** (slot de `horarios_aula`), nunca por horário livre.
- Cada aula tem turno (`manha`, `tarde`, `noite`), ordem dentro do turno, início, fim e dias da semana em que vale (ISO: 1 = segunda … 7 = domingo). Há aulas aos sábados.
- Duas aulas ativas que valem num mesmo dia da semana não podem se sobrepor no tempo.
- A reserva guarda uma **cópia** de início e fim (snapshot). Editar a grade depois não altera reservas já feitas.

### RN03 Aulas seguidas
- Numa reserva avulsa o professor escolhe 1..N aulas. Elas devem ser:
  - do **mesmo turno**;
  - com `ordem` **consecutiva** (sem buracos);
  - todas ativas e válidas no dia da semana da data escolhida.
- A reserva ocupa o intervalo `[início da primeira aula, fim da última aula)`; intervalos entre aulas (ex.: 09:10–09:30) ficam dentro do bloco.
- Uma reserva = um bloco contínuo numa data (uma linha em `reservas`).

### RN04 Conflito
- Nunca duas reservas **ativas** do mesmo ambiente com intervalos sobrepostos na mesma data. Intervalos que apenas se tocam (fim = início) não conflitam.
- Validação no service (mensagem amigável, lista de conflitos) **e** no banco: constraint de exclusão `EXCLUDE USING gist (sala_id WITH =, periodo WITH &&) WHERE (status = 'ativa')` (ADR-0003). Se duas requisições concorrentes passarem pelo service, o banco rejeita a segunda e a API devolve o mesmo 409.
- Reservas canceladas não ocupam o ambiente.

### RN05 Datas válidas
- Não se cria reserva cujo início (data + início da primeira aula) já passou. Vale para professor e admin.
- Datas e horas são locais (fuso `America/Sao_Paulo`, variável `TZ`). O banco guarda `date` + `time` sem fuso.
- Reserva avulsa pode ser em qualquer data futura (não precisa estar dentro de semestre).

### RN06 Recorrência semanal
- O professor informa ambiente, data inicial e aulas (mesmas regras de RN03). As ocorrências são a data inicial e todas as datas `+7, +14, …` dias até a `data_fim` do **semestre que contém a data inicial**. Sem semestre contendo a data inicial: erro 422 `SEM_SEMESTRE`.
- **Prévia** (não grava nada): lista cada data com `livre: true|false` e, se ocupada, quem ocupa.
- **Confirmação**: o cliente envia explicitamente as datas que quer reservar (normalmente só as livres). O servidor valida que cada data pertence à série, e grava todas numa transação: se alguma ficou ocupada entre a prévia e a confirmação, nada é gravado e a API devolve 409 com os conflitos atuais (o cliente refaz a prévia).
- Todas as ocorrências gravadas compartilham um `grupo_recorrencia_id` (tabela `grupos_recorrencia`).

### RN07 Cancelamento
- Cancelar não apaga: `status = 'cancelada'`, grava `cancelada_em`, `cancelada_por_id` e `motivo_cancelamento` opcional.
- Professor cancela **só as próprias**, e só enquanto `agora < data + início`. Depois disso: 422 `RESERVA_JA_INICIADA`.
- Admin cancela qualquer reserva, a qualquer hora (inclusive já iniciada ou passada).
- Cancelar o grupo: cancela todas as ocorrências **ativas e ainda não iniciadas** do grupo (para professor e admin). Ocorrências passadas ficam como histórico. Resposta informa quantas foram canceladas.
- Cancelar uma reserva já cancelada: 409 `RESERVA_JA_CANCELADA`.

### RN08 Permissões e autenticação
- Login com RM + senha → JWT Bearer (HS256, expira em `JWT_EXPIRA_MINUTOS`, padrão 480). Senhas com bcrypt.
- O professor dono da reserva vem **sempre do token**. Professor que envia `professor_id` no corpo recebe 403. Admin pode enviar `professor_id` para reservar em nome de outro.
- Conta inativa não loga (401) e tokens dela passam a ser rejeitados (401).
- Admin não pode desativar a si mesmo nem remover o próprio papel de admin (422 `OPERACAO_EM_SI_MESMO`).
- Rotas de leitura do catálogo e da agenda são públicas; a agenda pública mostra o **nome** do professor, nunca o RM.
- Matriz completa de permissões por rota: `docs/api-contrato.md`.

### RN09 Fotos
- Upload só por admin. Formatos JPEG, PNG, WebP; até `UPLOAD_MAX_MB` (padrão 5 MB). O servidor confere o conteúdo (assinatura do arquivo), não só a extensão.
- O nome no disco é gerado pelo servidor (UUID + extensão); o nome original não é usado no caminho.
- Arquivos ficam em volume Docker e são servidos como estáticos em `/uploads/...`.
- Ordem da galeria editável; excluir foto apaga o registro e o arquivo.

## 5. Fora de escopo (v1)

- Bloqueio de ambiente por manutenção.
- Notificações, e-mail, lembretes.
- Relatórios, exportação PDF/CSV.
- Autocadastro e recuperação de senha por e-mail (o admin redefine).
- Feriados/calendário acadêmico (recorrência não pula feriados; o professor desmarca na prévia).
- Recorrência diferente de semanal, ou que cruze semestres.
- Editar uma reserva existente (cancela e cria outra).
- Impedir que o mesmo professor reserve dois ambientes no mesmo horário.
- Aulas seguidas que atravessam turnos.
- Plugins pagos do FullCalendar (timeline/resource).
- Refresh token, SSO, LDAP.
