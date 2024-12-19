from dataclasses import dataclass
from logging import basicConfig
from typing import NamedTuple

import imgui
import pygame
from fire import Fire

from draw import Brush, DrawWorld, key_handler, window
from gameloop import Gameloop
from util.itypes import Vec2

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


class Super(DrawWorld):
    def __init__(self, game_name=None, replay_file=None):
        super().__init__()

        self.gameloop = Gameloop(
            replay_file=replay_file,
            game_name=game_name,
        ).launch_async()

        self.wb = self.gameloop.world_builder
        self.config = Config()

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

    @key_handler(pygame.K_LEFT)
    def time_left(self, _):
        self.config.realtime = False
        self.config.timepoint = max(0, self.config.timepoint - 1)

    @key_handler(pygame.K_RIGHT)
    def time_right(self, _):
        self.config.realtime = False
        self.config.timepoint = min(self.config.timepoint + 1, len(self.wb.history) - 1)

    @key_handler(pygame.K_UP)
    def time_realtime(self, _):
        self.config.realtime = True

    def draw_world(self, brush: Brush):
        world = self.get_world_to_draw()

        for item in world.map:
            brush.image(self.fromgrid(item), "stone")

    def get_world_to_draw(self):
        if self.config.realtime:
            world, n = self.wb.get_latest_world()
            self.config.timepoint = n
            return world

        return self.wb.history[self.config.timepoint]

    def draw_ui(self):
        c = self.config

        timelen = len(self.wb.history)

        with window("Sacred Timeline"):
            changed, c.timepoint = imgui.slider_int(
                "Timepoint",
                c.timepoint,
                min_value=0,
                max_value=timelen - 1,
            )

            if changed:
                c.realtime = False
            _, c.realtime = imgui.checkbox("Realtime", c.realtime)


def main(replay_file=None):
    if replay_file:
        Super(replay_file=replay_file).start()
    else:
        Super(game_name="t__est1").start()


if __name__ == "__main__":
    Fire(main)
