import threading
from dataclasses import dataclass
from logging import getLogger
from random import shuffle
from time import perf_counter, sleep
from typing import Literal

from algo import find_path, sort_food_by_distance, sort_food_by_price
from client import ApiClient
from gt import Map, Snake, Vec3d, parse_map
from util.itypes import TIMERS, measure
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
        foodmap = {f.coordinate: f for f in local.food}

        for item in local.sus:
            if item.coordinate in foodmap:
                foodmap[item.coordinate].type = "suspicious"

        for item in local.golden:
            if item.coordinate in foodmap:
                foodmap[item.coordinate].type = "golden"

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
    thinks: str = "I'm a snake"


@dataclass
class UpdateState:
    turn: int
    frame: int
    state: Literal["Network", "Algorithm", "Command Send"]
    timeout: int
    algo_for_turn: int

    @property
    def algo_done(self):
        return self.algo_for_turn == self.turn


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

        self.upd = UpdateState(0, 0, "Network", 0, 0)

        self.commands = []

        self.paths: list[SnakeBrain] = []

    def add_command(self, command):
        self.commands.append(command)

    def collect_commands(self):
        snakes = [p.snake.move_command(p.direction) for p in self.paths]

        return snakes

    def get_brain(self, snake: Snake):
        for p in self.paths:
            if p.snake.id == snake.id:
                return p

        return None

    def algos(self, world: Map, timeout):
        paths = []
        snakes = list(filter(bool, world.snakes))
        shuffle(snakes)

        remaining_time = timeout

        for i, snake in enumerate(snakes):
            if not snake:
                continue

            food = sort_food_by_distance(world, snake)

            if not food:
                continue

            goal = food[0].coordinate

            with measure(f"{snake.name} find_path"):
                start = perf_counter()

                local_timeout = remaining_time / (len(snakes) - i)

                path = find_path(world, snake.head, goal, timeout=local_timeout)

                if path and len(path) > 1:
                    direction = path[1] - path[0]
                    paths.append(SnakeBrain(snake, path, direction, "FOOD"))

                center = world.size / 2
                to_center = center - snake.head

                if not path and to_center.len() > world.size.len() / 4:
                    to_center_unit = to_center.normalize() * min(
                        10, to_center.len() - 3
                    )

                    b = (snake.head + to_center_unit).round()

                    path = find_path(world, snake.head, b, local_timeout)

                    if path and len(path) > 1:
                        direction = path[1] - path[0]
                        paths.append(SnakeBrain(snake, path, direction, "CENTER "))

                if not path and len(food) > 1:
                    next_food = sort_food_by_price(world, snake, 40)[0].coordinate

                    path = find_path(world, snake.head, next_food, local_timeout)

                    if path and len(path) > 1:
                        direction = path[1] - path[0]
                        paths.append(SnakeBrain(snake, path, direction, "JUSY FOOD"))

                remaining_time -= perf_counter() - start
                # todo - next goal try 3 food or move closer to center

        self.paths = paths

    def loop(self):
        logger.info("Gameloop started")
        try:
            while self.running:
                with measure("world_load"):
                    self.upd.state = "Network"
                    self.world = self.world_builder.load_world_state(self.commands)
                    self.commands = []
                    self.upd.turn = self.world.turn
                    self.upd.timeout = self.world.tick_remain_ms

                if self.replay and self.replay_loading:
                    continue

                if self.replay and not self.replay_loading and self.replay_simulate:
                    self.world = self.world_builder.history[self.replay_simulate]
                    self.upd.turn = self.world.turn
                    self.upd.timeout = self.world.tick_remain_ms

                # assume that second call will be the same
                # save time for network call
                dt = TIMERS["world_load"]
                timeout = self.world.tick_remain_ms / 1000 - dt

                if self.replay:
                    # just some reasonable value
                    timeout = 0.8

                # Сначала идет в 1
                # потом через мир, отправляет сразу команды
                # (тут есть гибкость еще оттянуть время)
                # потом идет в 2, спит, и по кругу

                if not self.upd.algo_done:
                    # 1
                    with measure("algo"):
                        self.upd.state = "Algorithm"
                        self.algos(self.world, timeout=timeout)
                        self.upd.algo_for_turn = self.world.turn

                else:
                    if self.replay:
                        sleep(0.33)

                    # 2
                    if not self.replay:
                        with measure("gameloop_sleep"):
                            sleep(max(0, timeout))

        except Exception as e:
            logger.error("Gameloop error", exc_info=e)
        finally:
            self.running = False
            logger.info("Gameloop ended")

    def launch_async(self):
        self.executor_thread = threading.Thread(target=self.loop)
        self.executor_thread.start()
        return self
