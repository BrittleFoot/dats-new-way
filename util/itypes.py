from typing import NamedTuple

import imgui


class Vec2(NamedTuple):
    x: float
    y: float

    def __add__(self, other: "Vec2 | float") -> "Vec2":
        if isinstance(other, Vec2) or hasattr(other, "__iter__") == 2:
            x, y = other
            return Vec2(self.x + x, self.y + y)

        return Vec2(self.x + other, self.y + other)

    def __sub__(self, other: "Vec2 | float") -> "Vec2":
        if isinstance(other, Vec2) or hasattr(other, "__iter__") == 2:
            x, y = other
            return Vec2(self.x - x, self.y - y)

        return Vec2(self.x - other, self.y - other)

    def __mul__(self, other: float) -> "Vec2":
        if isinstance(other, Vec2) or hasattr(other, "__iter__") == 2:
            x, y = other
            return Vec2(self.x * x, self.y * y)

        return Vec2(self.x * other, self.y * other)

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x / scalar, self.y / scalar)

    def __floordiv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x // scalar, self.y // scalar)

    def __mod__(self, scalar: float) -> "Vec2":
        return Vec2(self.x % scalar, self.y % scalar)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def magnitude(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5

    def normalize(self) -> "Vec2":
        mag = self.magnitude()
        if mag == 0:
            return Vec2(0, 0)
        return Vec2(self.x / mag, self.y / mag)

    @staticmethod
    def ONE() -> "Vec2":
        return Vec2(1, 1)

    @staticmethod
    def ZERO() -> "Vec2":
        return Vec2(0, 0)


class Color(NamedTuple):
    r: float
    g: float
    b: float
    a: float

    def int(self) -> int:
        return imgui.get_color_u32_rgba(*self)
