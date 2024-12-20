from dataclasses import dataclass
from logging import basicConfig
from os import environ
from typing import NamedTuple

import imgui
import pygame
from fire import Fire

from client import ApiClient
from draw import DrawWorld, key_handler, window
from gameloop import Gameloop
from gt import Map, Snake, Vec3d, parse_map
from util.brush import PixelBrush
from util.itypes import Color, Vec2

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

    current_z = 0
    fade = 0.05


class Super(DrawWorld):
    def __init__(
        self,
        init: Map = None,
        game_name=None,
        replay_file=None,
    ):
        super().__init__()

        self.gameloop = Gameloop(
            replay_file=replay_file,
            game_name=game_name,
            init=init,
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

    @key_handler(pygame.K_SPACE)
    def reset_camera(self, _):
        self.offset = Vec2(0, 0)
        if self.snake:
            self.offset = (
                -self.snake.head.to2() * self.S + self.window_size / 2 / self.scale
            )
        # self.scale = 2

    #####
    ###################################

    def draw_world(self):
        brush = PixelBrush(self)
        world = self.get_world_to_draw()

        xy, z = world.size.t2()

        if self.snake:
            self.config.current_z = self.snake.head.z

        cz = self.config.current_z

        hide = lambda z: self.config.fade if z != cz else 1

        for snake in world.snakes:
            if not snake.geometry:
                continue

            v, z = snake.head.t2()

            if self.snake and snake.id == self.snake.id:
                brush.image(
                    self.fromgrid(v), "snowman_happy", color=Color.GREEN.but(a=hide(z))
                )
            else:
                brush.square(self.fromgrid(v), Color.GOLD.but(a=hide(z)))

            for point in snake.body:
                v, z = point.t2()
                brush.square(self.fromgrid(v), Color.YELLOW.but(a=hide(z)))

        for enemy in world.enemies:
            if not enemy.geometry:
                continue

            v, z = enemy.head.t2()
            brush.square(self.fromgrid(v), Color.RED.but(a=hide(z)))
            for point in enemy.body:
                v, z = point.t2()
                brush.square(self.fromgrid(v), Color.PINK.but(a=hide(z)))

        for food in world.food:
            v, z = food.coordinate.t2()
            brush.image(self.fromgrid(v), "gift", color=Color.WHITE.but(a=hide(z)))

        for food in world.golden:
            v, z = food.coordinate.t2()
            brush.image(self.fromgrid(v), "gift2", color=Color.WHITE.but(a=hide(z)))

        for food in world.sus:
            v, z = food.coordinate.t2()
            brush.image(self.fromgrid(v), "hat", color=Color.WHITE.but(a=hide(z)))

        for fence in world.fences:
            v, z = fence.t2()
            brush.square(self.fromgrid(v), Color.WHITE.but(a=hide(z)))

    ###################################
    #####

    def get_world_to_draw(self):
        if self.config.realtime:
            world, n = self.wb.get_latest_world()
            self.config.timepoint = n
            return world

        return self.wb.history[self.config.timepoint]

    def draw_ui(self):
        self.imgui_keybindings()

        w = self.get_world_to_draw()

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

        with window("Snakes"):
            for snake in w.snakes:
                if self.snake and snake.id == self.snake.id:
                    imgui.text_colored("You", 0, 255, 0)

                imgui.text(f"Snake: {snake.id[:5]}...")
                imgui.text(f"Length: {len(snake.geometry)}")
                imgui.text(f"Status: {snake.status}")
                imgui.text(f"Head: {snake.head}")

                if imgui.button(f"Focus #{snake.id}"):
                    self.snake = snake

                imgui.separator()

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

    def imgui_keybindings(self):
        C = self.config

        if self.snake:
            if imgui.is_key_pressed(imgui.KEY_LEFT_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(-1, 0, 0)))

            if imgui.is_key_pressed(imgui.KEY_RIGHT_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(1, 0, 0)))

            if imgui.is_key_pressed(imgui.KEY_UP_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(0, -1, 0)))

            if imgui.is_key_pressed(imgui.KEY_DOWN_ARROW, repeat=False):
                self.gameloop.add_command(self.snake.move_command(Vec3d(0, 1, 0)))

    def status_window(self):
        imgui.text_disabled("Turn:")
        imgui.same_line()
        imgui.text(f"{self.config.timepoint}")
        imgui.same_line()
        imgui.text_disabled(f"out of {len(self.wb.history) - 1}")

        imgui.text_disabled("Ofst:")
        imgui.same_line()
        imgui.text(f"{self.offset}")

        imgui.text_disabled("Scle:")
        imgui.same_line()
        imgui.text(f"{self.scale:.2f}")

        imgui.text_disabled("Mise:")
        imgui.same_line()
        imgui.text(f"{self.window_mouse_pos}")

        imgui.text_disabled("Mpix:")
        imgui.same_line()
        imgui.text(f"{self.mouse_pix}")


def main(replay_file=None):
    if replay_file:
        Super(replay_file=replay_file).start()
    else:
        rounds = ApiClient("test").rounds()

        actives = [r for r in rounds["rounds"] if r["status"] == "active"]

        if len(actives) == 0:
            print("No active games")
            return

        active = actives[0]

        name = active["name"]
        print(f"🚀 Playing round: {name}")

        m = parse_map(ApiClient("test").world())
        sup = Super(game_name=f"{name}-" + environ.get("USER", "dashik"), init=m)
        sup.start()


if __name__ == "__main__":
    Fire(main)
