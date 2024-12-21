import heapq
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
) -> Tuple[Dict[Vec3d, int], Dict[Vec3d, Vec3d]]:
    """
    Runs A* from 'start' to find paths to any of the 'goal_positions'.
    Returns:
      - gScore: dict of distance from start to each visited cell
      - came_from: to reconstruct path to any visited cell
    We'll continue searching until all goals are found (or the open set is empty).
    """

    # Convert goal_positions to a set for quick membership checks
    goal_set = set(goal_positions)

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

    while openSet:
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
        for neighbor in current.neighbors():
            if not is_valid_cell(neighbor, game_map):
                continue

            tentative_gScore = gScore[current] + 1  # cost 1 per move
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
) -> Optional[Vec3d]:
    """
    1. Filter food by radius (optional).
    2. Run A* from snake head to all goals (foods).
    3. Among the reachable foods, pick the best ratio = points/distance.
    4. Reconstruct path, return the first step's direction.
    """

    snake_head = snake.head
    # Combine normal + golden + suspicious
    all_foods = game_map.food + game_map.golden + game_map.sus

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
    gScore, came_from = a_star_multi_goal(snake_head, goal_positions, game_map)

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


def snake_ai_move_astar_multi(map_data: Map, snake: Snake) -> Dict:
    """
    Example function that picks a direction for our snake using multi-goal A*.
    """
    if not snake:
        return None

    direction, path, food = get_next_move_astar_multi(snake, map_data, radius=100)
    if not direction:
        # fallback
        return None

    return SnakeBrain(snake, path, direction, f"FOOD {food}")
