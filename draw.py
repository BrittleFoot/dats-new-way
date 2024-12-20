#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys
from collections import defaultdict, deque
from contextlib import contextmanager

import imgui
import OpenGL.GL as gl
import pygame
from imgui.integrations.pygame import PygameRenderer

from gameloop import Gameloop
from util.brush import PixelBrush
from util.itypes import Color, Vec2


@contextmanager
def window(name, **kwargs):
    imgui.begin(name, **kwargs)
    try:
        yield
    finally:
        imgui.end()


@contextmanager
def child(name, **kwargs):
    imgui.begin_child(name, **kwargs)
    try:
        yield
    finally:
        imgui.end_child()


@contextmanager
def color(what, color: Color):
    imgui.push_style_color(what, *color)
    try:
        yield
    finally:
        imgui.pop_style_color()


SIZE = 16
HSIZE = SIZE // 2


key_handlers = defaultdict(list)
mouse_handlers = defaultdict(list)


def key_handler(key, mod=0):
    def decorator(func):
        key_handlers[(key, mod)].append(func)
        return func

    return decorator


def mouse_handler(button):
    def decorator(func):
        mouse_handlers[button].append(func)
        return func

    return decorator


class DrawWorld:
    gameloop: Gameloop

    def __init__(self):
        pygame.init()
        self.WIN_SIZE = Vec2(1344, 768)

        pygame.display.set_mode(self.WIN_SIZE, pygame.DOUBLEBUF | pygame.OPENGL)

        imgui.create_context()
        self.impl = PygameRenderer()
        self.io = imgui.get_io()
        self.io.display_size = self.WIN_SIZE

        self.handler_queue = deque()

        self.running = True
        #
        self.init_ui()
        #

    def init_ui(self):
        self.scale_speed = 0.1
        self.scale_max = 10

        self.scale = 2
        self.offset = Vec2(0, 0)

        self.window_pos = Vec2(0, 0)
        self.window_size = Vec2(0, 0)
        self.window_mouse_pos = Vec2(0, 0)
        self.window_mouse_raw = Vec2(0, 0)

        self.mouse_pix = Vec2(0, 0)  # mouse grid position

    @property
    def vscale(self):
        return Vec2(self.scale, self.scale)

    @property
    def S(self):
        return Vec2(SIZE, SIZE)

    @property
    def size(self):
        return SIZE * self.scale

    @property
    def soffset(self):
        """Scaled offset"""
        return self.offset * self.scale

    @property
    def offset_snap(self):
        return (self.soffset) % self.size

    def get_win_mouse_pos(self):
        mouse = Vec2(*imgui.get_mouse_pos())
        zero = Vec2(*imgui.get_window_position())

        return mouse - zero

    def handle_system_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                key = (event.key, event.mod)
                if key in key_handlers:
                    for handler in key_handlers[key]:
                        self.handler_queue.append((handler, event))

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.zoom_wheel(event)

            # todo: drag handler

            if event.type == pygame.MOUSEBUTTONDOWN:
                pass

            if event.type == pygame.MOUSEMOTION:
                pass

            if event.type == pygame.MOUSEBUTTONUP:
                pass

            self.impl.process_event(event)
        self.impl.process_inputs()

    def clear_render(self):
        gl.glClearColor(0, 0, 0, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)
        imgui.render()
        self.impl.render(imgui.get_draw_data())
        pygame.display.flip()

    def zoom_wheel(self, event):
        if event.button == pygame.BUTTON_WHEELDOWN:
            self.zoom_out(event)
        if event.button == pygame.BUTTON_WHEELUP:
            self.zoom_in(event)

    @key_handler(pygame.K_MINUS)
    def zoom_out(self, event):
        if self.scale < self.scale_speed * 2:
            return

        return self.zoom(-self.scale_speed * self.scale / 2)

    @key_handler(pygame.K_EQUALS)
    def zoom_in(self, event):
        if self.scale >= self.scale_max:
            return

        return self.zoom(self.scale_speed * self.scale / 2)

    def zoom(self, speed):
        self.scale = max(self.scale_speed, min(self.scale_max, self.scale + speed))

        mouse = self.window_mouse_raw - self.window_pos
        self.offset = self.offset + mouse * (1 / self.scale - 1 / (self.scale - speed))

    @property
    def offset_grid(self):
        return self.soffset // self.size

    def togrid(self, screen_coords):
        centered_vec = Vec2(*screen_coords) + self.size / 2 - self.offset_snap
        return centered_vec // self.size - self.offset_grid

    def fromgrid(self, grid_coords):
        return Vec2(*grid_coords) * self.size + self.soffset

    def main_loop(self):
        while self.running and self.gameloop.running:
            self.handle_system_events()

            imgui.new_frame()

            if imgui.is_mouse_dragging(imgui.BUTTON_MOUSE_BUTTON_RIGHT):
                x, y = imgui.get_mouse_drag_delta(imgui.BUTTON_MOUSE_BUTTON_RIGHT)
                self.offset = self.offset + Vec2(x, y) * (1 / self.scale)
                imgui.reset_mouse_drag_delta(imgui.BUTTON_MOUSE_BUTTON_RIGHT)

            bf_part = 0.7
            cf_part = 1 - bf_part
            win = self.WIN_SIZE

            imgui.set_next_window_size(*(win * Vec2(bf_part, 1) - 2 * SIZE))
            imgui.set_next_window_position(*(self.S + Vec2(win.x * cf_part, 0)))

            with window("Battlefield", flags=imgui.WINDOW_NO_TITLE_BAR):
                self.window_pos = Vec2(*imgui.get_window_position())
                self.window_size = Vec2(*imgui.get_window_size())
                self.window_mouse_raw = Vec2(*imgui.get_mouse_pos())
                self.window_mouse_pos = (
                    self.get_win_mouse_pos() - self.soffset
                ) / self.scale

                self.mouse_pix = self.togrid(self.get_win_mouse_pos())

                while self.handler_queue:
                    handler, *args = self.handler_queue.popleft()
                    handler(self, *args)

                pix = PixelBrush(self)

                pix.image(self.fromgrid((0, 0)), "snowman_happy")

                self.draw_world()

                self._status_window()

                x, y = self.get_win_mouse_pos()

                pix.highlight(
                    self.fromgrid(self.mouse_pix),
                    color=Color.BLACK,
                    thickness=3,
                )
                pix.highlight(self.fromgrid(self.mouse_pix))
                pix.image(
                    self.fromgrid(self.mouse_pix),
                    "cursor",
                    offset_percent=Vec2(0.5, 0.5),
                    scale_percent=Vec2(1, 1) * (4 / self.scale),
                    color=Color.WHITE.but(a=0.8),
                    smooth=True,
                )

            with window("Camera Controls"):
                if imgui.button("Reset Scale"):
                    self.scale = 2
                imgui.same_line()
                if imgui.button("Reset Offset"):
                    self.offset = Vec2(0, 0)

            self.draw_ui()

            ###############################
            self.clear_render()

    def _status_window(self):
        with color(imgui.COLOR_CHILD_BACKGROUND, Color(0.1, 0.2, 0.1, 0.7)):
            with child("State", border=True, width=180, height=100):
                self.status_window()

    def status_window(self):
        """Override this method to draw the status window"""
        pass

    def draw_world(self):
        """Override this method to draw the world"""
        pass

    def draw_ui(self):
        """Override this method to draw the UI"""
        pass


if __name__ == "__main__":
    DrawWorld().main_loop()
