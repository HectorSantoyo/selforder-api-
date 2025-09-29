# SelfOrderM API

## Dev quickstart
```bash
docker compose up --build
# luego abre http://localhost:8000/api/v1/health


## Migrations & Seeds

Correr migraciones:
```bash
docker compose run --rm -T api poetry run alembic upgrade head

