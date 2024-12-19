import threading
from copy import deepcopy
from dataclasses import dataclass
from logging import getLogger
from time import sleep

from client import ApiClient
from util.itypes import Vec2
from util.scribe import Scribe

api = ApiClient("test")

logger = getLogger(__name__)


@dataclass
class World:
    turn: int
    timeout: int
    map: dict


class WorldBuild:
    def __init__(self, scribe: Scribe, replay: bool):
        self.replay = replay
        self.scribe = scribe

        if replay:
            self.replay_data = scribe.replay_iterator()

        self.world = World(0, 0, {})

        self.history = [self.world]

    def pull_world(self):
        if self.replay:
            return self._pull_replay()

        return self._pull_api()

    def _pull_replay(self):
        try:
            return next(self.replay_data)
        except StopIteration:
            return None

    def _pull_api(self):
        try:
            data = api.test_world()

            self.scribe.dump_world(lambda: data)

            return data

        except Exception as e:
            logger.error("Error pulling world", exc_info=e)
            return None

    def get_latest_world(self):
        return self.history[-1], len(self.history) - 1

    def load_world_state(self):
        world = self.pull_world()

        if not world:
            return self.get_latest_world()

        turn = world["turn"]
        timeout = world["turnEndsInSec"]
        map = world["map"]

        current = self.history[-1]
        seen_now = World(turn, timeout, map)
        combined = self.merge_world(current, seen_now)

        self.history.append(combined)

        return combined, len(self.history)

    def merge_world(self, glob: World, local: World):
        m = deepcopy(glob.map)

        for item in local.map:
            point = Vec2(**item)
            m[point] = item

        return World(local.turn, local.timeout, m)


class Gameloop:
    def __init__(self, replay_file=None, game_name=None):
        if not replay_file and not game_name:
            raise ValueError("Either `replay_file` or `game_name` must be provided")

        self.running = True
        self.replay = False

        if game_name:
            self.replay = False
            self.scribe = Scribe(f"data/{game_name}.ljson")

        if replay_file:
            self.replay = True
            self.scribe = Scribe(replay_file, enabled=False)

        self.world_builder = WorldBuild(self.scribe, self.replay)
        self.world, self.history_point = self.world_builder.get_latest_world()

    def loop(self):
        logger.info("Gameloop started")
        try:
            while self.running:
                self.world, history_point = self.world_builder.load_world_state()

                if history_point <= self.history_point:
                    sleep(0.1)

                self.history_point = history_point

                if not self.replay:
                    sleep(self.world.timeout)

        except Exception as e:
            logger.error("Gameloop error", exc_info=e)
        finally:
            self.running = False

    def launch_async(self):
        executor_thread = threading.Thread(target=self.loop)
        executor_thread.start()
        return self
