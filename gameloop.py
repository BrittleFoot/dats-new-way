import threading
from dataclasses import dataclass
from logging import getLogger
from random import randint, shuffle
from time import perf_counter, sleep
from typing import Literal

from algo import find_path_brain
from algo2 import (
    calculate_surrounding_values,
    snake_ai_move_astar_multi,
)
from client import ApiClient
from gt import Map, Snake, SnakeBrain, Vec3d, parse_map
from util.itypes import TIMERS, measure
from util.scribe import Scribe

api = ApiClient("prod")

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
        self.banned = set()

        self.latest_targets = {}

    def add_command(self, command):
        self.commands.append(command)

    def collect_commands(self):
        snakes = [p.snake.move_command(p.direction) for p in self.paths]

        return snakes

    def ban_target(self, target: Vec3d):
        self.banned.add(target)

    def get_brain(self, snake: Snake):
        for p in self.paths:
            if p.snake.id == snake.id:
                return p

        return None

    def algos2(self, world: Map, timeout):
        brains = []

        snakes = list(filter(bool, world.snakes))
        shuffle(snakes)
        snakes = sorted(snakes, key=lambda x: x.id)

        remaining_time = timeout

        best_food_cache = None

        targets = set()

        for i, snake in enumerate(snakes):
            snake_time = remaining_time / (len(snakes) - i)

            center = world.size / 2
            radius = center.len() / 2
            to_center = center - snake.head
            is_okraina = to_center.len() > 2 * radius / 3
            is_okraina = False

            with measure(f"{snake.name} find_path"):
                ai_start = perf_counter()

                snake_time = remaining_time / (len(snakes) - i)
                main_time = snake_time * 0.8

                if is_okraina:
                    brain = None
                else:
                    not_my_targets = {
                        v for k, v in self.latest_targets.items() if k != snake.id
                    }

                    brain = snake_ai_move_astar_multi(
                        world,
                        snake,
                        timeout=main_time,
                        ignore=targets | self.banned | not_my_targets,
                    )
                if brain:
                    brains.append(brain)
                    remaining_time -= perf_counter() - ai_start
                    targets.add(brain.path[-1])
                    self.latest_targets[snake.id] = brain.path[-1]
                    continue

                snake_time -= perf_counter() - ai_start

                if not best_food_cache and not is_okraina:
                    with measure("calculate_surroundings"):
                        best_food_cache = calculate_surrounding_values(world, radius=70)

                best = None
                if not is_okraina and best_food_cache:
                    _, best = best_food_cache[0]
                    while best_food_cache and best.coordinate in targets:
                        best_food_cache.pop(0)
                        if best_food_cache:
                            _, best = best_food_cache[0]

                    newcache = []

                    for _, food in best_food_cache:
                        if food.coordinate not in targets:
                            if best.coordinate.distance(food.coordinate) > 35:
                                newcache.append((_, food))

                    best_food_cache = newcache

                if best:
                    b = best.coordinate
                    reachable = snake.head.manh(best.coordinate) < 20

                    if not reachable:
                        vector_to_best = best.coordinate - snake.head
                        b = (snake.head + vector_to_best.normalize() * 10).round()

                    brain = find_path_brain(
                        world,
                        snake,
                        b,
                        timeout=snake_time,
                        label=f"BEST {best.points, best.type} {reachable=}",
                    )
                    if brain:
                        brains.append(brain)
                        targets.add(best.coordinate)
                        remaining_time -= perf_counter() - ai_start
                        continue

                center = world.size / 2
                to_center = center - snake.head
                to_center_unit = to_center.normalize() * min(10, to_center.len() - 5)
                if to_center.len() > world.size.len() / 16:
                    b = (snake.head + to_center_unit).round()
                    brain = find_path_brain(
                        world,
                        snake,
                        b,
                        timeout=snake_time,
                        label="RUN AWAY" if is_okraina else "CENTER",
                    )
                    if brain:
                        brains.append(brain)
                        remaining_time -= perf_counter() - ai_start
                        continue

                snake_time -= perf_counter() - ai_start

                random = Vec3d(randint(3, 6), randint(3, 6), randint(3, 6))
                b = snake.head + random
                brain = find_path_brain(
                    world, snake, b, timeout=snake_time, label="RANDOM"
                )
                if brain:
                    brains.append(brain)
                    remaining_time -= perf_counter() - ai_start
                    continue

        self.paths = brains

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

                if not self.upd.algo_done and False:
                    # 1
                    with measure("algo"):
                        self.upd.state = "Algorithm"
                        self.algos2(self.world, timeout=timeout * 0.95)
                        self.upd.algo_for_turn = self.world.turn

                else:
                    if self.replay:
                        sleep(0.01)

                    # 2
                    if not self.replay:
                        with measure("gameloop_sleep"):
                            sleep(max(0, timeout + 0.09))

        except Exception as e:
            logger.error("Gameloop error", exc_info=e)
        finally:
            self.running = False
            logger.info("Gameloop ended")

    def launch_async(self):
        self.executor_thread = threading.Thread(target=self.loop)
        self.executor_thread.start()
        return self
