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

from util.itypes import Color, Vec2
from util.texture import get_texture_cached


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


class Brush:
    def __init__(self, world: "DrawWorld"):
        """
        Brush could be created only inside the BattleField window, segfault otherwise
        """
        self.draw_list = imgui.get_window_draw_list()
        self.x0, self.y0 = imgui.get_window_position()
        self.zero = Vec2(self.x0, self.y0)
        self.world = world

    def square(self, center, color: Color = Color(1, 1, 1, 0.8)):
        a = center - self.world.size / 2
        b = center + self.world.size / 2

        self.draw_list.add_rect_filled(
            *(self.zero + a),
            *(self.zero + b),
            imgui.get_color_u32_rgba(*color),
        )

    def highlight(self, center, color: Color = Color(0.9, 1, 0.3, 0.5), **kwargs):
        a = center - self.world.size / 2
        b = center + self.world.size / 2
        kwargs.setdefault("thickness", 2)
        kwargs.setdefault("rounding", 3)

        self.draw_list.add_rect(
            *(self.zero + a),
            *(self.zero + b),
            imgui.get_color_u32_rgba(*color),
            **kwargs,
        )

    def image(
        self,
        center,
        name,
        color: Color = Color(1, 1, 1, 1),
        offset_percent=Vec2(0, 0),
        scale_percent=Vec2(1, 1),
        **kwargs,
    ):
        size = scale_percent * self.world.size
        a = Vec2(*center) - size / 2 + offset_percent * size
        b = Vec2(*center) + size / 2 + offset_percent * size

        texture = get_texture_cached(name, **kwargs)

        start = self.zero + a
        end = self.zero + b

        self.draw_list.add_image(
            texture.texture_id,
            tuple(start),
            tuple(end),
            col=imgui.get_color_u32_rgba(*color),
        )


key_handlers = defaultdict(list)
mouse_handlers = defaultdict(list)


def key_handler(key, mod=0):
    def decorator(func):
        key_handlers[(key, mod)].append(func)
        return func

    return decorator


def mouse_handler(button):
    def decorator(func):
        mouse[button].append(func)
        return func

    return decorator


class DrawWorld:
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

        self.mouse_at = Vec2(0, 0)  # mouse grid position

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

        mouse = self.window_mouse_pos - self.window_pos
        self.offset = self.offset + mouse * (1 / self.scale - 1 / (self.scale - speed))

    @property
    def offset_grid(self):
        return self.soffset // self.size

    def togrid(self, screen_coords):
        centered_vec = Vec2(*screen_coords) + self.size / 2 - self.offset_snap
        return centered_vec // self.size - self.offset_grid

    def fromgrid(self, grid_coords):
        return Vec2(*grid_coords) * self.size + self.soffset

    def status_window(self):
        with color(imgui.COLOR_CHILD_BACKGROUND, Color(0.1, 0.2, 0.1, 0.7)):
            with child("State", border=True, width=180, height=100):
                imgui.text_disabled("Turn:")
                imgui.same_line()
                imgui.text(f"{self.gameloop.turn}")

                imgui.text_disabled("Next:")
                imgui.same_line()
                imgui.text(f"{self.gameloop.next_time:.2f}")

                imgui.text_disabled("Ofst:")
                imgui.same_line()
                imgui.text(f"{self.offset}")

                imgui.text_disabled("Scle:")
                imgui.same_line()
                imgui.text(f"{self.scale:.2f}")

                imgui.text_disabled("Mise:")
                imgui.same_line()
                imgui.text(f"{self.mouse_at}")

    def main_loop(self):
        while self.running:
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
                self.window_mouse_pos = Vec2(*imgui.get_mouse_pos())

                self.mouse_at = self.togrid(self.get_win_mouse_pos())

                while self.handler_queue:
                    handler, *args = self.handler_queue.popleft()
                    handler(self, *args)

                brush = Brush(self)

                brush.image(self.fromgrid((0, 0)), "snowman_happy")
                brush.image(self.fromgrid((6, 6)), "snowman_angry")
                brush.image(self.fromgrid((5, 6)), "santa")
                brush.image(self.fromgrid((4, 6)), "dirt")
                brush.image(self.fromgrid((3, 6)), "dirt")
                brush.image(self.fromgrid((2, 6)), "grinch")

                self.draw_world(brush)

                self.status_window()

                x, y = self.get_win_mouse_pos()

                brush.highlight(
                    self.fromgrid(self.mouse_at),
                    color=Color.BLACK,
                    thickness=3,
                )
                brush.highlight(self.fromgrid(self.mouse_at))
                brush.image(
                    self.fromgrid(self.mouse_at),
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

            ###############################
            self.clear_render()

    def draw_world(self, brush: Brush):
        """Override this method to draw the world"""
        pass

    def draw_ui(self):
        """Override this method to draw the UI"""
        pass


if __name__ == "__main__":
    DrawWorld().main_loop()
