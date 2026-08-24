# Privio Commitments API

API REST para gerenciamento de compromissos financeiros e projeções orçamentárias construída com **FastAPI**, **SQLAlchemy 2.0**, **PostgreSQL**, empacotada e gerenciada com **uv**, com linter/formatador **Ruff** e checagem de tipos estáticos via **Astral ty**.

---

## 🛠️ Tecnologias e Ferramentas

- **Python**: `>= 3.11`
- **Gerenciador de Pacotes e Ambiente**: [uv](https://docs.astral.sh/uv/)
- **Framework Web**: [FastAPI](https://fastapi.tiangolo.com/)
- **Frontend Server-Rendered**: [Jinja2](https://jinja.palletsprojects.com/) + [HTMX](https://htmx.org/) (sem React/Vue)
- **Design & CSS**: [Pico.css v2](https://picocss.com/) via CDN (responsivo e temas claro/escuro nativos)
- **ORM & Banco de Dados**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/) + [PostgreSQL](https://www.postgresql.org/) (driver `psycopg 3`)
- **Validação de Schemas**: [Pydantic v2](https://docs.pydantic.dev/) + `pydantic-settings`
- **Linter & Formatação**: [Ruff](https://docs.astral.sh/ruff/)
- **Type Checker**: [ty (Astral)](https://github.com/astral-sh/ty)
- **Testes Automatizados**: [pytest](https://docs.pytest.org/) + `httpx`

---

## 📁 Estrutura do Projeto

```
privio_v1/
├── .env.example              # Exemplo de variáveis de ambiente (Postgres, host, debug)
├── .gitignore                # Arquivos ignorados pelo Git
├── pyproject.toml            # Configurações de dependências, Ruff, ty e pytest
├── uv.lock                   # Lockfile determinístico do uv
├── README.md                 # Documentação do projeto
├── scripts/
│   ├── check.sh              # Script shell para rodar 'ruff check', 'ruff format --check' e 'ty check'
│   └── check.py              # Runner Python multiplataforma para os mesmos checks
├── app/
│   ├── __init__.py
│   ├── config.py             # Configurações via pydantic-settings
│   ├── database.py           # Engine SQLAlchemy, SessionLocal e get_db() dependency
│   ├── main.py               # Instância FastAPI, middlewares e registro de rotas
│   ├── models/
│   │   ├── __init__.py
│   │   └── commitment.py     # Modelo SQLAlchemy Commitment e Enums
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── commitment.py     # Schemas Pydantic (Create, Update, Response, Occurrence, SuggestedMonthly)
│   ├── services/
│   │   ├── __init__.py
│   │   └── recurrence.py     # Resolução de recorrências e projeções mensais
│   └── routers/
│       ├── __init__.py
│       └── commitments.py    # Rotas CRUD e endpoints customizados
└── tests/
    ├── __init__.py
    ├── conftest.py           # Fixtures com banco SQLite in-memory para testes isolados
    └── test_commitments.py   # Testes unitários e de integração
```

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos e Instalação do uv

Se ainda não possuir o `uv` instalado:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

Edite as configurações no `.env`:
```ini
# Conexão PostgreSQL
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/privio_db

# Credenciais HTTP Basic Auth
EDITOR_USER=editor
EDITOR_PASS=editor123
VIEWER_USER=viewer
VIEWER_PASS=viewer123
```

### 3. Autenticação & Papéis (HTTP Basic Auth)

A aplicação implementa **HTTP Basic Auth** com dois níveis de acesso configuráveis via `.env`:
- **Editor (`EDITOR_USER` / `EDITOR_PASS`)**:
  - Acesso de leitura e escrita (Criar, Editar, Atualizar status e Excluir compromissos e depósitos).
- **Viewer (`VIEWER_USER` / `VIEWER_PASS`)**:
  - Acesso somente leitura (Visualizar dashboard, listar compromissos, próximos vencimentos, sugestão mensal e saldo de reserva).
  - Tentativas de mutação (POST/PUT/PATCH/DELETE) retornam **HTTP 403 Forbidden**.

### 4. Internacionalização (i18n para PT / EN / IT)

O sistema conta com internacionalização via dicionário Python nativo com troca dinâmica por parâmetro de URL:
- Português (padrão): `http://localhost:8000/?lang=pt`
- Inglês: `http://localhost:8000/?lang=en`
- Italiano: `http://localhost:8000/?lang=it`

O seletor de idiomas no topo da página permite alternar instantaneamente entre os idiomas.

### 5. Instalar Dependências

Sincronize o ambiente virtual com `uv`:
```bash
uv sync --all-groups
```

### 4. Iniciar o Servidor de Desenvolvimento

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acesse a documentação interativa Swagger/OpenAPI em:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔍 Qualidade de Código & Tipagem

Para rodar todos os linters, checagens de formatação e verificação de tipos (`ruff check`, `ruff format --check` e `ty check`):

```bash
# Via script shell
./scripts/check.sh

# Ou via runner Python
uv run python scripts/check.py
```

### Comandos Individuais
```bash
# Linting
uv run ruff check .

# Formatação
uv run ruff format --check .   # apenas verificar
uv run ruff format .           # formatar arquivos

# Checagem de tipos com ty
uv run ty check .
```

---

## 🧪 Testes Automatizados

Os testes rodam de forma isolada utilizando banco SQLite in-memory:

```bash
uv run pytest
```

---

## ☁️ Deploy em Produção (Render / Fly.io + Neon PostgreSQL)

O projeto já inclui todos os arquivos de configuração necessários para deploy:
- **Neon**: Compatibilidade com PostgreSQL Serverless (pooling e auto-reconexão com `pool_pre_ping=True`).
- **Render**: Arquivo [`render.yaml`](file:///Users/alanviana/Projects/privio_v1/render.yaml) para deploy com 1 clique via Blueprint.
- **Fly.io**: Arquivos [`fly.toml`](file:///Users/alanviana/Projects/privio_v1/fly.toml), [`Dockerfile`](file:///Users/alanviana/Projects/privio_v1/Dockerfile) e [`.dockerignore`](file:///Users/alanviana/Projects/privio_v1/.dockerignore).

📖 **Confira o passo a passo detalhado no [Guia de Deploy (DEPLOYMENT.md)](file:///Users/alanviana/Projects/privio_v1/DEPLOYMENT.md).**

---

## 🖥️ Frontend Server-Rendered (Jinja2 + HTMX + Pico.css)

Acesse `http://localhost:8000/` no navegador para abrir o Dashboard:
- **Cards de Métricas**: Total Sugerido do Mês (com detalhamento de mensais, semestrais e anuais) e Saldo de Reserva em tempo real.
- **Próximos Vencimentos (30 / 60 / 90 dias)**: Alternância dinâmica via HTMX (`/ui/upcoming?days=30|60|90`) com projeção de ocorrências de recorrência.
- **Formulário de Criar/Editar Compromisso**: Modais dinâmicos com salvamento e validação assíncrona via HTMX sem recarregar a página.
- **Ações Rápidas**: Marcar como pago/pendente com 1 clique, exclusão com confirmação e registro rápido de depósitos na reserva.

---

## 📌 Endpoints da API

### CRUD de Compromissos (`Commitment`)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/commitments` | Cria um novo compromisso |
| `GET` | `/commitments` | Lista compromissos (com filtros `category`, `status`, `recurrence`, paginação) |
| `GET` | `/commitments/{id}` | Obtém detalhes de um compromisso por ID |
| `PUT` | `/commitments/{id}` | Atualização completa de um compromisso |
| `PATCH` | `/commitments/{id}` | Atualização parcial de um compromisso |
| `DELETE` | `/commitments/{id}` | Remove um compromisso (HTTP 204) |

### CRUD de Depósitos (`Deposit`)

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/deposits` | Registra uma nova transferência/depósito |
| `GET` | `/deposits` | Lista depósitos (filtros `start_date`, `end_date`, paginação) |
| `GET` | `/deposits/{id}` | Obtém detalhes de um depósito por ID |
| `PUT` | `/deposits/{id}` | Atualização completa de um depósito |
| `PATCH` | `/deposits/{id}` | Atualização parcial de um depósito |
| `DELETE` | `/deposits/{id}` | Remove um depósito (HTTP 204) |

### Endpoints Especiais

#### `GET /upcoming?days=30`
Projeta as próximas ocorrências de compromissos que vencem nos próximos `N` dias, resolvendo automaticamente recorrências (`weekly`, `monthly`, `semiannual`, `annual`) a partir do `due_date` original e ordenando cronologicamente.

- Parâmetros:
  - `days` (opcional, padrão `30`): Janela em dias para frente.
  - `from_date` (opcional, padrão `hoje`): Data base de início.

#### `GET /suggested-monthly`
Calcula o orçamento mensal sugerido baseado na fórmula:
$$\text{Total Sugerido} = \sum \text{Mensais} + \frac{\sum \text{Anuais}}{12} + \frac{\sum \text{Semestrais}}{6}$$
Considera apenas compromissos ativos (`status == 'pending'`).

- Parâmetros:
  - `only_active` (opcional, padrão `true`): Considera apenas pendentes.

#### `GET /reserve-balance`
Calcula o saldo de reserva da conta/reserva financeira:
$$\text{Saldo de Reserva} = \sum \text{Depósitos} - \sum \text{Compromissos Pagos}$$
Retorna o total de depósitos, o total de compromissos já pagos, o saldo líquido e a contagem de registros.
