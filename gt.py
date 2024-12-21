from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, List, Literal, NamedTuple, Optional

from util.itypes import Vec2

snakes = ["Abra", "Kadabra", "Bobra", "Vydra", "Tundra"][::-1]
id_to_name = {}


class Vec3d(NamedTuple):
    x: int
    y: int
    z: int

    def manh(self, other: "Vec3d") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)

    def len(self) -> float:
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    def distance(self, other: "Vec3d") -> float:
        return (self - other).len()

    def to2(self):
        return Vec2(self.x, self.y)

    def t2(self):
        return Vec2(self.x, self.y), self.z

    def __add__(self, other: "Vec3d") -> "Vec3d":
        return Vec3d(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3d") -> "Vec3d":
        return Vec3d(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, c: float) -> "Vec3d":
        return Vec3d(self.x * c, self.y * c, self.z * c)

    def __truediv__(self, c: float) -> "Vec3d":
        return Vec3d(self.x / c, self.y / c, self.z / c)

    def normalize(self) -> "Vec3d":
        if self == Vec3d(0, 0, 0):
            return self
        return self / self.len()

    def round(self):
        return Vec3d(round(self.x), round(self.y), round(self.z))

    def neighbors(self):
        # Orthogonal moves: up/down/left/right/forward/back in 3D
        # You can add more if diagonals or other moves are allowed.
        directions = [
            Vec3d(1, 0, 0),
            Vec3d(-1, 0, 0),
            Vec3d(0, 1, 0),
            Vec3d(0, -1, 0),
            Vec3d(0, 0, 1),
            Vec3d(0, 0, -1),
        ]
        for d in directions:
            yield self + d


@dataclass
class Snake:
    id: int
    direction: Vec3d
    old_direction: Vec3d
    geometry: List[Vec3d]
    death_count: int
    status: Literal["alive", "dead"]
    revive_remain_ms: Optional[int] = None

    def move_command(self, direction: Vec3d):
        return {"id": self.id, "direction": list(direction)}

    @property
    def head(self):
        if not self.geometry:
            return None
        return self.geometry[0]

    @property
    def body(self):
        if not self.geometry:
            return []
        return self.geometry[1:]

    @property
    def name(self):
        if self.id not in id_to_name:
            id_to_name[self.id] = snakes.pop()
        return f"{id_to_name[self.id]}#{self.id[:5]}"

    def __bool__(self):
        return self.status == "alive" and bool(self.geometry)

    def __eq__(self, other):
        return self.id == other.id


@dataclass
class EnemySnake:
    geometry: List[Vec3d]
    status: str
    kills: int

    @property
    def head(self):
        if not self.geometry:
            return None

        return self.geometry[0]

    @property
    def body(self):
        if not self.geometry:
            return []
        return self.geometry[1:]


@dataclass
class Food:
    coordinate: Vec3d
    points: int
    type: Literal["normal", "golden", "suspicious"]


@dataclass
class Map:
    size: Vec3d
    points: int
    name: str

    fences: List[Vec3d]

    food: List[Food]
    golden: List[Food]
    sus: List[Food]

    enemies: List[EnemySnake]

    snakes: List[Snake]
    turn: int
    tick_remain_ms: int
    revive_timeout: int


def parse_snake(data: Dict[str, Any]) -> Snake:
    return Snake(
        id=data["id"],
        direction=Vec3d(*data["direction"]),
        old_direction=Vec3d(*data["oldDirection"]),
        geometry=[Vec3d(*coord) for coord in data["geometry"]],
        death_count=data["deathCount"],
        status=data["status"],
        revive_remain_ms=data.get("reviveRemainMs"),
    )


def parse_enemy_snake(data: Dict[str, Any]) -> EnemySnake:
    return EnemySnake(
        geometry=[Vec3d(*coord) for coord in data["geometry"]],
        status=data["status"],
        kills=data["kills"],
    )


def parse_food(data: Dict[str, any]):
    return Food(coordinate=Vec3d(*data["c"]), points=data["points"], type="normal")


def parse_special_food(pos: tuple, type):
    return Food(coordinate=Vec3d(*pos), points=0, type=type)


@dataclass
class SnakeBrain:
    snake: Snake
    path: list[Vec3d]
    direction: Vec3d
    thinks: str = "I'm a snake"


# Helper functions to convert JSON into dataclasses
def parse_map(data: Dict[str, Any]) -> Map:
    return Map(
        size=Vec3d(*data["mapSize"]),
        name=data["name"],
        points=data["points"],
        #
        fences=[Vec3d(*fence) for fence in data["fences"]],
        #
        food=([parse_food(f) for f in data["food"]]),
        golden=[
            parse_special_food(f, "golden")
            for f in data.get("specialFood", {}).get("golden", [])
        ],
        sus=[
            parse_special_food(f, "suspicious")
            for f in data.get("specialFood", {}).get("suspicious", [])
        ],
        #
        turn=data["turn"],
        tick_remain_ms=data["tickRemainMs"],
        revive_timeout=data["reviveTimeoutSec"],
        #
        snakes=[parse_snake(snake) for snake in data["snakes"]],
        enemies=[parse_enemy_snake(enemy) for enemy in data["enemies"]],
    )


if __name__ == "__main__":
    example = {
        "mapSize": [180, 180, 30],
        "name": "CleanCrib envious",
        "points": 275,
        "fences": [[152, 51, 10]],
        "snakes": [
            {
                "id": "db59f7bff43351d69b540c666fa8ff9f1c81f05c",
                "direction": [1, 0, 0],
                "oldDirection": [0, 0, -1],
                "geometry": [[152, 51, 10]],
                "deathCount": 16,
                "status": "alive",
                "reviveRemainMs": 0,
            }
        ],
        "enemies": [{"geometry": [[152, 51, 10]], "status": "alive", "kills": 0}],
        "food": [{"c": [152, 51, 10], "points": 6}],
        "specialFood": {"golden": [[152, 51, 10]], "suspicious": [[152, 51, 10]]},
        "turn": 1548,
        "reviveTimeoutSec": 5,
        "tickRemainMs": 60,
        "errors": [],
    }

    data = parse_map(example)
    pprint(data)
