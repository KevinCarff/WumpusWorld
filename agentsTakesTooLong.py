import random
from pysat.solvers import Glucose3
from collections import deque

class Agent:
    def __init__(self, world):
        self.world = world

    def perceive(self):
        return self.world.get_percepts(self.world.agent_pos)

    def move(self, direction):
        x, y = self.world.agent_pos
        if direction == 'up':
            new_pos = (x - 1, y)
        elif direction == 'down':
            new_pos = (x + 1, y)
        elif direction == 'left':
            new_pos = (x, y - 1)
        elif direction == 'right':
            new_pos = (x, y + 1)
        else:
            new_pos = (x, y)
        self.world.move_agent(new_pos)

class CNFAgent(Agent):
    def __init__(self, world, debug=False):
        super().__init__(world)
        self.debug = debug

        # Keep track of visited cells (cells where percepts have been acquired)
        self.visited = set()

        # Global CNF knowledge base (list of clauses)
        self.cnf = []

        # World size and variable offset.
        self.world_size = world.size
        self.offset = self.world_size * self.world_size

        # Use an incremental SAT solver—clauses will be added as they are discovered.
        self.solver = Glucose3()

        # A simple experience map: if a move to a cell eventually causes death,
        # we will add extra risk to that cell.
        self.experience = {}  # {cell: additional risk value}

        # Goal management: if we perceive gold, we set a goal (e.g. return to start).
        self.has_gold = False
        self.goal = None
        # Assume the world provides a starting position (default (0,0) if not)
        self.start = getattr(world, 'start', (0, 0))

    # --- Variable Mapping ---
    def pit_var(self, cell):
        i, j = cell
        return i * self.world_size + j + 1

    def wumpus_var(self, cell):
        i, j = cell
        return self.offset + i * self.world_size + j + 1

    # --- CNF Update from Percepts ---
    def update_cnf_for_cell(self, pos):
        """
        Query the world at cell 'pos', add clauses to the SAT solver based on the percepts,
        and mark pos as visited.
        """
        percept = self.world.get_percepts(pos)
        self.visited.add(pos)
        neighbors = self.get_neighbors(pos)

        # For pits:
        if not percept.get('breeze', False):
            # No breeze means none of the neighbors has a pit.
            for n in neighbors:
                clause = [-self.pit_var(n)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                if self.debug:
                    print(f"[DEBUG] Added clause (no pit at {n}): {clause}")
        else:
            # Breeze means at least one neighbor has a pit.
            clause = [self.pit_var(n) for n in neighbors]
            self.cnf.append(clause)
            self.solver.add_clause(clause)
            if self.debug:
                print(f"[DEBUG] Added clause (breeze at {pos} implies pit in neighbors): {clause}")

        # For Wumpus:
        if not percept.get('stench', False):
            # No stench implies no neighbor contains the Wumpus.
            for n in neighbors:
                clause = [-self.wumpus_var(n)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                if self.debug:
                    print(f"[DEBUG] Added clause (no Wumpus at {n}): {clause}")
        else:
            # Stench means at least one neighbor must contain the Wumpus.
            clause = [self.wumpus_var(n) for n in neighbors]
            self.cnf.append(clause)
            self.solver.add_clause(clause)
            if self.debug:
                print(f"[DEBUG] Added clause (stench at {pos} implies Wumpus in neighbors): {clause}")

        # Goal management: if gold is perceived, set the goal to the start (exit).
        if percept.get("glitter", False):
            self.has_gold = True
            self.goal = self.start
            if self.debug:
                print("[DEBUG] Gold found! Setting goal to return to start.")

    # --- CNF-based Safety and Hazard Inference ---
    def is_cell_safe(self, cell):
        """
        A cell is considered safe if assuming a pit or Wumpus there makes the CNF unsolvable.
        """
        pit_unsat = not self.solver.solve(assumptions=[self.pit_var(cell)])
        wumpus_unsat = not self.solver.solve(assumptions=[self.wumpus_var(cell)])
        if self.debug:
            print(f"[DEBUG] Safety check for {cell}: pit_unsat={pit_unsat}, wumpus_unsat={wumpus_unsat}")
        return pit_unsat and wumpus_unsat

    def infer_hazards(self, cell):
        """
        Returns a tuple (pit_status, wumpus_status) where:
          "H!"  => hazard is definitely present,
          "NoH" => hazard is definitely not present,
          "?"   => ambiguous.
        Uses the incremental solver with assumptions.
        """
        no_pit_unsat = not self.solver.solve(assumptions=[-self.pit_var(cell)])
        pit_unsat = not self.solver.solve(assumptions=[self.pit_var(cell)])
        if no_pit_unsat:
            pit_status = "H!"
        elif pit_unsat:
            pit_status = "NoH"
        else:
            pit_status = "?"
            
        no_wumpus_unsat = not self.solver.solve(assumptions=[-self.wumpus_var(cell)])
        wumpus_unsat = not self.solver.solve(assumptions=[self.wumpus_var(cell)])
        if no_wumpus_unsat:
            wumpus_status = "W!"
        elif wumpus_unsat:
            wumpus_status = "NoW"
        else:
            wumpus_status = "?"
            
        return pit_status, wumpus_status

    # --- Risk Estimation (Probabilistic Flair) ---
    def risk_estimate(self, cell):
        """
        Returns a floating-point risk score for entering a cell.
        Factors include CNF-based hazard inference, neighboring percepts,
        distance, and past experience.
        """
        pit_status, wumpus_status = self.infer_hazards(cell)
        risk = 0.0
        if pit_status == "H!":
            risk += 1.0
        elif pit_status == "?":
            risk += 0.5
        if wumpus_status == "W!":
            risk += 1.0
        elif wumpus_status == "?":
            risk += 0.5

        # Add risk from nearby visited cells' percepts.
        for n in self.get_neighbors(cell):
            if n in self.visited:
                percept = self.world.get_percepts(n)
                if percept.get("breeze", False):
                    risk += 0.25
                if percept.get("stench", False):
                    risk += 0.25

        # Add a factor for distance (normalized by grid size).
        risk += self.find_distance(cell) / (self.world_size * 2)

        # Incorporate any additional risk learned from experience.
        risk += self.experience.get(cell, 0)
        return risk

    def lookahead_risk(self, cell):
        """
        A simple lookahead that considers the cell's own risk plus
        the average risk of its unvisited neighbors.
        """
        base_risk = self.risk_estimate(cell)
        additional = 0.0
        count = 0
        for n in self.get_neighbors(cell):
            if n not in self.visited:
                additional += self.risk_estimate(n)
                count += 1
        if count > 0:
            return base_risk + additional / count
        return base_risk

    def update_experience(self, cell, outcome):
        """
        Update risk estimates based on outcomes.
        If moving into a cell eventually led to death, increase its risk.
        """
        if outcome == "death":
            self.experience[cell] = self.experience.get(cell, 0) + 1.0
            if self.debug:
                print(f"[DEBUG] Experience updated for {cell}: now {self.experience[cell]} risk.")

    # --- Pathfinding: Using only Visited Cells ---
    def find_visited_path(self, start, target):
        """
        Uses BFS to find a path from start to target that traverses only visited cells.
        Returns a list of cells representing the path, or None if no such path exists.
        """
        queue = deque([start])
        came_from = {start: None}
        while queue:
            cur = queue.popleft()
            if cur == target:
                path = []
                while cur is not None:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                if self.debug:
                    print(f"[DEBUG] Found visited path: {path}")
                return path
            for n in self.get_neighbors(cur):
                if n not in came_from and n in self.visited:
                    came_from[n] = cur
                    queue.append(n)
        if self.debug:
            print(f"[DEBUG] No visited path from {start} to {target}")
        return None

    # --- Helper Methods ---
    def get_neighbors(self, pos):
        x, y = pos
        nbs = []
        if x > 0:
            nbs.append((x - 1, y))
        if x < self.world.size - 1:
            nbs.append((x + 1, y))
        if y > 0:
            nbs.append((x, y - 1))
        if y < self.world.size - 1:
            nbs.append((x, y + 1))
        return nbs

    def find_distance(self, cell):
        cx, cy = self.world.agent_pos
        return abs(cell[0] - cx) + abs(cell[1] - cy)

    def direction_from_to(self, current, neighbor):
        cx, cy = current
        nx, ny = neighbor
        if nx < cx:
            return 'up'
        elif nx > cx:
            return 'down'
        elif ny < cy:
            return 'left'
        elif ny > cy:
            return 'right'
        return random.choice(['up', 'down', 'left', 'right'])

    # --- World View ---
    def construct_world_view(self):
        """
        Constructs a grid view of the world based on current knowledge:
          - "A" for the agent’s position.
          - "V" for visited cells with percept abbreviations (B for breeze, S for stench, G for glitter).
          - For unvisited cells, "S" if safe, or "U(...)" showing hazard inference.
        """
        size = self.world.size
        view = []
        for i in range(size):
            row = []
            for j in range(size):
                cell = (i, j)
                if cell == self.world.agent_pos:
                    row.append("A")
                elif cell in self.visited:
                    percept = self.world.get_percepts(cell)
                    code = "V"
                    if percept.get("breeze", False):
                        code += "B"
                    if percept.get("stench", False):
                        code += "S"
                    if percept.get("glitter", False):
                        code += "G"
                    row.append(code)
                else:
                    if self.is_cell_safe(cell):
                        row.append("S")
                    else:
                        pit_status, wumpus_status = self.infer_hazards(cell)
                        row.append(f"U({pit_status},{wumpus_status})")
            view.append(row)
        return view

    def display_world_view(self):
        view = self.construct_world_view()
        print("Agent's World View (based on CNF inference and risk estimates):")
        for row in view:
            print(" | ".join(row))

    # --- Decision Making ---
    def choose_action(self):
        current_pos = self.world.agent_pos

        # Update knowledge with current percepts.
        self.update_cnf_for_cell(current_pos)

        # If the agent has found gold, try to return to the exit.
        if self.has_gold and self.goal:
            path = self.find_visited_path(current_pos, self.goal)
            if path and len(path) > 1:
                next_cell = path[1]
                move = self.direction_from_to(current_pos, next_cell)
                if self.debug:
                    print(f"[DEBUG] Returning with gold via path {path} -> {move}")
                return move

        # First, look for safe unvisited cells.
        safe_unvisited = []
        for visited_cell in self.visited:
            for cell in self.get_neighbors(visited_cell):
                if cell not in self.visited and self.is_cell_safe(cell):
                    safe_unvisited.append(cell)
        if safe_unvisited:
            target = min(safe_unvisited, key=lambda cell: self.find_distance(cell))
            path = self.find_visited_path(current_pos, target)
            if path and len(path) > 1:
                next_cell = path[1]
                move = self.direction_from_to(current_pos, next_cell)
                if self.debug:
                    print(f"[DEBUG] Moving toward safe cell {target} via path {path} -> {move}")
                return move
            elif self.debug:
                print("[DEBUG] No path found for safe move.")

        # If no clearly safe move, evaluate all unvisited cells using lookahead risk.
        risky_candidates = []
        for i in range(self.world_size):
            for j in range(self.world_size):
                cell = (i, j)
                if cell in self.visited:
                    continue
                risk = self.lookahead_risk(cell)
                risky_candidates.append((cell, risk))
                if self.debug:
                    print(f"[DEBUG] Lookahead risk for candidate {cell}: {risk}")

        if risky_candidates:
            target, _ = min(risky_candidates, key=lambda t: t[1])
            if self.debug:
                print(f"[DEBUG] Selected risky target {target}")
            # Attempt to move via a visited neighbor of the target.
            visited_neighbors = [n for n in self.get_neighbors(target) if n in self.visited]
            if visited_neighbors:
                best_neighbor = min(visited_neighbors, key=lambda n: self.find_distance(n))
                path = self.find_visited_path(current_pos, best_neighbor)
                if path and len(path) > 1:
                    next_cell = path[1]
                    move = self.direction_from_to(current_pos, next_cell)
                    if self.debug:
                        print(f"[DEBUG] Risky move: heading to visited border {best_neighbor} for target {target} via {path} -> {move}")
                    return move
                elif self.debug:
                    print("[DEBUG] No path found for risky move.")
        
        # As a last resort, take a random move.
        nbs = self.get_neighbors(current_pos)
        move = self.direction_from_to(current_pos, random.choice(nbs))
        if self.debug:
            print(f"[DEBUG] Fallback: taking random move from {current_pos} -> {move}")
        return move

class RandomWalkAgent(Agent):
    def choose_action(self):
        return random.choice(['up', 'down', 'left', 'right'])
