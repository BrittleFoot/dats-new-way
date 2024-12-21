import heapq
import time
from typing import Dict, List, Optional, Tuple

from gt import Food, Map, Snake, SnakeBrain, Vec3d


def is_valid_cell(pos: Vec3d, game_map: Map) -> bool:
    # Basic checks
    if not (0 <= pos.x < game_map.size.x):
        return False
    if not (0 <= pos.y < game_map.size.y):
        return False
    if not (0 <= pos.z < game_map.size.z):
        return False
    if pos in game_map.fences:
        return False
    # Potentially avoid snake bodies, enemies, etc.
    return True


def manhattan_3d(a: Vec3d, b: Vec3d) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z)


def multi_goal_heuristic(current: Vec3d, goals: List[Vec3d]) -> float:
    """
    For multi-goal A*, the heuristic to a set of goals
    can be the *minimum* distance from 'current' to any goal.
    """
    return min(manhattan_3d(current, g) for g in goals)


def a_star_multi_goal(
    start: Vec3d,
    goal_positions: List[Vec3d],
    game_map: Map,
    timeout: float,
    ignore: set,
) -> Tuple[Dict[Vec3d, int], Dict[Vec3d, Vec3d]]:
    """
    Runs A* from 'start' to find paths to any of the 'goal_positions'.
    Returns:
      - gScore: dict of distance from start to each visited cell
      - came_from: to reconstruct path to any visited cell
    We'll continue searching until all goals are found (or the open set is empty).
    """
    strt_t = time.perf_counter()

    # Convert goal_positions to a set for quick membership checks
    goal_set = set(goal_positions)

    bad_cells = set(game_map.fences)
    for snake in game_map.snakes:
        bad_cells.update(snake.geometry)

    for enemy in game_map.enemies:
        bad_cells.update(enemy.geometry)
        bad_cells.update(enemy.head.neighbors())

    ATTRACTOR = game_map.size / 2

    # Initialize
    gScore: Dict[Vec3d, float] = {}
    gScore[start] = 0

    fScore: Dict[Vec3d, float] = {}
    fScore[start] = multi_goal_heuristic(start, goal_positions)

    came_from: Dict[Vec3d, Vec3d] = {}

    openSet = []
    # push (fScore, node)
    heapq.heappush(openSet, (fScore[start], start))

    # Track how many distinct goals we've found
    found_goals = 0
    discovered_goals = {}

    while openSet and time.perf_counter() - strt_t < timeout:
        _, current = heapq.heappop(openSet)

        # If 'current' is a goal, record it
        if current in goal_set and current not in discovered_goals:
            discovered_goals[current] = gScore[current]
            found_goals += 1

            # If we've found them all, we could break now.
            # But if we want absolutely all distances (even to non-goal cells),
            # we'd keep going. Typically you can break if you're only interested
            # in the distances to goals. We'll do a check:
            if found_goals == len(goal_set):
                # We discovered all goals
                break

        # Explore neighbors
        neighbors = current.neighbors()
        # sort by angle to target
        neighbors = sorted(neighbors, key=lambda x: x.cos_to(ATTRACTOR))

        for neighbor in current.neighbors():
            if not is_valid_cell(neighbor, game_map):
                continue

            if neighbor in bad_cells:
                continue

            if neighbor in ignore:
                continue

            direction = neighbor - current
            dangerous_path = (neighbor + direction) in bad_cells

            center_cost = (
                2 * min(30, ATTRACTOR.distance(neighbor)) / game_map.size.len()
            )

            other_snake_cost = 0
            brother_mass = Vec3d(0, 0, 0)
            for brother in game_map.snakes:
                if brother and brother.head == start:
                    brother_mass = brother_mass + brother.head

            brother_mass = brother_mass * (1 / (len(game_map.snakes) - 1))
            to_brother = brother_mass - neighbor

            brother_cost = 1 - min(30, to_brother.len()) / 30

            cost = 1
            dangerous_path_cost = 1 if dangerous_path else 0

            tentative_gScore = (
                gScore[current]
                + cost
                + center_cost**2
                + dangerous_path_cost
                + brother_cost
            )
            old_gScore = gScore.get(neighbor, float("inf"))

            if tentative_gScore < old_gScore:
                came_from[neighbor] = current
                gScore[neighbor] = tentative_gScore
                fScore[neighbor] = tentative_gScore + multi_goal_heuristic(
                    neighbor, goal_positions
                )

                # If not in openSet, push with updated priority
                heapq.heappush(openSet, (fScore[neighbor], neighbor))

    return gScore, came_from


