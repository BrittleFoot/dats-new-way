# type: ignore
try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    print("🥵 No psycopg3 was found, falling back to psycopg2")
    import psycopg2 as psycopg
    from psycopg2.extras import Json as Jsonb


def db():
    return psycopg.connect("postgres://postgres@localhost:5400/postgres")


if __name__ == "__main__":
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 'Hello, world!'")
            print(cur.fetchone())


__all__ = ["db", "Jsonb"]
