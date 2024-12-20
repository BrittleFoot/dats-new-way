import threading
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter, sleep

from algo import find_path, sort_food_by_distance
from client import ApiClient
from gt import Map, Snake, Vec3d, parse_map
from util.scribe import Scribe

api = ApiClient("test")

logger = getLogger(__name__)


class WorldBuild:
    def __init__(self, scribe: Scribe, replay: bool, init: Map, gl: "Gameloop"):
        self.replay = replay
        self.scribe = scribe

        if replay:
            self.replay_data = scribe.replay_iterator()

        self.world = init

        self.history: list[Map] = [init]
        self.gl = gl

    def pull_world(self, commands):
        if self.replay:
            return self._pull_replay()

        return self._pull_api(commands)

    def _pull_replay(self):
        try:
            data = next(self.replay_data)
            return parse_map(data)
        except StopIteration:
            return None

    def _pull_api(self, commands):
        commands = commands or []

        for snake in self.gl.paths:
            if snake:
                commands.append(snake.id)

        try:
            data = api.world({"snakes": commands})
            self.scribe.dump_world(lambda: data)

            mp = parse_map(data)

            return mp

        except Exception as e:
            logger.error("Error pulling world", exc_info=e)
            return None

    def get_latest_world(self):
        return self.history[-1], len(self.history) - 1

    def load_world_state(self, commands):
        world = self.pull_world(commands)

        if not world:
            return self.get_latest_world()

        current = self.history[-1]
        combined = self.merge_world(current, world)

        self.history.append(combined)

        return combined, len(self.history)

    def merge_world(self, glob: Map, local: Map):
        # m = deepcopy(glob.map)

        # for item in local.map:
        #     point = Vec2(**item)
        #     m[point] = item

        return local


@dataclass
class SnakeBrain:
    snake: Snake
    path: list[Vec3d]


class Gameloop:
    def __init__(self, init: Map = None, replay_file=None, game_name=None):
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

        self.world_builder = WorldBuild(self.scribe, self.replay, init, self)
        self.world, self.history_point = self.world_builder.get_latest_world()

        self.commands = []

        self.paths: list[SnakeBrain] = []

    def add_command(self, command):
        self.commands.append(command)

    def algos(self, world: Map):
        for snake in world.snakes:
            if not snake:
                continue

            food = sort_food_by_distance(world, snake)

            if not food:
                continue

            goal = food[0].coordinate

            path = find_path(world, snake.head, goal)

            if path:
                self.paths.append(SnakeBrain(snake, path))

    def loop(self):
        logger.info("Gameloop started")
        try:
            while self.running:
                self.world, history_point = self.world_builder.load_world_state(
                    self.commands
                )

                print(self.history_point)
                if history_point <= self.history_point:
                    sleep(0.5)

                self.history_point = history_point

                t = perf_counter()

                self.algos(self.world)

                dt = perf_counter() - t

                if not self.replay:
                    sleep(max(0, self.world.tick_remain_ms / 1000 - dt))

        except Exception as e:
            logger.error("Gameloop error", exc_info=e)
        finally:
            self.running = False

    def launch_async(self):
        executor_thread = threading.Thread(target=self.loop)
        executor_thread.start()
        return self
