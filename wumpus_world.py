# wumpus_world.py

import random

class WumpusWorld:
    def __init__(self, size=8, num_pits=3):
        self.size = size
        self.num_pits = num_pits
        # The agent always starts in the bottom-left corner.
        self.agent_pos = (size - 1, 0)
        self.agent_alive = True
        self.gold_found = False
        self._generate_world()

    def _generate_world(self):
        valid = False
        while not valid:
            # Create a fresh grid.
            self.grid = [[{'pit': False, 'wumpus': False, 'gold': False} for _ in range(self.size)] for _ in range(self.size)]
            # Generate list of all positions except the starting cell.
            positions = [(i, j) for i in range(self.size) for j in range(self.size) if (i, j) != self.agent_pos]
            # Randomly place pits.
            pit_positions = random.sample(positions, self.num_pits)
            for pos in pit_positions:
                self.grid[pos[0]][pos[1]]['pit'] = True
            # Choose Wumpus position from positions that are not pits.
            remaining = [pos for pos in positions if pos not in pit_positions]
            self.wumpus_pos = random.choice(remaining)
            self.grid[self.wumpus_pos[0]][self.wumpus_pos[1]]['wumpus'] = True
            # Choose gold position from remaining positions (neither pit nor Wumpus).
            remaining = [pos for pos in remaining if pos != self.wumpus_pos]
            self.gold_pos = random.choice(remaining)
            self.grid[self.gold_pos[0]][self.gold_pos[1]]['gold'] = True

            # Check if there's a safe path from the starting cell to the gold.
            if self._is_winnable():
                valid = True
            # If not winnable, the loop repeats and a new world is generated.

    def _is_winnable(self):
        """
        Check if there's a path from the starting cell (agent_pos) to the gold (gold_pos)
        that does not pass through any cell containing a pit or the Wumpus.
        """
        start = self.agent_pos
        target = self.gold_pos
        visited = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            for neighbor in self.get_adjacent_positions(current):
                # Only add safe cells (no pit and no Wumpus) to the queue.
                if not self.grid[neighbor[0]][neighbor[1]]['pit'] and not self.grid[neighbor[0]][neighbor[1]]['wumpus']:
                    queue.append(neighbor)
        return False

    def get_adjacent_positions(self, pos):
        x, y = pos
        positions = []
        if x > 0:
            positions.append((x - 1, y))
        if x < self.size - 1:
            positions.append((x + 1, y))
        if y > 0:
            positions.append((x, y - 1))
        if y < self.size - 1:
            positions.append((x, y + 1))
        return positions

    def get_percepts(self, pos):
        percepts = {'breeze': False, 'stench': False, 'glitter': False}
        for adj in self.get_adjacent_positions(pos):
            if self.grid[adj[0]][adj[1]]['pit']:
                percepts['breeze'] = True
            if self.grid[adj[0]][adj[1]]['wumpus']:
                percepts['stench'] = True
        if self.grid[pos[0]][pos[1]]['gold']:
            percepts['glitter'] = True
        return percepts

    def move_agent(self, new_pos):
        if (new_pos[0] < 0 or new_pos[0] >= self.size or 
            new_pos[1] < 0 or new_pos[1] >= self.size):
            return False  # Illegal move.
        self.agent_pos = new_pos
        cell = self.grid[new_pos[0]][new_pos[1]]
        if cell['pit'] or cell['wumpus']:
            self.agent_alive = False
        if cell['gold']:
            self.gold_found = True
        return True

    def analyze_state(self):
        analysis = {}
        for i in range(self.size):
            for j in range(self.size):
                analysis[(i, j)] = {
                    'has_pit': self.grid[i][j]['pit'],
                    'has_wumpus': self.grid[i][j]['wumpus'],
                    'has_gold': self.grid[i][j]['gold']
                }
        return analysis
