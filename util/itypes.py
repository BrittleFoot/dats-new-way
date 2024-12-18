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

    def add(self, other: "Vec2 | float") -> "Vec2":
        return self + other

    def sub(self, other: "Vec2 | float") -> "Vec2":
        return self - other

    def __sub__(self, other: "Vec2 | float") -> "Vec2":
        if isinstance(other, Vec2) or hasattr(other, "__iter__") == 2:
            x, y = other
            return Vec2(self.x - x, self.y - y)

        return Vec2(self.x - other, self.y - other)

    def __mul__(self, other: "Vec2 | float") -> "Vec2":
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

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def dot(self, other: "Vec2") -> float:
        return self.x * other.x + self.y * other.y

    def len(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5

    def distance(self, other: "Vec2") -> float:
        return (self - other).len()

    def in_radius(self, other: "Vec2", radius: float) -> bool:
        return (self - other).len() < radius

    def __abs__(self) -> float:
        return self.len()

    def normalize(self) -> "Vec2":
        mag = self.len()
        if mag == 0:
            return Vec2(0, 0)
        return Vec2(self.x / mag, self.y / mag)

    @staticmethod
    def ONE() -> "Vec2":
        return Vec2(1, 1)

    @staticmethod
    def ZERO() -> "Vec2":
        return Vec2(0, 0)

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"


class Color(NamedTuple):
    r: float
    g: float
    b: float
    a: float

    def int(self) -> int:
        return imgui.get_color_u32_rgba(*self)

    def but(self, **kwargs) -> "Color":
        """
        Return a new color with the given values updated

        usage:
        color = COLOR.RED.but(a=0.5)
        """
        return Color(**{**self._asdict(), **kwargs})

    WHITE = None
    BLACK = None
    RED = None
    GREEN = None
    BLUE = None
    YELLOW = None
    CYAN = None
    MAGENTA = None
    TRANSPARENT = None
    GRAY = None
    LIGHT_GRAY = None
    DARK_GRAY = None
    BROWN = None
    ORANGE = None
    PINK = None
    PURPLE = None
    LIME = None
    TEAL = None
    AQUA = None
    OLIVE = None
    MAROON = None
    NAVY = None
    TEAL = None
    SILVER = None
    GOLD = None
    BRONZE = None
    COPPER = None
    PLATINUM = None


Color.WHITE = Color(1, 1, 1, 1)
Color.BLACK = Color(0, 0, 0, 1)
Color.RED = Color(1, 0, 0, 1)
Color.GREEN = Color(0, 1, 0, 1)
Color.BLUE = Color(0, 0, 1, 1)
Color.YELLOW = Color(1, 1, 0, 1)
Color.CYAN = Color(0, 1, 1, 1)
Color.MAGENTA = Color(1, 0, 1, 1)
Color.TRANSPARENT = Color(0, 0, 0, 0)
Color.GRAY = Color(0.5, 0.5, 0.5, 1)
Color.LIGHT_GRAY = Color(0.75, 0.75, 0.75, 1)
Color.DARK_GRAY = Color(0.25, 0.25, 0.25, 1)
Color.BROWN = Color(0.6, 0.3, 0, 1)
Color.ORANGE = Color(1, 0.5, 0, 1)
Color.PINK = Color(1, 0.6, 0.6, 1)
Color.PURPLE = Color(0.6, 0, 0.6, 1)
Color.LIME = Color(0.5, 1, 0, 1)
Color.TEAL = Color(0, 0.5, 0.5, 1)
Color.AQUA = Color(0, 1, 1, 1)
Color.OLIVE = Color(0.5, 0.5, 0, 1)
Color.MAROON = Color(0.5, 0, 0, 1)
Color.NAVY = Color(0, 0, 0.5, 1)
Color.TEAL = Color(0, 0.5, 0.5, 1)
Color.SILVER = Color(0.75, 0.75, 0.75, 1)
Color.GOLD = Color(1, 0.84, 0, 1)
Color.BRONZE = Color(0.8, 0.5, 0.2, 1)
Color.COPPER = Color(0.72, 0.45, 0.2, 1)
Color.PLATINUM = Color(0.9, 0.9, 0.9, 1)
