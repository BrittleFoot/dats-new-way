from typing import NamedTuple

import pygame

from draw import Brush, DrawWorld, key_handler
from gameloop import Gameloop
from util.itypes import Vec2


class Point(NamedTuple):
    x: float
    y: float


class Game(DrawWorld):
    def __init__(self):
        super().__init__()
        self.gameloop = Gameloop().launch_async()

    def start(self):
        try:
            self.main_loop()
        except KeyboardInterrupt:
            pass

    @key_handler(pygame.K_SPACE)
    def reset_camera(self):
        self.offset = Vec2(0, 0)
        self.scale = 2

    def draw_world(self, brush: Brush):
        for item in self.gameloop.whole_world:
            brush.image(self.fromgrid(item), "stone")


if __name__ == "__main__":
    game = Game()
    game.start()
