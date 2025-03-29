import random
from pysat.solvers import Glucose3

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

        # Record visited cells (to build CNF from percepts)
        self.visited = set()

        # Global CNF knowledge base (list of clauses)
        self.cnf = []

        # For CNF reasoning: assign two variables per cell:
        # For pits: P_i_j; for Wumpus: W_i_j.
        self.world_size = world.size
        self.offset = self.world_size * self.world_size

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
        Query the world at cell 'pos', convert its percepts into CNF clauses,
        and add them to the global CNF. Also mark pos as visited.
        """
        percept = self.world.get_percepts(pos)
        self.visited.add(pos)
        if self.debug:
            print(f"[DEBUG] Updating CNF for cell {pos} with percepts {percept}")
        neighbors = self.get_neighbors(pos)
        # For pits:
        if not percept.get('breeze', False):
            for n in neighbors:
                clause = [-self.pit_var(n)]
                self.cnf.append(clause)
                # if self.debug:
                #     print(f"[DEBUG] Added clause (no pit at {n}): {clause}")
        else:
            clause = [self.pit_var(n) for n in neighbors]
            self.cnf.append(clause)
            # if self.debug:
            #     print(f"[DEBUG] Added clause (breeze at {pos} implies pit in neighbors): {clause}")
        # For Wumpus:
        if not percept.get('stench', False):
            for n in neighbors:
                clause = [-self.wumpus_var(n)]
                self.cnf.append(clause)
                # if self.debug:
                #     print(f"[DEBUG] Added clause (no Wumpus at {n}): {clause}")
        else:
            clause = [self.wumpus_var(n) for n in neighbors]
            self.cnf.append(clause)
            # if self.debug:
            #     print(f"[DEBUG] Added clause (stench at {pos} implies Wumpus in neighbors): {clause}")

    # --- CNF-based Safety Inference ---
    def is_cell_safe(self, cell):
        """
        Determine if cell 'cell' is safe by checking if assuming a pit or a Wumpus
        there makes the CNF unsatisfiable.
        """
        clauses = self.cnf.copy()
        # Test pit assumption.
        solver_pit = Glucose3()
        for cl in clauses:
            solver_pit.add_clause(cl)
        solver_pit.add_clause([self.pit_var(cell)])
        pit_unsat = not solver_pit.solve()
        solver_pit.delete()
        # Test Wumpus assumption.
        solver_wumpus = Glucose3()
        for cl in clauses:
            solver_wumpus.add_clause(cl)
        solver_wumpus.add_clause([self.wumpus_var(cell)])
        wumpus_unsat = not solver_wumpus.solve()
        solver_wumpus.delete()
        # if self.debug:
        #     print(f"[DEBUG] CNF inference for cell {cell}: pit_unsat={pit_unsat}, wumpus_unsat={wumpus_unsat}")
        return pit_unsat and wumpus_unsat

    def infer_hazards(self, cell):
        """
        For an unvisited cell, further refine the inference:
        - If assuming no pit is unsat, then the cell must have a pit.
        - Similarly for the Wumpus.
        Returns a tuple (pit_status, wumpus_status):
          "H!"  => definitely has hazard,
          "NoH" => definitely does not,
          "?"   => ambiguous.
        """
        clauses = self.cnf.copy()
        # Pit inference.
        solver1 = Glucose3()
        for cl in clauses:
            solver1.add_clause(cl)
        solver1.add_clause([-self.pit_var(cell)])
        no_pit_unsat = not solver1.solve()
        solver1.delete()

        solver2 = Glucose3()
        for cl in clauses:
            solver2.add_clause(cl)
        solver2.add_clause([self.pit_var(cell)])
        pit_unsat = not solver2.solve()
        solver2.delete()

        if no_pit_unsat:
            pit_status = "H!"  # Must have pit.
        elif pit_unsat:
            pit_status = "NoH"
        else:
            pit_status = "?"
        
        # Wumpus inference.
        solver3 = Glucose3()
        for cl in clauses:
            solver3.add_clause(cl)
        solver3.add_clause([-self.wumpus_var(cell)])
        no_wumpus_unsat = not solver3.solve()
        solver3.delete()

        solver4 = Glucose3()
        for cl in clauses:
            solver4.add_clause(cl)
        solver4.add_clause([self.wumpus_var(cell)])
        wumpus_unsat = not solver4.solve()
        solver4.delete()

        if no_wumpus_unsat:
            wumpus_status = "W!"
        elif wumpus_unsat:
            wumpus_status = "NoW"
        else:
            wumpus_status = "?"
        return pit_status, wumpus_status

    # --- Constructing World View from CNF ---
    def construct_world_view(self):
        """
        Build a grid view of the world based solely on the CNF knowledge.
        For each cell:
          - Mark "A" for the agent's current cell.
          - If visited, mark "V" along with percept abbreviations (B, S, G).
          - If unvisited and CNF inference indicates safe, mark "S".
          - Otherwise, mark "U(...)" with hazard inference details.
        Returns a list of lists representing rows of the grid.
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
        print("Agent's World View (based on CNF inference):")
        for row in view:
            print(" | ".join(row))

    # --- Pathfinding ---
    def get_neighbors(self, pos):
        x, y = pos
        nbs = []
        if x > 0: nbs.append((x - 1, y))
        if x < self.world.size - 1: nbs.append((x + 1, y))
        if y > 0: nbs.append((x, y - 1))
        if y < self.world.size - 1: nbs.append((x, y + 1))
        return nbs

    def find_path(self, start, target):
        """
        Compute a path from 'start' to 'target' using BFS.
        Only cells that are CNF-inferred safe are allowed, except that the target is always allowed.
        """
        frontier = [start]
        came_from = {start: None}
        while frontier:
            cur = frontier.pop(0)
            if cur == target:
                path = []
                while cur:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                return path
            for n in self.get_neighbors(cur):
                if n in came_from:
                    continue
                # Allow neighbor if it is safe OR if it is the target.
                if n == target or self.is_cell_safe(n):
                    came_from[n] = cur
                    frontier.append(n)
        return None

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

    # --- Decision Making ---
    def choose_action(self):
        current_pos = self.world.agent_pos
        # Update CNF with current percepts.
        self.update_cnf_for_cell(current_pos)
        # if self.debug:
        #     print("[DEBUG] Global CNF knowledge base:")
        #     for cl in self.cnf:
        #         print(cl)
        # First, try to find safe unvisited cells.
        safe_unvisited = []
        for visited_cell in self.visited:
            neighboring_cells = self.get_neighbors(visited_cell)
            for cell in neighboring_cells:
                if cell in self.visited:
                    continue
                if self.is_cell_safe(cell):
                    safe_unvisited.append(cell)
        if self.debug:
            print(f"[DEBUG] Safe unvisited cells according to CNF: {safe_unvisited}")
        while safe_unvisited:
            target = min(safe_unvisited, key=lambda cell: self.find_distance(cell))
            path = self.find_path(current_pos, target)
            if path and len(path) > 1:
                next_cell = path[1]
                move = self.direction_from_to(current_pos, next_cell)
                if self.debug:
                    print(f"[DEBUG] Moving toward safe cell {target} via path {path} -> {move}")
                return move
            else:
                path = self.find_path(current_pos, target)
                if path and len(path) > 1:
                    next_cell = path[1]
                    move = self.direction_from_to(current_pos, next_cell)
                    if self.debug:
                        print(f"[DEBUG] Moving toward safe cell {target} via path {path} -> {move}")
                    return move
                if self.debug:
                    print(f"[DEBUG] Removing {target}")
                safe_unvisited.remove(target)
        
        # If no safe cell is found, search for a risky cell.
        # Collect all unvisited cells and assign a risk score using hazard inference.
        risky_found = []
        risky_candidates = []
        for visited_cell in self.visited:
            neighboring_cells = self.get_neighbors(visited_cell)
            for unknown_cell in neighboring_cells:
                if unknown_cell in self.visited:
                    continue
                if unknown_cell in risky_found:
                    continue
                pit_status, wumpus_status = self.infer_hazards(unknown_cell)
                if pit_status == "H!":
                    continue
                if pit_status == "W!":
                    continue
                risk = 0
                for neighbor_cell in self.get_neighbors(unknown_cell):
                    if neighbor_cell in self.visited:
                        percept = self.world.get_percepts(cell)
                        if percept.get("breeze", False):
                            risk += 25
                        if percept.get("stench", False):
                            risk += 25
                dist = 0
                dist += self.find_distance(unknown_cell)
                risky_found.append(unknown_cell)
                risky_candidates.append((unknown_cell, dist + risk))
                if self.debug:
                    print(f"[DEBUG] Distance for cell {cell}: {dist + risk} ({pit_status}, {wumpus_status})")
        if self.debug:
            print(f"[DEBUG] Safe unvisited cells according to CNF: {risky_found}")
        if risky_candidates:
            # Choose the cell with the minimal risk.
            target, _ = min(risky_candidates, key=lambda t: t[1])
            path = self.find_path(current_pos, target)
            if self.debug:
                print(f"[DEBUG] Path length to cell {path}")
            if path and len(path) > 1:
                next_cell = path[1]
                move = self.direction_from_to(current_pos, next_cell)
                if self.debug:
                    print(f"[DEBUG] Risky move: Moving toward cell {target} via path {path} -> {move}")
                return move

        # As a last resort, choose a random neighbor.
        nbs = self.get_neighbors(current_pos)
        move = self.direction_from_to(current_pos, random.choice(nbs))
        if self.debug:
            print(f"[DEBUG] No candidate found; taking random move from {current_pos} -> {move}")
        return move

    def find_distance(self, cell):
        block_distance = abs(cell[0] - self.world.agent_pos[0]) + abs(cell[1] - self.world.agent_pos[1])        
        return block_distance

    def display_world_view(self):
        view = self.construct_world_view()
        print("Agent's World View:")
        for row in view:
            print(" | ".join(row))

    def construct_world_view(self):
        """
        Construct a grid (list of lists) representing the agent's world view based solely on CNF inference.
        For each cell:
          - "A" for the agent's current cell.
          - For visited cells, "V" plus abbreviations for percepts (B, S, G).
          - For unvisited cells: "S" if safe, else "U(pit_status, wumpus_status)".
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

    # --- Additional Helper for Risky Pathfinding ---
    # def find_path_risky(self, start, target):
    #     """
    #     Compute a path from 'start' to 'target' using BFS (without filtering by CNF safety).
    #     This is used for risky moves.
    #     """
    #     frontier = [start]
    #     came_from = {start: None}
    #     while frontier:
    #         cur = frontier.pop(0)
    #         if cur == target:
    #             path = []
    #             while cur:
    #                 path.append(cur)
    #                 cur = came_from[cur]
    #             path.reverse()
    #             return path
    #         for n in self.get_neighbors(cur):
    #             if n not in came_from:
    #                 came_from[n] = cur
    #                 frontier.append(n)
    #     return None

    def display_known_world(self):
        view = self.construct_world_view()
        print("Agent's World View (based on CNF inference):")
        for row in view:
            print(" | ".join(row))




class RandomWalkAgent(Agent):
    def choose_action(self):
        return random.choice(['up', 'down', 'left', 'right'])