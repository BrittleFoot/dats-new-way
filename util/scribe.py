import itertools
import json
from logging import getLogger
from pathlib import Path

from fire import Fire

logger = getLogger(__name__)


class Scribe:
    """
    Dump server world state to a file.

    ie responses from the server.
    """

    # Pickle variant, no need, we're dumping JSON

    # def encode(self, data):
    #     return b64encode(pickle.dumps(data))

    # def decode(self, data):
    #     return pickle.loads(b64decode(data))

    def encode(self, data):
        return json.dumps(data, ensure_ascii=True)

    def decode(self, data):
        return json.loads(data)

    #

    def __init__(self, path: str, *, enabled=True, **kwargs):
        self.replay = Path(path)
        self.enabled = enabled
        self.kwargs = kwargs
        if not self.enabled:
            if not self.replay.is_file():
                raise FileNotFoundError(f"Replay file not found: {self.replay}")
            logger.info(f"📁 ▶️ Scribe in replay mode, reading from {self.replay}")

        else:
            logger.info(f"📁 ✍️ Scribe recording: {self.replay}")
            self.replay.touch()

    def dump_world(self, world_supplier):
        if not self.enabled:
            return

        data = self.encode(world_supplier())
        with self.replay.open("a") as f:
            print(data, file=f)

    def _cleanup_replay(self):
        if not self.enabled:
            return

        logger.info(f"📁 Replay file: {self.replay}")
        if self.replay.exists():
            self.replay.unlink()
            self.replay.touch()
            logger.info("🧹 Replay file cleaned")

    def replay_iterator(self):
        upto = self.kwargs.get("upto")

        with self.replay.open("r") as replay:
            lines = filter(bool, map(str.strip, replay))

            if upto:
                lines = itertools.islice(lines, upto)

            for line in lines:
                yield self.decode(line)


def test(file):
    scribe = Scribe(file)

    scribe.dump_world(lambda: {"a": 1})

    for item in scribe.replay_iterator():
        print(item)


if __name__ == "__main__":
    Fire(test)
