# Dats New Way

```bash

# python >=3.12
pip install -r requirements.txt

python super.py <path/to/replay.ljson>

```

## Aftermath

see `sotre` package.

```bash

# store existing ljson replay file in postgres, and other db utils like migration
python -m store --help

# websocket stream from postgres
python -m store.stream
```

My idea is to

1. store replays in a database from now on
2. stream the replays to the frontend (valkey for realtime, from postgres for history)

To think: 3. tnink about manual control (other way pubsub from frontend to backend)
