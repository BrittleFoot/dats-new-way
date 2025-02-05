import pprint
from dataclasses import dataclass
from datetime import datetime
from logging import basicConfig
from math import ceil, log2
from os import environ
from time import sleep
from typing import NamedTuple

import imgui
import pygame
from fire import Fire

from client import ApiClient
from draw import DrawWorld, key_handler, window
from gameloop import Gameloop, api
from gt import Map, Snake, Vec3d, parse_map
from util.brush import PixelBrush
from util.itypes import TIMERS, Color, Vec2

basicConfig(
    level="INFO",
    format="[%(levelname)s][%(name)s] %(message)s",
)


class Point(NamedTuple):
    x: float
    y: float


@dataclass
class Config:
    timepoint = 0
    realtime = True

    fade = 0.06

    follow = True
    current_z = 0


class Super(DrawWorld):
    def __init__(
        self,
        init: Map = None,
        game_name=None,
        replay_file=None,
        upto=None,
    ):
        super().__init__()

        self.gameloop = Gameloop(
            replay_file=replay_file,
            game_name=game_name,
            init=init,
            upto=upto,
        ).launch_async()

        self.wb = self.gameloop.world_builder
        self.config = Config()

        self.snake: Snake = None

    def start(self):
        try:
            self.main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self.gameloop.running = False
            self.running = False

    #####
    ###################################

    def draw_world(self):
        brush = PixelBrush(self)
        world = self.get_world_to_draw()
        if not world:
            return

        if self.snake:
            for s in world.snakes:
                if s.id == self.snake.id:
                    self.snake = s

        xy, z = world.size.t2()

        if self.snake and self.config.follow:
            self.config.current_z = self.snake.head.z
            self.focus_snake(scale=False)

        cz = self.config.current_z

        def hide(z):
            diff = abs(z - cz)
            if diff == 0:
                return 1

            if diff > 10:
                return self.config.fade / log2(diff)

            return self.config.fade

        def g(v):
            return self.fromgrid(v)

        for snake in world.snakes:
            if not snake.geometry:
                continue

            if not self.snake:
                self.snake = snake

            v, z = snake.head.t2()

            if self.snake and snake.id == self.snake.id:
                brush.image(g(v), "snowman_happy", color=Color.GREEN.but(a=hide(z)))
            else:
                brush.square(g(v), Color.GOLD.but(a=hide(z)))

            for point in snake.body:
                v, z = point.t2()
                brush.square(g(v), Color.YELLOW.but(a=hide(z)))

        for path in self.gameloop.paths:
            snake = path.snake
            if path.direction.z != 0:
                brush.image(
                    g(snake.head.to2()),
                    "trapdoor",
                    Color.PINK.but(a=hide(snake.head.z)),
                    scale_percent=Vec2(0.30, 0.30),
                )
            else:
                brush.arrow(
                    g(snake.head.to2()),
                    g((snake.head + path.direction).to2()),
                    Color.PINK.but(a=hide(snake.head.z)),
                    thickness=10,
                )

            for point1, point2 in zip(path.path, path.path[1:]):
                v1, z1 = point1.t2()
                a = hide(z1) * 4
                blue = Color.BLUE.but(a=a, r=0.1, g=0.1)

                v2, z2 = point2.t2()

                if v1 == v2 and z1 != z2:
                    brush.image(
                        g(v1),
                        "trapdoor",
                        blue,
                        scale_percent=Vec2(0.25, 0.25),
                    )
                else:
                    brush.arrow(g(v1), g(v2), blue)

        for enemy in world.enemies:
            if not enemy.geometry:
                continue

            v, z = enemy.head.t2()
            brush.image(g(v), "grinch", Color.RED.but(a=hide(z)))
            for point in enemy.body:
                v, z = point.t2()
                brush.square(g(v), Color.PINK.but(a=hide(z)))

        for food in world.food:
            v, z = food.coordinate.t2()
            brush.image(g(v), "gift", Color.WHITE.but(a=hide(z)))
            brush.text(g(v), f"{food.points}", Color.WHITE.but(a=hide(z) * 4))

        for food in world.golden:
            v, z = food.coordinate.t2()
            brush.image(g(v), "gift2", Color.WHITE.but(a=hide(z)))

        for food in world.sus:
            v, z = food.coordinate.t2()
            brush.image(g(v), "hat", Color.WHITE.but(a=hide(z)))

        for fence in world.fences:
            v, z = fence.t2()
            brush.square(g(v), Color.WHITE.but(a=hide(z)))

        brush.rect(self.fromgrid(Vec2(0, 0) - 1), self.fromgrid(xy) + 1, thickness=2)

    ###################################
    #####

    def focus_snake(self, scale=False):
        if self.snake:
            if scale:
                self.scale = 2

            self.offset = Vec2(0, 0)
            self.offset = (
                -self.snake.head.to2() * self.S + self.window_size / 2 / self.scale
            )
            self.config.current_z = self.snake.head.z

    def get_world_to_draw(self):
        if self.config.realtime:
            world, n = self.wb.get_latest_world()
            self.config.timepoint = n
            return world

        return self.wb.history[self.config.timepoint]

    def labeled(self, key, value):
        imgui.text_disabled(f"{key}:")
        imgui.same_line()
        imgui.text(value)

    def draw_ui(self):
        self.imgui_keybindings()

        w = self.get_world_to_draw()
        if not w:
            return

        C = self.config
        timelen = len(self.wb.history) - 1

        with window("Display"):
            _, C.current_z = imgui.slider_int(
                "Z",
                C.current_z,
                min_value=0,
                max_value=w.size.z,
            )

            _, C.fade = imgui.slider_float(
                "Snake Fade",
                C.fade,
                min_value=0,
                max_value=1,
            )

            _, C.follow = imgui.checkbox("Follow", C.follow)

        with window("Timers"):
            self.timers()

        with window("Snakes"):
            for snake in sorted(w.snakes, key=lambda s: s.name):
                if self.snake and snake == self.snake:
                    imgui.text_colored("You", 0, 255, 0)

                imgui.text(f" Snake: {snake.name}...")
                imgui.text(f"Length: {len(snake.geometry)}")
                color = Color.GREEN if snake.status == "alive" else Color.RED
                imgui.text_colored(f"Status: {snake.status}", *color)
                imgui.text(f"  Head: {snake.head}")

                brain = self.gameloop.get_brain(snake)
                if brain:
                    self.labeled("  Path:", f"{len(brain.path)} cells")
                    self.labeled("  Thnk:", f"{brain.thinks}")
                else:
                    imgui.text("  Path:  No brain")
                    imgui.text("  Thnk:  No brain")

                if imgui.button(f"Focus##{snake.id}"):
                    self.snake = snake
                    self.focus_snake()

                if brain:
                    target = brain.path[-1]
                    imgui.same_line()
                    if imgui.button(f"Ban Target {target}##{snake.id}"):
                        self.gameloop.ban_target(target)

                imgui.separator()

            if imgui.button(f"Clean banned targets ({len(self.gameloop.banned)})"):
                self.gameloop.banned = set()

            imgui.separator()

            if self.snake:
                golden = [f for f in w.food if f.type == "golden"]
                sorted_golden = sorted(
                    golden, key=lambda f: f.coordinate.manh(self.snake.head)
                )

                for food in sorted_golden[:5]:
                    dist = food.coordinate.manh(self.snake.head)
                    if imgui.button(
                        f"Go to {food.coordinate}, {dist}##{food.coordinate}"
                    ):
                        pass

        with window("Sacred Timeline"):
            changed, C.timepoint = imgui.slider_int(
                "Timepoint",
                C.timepoint,
                min_value=0,
                max_value=timelen,
            )

            if changed:
                C.realtime = False

                if C.timepoint == timelen:
                    C.realtime = True

            _, C.realtime = imgui.checkbox("Realtime", C.realtime)

        self.gameloop.replay_simulate = C.timepoint

    @key_handler(pygame.K_MINUS)
    def zoom_minus(self, event):
        if self.config.current_z >= self.get_world_to_draw().size.z:
            return

        self.config.current_z += 1

    @key_handler(pygame.K_EQUALS)
    def zoom_plus(self, event):
        if self.config.current_z <= 0:
            return

        self.config.current_z -= 1

    @key_handler(pygame.K_BACKSPACE)
    def ban_target(self, event):
        if self.snake:
            brain = self.gameloop.get_brain(self.snake)
            if brain:
                self.gameloop.ban_target(brain.path[-1])

    def imgui_keybindings(self):
        C = self.config

        if self.config.follow:
            self.focus_snake()

        if self.snake and not self.gameloop.replay:
            if imgui.is_key_pressed(imgui.KEY_LEFT_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(-1, 0, 0)))

            if imgui.is_key_pressed(imgui.KEY_RIGHT_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(1, 0, 0)))

            if imgui.is_key_pressed(imgui.KEY_UP_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(0, -1, 0)))

            if imgui.is_key_pressed(imgui.KEY_DOWN_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(0, 1, 0)))

        if self.snake:
            if imgui.is_key_pressed(imgui.KEY_SPACE, repeat=False):
                self.focus_snake()

        if self.gameloop.replay:
            if imgui.is_key_pressed(imgui.KEY_LEFT_ARROW, repeat=True):
                self.config.timepoint = max(0, self.config.timepoint - 1)
                self.config.realtime = False

            if imgui.is_key_pressed(imgui.KEY_RIGHT_ARROW, repeat=True):
                self.config.timepoint = min(
                    len(self.wb.history) - 1, self.config.timepoint + 1
                )
                if self.config.timepoint == len(self.wb.history) - 1:
                    self.config.realtime = True

    def status_window(self):
        w = self.get_world_to_draw()

        imgui.text_disabled("Stts:")
        imgui.same_line()
        imgui.text(self.gameloop.upd.state)

        imgui.text_disabled("Turn:")
        imgui.same_line()
        imgui.text(f"{self.gameloop.upd.turn}")

        imgui.text_disabled("Timeout:")
        imgui.same_line()
        imgui.text(f"{self.gameloop.upd.timeout}")

        imgui.text_disabled("Scle:")
        imgui.same_line()
        imgui.text(f"{self.scale:.2f}")

        imgui.text_disabled("Mpix:")
        imgui.same_line()
        imgui.text(f"{self.mouse_pix}")

        if w:
            self.labeled("  KD", f"{w.revive_timeout}")

    def timers(self):
        for name, value in TIMERS.items():
            imgui.text_disabled(f"{name}:")
            imgui.same_line()
            imgui.text(f"{value*1000:.2f}ms")


def main(replay_file=None, *, upto: int = None):
    if replay_file:
        Super(replay_file=replay_file, upto=upto).start()
    else:
        rounds = api.rounds()
        rounds["rounds"] = [r for r in rounds["rounds"] if r["status"] != "ended"]

        actives = [r for r in rounds["rounds"] if r["status"] == "active"]

        if len(actives) == 0:
            pprint.pprint(rounds)
            print("No active games")

            now = datetime.fromisoformat(rounds["now"])
            closest = min(
                rounds["rounds"],
                key=lambda r: abs(datetime.fromisoformat(r["startAt"]) - now),
            )

            start_in = datetime.fromisoformat(closest["startAt"]) - now

            print(
                f"Next game: {closest['name']} at {closest['startAt']} (in {start_in})"
            )

            seconds = ceil(start_in.total_seconds())

            print(f"Sleeping for {seconds} seconds")
            sleep(seconds)
            return main()

        active = actives[0]

        name = active["name"]
        print(f"🚀 Playing round: {name}")

        m = parse_map(ApiClient("test").world())
        sup = Super(game_name=f"{name}-" + environ.get("USER", "dashik"), init=m)
        sup.start()


if __name__ == "__main__":
    Fire(main)
