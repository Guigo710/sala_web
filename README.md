## 1. Descrição do projeto
O projeto consiste no desenvolvimento de um sistema web para gerenciamento, consulta e reserva de salas e laboratórios escolares.
A aplicação terá como objetivo facilitar a organização dos espaços utilizados pela instituição, permitindo que professores consultem a disponibilidade dos ambientes e realizem reservas de acordo com a necessidade de suas aulas.
Diferentemente de um aplicativo instalado em dispositivos móveis, o sistema será desenvolvido como uma aplicação web acessível por navegador, podendo ser utilizado em computadores, notebooks e outros dispositivos conectados à rede.
O sistema apresentará uma agenda mensal contendo as reservas realizadas, permitindo visualizar quais salas estão ocupadas e quais horários estão disponíveis.
Cada ambiente possuirá informações próprias, como:
- Nome ou identificação da sala;
- Capacidade máxima de alunos;
- Fotografia da sala;
- Computadores disponíveis;
- Quantidade e especificações das máquinas;
- Projetor;
- Ar-condicionado;
- Quadro branco ou quadro negro;
- Carrinho de notebooks;
- Outros equipamentos disponíveis.
O professor poderá selecionar uma sala, escolher a data e o horário desejado e informar seu RM (Registro de Matrícula) para confirmar a reserva. Após a confirmação, a informação será armazenada no banco de dados e automaticamente refletida na agenda.
## 2. Objetivo geral
Desenvolver um sistema web simples e funcional para facilitar o gerenciamento e agendamento dos espaços escolares, permitindo consultar suas características, disponibilidade e reservas de maneira organizada e eficiente.
## 3. Objetivos específicos
- Cadastrar salas e laboratórios.
- Consultar informações dos ambientes.
- Visualizar fotografias das salas.
- Visualizar capacidade e equipamentos.
- Visualizar a agenda mensal.
- Identificar salas ocupadas e disponíveis.
- Selecionar uma sala para realizar uma reserva.
- Escolher data e horário.
- Informar o RM do professor.
- Confirmar a reserva.
- Salvar a reserva no banco de dados.
- Atualizar automaticamente a agenda.
- Impedir reservas conflitantes para a mesma sala e horário.
- Permitir cancelamento de reservas, caso essa funcionalidade seja implementada.
## 4. Funcionamento do sistema
'''
Professor
   ↓
Acessa o sistema web
   ↓
Visualiza a agenda
   ↓
Escolhe uma data
   ↓
Escolhe horário
   ↓
Visualiza salas disponíveis
   ↓
Seleciona a sala
   ↓
Visualiza foto + capacidade + equipamentos
   ↓
Informa RM
   ↓
Confirma reserva
   ↓
Frontend envia requisição para API
   ↓
FastAPI valida os dados
   ↓
Banco de dados salva a reserva
   ↓
Agenda é atualizada
   ↓
Sala aparece como ocupada '''
Um ponto importante: a sala não deve ser realmente retirada do banco de dados quando estiver ocupada. O banco continua contendo a sala. O que muda é a disponibilidade daquela sala naquele horário.
Sala 201
Capacidade: 40
Projetor: Sim
Ar-condicionado: Sim

08:00 → Livre
09:00 → Ocupada
10:00 → Livre
11:00 → Livre
5. Arquitetura recomendada
A arquitetura recomendada é uma arquitetura de três camadas, com frontend separado do backend e do banco de dados.
┌──────────────────────────────┐
│          FRONTEND            │
│        React + Vite          │
│                              │
│  Agenda                      │
│  Salas                       │
│  Detalhes                    │
│  Formulário de reserva       │
└──────────────┬───────────────┘
               │ HTTP / JSON
               ↓
┌──────────────────────────────┐
│           BACKEND            │
│           FastAPI            │
│                              │
│  Rotas                       │
│  Regras de negócio           │
│  Validação                   │
│  Autenticação                │
│  Reservas                    │
└──────────────┬───────────────┘
               │ SQLAlchemy
               ↓
