import heapq
from typing import Dict, List, Optional

from gt import Vec3d


def is_obstacle(v: Vec3d, fences, enemies):
    # Example: consider fences and enemies as obstacles.
    # This is a simple check. You may need to adapt it depending on your data structures.
    if v in fences:
        return True
    # Similarly check enemies:
    # If the coordinates occupied by enemies are blocked:
    enemy_positions = [seg for e in enemies for seg in e.geometry]
    if v in enemy_positions:
        return True
    return False


def in_bounds(v: Vec3d, SIZE):
    # Check that v is within the world boundaries: 0 <= x,y,z < SIZE
    return 0 <= v.x < SIZE.x and 0 <= v.y < SIZE.y and 0 <= v.z < SIZE.z


def a_star(start: Vec3d, goal: Vec3d, SIZE: Vec3d, fences: List[Vec3d], enemies: List):
    # Convert lists to sets for quick lookups
    fence_set = set(fences)

    # For simplicity, assume enemies is a list of EnemySnake objects, each with geometry as a list of Vec3d
    # Flatten enemy positions into a set
    enemy_positions = {seg for e in enemies for seg in e.geometry}

    # Priority queue for frontier
    # Each entry: (f_cost, g_cost, current_position)
    frontier = []
    heapq.heappush(frontier, (start.manh(goal), 0, start))

    came_from: Dict[Vec3d, Optional[Vec3d]] = {start: None}
    cost_so_far: Dict[Vec3d, int] = {start: 0}

    while frontier:
        _, g, current = heapq.heappop(frontier)

        if current == goal:
            # Reconstruct path
            path = []
            while current is not None:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path  # This is your found path

        for nxt in current.neighbors():
            if not in_bounds(nxt, SIZE):
                continue
            if nxt in fence_set or nxt in enemy_positions:
                continue

            new_cost = cost_so_far[current] + 1  # cost of moving to next cell
            if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                cost_so_far[nxt] = new_cost
                priority = new_cost + nxt.manh(goal)
                came_from[nxt] = current
                heapq.heappush(frontier, (priority, new_cost, nxt))

    # If we exit the loop, no path was found
    return None


# Example usage:
if __name__ == "__main__":
    SIZE = Vec3d(200, 200, 20)  # just an example size
    fences = [Vec3d(x=152, y=51, z=10)]  # Example fence

    # Example enemy with single segment
    class EnemySnake:
        def __init__(self, geometry, status, kills):
            self.geometry = geometry
            self.status = status
            self.kills = kills

    enemies = [EnemySnake(geometry=[Vec3d(152, 51, 10)], status="alive", kills=0)]

    start = Vec3d(5, 5, 5)
    goal = Vec3d(8, 8, 8)

    path = a_star(start, goal, SIZE, fences, enemies)
    if path:
        print("Path found!")
        for p in path:
            print(p.x, p.y, p.z)
    else:
        print("No path found.")
