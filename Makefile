.PHONY: migrate upgrade lint test typecheck

m ?= migration

migrate:
	cd backend && ./.venv/bin/alembic revision --autogenerate -m "$(m)"

upgrade:
	cd backend && ./.venv/bin/alembic upgrade head

lint:
	cd backend && ./.venv/bin/ruff check .

test:
	cd backend && ./.venv/bin/pytest

typecheck:
	cd backend && ./.venv/bin/mypy app