┌──────────────────────────────┐
│          DATABASE            │
│         PostgreSQL           │
│                              │
│  Professores                 │
│  Salas                       │
│  Equipamentos                │
│  Reservas                    │
└──────────────────────────────┘
A separação é importante porque cada parte possui uma responsabilidade: o frontend mostra a interface; o backend executa a lógica; o banco armazena os dados.
6. Tecnologias
Camada
Tecnologia
Frontend
React
Build
Vite
Backend
Python + FastAPI
ORM
SQLAlchemy
Validação
Pydantic
Banco
PostgreSQL
API
REST/JSON
Agenda
Componente de calendário React
Fotos
Arquivos estáticos ou armazenamento externo

React será utilizado para construir a interface e organizar a aplicação em componentes. Vite será usado no desenvolvimento e build do frontend. FastAPI será usado para expor a API REST, validar dados e concentrar as regras de negócio. SQLAlchemy fará a comunicação entre Python e PostgreSQL. Pydantic será usado para os schemas de entrada e saída da API.
7. Frontend
7.1 React
O React será responsável pela interface do sistema. A aplicação poderá ser dividida em componentes como Calendar, RoomCard, RoomDetails e ReservationModal.
7.2 Vite
O Vite será utilizado para criar o projeto React, fornecer o servidor de desenvolvimento e gerar o build de produção.
8. Backend
FastAPI é recomendado para o backend por combinar bem com Python e por facilitar a criação de APIs REST, validação com Pydantic e documentação interativa da API. A documentação automática também será útil durante os testes do projeto.
React
   ↓
GET /salas
   ↓
FastAPI
   ↓
PostgreSQL
9. Banco de dados
PostgreSQL é recomendado como banco de dados principal. Ele atende melhor a um sistema que pode receber vários usuários e reservas simultâneas do que uma solução local simples como SQLite.
10. Estrutura do banco de dados
PROFESSORES
-----------
id
rm
nome

SALAS
-----------
id
nome
descricao
capacidade
foto_url

EQUIPAMENTOS
-----------
id
nome

SALA_EQUIPAMENTO
-----------
sala_id
equipamento_id

RESERVAS
-----------
id
sala_id
professor_id
data
hora_inicio
hora_fim
status
created_at
11. Relacionamento entre as tabelas
PROFESSOR
   │
   │ 1
   │
   │ N
 RESERVA
   │
   │ N
   │
   │ 1
  SALA
   │
   │ N
   │
   │ N
EQUIPAMENTO
Um professor pode realizar várias reservas. Uma sala também pode possuir várias reservas em horários diferentes.
Sala 202

08:00 → Professor A
09:00 → Professor B
10:00 → Livre
11:00 → Professor C
12. Modelo da tabela de salas
class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    capacity = Column(Integer, nullable=False)
    photo_url = Column(String, nullable=True)
Exemplo de registro:
id: 1
name: "Laboratório 01"
description: "Laboratório de informática"
capacity: 30
photo_url: "/images/lab01.jpg"
13. Modelo de professor
class Professor(Base):
    __tablename__ = "professors"

    id = Column(Integer, primary_key=True)
    rm = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
