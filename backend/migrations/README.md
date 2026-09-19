# Database migrations

This project uses [Alembic](https://alembic.sqlalchemy.org/) to manage the
database schema. `backend/migrations/versions/` is the history of every
schema change, in order — it's what lets you upgrade an existing database
(with real data in it) instead of deleting it and starting over.

## First-time setup / after pulling schema changes

```bash
alembic upgrade head
```

Run this from the project root (where `alembic.ini` lives). It uses the
same `DATABASE_URL` environment variable (and the same local-SQLite
fallback) the app itself uses — see `backend/db/session.py` — so it always
targets the same database `uvicorn backend.main:app` will connect to.

## Making a schema change

1. Edit the model(s) in `backend/models/`.
2. Generate a migration:
   ```bash
   alembic revision --autogenerate -m "short description of the change"
   ```
3. **Open the generated file in `versions/` and read it.** Autogenerate is
   very good but not infallible — it can miss things like column renames
   (it sees a drop + an add) or complex type changes. Fix by hand if needed.
4. Apply it: `alembic upgrade head`.
5. Commit the migration file alongside the model change, in the same commit.

## Notes

- SQLite can't `ALTER TABLE` for most operations (dropping/altering a
  column, etc.). `backend/migrations/env.py` enables Alembic's batch mode
  automatically when the target database is SQLite, which works around
  this by rebuilding the table under the hood. Postgres doesn't need this
  and isn't affected.
- Tests do **not** use these migrations — `backend/tests/conftest.py` calls
  `Base.metadata.create_all()` directly against a disposable per-session
  SQLite file, since a test database has no upgrade history to track and
  no real data to protect. Migrations matter for the database you actually
  keep data in.
