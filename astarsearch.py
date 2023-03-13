import numpy as np
from heapq import heappush, heappop

class PriorityQueue:
    
    def __init__(self, iterable=[]):
        self.heap = []
        for value in iterable:
            heappush(self.heap, (0, value))
    
    def add(self, value, priority=0):
        heappush(self.heap, (priority, value))
    
    def pop(self):
        priority, value = heappop(self.heap)
        return value
    
    def __len__(self):
        return len(self.heap)

def Astar_search (start, goal, grid):
    visited = set()
    path_from = dict()
    distance = {start: 0}
    
    frontier = PriorityQueue()
    frontier.add(start)
    
    while frontier:
        node = frontier.pop()
        if node in visited:
            # Skip this node if visited
            continue

        if is_goal (node, goal):
            # Return since we have found the goal
            return backtrack (path_from, start, node)
        # Otherwise add the node to the visited set
        visited.add (node)

        # Generate the successors and compute their respective distances, paths and priorities
        successors = get_successors (node, grid)
        for s in successors:
            if (s not in distance or distance[node] + 1 < distance[s]):
                distance[s] = distance[node] + 1
                path_from[s] = node
            
            f = distance[node] + 1 + heuristic (s, goal)
            frontier.add (s, priority = f)
            
    return None

def backtrack (path_from, start, end):
    path = [end]
    while end != start:
        end = path_from[end]
        path.append (end)

    return list (reversed (path))

def is_goal (cell, goal):
    return cell == goal

def get_successors (cell, grid):
    i, j = cell
    successors = []
    for k in (-1, 0, 1):
        for l in (-1, 0, 1):
            s_i = i + k
            s_j = j + l
            if (s_i >= 0 and s_i < grid.shape[0]):
                if (s_j >= 0 and s_j < grid.shape[1]):
                    if (k != 0 or l != 0):
                        if (grid[s_i][s_j] == 0):
                            successors.append ((s_i, s_j))
    return successors 

def heuristic (cell, goal):
    (a, b) = goal
    (i, j) = cell
    return max (abs (a - i), abs (b - j))
    



if __name__ == "main":
    grid = [
        [0,0,0,1,0,0,1,0],
        [0,0,0,0,0,0,0,0],
        [1,0,0,1,1,0,1,0],
        [0,1,1,1,0,0,0,0],
        [0,0,0,0,0,1,1,1],
        [1,0,1,0,0,0,0,0],
        [1,1,0,0,0,1,0,0],
        [0,0,0,0,0,1,0,0]
    ]   
    
    grid = np.asarray (grid)
    # grid = np.zeros (shape = (100, 100))

    start = (0, 0)
    goal = (6, 6)

    s_x, s_y, s_z = 0, 5, 0
    s_x, s_y, s_z = 0, 5, 0
    d_x, d_y, d_z = 10, 5, 10

    path = Astar_search (start, goal, grid)
    print (path)
