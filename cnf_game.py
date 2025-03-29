import argparse
import pickle
import random
import pygame
import sys
from wumpus_world import WumpusWorld
from agents import CNFAgent

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
    # Draw the agent.
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

def simulate_cnf(tile_size=50, fps=2, max_steps=200, debug=False, load_file=None):
    # Load world from pickle if a file is provided; otherwise, generate a new world.
    if load_file:
        with open(load_file, 'rb') as f:
            world = pickle.load(f)
        print(f"Loaded world from {load_file}")
    else:
        world = WumpusWorld(size=8, num_pits=3)
    
    agent = CNFAgent(world, debug=debug)
    
    pygame.init()
    ui_panel_height = 200
    game_area_height = world.size * tile_size
    screen_width = world.size * tile_size
    screen_height = game_area_height + ui_panel_height
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("CNF-based Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    ui_panel_rect = pygame.Rect(0, game_area_height, screen_width, ui_panel_height)
    
    move_logs = []
    step = 0
    running = True

    current_pos = world.agent_pos
    percepts = world.get_percepts(current_pos)
    
    while running and step < max_steps and world.agent_alive and not world.gold_found:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
        current_pos = world.agent_pos
        action = agent.choose_action()
        # if debug:
        #     print(f"[DEBUG] Agent chose action: {action}")
        world.move_agent(get_new_position(current_pos, action))
        current_pos = world.agent_pos
        percepts = world.get_percepts(current_pos)
        if debug:
        #     print(f"[DEBUG] Step {step}: Agent at {current_pos} sees {percepts}")
            agent.display_world_view()  # Print the agent's CNF-based world view.
        if not world.agent_alive:
            outcome = "Agent died!"
        elif world.gold_found:
            outcome = "Gold found! Agent wins!"
        else:
            outcome = "Moved"
        move_logs.append(f"Step {step}: {action} | New Pos: {current_pos} | {outcome} | Percepts: {percepts}")
        step += 1
        screen.fill((255, 255, 255))
        draw_world(screen, world, tile_size)
        draw_ui_panel(screen, move_logs, ui_panel_rect, font)
        pygame.display.flip()
        clock.tick(fps)

    if not world.agent_alive:
        move_logs.append("Game Over: Agent died!")
    elif world.gold_found:
        move_logs.append("Agent found the gold!")
    screen.fill((255, 255, 255))
    draw_world(screen, world, tile_size)
    draw_ui_panel(screen, move_logs, ui_panel_rect, font)
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                waiting = False
                pygame.quit()
                sys.exit()
    return world, move_logs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CNF-based Wumpus World Simulation")
    parser.add_argument("--load", type=str, default=None, help="Load a world from a pickle file")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()
    
    simulate_cnf(debug=args.debug, load_file=args.load)
