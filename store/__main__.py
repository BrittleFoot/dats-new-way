import json
import subprocess
from itertools import batched
from pathlib import Path

from fire import Fire

from store.connect import Jsonb, db


def wc(file: Path) -> int:
    try:
        return int(subprocess.check_output(["wc", "-l", str(file)]).split()[0])
    except subprocess.CalledProcessError:
        print("🥵 Error running wc, no progress awailable")
        return -1


class DbActions:
    def migrate(self):
        print("🛢️ 🚛 Migrating database")
        with db() as conn, conn.cursor() as cur:
            cur.execute("""
                        CREATE TABLE IF NOT EXISTS replays (
                            id SERIAL PRIMARY KEY,
                            turn INT,
                            name TEXT,
                            data JSONB,
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                        """)
            conn.commit()
        print("🛢️ ✅ Done")

    def drop(self):
        print("🛢️ 🚫 Dropping database")
        if input("❓❓❓ Are you sure? (yes/n): ") != "yes":
            print("🥵 Aborting")
            return

        with db() as conn, conn.cursor() as cur:
            cur.execute("DROP TABLE replays")
            conn.commit()

        print("🛢️ ✅ Dropped")

    def delete(self, name: str):
        print("🛢️ 🗑️ Deleting data")
        with db() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM replays WHERE name = %s RETURNING id", (name,))
            conn.commit()
            ids = cur.fetchall()
        print(f"🛢️ ✅ Deleted {len(ids)} items")

    def summary(self):
        print("🛢️ 📊 Database summary")
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT name, COUNT(turn) FROM replays GROUP BY name")
            summary = cur.fetchall()
            for name, count in summary:
                print(f"📊 ➡️ {name}: {count} turns recorded")
            print(f"📊 Total replays: {len(summary)}")

    def upload(self, name: str, *, batch: int = 3000):
        path = Path(name)
        if not path.is_file():
            print(f"🥵 File `{name}` not found")
            return

        name = path.stem

        print(f"🛢️ ⬆️ Uploading data with name=`{name}`")

        lines = wc(path)
        if lines >= 0:
            print(f"🛢️ ➡️ {lines} lines")

        total = 0

        with db() as conn, conn.cursor() as cur:
            with path.open() as file:
                for json_lines in batched(file, batch):
                    loaded = (json.loads(line) for line in json_lines)

                    prepared = ((name, data["turn"], Jsonb(data)) for data in loaded)

                    cur.executemany(
                        "INSERT INTO replays (name, turn, data) VALUES (%s, %s, %s)",
                        prepared,
                    )

                    total += batch

                    if lines > 0:
                        proc = min(total / lines * 100, 100)
                        print(f"🛢️ 🚀 {proc:.2f}%")
                    else:
                        print(f"🛢️ 🚀 {total} loaded")

            conn.commit()

        print("🛢️ ✅ Uploaded")


if __name__ == "__main__":
    Fire(DbActions())
