import heapq
import math
import matplotlib.pyplot as plt

class Node:
    """Represents a node in the grid."""
    def __init__(self, x, y, cost=0, parent=None):
        self.x = x
        self.y = y
        self.cost = cost
        self.parent = parent

    def __lt__(self, other):
        return self.cost < other.cost

def heuristic(node, goal):
    """Heuristic function: Euclidean distance."""
    return math.sqrt((node.x - goal.x) ** 2 + (node.y - goal.y) ** 2)

def a_star(start, goal, obstacles, grid_size):
    """A* pathfinding algorithm with additional checks to avoid infinite loops"""
    open_list = []
    closed_list = set()
    heapq.heappush(open_list, (0, start))

    while open_list:
        # Pop the node with the smallest cost
        _, current_node = heapq.heappop(open_list)
        print(f"Exploring Node: ({current_node.x}, {current_node.y})")

        # Check if the current node is the goal
        if (current_node.x, current_node.y) == (goal.x, goal.y):
            print("Goal reached!")
            path = []
            while current_node:
                path.append((current_node.x, current_node.y))
                current_node = current_node.parent
            return path[::-1]  # Return the path in the correct order

        # Add current node to closed list
        closed_list.add((current_node.x, current_node.y))

        # Explore neighbors
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:  # Up, Down, Left, Right
            neighbor_x, neighbor_y = current_node.x + dx, current_node.y + dy

            # Skip out-of-bounds neighbors
            if not (0 <= neighbor_x < grid_size[0] and 0 <= neighbor_y < grid_size[1]):
                continue

            # Skip obstacles or already processed nodes
            if (neighbor_x, neighbor_y) in obstacles or (neighbor_x, neighbor_y) in closed_list:
                print(f"Skipping Node: ({neighbor_x}, {neighbor_y}) - Obstacle or Already Processed")
                continue

            # Calculate the neighbor's cost and heuristic
            neighbor = Node(neighbor_x, neighbor_y, current_node.cost + 1, current_node)
            neighbor.cost += heuristic(neighbor, goal)

            # Skip adding neighbors already in the open list with a lower cost
            if any(neighbor_x == n.x and neighbor_y == n.y and neighbor.cost >= n.cost for _, n in open_list):
                print(f"Skipping Node: ({neighbor_x}, {neighbor_y}) - Already in Open List with Lower Cost")
                continue

            print(f"Adding Node: ({neighbor_x}, {neighbor_y}) with Cost: {neighbor.cost}")
            heapq.heappush(open_list, (neighbor.cost, neighbor))

    print("No path found!")  # If we exhaust the open list, no path exists
    return None

# Example Usage
grid_size = (10, 10)  # Define grid dimensions
obstacles = {(3, 3), (3, 4), (3, 5), (4, 5), (5, 5)}  # Obstacles on the grid
start = Node(0, 0)  # Start node
goal = Node(7, 7)  # Goal node

path = a_star(start, goal, obstacles, grid_size)

# Visualization
def visualize_path(grid_size, obstacles, path):
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.set_xlim(-1, grid_size[0])
    ax.set_ylim(-1, grid_size[1])
    ax.set_xticks(range(grid_size[0]))
    ax.set_yticks(range(grid_size[1]))
    ax.grid(which="both", color="gray", linestyle="--", linewidth=0.5)

    # Plot obstacles
    for obs in obstacles:
        ax.scatter(obs[0], obs[1], color="red", s=100, label="Obstacle" if 'Obstacle' not in ax.get_legend_handles_labels()[1] else "")

    # Plot path
    if path:
        path_x, path_y = zip(*path)
        ax.plot(path_x, path_y, color="blue", linewidth=2, label="Path")
        ax.scatter(path_x, path_y, color="blue", s=50)

    # Start and goal points
    ax.scatter(start.x, start.y, color="green", s=200, label="Start")
    ax.scatter(goal.x, goal.y, color="orange", s=200, label="Goal")

    ax.legend()
    ax.set_title("A* Pathfinding with obstacles")
    plt.show()

if path:
    print("Path Found:", path)
    visualize_path(grid_size, obstacles, path)
else:
    print("No path could be found.")
