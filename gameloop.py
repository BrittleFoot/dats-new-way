import threading
from logging import getLogger
from time import sleep

from client import ApiClient

api = ApiClient("test")

logger = getLogger(__name__)


class Gameloop:
    def __init__(self):
        self.running = True

        self.world = []
        self.whole_world = []
        self.turn = 0
        self.next_time = 0

    def loop(self):
        try:
            while self.running:
                info = api.test_world()

                next_time = info["next"]
                timeout = info["turnEndsInSec"]
                world = info["map"]
                turn = info["turn"]

                self.world = world

                self.whole_world.extend(world)
                self.turn = turn
                self.next_time = next_time

                sleep(timeout)

        except Exception as e:
            logger.error("Gameloop error: %s", exc_info=e)
        finally:
            self.running = False

    def launch_async(self):
        executor_thread = threading.Thread(
            target=self.loop,
            daemon=True,
        )
        executor_thread.start()
        return self


if __name__ == "__main__":
    gameloop = Gameloop().launch_async()

    try:
        while True:
            input()
    except KeyboardInterrupt:
        pass
