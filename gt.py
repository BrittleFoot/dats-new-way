from dataclasses import dataclass
from pprint import pprint
from typing import Any, Dict, List, Literal, NamedTuple, Optional


class Vec3d(NamedTuple):
    x: int
    y: int
    z: int

    def manh(self, other: "Vec3d") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)


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


@dataclass
class EnemySnake:
    geometry: List[Vec3d]
    status: str
    kills: int


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
    timeout: int


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
        geometry=[tuple(coord) for coord in data["geometry"]],
        status=data["status"],
        kills=data["kills"],
    )


def parse_food(data: Dict[str, any]):
    return Food(coordinate=Vec3d(*data["c"]), points=data["points"], type="normal")


def parse_special_food(pos: tuple, type):
    return Food(coordinate=Vec3d(*pos), points=0, type=type)


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
        timeout=data["reviveTimeoutSec"],
        #
        snakes=[parse_snake(snake) for snake in data["snakes"]],
        enemies=[parse_enemy_snake(enemy) for enemy in data["enemies"]],
    )


def command():
    return {
        "snakes": [
            {"id": "6c1dfac6d106e6f4d0ffdddb665238253574ac1f", "direction": [0, 0, 0]}
        ]
    }


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
