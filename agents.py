import random
from pysat.solvers import Glucose3
from collections import deque

# ============================================
# Base Agent Class and Utility Functions
# ============================================
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

def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# ============================================
# CNFAgent: Inference, Risk, and Path Planning
# ============================================
class CNFAgent(Agent):
    def __init__(self, world, debug=False):
        super().__init__(world)
        self.debug = debug

        # Exploration memory
        self.visited = set()       # Cells where percepts have been acquired.
        self.safe_map = set()      # Cells inferred safe but not yet visited.
        self.cnf = []              # Global CNF knowledge base.

        # World dimensions and SAT solver setup.
        self.world_size = world.size
        self.offset = self.world_size * self.world_size
        self.solver = Glucose3()

        # Goal management: if gold is seen, the agent’s goal is to return home.
        self.has_gold = False
        self.goal = None
        self.start = getattr(world, 'start', (0, 0))

        # For path planning.
        self.current_path = []     # Planned route (list of cells).
        self.current_target = None # Target cell for current plan.
        self.add_exactly_one_wumpus_constraint()
        self.infer_pit_by_exclusion()
        
    # --- Variable Mapping ---
    def deduce_pit_from_breeze_constraint(self):
        for cell in self.visited:
            percept = self.world.get_percepts(cell)
            if not percept.get("breeze", False):
                continue

            neighbors = self.get_neighbors(cell)
            known_safe = []
            unknown = []

            for n in neighbors:
                if n in self.visited:
                    known_safe.append(n)
                else:
                    unknown.append(n)

            # Direct deduction: 3 known safe, 1 unknown
            if len(unknown) == 1 and len(known_safe) == len(neighbors) - 1:
                must_be_pit = unknown[0]
                clause = [self.pit_var(must_be_pit)]
                if clause not in self.cnf:
                    self.cnf.append(clause)
                    self.solver.add_clause(clause)
                    # if self.debug:
                    #     print(f"Inferred pit at {must_be_pit} due to breeze at {cell} and 3 safe neighbors.")
            else:
                # SAT-based backup: all neighbors except one are UNSAT with pit assumption
                possible_pits = []
                for n in neighbors:
                    if self.solver.solve(assumptions=[self.pit_var(n)]):
                        possible_pits.append(n)
                if len(possible_pits) == 1:
                    must_be_pit = possible_pits[0]
                    clause = [self.pit_var(must_be_pit)]
                    if clause not in self.cnf:
                        self.cnf.append(clause)
                        self.solver.add_clause(clause)
                        # if self.debug:
                        #     print(f"Inferred pit at {must_be_pit} via SAT deduction from breeze at {cell}.")


    def deduce_wumpus_from_stench_constraint(self):
        for cell in self.visited:
            percept = self.world.get_percepts(cell)
            if not percept.get("stench", False):
                continue

            neighbors = self.get_neighbors(cell)
            known_safe = []
            unknown = []

            for n in neighbors:
                if n in self.visited:
                    known_safe.append(n)
                else:
                    unknown.append(n)

            # Direct deduction: 3 known safe, 1 unknown
            if len(unknown) == 1 and len(known_safe) == len(neighbors) - 1:
                must_be_wumpus = unknown[0]
                clause = [self.wumpus_var(must_be_wumpus)]
                if clause not in self.cnf:
                    self.cnf.append(clause)
                    self.solver.add_clause(clause)
                    # if self.debug:
                    #     print(f"Inferred Wumpus at {must_be_wumpus} due to stench at {cell} and 3 safe neighbors.")
            else:
                # SAT-based backup: all neighbors except one are UNSAT with wumpus assumption
                possible_wumpus = []
                for n in neighbors:
                    if self.solver.solve(assumptions=[self.wumpus_var(n)]):
                        possible_wumpus.append(n)
                if len(possible_wumpus) == 1:
                    must_be_wumpus = possible_wumpus[0]
                    clause = [self.wumpus_var(must_be_wumpus)]
                    if clause not in self.cnf:
                        self.cnf.append(clause)
                        self.solver.add_clause(clause)
                        # if self.debug:
                        #     print(f"Inferred Wumpus at {must_be_wumpus} via SAT deduction from stench at {cell}.")


    def infer_pit_by_exclusion(self):
        for i in range(self.world_size):
            for j in range(self.world_size):
                cell = (i, j)
                if cell in self.visited or not self.is_cell_safe(cell):
                    continue  # Already visited or known hazard

                neighbors = self.get_neighbors(cell)
                breeze_neighbors = [n for n in neighbors if n in self.visited and self.world.get_percepts(n).get("breeze", False)]
                unvisited_neighbors = [n for n in neighbors if n not in self.visited]

                if len(breeze_neighbors) >= 3 and len(unvisited_neighbors) == 1:
                    must_be_pit = unvisited_neighbors[0]
                    clause = [self.pit_var(must_be_pit)]
                    self.cnf.append(clause)
                    self.solver.add_clause(clause)
                    # if self.debug:
                    #     print(f"Inferred pit at {must_be_pit} due to 3 surrounding breezes.")

    def add_exactly_one_wumpus_constraint(self):
        all_cells = [(i, j) for i in range(self.world_size) for j in range(self.world_size)]
        wumpus_vars = [self.wumpus_var(cell) for cell in all_cells]

        # At least one Wumpus
        self.cnf.append(wumpus_vars)
        self.solver.add_clause(wumpus_vars)

        # At most one Wumpus: pairwise exclusions
        for i in range(len(wumpus_vars)):
            for j in range(i + 1, len(wumpus_vars)):
                clause = [-wumpus_vars[i], -wumpus_vars[j]]
                self.cnf.append(clause)
                self.solver.add_clause(clause)

        # if self.debug:
        #     print("Added exactly-one Wumpus constraint.")
        
    def pit_var(self, cell):
        i, j = cell
        return i * self.world_size + j + 1

    def wumpus_var(self, cell):
        i, j = cell
        return self.offset + i * self.world_size + j + 1

    # --- CNF Update from Percepts ---
    def update_cnf_for_cell(self, pos):
        percept = self.world.get_percepts(pos)
        self.visited.add(pos)
        # if self.debug:
        #     print(f"update_cnf_for_cell: at {pos} with percepts {percept}")
        for neighbor in self.get_neighbors(pos):
            # Pits:
            if not percept.get('breeze', False):
                clause = [-self.pit_var(neighbor)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                # if self.debug:
                #     print(f"Added clause (no pit at {neighbor}): {clause}")
            else:
                clause = [self.pit_var(n) for n in self.get_neighbors(pos)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                # if self.debug:
                #     print(f"Added clause (breeze at {pos}): {clause}")
            # Wumpus:
            if not percept.get('stench', False):
                clause = [-self.wumpus_var(neighbor)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                # if self.debug:
                #     print(f"Added clause (no Wumpus at {neighbor}): {clause}")
            else:
                clause = [self.wumpus_var(n) for n in self.get_neighbors(pos)]
                self.cnf.append(clause)
                self.solver.add_clause(clause)
                # if self.debug:
                #     print(f"Added clause (stench at {pos}): {clause}")
        if percept.get("glitter", False):
            self.has_gold = True
            self.goal = self.start
            # if self.debug:
            #     print("Gold detected! Setting goal to return home.")

    # --- CNF-Based Safety Inference ---
    def is_cell_safe(self, cell):
        pit_unsat = not self.solver.solve(assumptions=[self.pit_var(cell)])
        wumpus_unsat = not self.solver.solve(assumptions=[self.wumpus_var(cell)])
        # if self.debug:
        #     print(f"is_cell_safe({cell}): pit_unsat={pit_unsat}, wumpus_unsat={wumpus_unsat}")
        return pit_unsat and wumpus_unsat

    def infer_hazards(self, cell):
        no_pit_unsat = not self.solver.solve(assumptions=[-self.pit_var(cell)])
        pit_unsat = not self.solver.solve(assumptions=[self.pit_var(cell)])
        pit_status = "H!" if no_pit_unsat else ("NoH" if pit_unsat else "?")
        no_wumpus_unsat = not self.solver.solve(assumptions=[-self.wumpus_var(cell)])
        wumpus_unsat = not self.solver.solve(assumptions=[self.wumpus_var(cell)])
        wumpus_status = "W!" if no_wumpus_unsat else ("NoW" if wumpus_unsat else "?")
        return pit_status, wumpus_status

    # ============================================
    # Risk Estimation Module
    # ============================================
    def risk_estimate(self, cell):
        pit_status, wumpus_status = self.infer_hazards(cell)
        risk = 0.0
        if pit_status == "H!":
            risk += 1000.0
        elif pit_status == "NoH":
            risk -= 50
        if wumpus_status == "W!":
            risk += 1000.0
        elif wumpus_status == "NoW":
            risk -= 50
        for n in self.get_neighbors(cell):
            if n in self.visited:
                percept = self.world.get_percepts(n)
                if percept.get("breeze", False):
                    risk += 0
                if percept.get("stench", False):
                    risk += 0
        risk += manhattan_distance(cell, self.world.agent_pos) / (self.world_size * 2)/100
        if (cell in self.visited):
            risk += 2
        elif (self.is_cell_safe(cell)):
            risk -= 5000
        else:
            risk -= 25
        # if self.debug:
        #     print(f"risk_estimate({cell}) = {risk}")
        return risk

    # ============================================
    # Consolidated Safe Path Search
    # ============================================
    def find_closest_safe_path(self, current_pos):
        best_path = []
        best_candidate = current_pos
        orderedSafeMap = sorted(self.safe_map, key=lambda n: manhattan_distance(n, current_pos))
        # if self.debug:
        #     print(f"find_closest_safe_path: safe map = {orderedSafeMap}")
        for candidate in orderedSafeMap:
            # print("Looking for an alternative path")
            path = self.find_safe_path(current_pos, candidate)
            if path is None:
                # if self.debug:
                #     print("Looking for an alternative path")
                continue
            else:
                best_path = path
                best_candidate = candidate
                break
            # if self.debug:
            #     print(f"Candidate {candidate}: path = {path} | length = {len(path)}")
            # candidates.append((candidate, path, len(path)))
        if best_candidate == current_pos:
            # if self.debug:
            #     print("find_closest_safe_path: no valid candidate found")
            return None, None
        # if self.debug:
        #     print(f"find_closest_safe_path: Best candidate: {best_candidate} with path: {best_path}, length: {manhattan_distance(best_candidate, current_pos)}")
        return best_candidate, best_path


    # ============================================
    # Helper Functions
    # ============================================
    def get_neighbors(self, pos):
        x, y = pos
        nbs = []
        if x > 0: nbs.append((x - 1, y))
        if x < self.world.size - 1: nbs.append((x + 1, y))
        if y > 0: nbs.append((x, y - 1))
        if y < self.world.size - 1: nbs.append((x, y + 1))
        return nbs

    def direction_from_to(self, current, neighbor):
        cx, cy = current
        nx, ny = neighbor
        if nx < cx: return 'up'
        if nx > cx: return 'down'
        if ny < cy: return 'left'
        if ny > cy: return 'right'
        return random.choice(['up', 'down', 'left', 'right'])
    
    def is_known_hole(self, cell):
        pit_status, wumpus_status = self.infer_hazards(cell)
        return pit_status == "H!" or wumpus_status == "W!"

    def find_safe_path(self, start, target):
        queue = deque([start])
        came_from = {start: None}

        while queue:
            cur = queue.popleft()

            if cur == target:
                path = []
                while cur:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                # if self.debug:
                #     print(f"find_safe_path: path found {path}")
                return path

            neighbors = sorted(self.get_neighbors(cur), key=lambda n: manhattan_distance(n, target))
            # if (neighbors):
            #     for myN in neighbors:
                    # print(f"neighbors: {myN}")
            for n in neighbors:
                if n in came_from:
                    continue  # already visited in BFS

                # print(f"neighbors1: {n}")
                
                pit_status, wumpus_status = self.infer_hazards(n)
                if (pit_status != "NoH" or wumpus_status != "NoW") and n not in self.visited:
                    continue  # skip confirmed hazards

                # print(f"neighbors2: {n}")
                
                # ✅ Allow all known safe cells, whether visited or not
                if self.is_cell_safe(n) or n in self.visited:
                    came_from[n] = cur
                    queue.append(n)

        # if self.debug:
        #     print(f"find_safe_path: no path from {start} to {target}")
        return None

    def find_safe_path_to_risky(self, start, target):
        queue = deque([start])
        came_from = {start: None}

        while queue:
            cur = queue.popleft()

            if cur == target:
                path = []
                while cur:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                # if self.debug:
                #     print(f"find_safe_path: path found {path}")
                return path

            neighbors = sorted(self.get_neighbors(cur), key=lambda n: manhattan_distance(n, target))
            for n in neighbors:
                if n != target:
                    if n in came_from:
                        continue  # already visited in BFS

                    pit_status, wumpus_status = self.infer_hazards(n)
                    if pit_status != "NoH" or wumpus_status != "NoW":
                        continue  # skip confirmed hazards
                # ✅ Allow all known safe cells, whether visited or not
                if self.is_cell_safe(n) or n == target:
                    came_from[n] = cur
                    queue.append(n)

        # if self.debug:
        #     print(f"find_safe_path: no path from {start} to {target}")
        return None

    # ============================================
    # Decision Making Module
    # ============================================
    def choose_action(self):
        current_pos = self.world.agent_pos

        # 1. Update knowledge at the current cell.
        self.update_cnf_for_cell(current_pos)
        
        self.deduce_pit_from_breeze_constraint()
        self.deduce_wumpus_from_stench_constraint()
        # if self.debug:
        #     print(f"CNF now has {len(self.cnf)} clauses after update at {current_pos}.")

        # 2. Refresh safe_map: add neighbors of visited cells that are safe.
        self.safe_map.clear()
        for cell in self.visited:
            for neighbor in self.get_neighbors(cell):
                # if self.debug:
                #     print(f"visited cells: {neighbor}")

                pit_status, wumpus_status = self.infer_hazards(neighbor)
                if pit_status != "NoH" or wumpus_status != "NoW":
                    # if self.debug:
                    #     print(f"pit_status: {pit_status}, wumpus_status: {wumpus_status}")
                    continue
                if neighbor not in self.visited and self.is_cell_safe(neighbor):
                    self.safe_map.add(neighbor)
                    # if self.debug:
                    #     print(f"safe cells: {self.safe_map}")

        move_type = None  # To log the type of move.

        # 3. If carrying gold, plan a path home.
        # if self.has_gold and self.goal:
        #     path = self.find_visited_path(current_pos, self.goal)
        #     if path and len(path) > 1:
        #         self.current_path = path
        #         self.current_target = self.goal
        #         move_type = "safe (goal)"
        #         print(f"Move type: {move_type}")
        #         return self.direction_from_to(current_pos, path[1])

        # 4. Follow an existing plan if still valid.
        # if self.current_path and self.current_target:
        #     if len(self.current_path) > 1:
        #         next_cell = self.current_path[1]
        #         pit_status, wumpus_status = self.infer_hazards(next_cell)
        #         if pit_status == "NoH" and wumpus_status == "NoW":
        #             self.current_path = self.current_path[1:]
        #             move_type = "safe (following plan)"
        #             print(f"Move type: {move_type}")
        #             return self.direction_from_to(current_pos, next_cell)
        #     self.current_path = []
        #     self.current_target = None

        # 5. Use consolidated safe path search.
        # 5. Use consolidated closest safe path search.
        candidate, path = self.find_closest_safe_path(current_pos)
        if candidate and path and len(path) > 1:
            # if self.debug:
            #     print(f"Current Path: {path}")
            self.current_path = path
            self.current_target = candidate
            move_type = "safe (closest candidate from safe map)"
            # print(f"Move type: {move_type}")
            # print(f"Chosen path: {path} | Next move: {path[1]}")
            return self.direction_from_to(current_pos, path[1])


        # 6. Fallback: Risk-based evaluation.
        risky_candidates = []
        for i in range(self.world_size):
            for j in range(self.world_size):
                cell = (i, j)
                if (cell in self.visited):
                    continue
                # if self.debug:
                #     print(f"Current Path: {cell}")
                risk = self.risk_estimate(cell)
                risky_candidates.append((cell, risk))
        while risky_candidates:
            target, _ = min(risky_candidates, key=lambda t: t[1])
            if target:
                path = self.find_safe_path_to_risky(current_pos, target)
                if path and len(path) > 1:
                    self.current_path = path
                    self.current_target = target
                    move_type = "risky"
                    # print(f"Move type: {move_type}")
                    return self.direction_from_to(current_pos, path[1])
                risky_candidates.remove(min(risky_candidates, key=lambda t: t[1]))

        # 7. Fallback: Choose the closest adjacent neighbor.
        nbs = self.get_neighbors(current_pos)
        if nbs:
            best = min(nbs, key=lambda cell: manhattan_distance(cell, current_pos))
            self.current_path = [current_pos, best]
            self.current_target = best
            move_type = "random fallback"
            # print(f"Move type: {move_type}")
            return self.direction_from_to(current_pos, best)

        # 8. Ultimate fallback: Random move.
        move_type = "ultimate random"
        # print(f"Move type: {move_type}")
        return random.choice(['up', 'down', 'left', 'right'])

    # ============================================
    # World View Module
    # ============================================
    def construct_world_view(self):
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
        # print("Agent's World View (based on CNF and risk estimates):")
        # for row in view:
            # print(" | ".join(row))

class RandomWalkAgent(Agent):
    def choose_action(self):
        return random.choice(['up', 'down', 'left', 'right'])
