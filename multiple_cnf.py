import argparse
import pickle
import os
import random
import sys
from wumpus_world import WumpusWorld
from agents import CNFAgent

# If display is enabled, we import and use pygame.
try:
    import pygame
except ImportError:
    pygame = None

def get_new_position(pos, direction):
    x, y = pos
    if direction == 'up':
        return (x - 1, y)
    elif direction == 'down':
        return (x + 1, y)
    elif direction == 'left':
        return (x, y - 1)
    elif direction == 'right':
        return (x, y + 1)
    return pos

# These drawing functions are used only if display is enabled.
def draw_world(screen, world, tile_size):
    for i in range(world.size):
        for j in range(world.size):
            rect = pygame.Rect(j * tile_size, i * tile_size, tile_size, tile_size)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)
            cell = world.grid[i][j]
            center = (j * tile_size + tile_size // 2, i * tile_size + tile_size // 2)
            if cell['pit']:
                pygame.draw.circle(screen, (50, 50, 50), center, tile_size // 4)
            if cell['wumpus']:
                pygame.draw.circle(screen, (255, 0, 0), center, tile_size // 4)
            if cell['gold']:
                pygame.draw.circle(screen, (255, 215, 0), center, tile_size // 4)
    # Draw agent.
    agent_x, agent_y = world.agent_pos
    agent_center = (agent_y * tile_size + tile_size // 2, agent_x * tile_size + tile_size // 2)
    pygame.draw.circle(screen, (0, 0, 255), agent_center, tile_size // 4)

def draw_ui_panel(screen, move_logs, panel_rect, font):
    pygame.draw.rect(screen, (200, 200, 200), panel_rect)
    log_start_y = panel_rect.top + 10
    logs_to_display = move_logs[-8:]
    for idx, log in enumerate(logs_to_display):
        text_surface = font.render(log, True, (0, 0, 0))
        screen.blit(text_surface, (panel_rect.left + 10, log_start_y + idx * 25))

def run_game(tile_size=50, fps=2, max_steps=200, debug=False, load_file=None, display=True):
    # If load_file is provided, load the world from that file; otherwise, generate a new one.
    if load_file:
        with open(load_file, 'rb') as f:
            world = pickle.load(f)
        print(f"Loaded world from {load_file}")
    else:
        world = WumpusWorld(size=8, num_pits=3)
    agent = CNFAgent(world, debug=debug)
    
    if display and pygame:
        pygame.init()
        ui_panel_height = 200
        game_area_height = world.size * tile_size
        screen_width = world.size * tile_size
        screen_height = game_area_height + ui_panel_height
        screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("CNF-based Simulation")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("Arial", 20)
    else:
        if debug:
            print("[DEBUG] Running in headless mode (no display).")
    
    move_logs = []
    step = 0
    running = True

    while running and step < max_steps and world.agent_alive and not world.gold_found:
        if display and pygame:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
        current_pos = world.agent_pos
        action = agent.choose_action()
        if debug:
            print(f"[DEBUG] Step {step}: Agent at {current_pos} chooses {action}")
        world.move_agent(get_new_position(current_pos, action))
        current_pos = world.agent_pos
        percepts = world.get_percepts(current_pos)
        if debug:
            print(f"[DEBUG] Step {step}: Agent now at {current_pos} perceives {percepts}")
            agent.display_world_view()  # Print the agent's world view based on CNF.
        if not world.agent_alive:
            outcome = "Agent died!"
        elif world.gold_found:
            outcome = "Gold found! Agent wins!"
        else:
            outcome = "Moved"
        move_logs.append(f"Step {step}: {action} | New Pos: {current_pos} | {outcome} | Percepts: {percepts}")
        step += 1
        if display and pygame:
            screen.fill((255, 255, 255))
            draw_world(screen, world, tile_size)
            draw_ui_panel(screen, move_logs, pygame.Rect(0, game_area_height, screen_width, ui_panel_height), font)
            pygame.display.flip()
            clock.tick(fps)
        else:
            print(move_logs[-1])
    
    if not world.agent_alive:
        move_logs.append("Game Over: Agent died!")
    elif world.gold_found:
        move_logs.append("Agent found the gold!")
    
    if display and pygame:
        screen.fill((255, 255, 255))
        draw_world(screen, world, tile_size)
        draw_ui_panel(screen, move_logs, pygame.Rect(0, game_area_height, screen_width, ui_panel_height), font)
        pygame.display.flip()
    return world, move_logs

def run_games(num_games, save_failures, load_file, debug, display):
    failures = 0
    game_index = 0
    while game_index < num_games:
        print(f"Running game {game_index}")
        world, logs = run_game(debug=debug, load_file=load_file, display=display)
        if not world.agent_alive:
            failures += 1
            if save_failures:
                filename = f"failed_game_{game_index}.pkl"
                world.agent_pos = (world.size-1, 0)
                world.agent_alive = True
                with open(filename, 'wb') as f:
                    pickle.dump(world, f)
                print(f"Game {game_index} failed. Saved world to {filename}")
        game_index += 1
    print(f"Total games: {num_games}, Failures: {failures}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run multiple CNF Agent games and save failures.")
    parser.add_argument("--num-games", type=int, default=10, help="Number of games to run")
    parser.add_argument("--save-failures", action="store_true", help="Save game worlds where the agent fails")
    parser.add_argument("--load", type=str, help="Load a specific world file instead of generating a new one")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--display", action="store_true", help="Enable Pygame display")
    args = parser.parse_args()

    run_games(args.num_games, args.save_failures, args.load, args.debug, args.display)
