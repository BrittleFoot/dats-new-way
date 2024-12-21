import heapq
import time
from typing import Dict, List, Optional

from gt import Food, Map, Snake, SnakeBrain, Vec3d


def in_bounds(v: Vec3d, SIZE):
    # Check that v is within the world boundaries: 0 <= x,y,z < SIZE
    return 0 <= v.x < SIZE.x and 0 <= v.y < SIZE.y and 0 <= v.z < SIZE.z


DEPTH = 2000


def a_star(
    start: Vec3d,
    goal: Vec3d,
    SIZE: Vec3d,
    fences: List[Vec3d],
    enemies: List,
    timeout,
):
    ATTRACTOR = SIZE / 2

    # Convert lists to sets for quick lookups
    fence_set = set(fences) - {start, goal}

    # For simplicity, assume enemies is a list of EnemySnake objects, each with geometry as a list of Vec3d
    # Flatten enemy positions into a set
    enemy_positions = {seg for e in enemies for seg in e.geometry} - {start, goal}

    bad_cells = fence_set | enemy_positions

    # Priority queue for frontier
    # Each entry: (f_cost, g_cost, current_position)
    frontier = []
    heapq.heappush(frontier, (start.manh(goal), 0, start))

    came_from: Dict[Vec3d, Optional[Vec3d]] = {start: None}
    cost_so_far: Dict[Vec3d, int] = {start: 0}

    start_time = time.perf_counter()

    while (
        frontier
        and time.perf_counter() - start_time < timeout
        and len(frontier) < DEPTH
    ):
        _, g, current = heapq.heappop(frontier)

        if current == goal:
            # Reconstruct path
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path  # This is your found path

        neighbors = current.neighbors()
        neighbors = sorted(neighbors, key=lambda x: x.cos_to(ATTRACTOR))

        for nxt in neighbors:
            if not in_bounds(nxt, SIZE):
                continue
            if nxt in fence_set or nxt in enemy_positions:
                continue

            # cost of moving to next cell is less if it is closer to the center
            direction = nxt - current
            dangerous_path = (nxt + direction) in bad_cells

            center_cost = 2 * ATTRACTOR.distance(nxt) / SIZE.len()
            cost = 1
            dangerous_path_cost = 1 if dangerous_path else 0

            full_cost = cost + center_cost**2 + dangerous_path_cost

            new_cost = cost_so_far[current] + full_cost
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                priority = new_cost + nxt.manh(goal)
                came_from[nxt] = current
                heapq.heappush(frontier, (priority, new_cost, nxt))

    # If we exit the loop, no path was found
    return None


def find_path(map: Map, start: Vec3d, goal: Vec3d, timeout: float):
    # Example usage:
    SIZE = map.size
    fences = map.fences
    enemies = map.snakes + map.enemies

    return a_star(start, goal, SIZE, fences, enemies, timeout)


def find_path_brain(map: Map, snake: Snake, goal: Vec3d, timeout: float, label: str):
    # Example usage:
    SIZE = map.size
    fences = map.fences
    enemies = map.snakes + map.enemies

    if not snake.geometry:
        return None

    path = a_star(snake.head, goal, SIZE, fences, enemies, timeout)
    if not path:
        return None

    direction = path[1] - path[0]
    return SnakeBrain(snake=snake, path=path, direction=direction, thinks=label)


def sort_food_by_distance(game_map: Map, snake: Snake) -> list[Food]:
    """
    Returns a list of all food (normal, golden, suspicious) sorted
    by their distance to the given snake’s head.
    """
    # Snake’s head position
    if not snake.geometry:
        return []

    ATTRACTOR = game_map.size / 2

    snake_head = snake.geometry[0]

    # Combine all types of food into a single list if desired
    all_food = game_map.food

    def food_distance(food: Food):
        # Sort by distance, using the manhattan distance defined in Vec3d
        if food.points <= 0:
            return 2**31

        mod = 1
        if food.type == "golden":
            mod = 0.5

        return (
            snake_head.manh(food.coordinate)
            + ATTRACTOR.distance(food.coordinate) ** 2 / ATTRACTOR.x * mod
        )

    # Sort by distance, using the manhattan distance defined in Vec3d
    sorted_food = sorted(all_food, key=food_distance)
    return sorted_food


def sort_food_by_price(game_map: Map, snake: Snake, radius) -> list[Food]:
    """
    Returns a list of all food (normal, golden, suspicious) sorted
    by their points.
    """
    # Combine all types of food into a single list if desired
    all_food = game_map.food

    all_food = [
        food for food in all_food if snake.head.distance(food.coordinate) <= radius
    ]

    # Sort by points
    sorted_food = sorted(all_food, key=lambda food: food.points, reverse=True)
    return sorted_food
