# WarehouseOptimizer

FastAPI application for planning warehouse package placement. It provides a 3D browser view, Excel import/export, and SQLite-backed optimization history.

## Local run

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser.

Rejestracja użytkowników jest lokalna: konto składa się z loginu i hasła zapisanych w bazie aplikacji. System nie korzysta z Google OAuth, Gmaila ani kontaktów Google. W trybie developerskim dane administracyjne to `admin` / `admin`. Przed wdrożeniem ustaw własne wartości:

```bash
export WAREHOUSE_ADMIN_USER=warehouse-admin
export WAREHOUSE_ADMIN_PASSWORD=strong-password
```

## Tests

```bash
./.venv/bin/python -m pytest -q app/test_packing.py
```

## Docker

Build and run with a persistent history database:

```bash
docker build -t warehouse-optimizer .
docker run --rm -p 8000:8000 -v warehouse-optimizer-data:/app/data warehouse-optimizer
```

The application listens on port `8000`. The SQLite database is stored in the `/app/data` volume. Set `WAREHOUSE_DB_PATH` to use another location.