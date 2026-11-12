# Glossário: sala_web

Termos do domínio. Use exatamente estes nomes em código, rotas, tickets e telas.

| Termo | Definição | Evitar |
|---|---|---|
| **Ambiente** | Qualquer espaço reservável: sala de aula, laboratório, auditório. No código é `Sala` / tabela `salas`, diferenciado por `tipo`. | "room", "espaço" |
| **Sala** | Nome técnico (tabela/rota) de um ambiente. Na interface, "Sala de aula" é só um dos tipos. | |
| **Laboratório (lab)** | Ambiente com `tipo` começando por `lab_` (`lab_informatica`, `lab_ciencias`, `lab_outro`). | |
| **Tipo** | Categoria fixa do ambiente (lista em `docs/api-contrato.md` §2.3). | "categoria" (reservado para software) |
| **Ativo / inativo** | Ambiente, aula ou conta desativados pelo admin: somem do uso diário, mas o histórico permanece. | "excluído" |
| **Equipamento** | Item do catálogo (Computador, Projetor, Ar-condicionado...). Associado ao ambiente com **quantidade** e **especificação**. | |
| **Especificação** | Texto livre descrevendo o equipamento naquele ambiente (ex.: "i5, 16 GB RAM"). | |
| **Software** | Programa instalado (nome, versão, categoria), associado a ambientes. | "programa", "app" |
| **Foto / galeria** | Imagens de um ambiente, com legenda e ordem. A **capa** é a de menor ordem. | |
| **Professor** | Conta de usuário (tabela `professores`). Pode ter papel `professor` ou `admin`. | "usuário" no código, "user" |
| **Admin** | Professor com `papel = admin`: mantém cadastros e cancela qualquer reserva. | "administrador" no código |
| **RM** | Registro de Matrícula do professor; login junto com a senha. Nunca exposto publicamente. | "matrícula", "login" |
| **Papel** | `professor` ou `admin`. | "role", "perfil" no código |
| **Aula (slot)** | Linha de `horarios_aula`: turno + ordem + início + fim + dias da semana. Unidade mínima de reserva. | "período", "slot" na interface |
| **Turno** | `manha`, `tarde`, `noite`. | |
| **Ordem** | Posição da aula dentro do turno (1ª, 2ª, ...). | |
| **Grade** | Conjunto de todas as aulas ativas. | "horário" (ambíguo) |
| **Aulas seguidas** | Aulas do mesmo turno com ordem consecutiva, reservadas como um bloco. | "aulas consecutivas" (aceitável na interface) |
| **Dia da semana** | Inteiro ISO: 1 = segunda … 6 = sábado, 7 = domingo. | 0 = domingo (só dentro do FullCalendar) |
| **Semestre** | Período letivo (nome, data início, data fim), ex.: "2026-2". Limita a recorrência. | "período letivo" no código |
| **Reserva** | Um bloco de aulas seguidas de um ambiente, numa data, para um professor. Status `ativa` ou `cancelada`. | "agendamento", "booking" |
| **Reserva avulsa** | Reserva de uma única data. | "simples", "pontual" |
| **Reserva recorrente** | Conjunto de reservas semanais (mesmo ambiente, dia da semana e aulas) até o fim do semestre. | |
| **Grupo de recorrência** | Registro (`grupos_recorrencia`) que une as ocorrências de uma reserva recorrente. | "série" no código |
| **Ocorrência** | Cada reserva (data) dentro de um grupo de recorrência. | |
| **Prévia** | Simulação da recorrência que lista datas livres e em conflito, sem gravar. | "preview" |
| **Conflito** | Sobreposição de tempo entre duas reservas ativas do mesmo ambiente. | "choque" |
| **Disponibilidade** | Situação livre/ocupada de um ambiente por aula numa data. | |
| **Cancelamento** | Mudar a reserva para `cancelada` (nunca apagar). Dono até o início da aula; admin sempre. | "excluir reserva" |
| **Agenda** | Visão de calendário (mês, semana, dia) das reservas. | |