def pick_best_food_astar(
    goal_positions: List[Food], gScore: Dict[Vec3d, int]
) -> Optional[Food]:
    """
    Among all the food positions that appear in gScore,
    pick the one maximizing 'points / distance'.
    """
    best_food = None
    best_score = float("-inf")

    for f in goal_positions:
        if f.coordinate not in gScore:
            continue  # unreachable
        dist = gScore[f.coordinate]
        if dist == 0:
            # Food is right under the head
            return f
        score = f.points / dist
        if score > best_score:
            best_score = score
            best_food = f

    return best_food


def reconstruct_path(target: Vec3d, came_from: Dict[Vec3d, Vec3d]) -> List[Vec3d]:
    """
    Rebuild path from start -> target by following 'came_from' in reverse.
    """
    path = []
    current = target
    while current in came_from:
        path.append(current)
        current = came_from[current]

    # The last 'current' is the start (which won't be in came_from),
    # so include it manually:
    path.append(current)
    path.reverse()
    return path


def get_next_move_astar_multi(
    snake: Snake,
    game_map: Map,
    radius: int,
    timeout: float,
    ignore: set,
):
    """
    1. Filter food by radius (optional).
    2. Run A* from snake head to all goals (foods).
    3. Among the reachable foods, pick the best ratio = points/distance.
    4. Reconstruct path, return the first step's direction.
    """

    snake_head = snake.head
    # Combine normal + golden + suspicious
    all_foods = game_map.food

    # (Optional) pre-filter by Manhattan radius to reduce the goal set
    def manhattan_3d(a: Vec3d, b: Vec3d) -> int:
        return abs(a.x - b.x) + abs(a.y - b.y) + abs(a.z - b.z)

    candidate_food = [
        f
        for f in all_foods
        if manhattan_3d(snake_head, f.coordinate) <= radius and f.points > 0
    ]

    if not candidate_food:
        return None

    # Build a list of goal coordinates
    goal_positions = [f.coordinate for f in candidate_food]

    # 2. Run multi-goal A*
    gScore, came_from = a_star_multi_goal(
        snake_head,
        goal_positions,
        game_map,
        timeout,
        ignore,
    )

    # 3. Pick best ratio
    best_food = pick_best_food_astar(candidate_food, gScore)
    if not best_food:
        return None

    # 4. Reconstruct path
    path = reconstruct_path(best_food.coordinate, came_from)
    if len(path) < 2:
        # Means snake_head == best_food or no path
        return None

    # The first move is path[1] minus snake_head
    next_pos = path[1]
    direction = next_pos - snake_head
    return direction, path, best_food


def snake_ai_move_astar_multi(
    map_data: Map, snake: Snake, timeout, ignore
) -> SnakeBrain:
    """
    Example function that picks a direction for our snake using multi-goal A*.
    """
    if not snake:
        return None

    answer = get_next_move_astar_multi(
        snake, map_data, radius=40, timeout=timeout, ignore=ignore
    )
    if not answer:
        return None

    direction, path, food = answer

    return SnakeBrain(snake, path, direction, f"FOOD {(food.points, food.type)}")


def find_best_food_with_surrounding_value(map_data: Map, radius: int = 70):
    """
    Returns a tuple (best_food, best_sum) where:
      - best_food is the Food object that has the greatest
        "surrounding sum of points" (including itself) within 'radius'.
      - best_sum is that total sum of points.

    If there are no foods at all, returns (None, 0).
    """

    # Gather all foods (normal + golden + suspicious)
    all_foods = [f for f in map_data.food if f.points > 0]

    if not all_foods:
        return None, 0  # no food at all

    best_food = None
    best_value = float("-inf")

    # For each food f, sum the points of all foods g within distance <= radius
    for f in all_foods:
        surrounding_sum = 0
        for g in all_foods:
            if manhattan_3d(f.coordinate, g.coordinate) <= radius:
                surrounding_sum += g.points

        if surrounding_sum > best_value:
            best_value = surrounding_sum
            best_food = f

    return best_food, best_value


def calculate_surrounding_values(
    map_data: Map,
    radius: int = 30,
):
    """
    Returns a list of (food_item, total_sum) for each food in the map,
    where 'total_sum' is the sum of points of all foods within distance <= radius
    of that food (including itself).
    """

    # Gather all food items (normal, golden, suspicious) in a single list
    all_foods = [f for f in map_data.food if f.points > 0]

    # Prepare an output list
    results = []

    for f in all_foods:
        surrounding_sum = 0
        for g in all_foods:
            if manhattan_3d(f.coordinate, g.coordinate) <= radius:
                surrounding_sum += g.points
        results.append((surrounding_sum, f))

    return sorted(results, reverse=True, key=lambda x: x[0])
