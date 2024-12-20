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
from gt import Map, Vec3d, parse_map
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


class Super(DrawWorld):
    def __init__(
        self,
        init: Map,
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

        self.head: Vec3d = None

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
        self.scale = 2

    #####
    ###################################

    def draw_world(self):
        brush = PixelBrush(self)
        world = self.get_world_to_draw()

        xy, z = world.size.t2()
        cz = self.config.current_z

        for snake in world.snakes:
            head, *tail = snake.geometry
            self.head = head

            v, z = head.t2()

            brush.square(self.fromgrid(v), Color.GOLD)
            for point in tail:
                v, z = point.t2()
                brush.square(self.fromgrid(v), Color.YELLOW)

        for enemy in world.enemies:
            head, *tail = enemy.geometry

            v, z = head.t2()
            brush.square(self.fromgrid(v), Color.RED)
            for point in tail:
                v, z = point.t2()
                brush.square(self.fromgrid(v), Color.RED)

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

            _, C.current_z = imgui.slider_float(
                "Z",
                C.current_z,
                min_value=0,
                max_value=w.size.z,
            )

    def imgui_keybindings(self):
        C = self.config

        if imgui.is_key_pressed(imgui.KEY_LEFT_ARROW, repeat=True):
            C.realtime = False
            C.timepoint = max(0, C.timepoint - 1)

        if imgui.is_key_pressed(imgui.KEY_RIGHT_ARROW, repeat=True):
            C.realtime = False
            C.timepoint = min(C.timepoint + 1, len(self.wb.history) - 1)
            if C.timepoint == len(self.wb.history) - 1:
                C.realtime = True

        if imgui.is_key_pressed(imgui.KEY_UP_ARROW, repeat=True):
            C.realtime = True

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
        m = parse_map(ApiClient("test").world())
        sup = Super(game_name="zero-" + environ["USER"], init=m)
        sup.start()


if __name__ == "__main__":
    Fire(main)
