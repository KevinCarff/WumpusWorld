import pygame
import sys
from wumpus_world import WumpusWorld
from agents import RandomWalkAgent

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

def simulate_random(tile_size=50, fps=2, max_steps=50):
    world = WumpusWorld(size=8, num_pits=3)
    agent = RandomWalkAgent(world)
    pygame.init()
    ui_panel_height = 200
    game_area_height = world.size * tile_size
    screen_width = world.size * tile_size
    screen_height = game_area_height + ui_panel_height
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Random Walk Simulation")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    ui_panel_rect = pygame.Rect(0, game_area_height, screen_width, ui_panel_height)
    move_logs = []
    step = 0
    running = True

    while running and step < max_steps and world.agent_alive and not world.gold_found:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
        current_pos = world.agent_pos
        percepts = world.get_percepts(current_pos)
        action = agent.choose_action()
        world.move_agent(get_new_position(current_pos, action))
        new_pos = world.agent_pos
        if not world.agent_alive:
            outcome = "Agent died!"
        elif world.gold_found:
            outcome = "Gold found! Agent wins!"
        else:
            outcome = "Moved"
        log_entry = f"Step {step}: {action} | New Pos: {new_pos} | {outcome} | Percepts: {percepts}"
        move_logs.append(log_entry)
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

if __name__ == "__main__":
    simulate_random()
