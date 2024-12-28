# type: ignore
try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    print("🥵 No psycopg3 was found, falling back to psycopg2")
    import psycopg2 as psycopg
    from psycopg2.extras import Json as Jsonb

import asyncpg

DATABASE_URL = "postgres://postgres@localhost:5400/postgres"


def async_db():
    return asyncpg.connect(DATABASE_URL)


def db():
    return psycopg.connect(DATABASE_URL)


if __name__ == "__main__":
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 'Hello, world!'")
            print(cur.fetchone())


__all__ = ["db", "Jsonb"]
