import threading
from dataclasses import dataclass
from logging import getLogger
from time import perf_counter, sleep
from typing import Literal

from algo import find_path, sort_food_by_distance
from client import ApiClient
from gt import Map, Snake, Vec3d, parse_map
from util.itypes import measure
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
            if self.gl.replay_loading:
                print("Replay Loaded")
                self.gl.replay_loading = False
            return None

    def _pull_api(self, commands):
        commands = commands or []

        algo_commands = self.gl.collect_commands()

        try:
            data = api.world({"snakes": algo_commands + commands})
            self.scribe.dump_world(lambda: data)

            mp = parse_map(data)

            return mp

        except Exception as e:
            logger.error("Error pulling world", e, exc_info=e)
            return None

    def get_latest_world(self):
        return self.history[-1], len(self.history) - 1

    def load_world_state(self, commands):
        world = self.pull_world(commands)

        if not world:
            return self.get_latest_world()[0]

        current = self.history[-1]
        combined = self.merge_world(current, world)

        self.history.append(combined)

        return combined

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
    direction: Vec3d


@dataclass
class UpdateState:
    turn: int
    frame: int
    state: Literal["Network", "Algorithm", "Command Send"]


class Gameloop:
    def __init__(
        self,
        init: Map = None,
        replay_file=None,
        game_name=None,
        upto=None,
    ):
        if not replay_file and not game_name:
            raise ValueError("Either `replay_file` or `game_name` must be provided")

        self.running = True
        self.executor_thread = None

        self.replay = False
        self.replay_loading = True
        self.replay_simulate = None

        if game_name:
            self.replay = False
            self.scribe = Scribe(f"data/{game_name}.ljson")

        if replay_file:
            self.replay = True
            self.scribe = Scribe(replay_file, enabled=False, upto=upto)

        self.world_builder = WorldBuild(self.scribe, self.replay, init, self)
        self.world, _ = self.world_builder.get_latest_world()

        self.upd = UpdateState(0, 0, "Network")

        self.commands = []

        self.paths: list[SnakeBrain] = []

    def add_command(self, command):
        self.commands.append(command)

    def collect_commands(self):
        snakes = [p.snake.move_command(p.direction) for p in self.paths]

        return snakes

    def get_path(self, snake: Snake):
        for p in self.paths:
            if p.snake.id == snake.id:
                return p.path

        return []

    def algos(self, world: Map):
        paths = []
        for snake in world.snakes:
            if not snake:
                continue

            food = sort_food_by_distance(world, snake)

            if not food:
                continue

            goal = food[0].coordinate

            with measure(f"{snake.name} find_path"):
                path = find_path(world, snake.head, goal, timeout=0.2)
                # todo next goal - closer to center

            if path and len(path) > 1:
                direction = path[1] - path[0]
                paths.append(SnakeBrain(snake, path, direction))

        self.paths = paths

    def loop(self):
        logger.info("Gameloop started")
        try:
            while self.running:
                with measure("world_load"):
                    self.upd.state = "Network"
                    self.world = self.world_builder.load_world_state(self.commands)
                    self.upd.turn = self.world.turn

                if self.replay and self.replay_loading:
                    continue

                if self.replay and not self.replay_loading and self.replay_simulate:
                    self.world = self.world_builder.history[self.replay_simulate]
                    self.upd.turn = self.world.turn

                t = perf_counter()

                with measure("algo"):
                    self.upd.state = "Algorithm"
                    self.algos(self.world)

                # вот тут отправить второй раз

                dt = perf_counter() - t

                if self.replay:
                    sleep(0.33)

                if not self.replay:
                    sleep(max(0, self.world.tick_remain_ms / 1000 - dt))

        except Exception as e:
            logger.error("Gameloop error", exc_info=e)
        finally:
            self.running = False
            logger.info("Gameloop ended")

    def launch_async(self):
        self.executor_thread = threading.Thread(target=self.loop)
        self.executor_thread.start()
        return self
