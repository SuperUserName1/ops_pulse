# Ops Pulse

Production-ready шаблон репозитория с backend на FastAPI и базовой инженерной обвязкой.

## Что Это За Проект

`Ops Pulse` — это шаблон/заготовка для внутреннего операционного сервиса (control panel / ops dashboard).
Он нужен как стартовая база для командной разработки backend + frontend без "пустого" репозитория:

- backend на `FastAPI` с единым форматом ошибок, request-id и API-структурой
- frontend на `React + Vite` с авторизацией, protected routes и refresh token flow
- PostgreSQL-схема (multi-tenant) и миграции `Alembic`
- базовая инженерная обвязка: `ruff`, `mypy`, `pytest`, шаблоны PR/issue

### Что Уже Работает Сейчас

- `GET /v1/health` — health endpoint
- `auth` demo API (`/v1/auth/*`) с JWT access/refresh token flow
- frontend login/profile UI с автологином по токенам и авто-refresh на `401`
- PostgreSQL схема для tenant-данных (`organizations`, `users`, `tasks`)

Важно:
- текущий `AuthService` в MVP использует in-memory demo пользователей (для демонстрации auth-flow)
- PostgreSQL уже подключается backend-ом и используется для миграций/схемы данных
- следующий шаг для product-функций: перевести сервисы (`auth/users/tasks`) на `SQLAlchemy` и `DbSessionDep`

## Структура

- `backend/` — FastAPI backend (async SQLAlchemy, настройки, middleware, тесты)
- `frontend/` — React/Vite frontend (login, protected routes, profile page)
- `.github/` — PR template + issue templates

## Как Работать С Проектом (Коротко)

1. Поднять PostgreSQL и создать БД `ops_pulse`
2. Настроить `backend/.env` (указать `DATABASE_URL`)
3. Применить миграции (`alembic upgrade head`)
4. Запустить backend (`uvicorn app.main:app --reload`)
5. Запустить frontend (`pnpm dev`)
6. Открыть UI и войти demo-пользователем (`admin / admin123`)

## Быстрый старт (backend)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

После запуска документация доступна по адресу: `http://127.0.0.1:8000/docs`.

## Быстрый старт (frontend)

```bash
cd frontend
pnpm install
cp .env.example .env
pnpm dev
```

По умолчанию frontend использует `VITE_API_BASE_URL=/v1` и проксирует `/v1` на `http://127.0.0.1:8000`.

## Команды разработки

### Dev

```bash
cd backend
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
pnpm dev
```

### Lint

```bash
cd backend
ruff check .
```

Frontend:

```bash
cd frontend
pnpm lint
```

### Test

```bash
cd backend
pytest
```

Frontend:

```bash
# тесты еще не добавлены (есть lint/typecheck)
cd frontend
pnpm typecheck
```

### Typecheck

```bash
cd backend
mypy app
```

### Migrations

```bash
make migrate m="init_multi_tenant_schema"
make upgrade
```

Примечание по PostgreSQL:
- backend использует async SQLAlchemy URL (`postgresql+asyncpg://...`)
- задайте `DATABASE_URL` в `backend/.env` (не хардкодьте пароль в репозиторий)

Пример локального `.env` значения:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:<password>@127.0.0.1:5432/ops_pulse
```

Пример создания БД через `psql`:

```bash
PGPASSWORD=<password> psql -h 127.0.0.1 -U postgres -d postgres -c \
  "CREATE DATABASE ops_pulse WITH OWNER postgres ENCODING 'UTF8';"
```

Проверка таблиц после миграций:

```bash
PGPASSWORD=<password> psql -h 127.0.0.1 -U postgres -d ops_pulse -c "\\dt"
```

## PostgreSQL Schema (Multi-tenant)

Основные таблицы:
- `organizations` — тенанты (slug/name)
- `users` — пользователи tenant-а (`org_id`, role, status, email)
- `tasks` — рабочие задачи tenant-а (`org_id`, status, assignee_user_id, created_at)

Tenant-модель:
- все бизнес-сущности имеют `org_id` (в текущем MVP: `users`, `tasks`)
- `organizations` — корневая tenant-сущность (для неё `org_id` не нужен)

Ключевые ограничения и индексы:
- `UNIQUE (org_id, email)` для `users`
- индексы на `users(status)`, `users(org_id, created_at)`
- индексы на `tasks(status)`, `tasks(assignee_user_id)`, `tasks(org_id, created_at)`

## Бизнес-Смысл (Зачем Нужен Ops Pulse)

Проект ориентирован на внутренние команды (operations/support/dispatch), которым нужен базовый веб-интерфейс для:

- управления пользователями внутри организации (tenant)
- работы с задачами/тикетами/операционными сущностями
- безопасной аутентификации и разграничения ролей (`admin`, `agent`, `viewer`)
- дальнейшего роста в полноценную internal-platform/API

Этот репозиторий удобен как "скелет" для новых фич:
- добавляете новые endpoints в `backend/app/api/v1/endpoints/`
- описываете схемы в `backend/app/schemas/`
- переносите данные из demo-сервисов в PostgreSQL через `SQLAlchemy`
- расширяете frontend pages/features под ваши процессы

## Branching Strategy

- `main` — стабильная ветка
- `feat/*` — новые фичи (пример: `feat/health-endpoint`)
- `fix/*` — исправления (пример: `fix/request-id-header`)

## Conventional Commits

Формат:

```text
type(scope): summary
```

Примеры:

- `feat(api): add health endpoint with request-id middleware`
- `fix(errors): unify validation error response format`
- `chore(repo): add editorconfig and github templates`

## PR / Issues

- Используйте `.github/pull_request_template.md` для описания изменений и проверок
- Используйте issue templates для багов и запросов фич
