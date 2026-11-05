# Crolo · API

## Requirements

- Python `3.10+` (the code uses `str | None` syntax)
- SQLite (bundled with Python)

## Setup

```bash
cd api

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Runtime dependencies used by the code but not listed in requirements.txt
pip install fastapi uvicorn sqlalchemy python-jose python-multipart
```

## Environment

Create `api/.env` from the example:

```bash
cp .env.example .env
```

| Variable     | Required | Description                                                                 |
| ------------ | -------- | --------------------------------------------------------------------------- |
| `SECRET_KEY` | Yes      | Secret used to sign JWTs. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. |

The app will fail to start if `SECRET_KEY` is missing.

## Database

The database is SQLite at `api/crolo.db` (configured in `database.py`). Tables are created automatically on import.

Seed the default roles (`user`, `admin`, `moderator`):

```bash
python setup_db.py
```

To start from a clean database, delete `crolo.db` and run `setup_db.py` again.

## Run

```bash
source venv/bin/activate
uvicorn main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Bind to another host/port:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path         | Auth   | Description                         |
| ------ | ------------ | ------ | ----------------------------------- |
| `GET`  | `/`          | No     | Health/welcome message              |
| `POST` | `/register/` | No     | Create a user (JSON)                |
| `POST` | `/token`     | No     | OAuth2 password grant (form-encoded) |
| `GET`  | `/users/me`  | Bearer | Current user                        |
| `GET`  | `/protected` | Bearer | Sample protected route              |
| `GET`  | `/items/{id}`| No     | Sample echo route                   |

Access tokens expire after 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES` in `auth.py`).

## Notes

- CORS is not enabled. Use the web app's Vite proxy (`/api` → `http://127.0.0.1:8000`) or enable CORS in `main.py` if the client is on another origin.
- `venv/`, `__pycache__/`, `.env`, and `crolo.db` are ignored by Git.
