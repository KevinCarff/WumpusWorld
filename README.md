Below is the complete README.md content. Simply copy the text below into a file named `README.md`:

```markdown
# Wumpus World Simulation with CNF and Random Walk Agents

This repository contains a simulation of the classic Wumpus World game. The project demonstrates two approaches for navigating the world:
- **CNF-Based Agent:** Uses Conjunctive Normal Form (CNF) reasoning to infer safe moves based on percepts.
- **Random Walk Agent:** Uses a simple random move strategy as a baseline.

Both agents interact with a randomly generated Wumpus World where:
- The world is represented as a grid (default 8×8).
- There are a number of pits (default 3), one stationary Wumpus, and one piece of gold.
- The agent always starts at the bottom-left corner.
- The agent receives percepts (breeze, stench, and glitter) from adjacent cells.

The simulation uses [Pygame](https://www.pygame.org/) for visualization, and [PySAT](https://pysathq.github.io/) (with the Glucose3 solver) for SAT-based inference in the CNF Agent.

## Features

- **CNF-Based Reasoning:** Infers hazards using logical constraints and a SAT solver.
- **Random Walk Baseline:** Demonstrates a naive approach to navigating the Wumpus World.
- **Multiple Game Simulation:** Scripts are provided to run several simulations in a row and log failures.
- **Visualization:** Optional Pygame display shows the world, the agent’s moves, and percept logs.
- **Failure Logging:** Optionally save game states where the agent dies for further analysis.

## Requirements

- Python 3.6+
- [Pygame](https://www.pygame.org/) (for visualization)
- [PySAT](https://pysathq.github.io/) (for CNF-based reasoning)

You can install the required Python packages using pip:

```bash
pip install pygame python-sat
```

## Repository Structure

- `agents.py`  
  Contains the implementation of both the CNF-based agent and the Random Walk agent.

- `wumpus_world.py`  
  Defines the Wumpus World environment, including world generation, percepts, and movement logic.

- `cnf_game.py`  
  Runs a single simulation of the CNF-based agent with Pygame visualization.

- `random_game.py`  
  Runs a single simulation of the Random Walk agent with Pygame visualization.

- `multiple_cnf.py`  
  Runs multiple CNF Agent games consecutively, with options to save failed game states.

- `multiple_random.py`  
  Runs multiple Random Walk Agent games consecutively, with similar logging options.

- `run.bat`, `time_CNF.bat`, `time_Random.bat`  
  (Windows batch files to run the simulations and benchmark timings.)

## How to Run

### Single Game Simulations

- **CNF-Based Simulation:**  
  Run the following command to start a simulation using the CNF agent (with optional debug output):
  ```bash
  python cnf_game.py --debug
  ```
  You can also load a pre-generated world (saved as a pickle file) by using the `--load` option:
  ```bash
  python cnf_game.py --load path/to/your/world.pkl
  ```

- **Random Walk Simulation:**  
  Run the following command to start a simulation using the Random Walk agent:
  ```bash
  python random_game.py
  ```

### Multiple Game Simulations

- **Multiple CNF Agent Games:**  
  Run multiple games with the CNF-based agent. You can set the number of games, enable display, and save failed games:
  ```bash
  python multiple_cnf.py --num-games 20 --save-failures --display
  ```
  Additional options include `--debug` and `--load` if you wish to start from a specific world.

- **Multiple Random Walk Agent Games:**  
  Similarly, run multiple simulations using the Random Walk agent:
  ```bash
  python multiple_random.py --num-games 20 --save-failures --display
  ```

### Using Batch Files (Windows)

For Windows users, batch files (`run.bat`, `time_CNF.bat`, `time_Random.bat`) are provided to simplify running the simulations and timing the executions. Simply double-click the appropriate batch file to run the corresponding simulation.

## Simulation Controls

- **Exiting the Simulation:**  
  During a simulation, close the Pygame window or press the `ESC` key to exit.
- **Visualization:**  
  The Pygame window displays:
  - The grid with cells outlined.
  - Pits (gray circles), Wumpus (red circle), and gold (gold circle).
  - The agent (blue circle).
  - A UI panel that logs each move, percepts, and game outcomes.

## Additional Notes

- The CNF-based agent uses logical inference to deduce hazards and plan safe moves, which can take additional computation time compared to the Random Walk agent.
- The world is re-generated until a winnable configuration (a safe path from the start to the gold) is produced.
- The code is structured to facilitate further modifications or enhancements, such as different world sizes or additional hazard types.

Enjoy exploring the Wumpus World and experimenting with AI-based reasoning!
``` 

Once you copy the text above, save it as `README.md` in your repository directory.
