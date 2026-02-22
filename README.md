# Ops Pulse

Production-ready шаблон репозитория с backend на FastAPI и базовой инженерной обвязкой.

## Структура

- `backend/` — FastAPI backend (async SQLAlchemy, настройки, middleware, тесты)
- `.github/` — PR template + issue templates

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

## Команды разработки

### Dev

```bash
cd backend
uvicorn app.main:app --reload
```

### Lint

```bash
cd backend
ruff check .
```

### Test

```bash
cd backend
pytest
```

### Typecheck

```bash
cd backend
mypy app
```

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
