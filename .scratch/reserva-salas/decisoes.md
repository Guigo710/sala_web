# Decisões do projeto (fonte da verdade)

Decisões tomadas com o dono do projeto. Todo agente lê este arquivo antes de trabalhar.
Se algo aqui contradiz o `README.md`, **vale este arquivo**.

## Contexto
- Trabalho de disciplina (FATEC Indaiatuba), equipe de 3 pessoas, sem prazo fixo.
- Web app para professores reservarem salas e laboratórios. Ao clicar num ambiente: descrição, equipamentos, galeria de fotos e softwares instalados.

## Stack
- Frontend: React + Vite, FullCalendar (somente plugins gratuitos: daygrid, timegrid, interaction).
- Backend: Python + FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic para migrations.
- Banco: PostgreSQL.
- Execução: Docker Compose (`db`, `backend`, `frontend`), custo zero rodando local/na escola.
- Estrutura na raiz do repo: `backend/` e `frontend/`. A pasta antiga `Sala/` foi apagada.

## Idioma
- Código, tabelas, classes e rotas em **português** (`/salas`, `/reservas`, `Sala`, `Reserva`).
- Textos da interface em português.

## Domínio
- **Ambientes**: uma tabela `salas` com campo `tipo` (ex.: `sala`, `lab_informatica`, `lab_ciencias`, ...). Hoje: 14 salas e 13 laboratórios; existem outros, com dados ainda incompletos. **Tudo editável pelo admin** (nada de dados fixos no código; o seed é só ponto de partida com nomes genéricos).
- **Fotos**: galeria, várias fotos por ambiente (tabela própria, com ordem/legenda). Upload feito pelo admin; arquivos numa pasta do servidor (volume Docker), servidos como estáticos.
- **Equipamentos**: catálogo de equipamentos + associação sala–equipamento com `quantidade` e `especificacao` (ex.: 30 PCs, i5, 16GB).
- **Softwares**: tabela própria (nome, versão, categoria) com associação N:N a ambientes. Permite filtro "quais labs têm X".
- **Horários**: aulas fixas (slots) em tabela `horarios_aula` editável pelo admin (turno, ordem, início, fim, dias da semana em que vale). Grade de referência FATEC Indaiatuba (ex.: manhã 07:30–08:20, 08:20–09:10, intervalo 09:10–09:30, ...). **Há aulas aos sábados** (poucas). O seed deve trazer uma grade plausível manhã/tarde/noite que o admin ajusta.
- Professor pode reservar **várias aulas seguidas** num mesmo dia.
- **Recorrência na v1**: reserva semanal até o fim do semestre letivo. Semestres: fevereiro–junho e agosto–dezembro → tabela `semestres` (nome, data início, data fim) editável pelo admin. Antes de confirmar, o sistema **lista as datas em conflito** e o professor escolhe reservar só as livres ou desistir. Ocorrências pertencem a um grupo de recorrência (cancelar uma ou todas).
- **Conflito**: nunca duas reservas ativas na mesma sala sobrepostas. Validar no service **e** garantir no banco (ex.: constraint de exclusão no Postgres, `btree_gist` + `tsrange`/slot único, ou unique parcial por sala+data+horário quando status ativo).
- **Bloqueio por manutenção**: fora da v1.

## Usuários e segurança
- Login com **RM + senha**, token JWT (Bearer). Senhas com hash (bcrypt/argon2).
- Papéis: `professor` e `admin`. **Só o admin cria contas** (sem autocadastro).
- Cancelamento: o dono cancela até o início da aula; admin cancela qualquer uma a qualquer hora. Reserva cancelada não é apagada (status `cancelada`, histórico).
- O RM do professor vem do token, nunca do corpo da requisição.

## Escopo v1
- Agenda (mês + dia/semana), consulta de disponibilidade, reserva avulsa e recorrente, bloqueio de conflito.
- Detalhe do ambiente: galeria de fotos, equipamentos (qtd + spec), softwares.
- Painel admin: CRUD de ambientes, fotos, equipamentos, softwares, professores, horários e semestres.
- "Minhas reservas" (ver e cancelar).
- Filtros: capacidade, tipo, equipamento, software.

## Futuro (não fazer agora)
Manutenção/bloqueio de salas, notificações, e-mail, relatórios, PDF, autocadastro.