O RM deve ser único. O atributo unique=True impede que o mesmo RM seja cadastrado mais de uma vez.
14. Modelo de reserva
class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True)

    room_id = Column(
        Integer,
        ForeignKey("rooms.id"),
        nullable=False
    )

    professor_id = Column(
        Integer,
        ForeignKey("professors.id"),
        nullable=False
    )

    date = Column(Date, nullable=False)

    start_time = Column(Time, nullable=False)

    end_time = Column(Time, nullable=False)

    status = Column(
        String,
        default="confirmed"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
15. Como funcionará a reserva
Suponha que o professor queira reservar uma sala para uma aula de uma hora:
Sala: Laboratório 02
Data: 15/09/2026
Horário: 14:00 - 15:00
RM: 123456
O React enviará os dados para a API:
{
    "room_id": 2,
    "professor_rm": "123456",
    "date": "2026-09-15",
    "start_time": "14:00",
    "end_time": "15:00"
}
A API verifica a existência do professor, a existência da sala e a disponibilidade no horário. Somente depois disso a reserva é criada e salva.
Existe professor com RM 123456?
        ↓
       SIM
        ↓
A sala 2 existe?
        ↓
       SIM
        ↓
A sala está livre às 14:00?
        ↓
       SIM
        ↓
Criar reserva
        ↓
Salvar no PostgreSQL
        ↓
Retornar sucesso
16. Regra mais importante: evitar conflito
A principal regra de negócio é impedir duas reservas que ocupem a mesma sala no mesmo intervalo de tempo.
Sala 101
10:00 - 11:00

Professor A reservou.

Professor B tenta reservar:
Sala 101
10:00 - 11:00

Resultado:
REJEITAR
Resposta sugerida da API:
{
    "detail": "Sala não disponível neste horário."
}
Essa validação deve existir no backend, e a integridade do banco também deve ser considerada para reduzir riscos de inconsistência.
17. Como a agenda funcionará
Como a reserva é por hora, recomenda-se combinar uma visão mensal com uma visão diária/por horário. A visão mensal permite enxergar a ocupação geral e, ao clicar em um dia, a interface mostra os horários e salas disponíveis.
Visão mensal

Setembro 2026

01 02 03 04 05

14 15 16 17 18
        ██████
        Sala 201
Visão diária - 15/09/2026

07:00
08:00    Sala 101 ✅

09:00    Sala 101 ❌
         Lab 01 ✅
         Sala 202 ✅

10:00    Sala 101 ✅
         Lab 01 ❌
Uma biblioteca de calendário em React pode ajudar nessa parte. É importante escolher uma solução compatível com o escopo do projeto e evitar dependências premium desnecessárias.
18. Tela de salas
SALAS DISPONÍVEIS

┌─────────────────────┐
│     FOTO DA SALA    │
├─────────────────────┤
│ Laboratório 01      │
│                     │
│ Capacidade: 30      │
│ 💻 Computadores     │
│ 📽 Projetor          │
│ ❄ Ar-condicionado   │
│ 📝 Quadro branco    │
│                     │
│       [Reservar]    │
└─────────────────────┘
19. Fluxo de escolha da sala
ESCOLHER DATA
      ↓
ESCOLHER HORÁRIO
      ↓
SISTEMA CONSULTA BD
      ↓
MOSTRA SALAS DISPONÍVEIS
      ↓
PROFESSOR ESCOLHE SALA
      ↓
MOSTRA DETALHES
      ↓
INFORMA RM
      ↓
CONFIRMA
20. API
20.1 Salas
GET /rooms
Lista todas as salas.

GET /rooms/{id}
Busca uma sala específica.
20.2 Professores
GET /professors/{rm}
Busca o professor pelo RM.
20.3 Reservas
GET /reservations
Lista reservas.

GET /reservations?date=2026-09-15
Lista reservas de um determinado dia.

GET /reservations?month=2026-09
Lista reservas do mês.
20.4 Verificar disponibilidade
GET /rooms/available

Exemplo:
GET /rooms/available?date=2026-09-15&start_time=14:00&end_time=15:00
20.5 Criar reserva
POST /reservations
20.6 Cancelar reserva
DELETE /reservations/{id}
Exemplo de retorno para salas disponíveis:
[
    {
        "id": 1,
        "name": "Sala 101",
        "capacity": 40
    },
    {
        "id": 3,
        "name": "Laboratório 02",
        "capacity": 30
    }
]
Exemplo de criação de reserva:
POST /reservations

{
    "room_id": 3,
    "professor_rm": "123456",
    "date": "2026-09-15",
    "start_time": "14:00",
    "end_time": "15:00"
}
21. Estrutura do backend
backend/
│
├── main.py
├── database.py
│
├── models/
│   ├── professor.py
│   ├── room.py
│   ├── equipment.py
│   └── reservation.py
│
├── schemas/
│   ├── professor.py
│   ├── room.py
│   └── reservation.py
│
├── routers/
│   ├── professors.py
│   ├── rooms.py
│   └── reservations.py
│
├── services/
│   └── reservation_service.py
│
└── requirements.txt
Essa estrutura mantém models, schemas, rotas e regras de negócio separados. Isso facilita manutenção e evolução do projeto.
22. Estrutura do frontend
frontend/
│
├── src/
│
├── components/
│   ├── Calendar.jsx
│   ├── RoomCard.jsx
│   ├── RoomDetails.jsx
│   ├── ReservationModal.jsx
│   └── Header.jsx
│
├── pages/
│   ├── Home.jsx
│   ├── Rooms.jsx
│   └── Reservations.jsx
│
├── services/
│   └── api.js
│
├── App.jsx
└── main.jsx
23. Página inicial
┌───────────────────────────────────────────────┐
│ LOGO       Salas    Agenda       Reservar     │
├───────────────────────────────────────────────┤
│       RESERVA DE SALAS ESCOLARES              │
│       Consulte e reserve seu espaço           │
│             [Ver agenda]                      │
├───────────────────────────────────────────────┤
│ Salas disponíveis hoje: 12                    │
│ Reservas hoje: 24                             │
└───────────────────────────────────────────────┘
24. Integração React → Python
No React, a comunicação com o backend pode ser feita com fetch ou Axios. Exemplo de consulta de salas:
const response = await fetch(
    "http://localhost:8000/rooms"
);

const rooms = await response.json();
setRooms(rooms);
Exemplo de envio de uma reserva:
await fetch(
    "http://localhost:8000/reservations",
    {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(reservation)
    }
);
25. Fluxo completo da integração
NAVEGADOR
     │
     ▼
React + Vite
     │
     │ HTTP
     ▼
FastAPI
     │
┌────┴─────┐
▼          ▼
SQLAlchemy  Regras
│          │
└────┬─────┘
     ▼
PostgreSQL
     │
     ▼
   Dados
26. Passo a passo de implementação
A recomendação é não começar pela agenda. Comece pelo banco e pela API, valide o fluxo de reservas e só depois construa a interface.
Etapa 1 — Criar o backend
Criar a pasta backend e instalar as dependências básicas.
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic
Etapa 2 — Configurar PostgreSQL
Criar o banco school_rooms e configurar conexão com usuário, senha e porta.
Host: localhost
Port: 5432
Database: school_rooms
User: postgres
Password: sua_senha
DATABASE_URL=postgresql://postgres:senha@localhost:5432/school_rooms
Etapa 3 — Criar os Models
Começar pelos Models Professor, Room, Equipment e Reservation, incluindo os relacionamentos.
Etapa 4 — Criar o CRUD de salas
Fazer funcionar cadastro, consulta, alteração e exclusão de salas.
POST /rooms
GET /rooms
GET /rooms/{id}
PUT /rooms/{id}
DELETE /rooms/{id}
Etapa 5 — Criar professores
Cadastrar professor e consultar pelo RM.
POST /professors
GET /professors/123456
Etapa 6 — Criar reservas
Implementar POST /reservations com a verificação de conflito antes de gravar.
Etapa 7 — Criar consulta de disponibilidade
Receber data e intervalo de horário, consultar reservas e retornar somente as salas livres.
Etapa 8 — Criar o frontend
Criar o projeto React com Vite e começar pela navegação, lista de salas e detalhes.
Etapa 9 — Criar a página de salas
Mostrar foto, capacidade, equipamentos e botão de reservar.
Etapa 10 — Criar a agenda
Buscar as reservas por mês e transformá-las em eventos na interface.
Etapa 11 — Criar o modal de reserva
Selecionar sala, data, horário e informar o RM do professor.
Etapa 12 — Confirmar reserva
Ao clicar em Confirmar, enviar POST /reservations, tratar a resposta e atualizar a agenda.
27. Exemplo do modal de reserva
┌─────────────────────────────┐
│ Reservar sala               │
├─────────────────────────────┤
│ Sala: Laboratório 01        │
│ Data: 15/09/2026            │
│ Horário: 14:00 - 15:00      │
│ RM do professor:            │
│ [____________________]      │
│ [Cancelar] [Confirmar]      │
└─────────────────────────────┘
28. O que acontece com a agenda depois
Antes:
Sala 201
14:00 🟢 Livre

Depois da reserva:
Sala 201
14:00 🔴 Reservada
Outra pessoa que consultar o mesmo horário não verá a Sala 201 como disponível.
29. Funcionalidades para a primeira versão
Para manter o projeto adequado ao contexto de uma disciplina, a versão inicial pode incluir somente:
Cadastro de salas
Foto da sala
Capacidade
Equipamentos
Cadastro de professores
RM
Agenda mensal
Horários
Consulta de disponibilidade
Reserva
Bloqueio de conflito
Atualização da agenda
PostgreSQL
Funcionalidades que podem ficar para versões futuras:
Login
Permissões
Administrador
Histórico
Relatórios
Notificações
Exportação PDF
E-mails
Manutenção de salas
30. Funcionalidade opcional: administrador
ADMIN
 │
 ├── Cadastrar sala
 ├── Alterar sala
 ├── Remover sala
 ├── Cadastrar equipamento
 ├── Cadastrar professor
 └── Ver todas as reservas

PROFESSOR
 │
 ├── Ver agenda
 ├── Consultar salas
 ├── Reservar
 └── Cancelar sua reserva
Isso cria uma separação simples entre funções administrativas e uso cotidiano dos professores.
31. Segurança
Mesmo em um projeto acadêmico, não é recomendável confiar exclusivamente no RM enviado pelo navegador. Na primeira versão, o RM pode funcionar como identificação. Em uma versão futura, o sistema pode utilizar login, senha e token de autenticação. O FastAPI possui recursos para implementar esquemas como OAuth2 e Bearer Token.
32. Arquitetura final recomendada
USUÁRIO
    │
    ▼
┌─────────────────┐
│     REACT       │
│      VITE       │
└────────┬────────┘
         │ HTTP / JSON
         ▼
┌─────────────────┐
│     FASTAPI     │
│                 │
│ Controllers     │
│ Services        │
│ Schemas         │
│ Validações      │
└────────┬────────┘
         │
     SQLAlchemy
         │
         ▼
┌─────────────────┐
│   POSTGRESQL    │
│                 │
│ Professores     │
│ Salas           │
│ Equipamentos    │
│ Reservas        │
└─────────────────┘
A abordagem pode ser apresentada como arquitetura cliente-servidor com API REST e separação em camadas.
33. Resumo da solução
SISTEMA WEB
     │
┌────┴──────────────┐
│                   │
AGENDA             SALAS
│                   │
Visualizar mês      Foto da sala
Ver horários        Capacidade
Ver reservas        Equipamentos
│                   │
└────────┬──────────┘
         │
      RESERVA
         │
   Data + Horário
         │
     Escolher sala
         │
       Informar RM
         │
       Confirmar
         │
         ▼
      DATABASE
         │
         ▼
  AGENDA ATUALIZADA
Stack final: React + Vite no frontend; Python + FastAPI no backend; SQLAlchemy como ORM; Pydantic para validação; PostgreSQL no banco; API REST/JSON para comunicação; e um componente de calendário React para a agenda.
34. Fontes técnicas consultadas
React — documentação oficial: https://react.dev/learn
Vite — documentação oficial: https://vite.dev/guide/
FastAPI — SQL Databases: https://fastapi.tiangolo.com/tutorial/sql-databases/
FastAPI — Security: https://fastapi.tiangolo.com/tutorial/security/
PostgreSQL — Constraints: https://www.postgresql.org/docs/16/ddl-constraints.html
FullCalendar — Timeline View: https://fullcalendar.io/docs/timeline-view
