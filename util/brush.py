import typing

import imgui

from util.itypes import Color, Vec2
from util.texture import get_texture_cached

if typing.TYPE_CHECKING:
    from draw import DrawWorld


class BrushyBrush:
    def __init__(self, drawer: "DrawWorld"):
        """
        Brush could be created only inside the BattleField window, segfault otherwise
        """
        self.drawer = drawer
        self.draw_list = imgui.get_window_draw_list()

        self.x0, self.y0 = imgui.get_window_position()
        self.zero = Vec2(self.x0, self.y0) + self.drawer.soffset

    def image_circle(
        self,
        center: Vec2,
        radius: float,
        name: str,
        color: Color = Color(1, 1, 1, 1),
        **kwargs,
    ):
        texture = get_texture_cached(name, **kwargs)

        a = center - radius
        b = center + radius

        start = a * self.drawer.scale
        end = b * self.drawer.scale

        self.draw_list.add_image(
            texture.texture_id,
            tuple(self.zero + start),
            tuple(self.zero + end),
            col=color.int(),
        )


class PixelBrush:
    def __init__(self, drawer: "DrawWorld"):
        """
        Brush could be created only inside the BattleField window, segfault otherwise
        """
        self.draw_list = imgui.get_window_draw_list()
        self.x0, self.y0 = imgui.get_window_position()
        self.zero = Vec2(self.x0, self.y0)
        self.drawer = drawer

    def square(self, center, color: Color = Color(1, 1, 1, 0.8)):
        a = center - self.drawer.size / 2
        b = center + self.drawer.size / 2

        self.draw_list.add_rect_filled(
            *(self.zero + a),
            *(self.zero + b),
            imgui.get_color_u32_rgba(*color),
        )

    def highlight(self, center, color: Color = Color(0.9, 1, 0.3, 0.5), **kwargs):
        a = center - self.drawer.size / 2
        b = center + self.drawer.size / 2
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
        size = scale_percent * self.drawer.size
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

    def arrow(self, a, b, color: Color = Color(1, 1, 1, 1), thickness=6):
        a = self.zero + a
        b = self.zero + b

        self.draw_list.add_line(
            a.x,
            a.y,
            b.x,
            b.y,
            imgui.get_color_u32_rgba(*color),
            thickness,
        )

    def rect(self, a, b, color: Color = Color(1, 1, 1, 1), thickness=1):
        a = self.zero + a
        b = self.zero + b

        self.draw_list.add_rect(
            a.x,
            a.y,
            b.x,
            b.y,
            imgui.get_color_u32_rgba(*color),
            thickness=thickness,
        )
