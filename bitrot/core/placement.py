# placement.py
import random
from core.data.config import GAME_WIDTH, GAME_HEIGHT, TILE_SIZE

def _is_colliding(rect, obstacles):
    """Checks if rect collides with any obstacle in the list."""
    return any(rect.colliderect(ob) for ob in obstacles)

def find_free_tile(rect, obstacles, items_on_ground=None, initial_pos=None, max_radius=10):
    if initial_pos:
        start_x = (initial_pos[0] // TILE_SIZE) * TILE_SIZE
        start_y = (initial_pos[1] // TILE_SIZE) * TILE_SIZE
    else:
        start_x = random.randint(0, (GAME_WIDTH // TILE_SIZE) - 1) * TILE_SIZE
        start_y = random.randint(0, (GAME_HEIGHT // TILE_SIZE) - 1) * TILE_SIZE

    rect.x = start_x
    rect.y = start_y

    if not _is_colliding(rect, obstacles):
        return (rect.x, rect.y)

    if initial_pos:
        for radius in range(1, max_radius + 1): 
            for i in range(-radius, radius + 1):
                for j in range(-radius, radius + 1):
                    if abs(i) < radius and abs(j) < radius:
                        continue

                    cand_x = start_x + i * TILE_SIZE
                    cand_y = start_y + j * TILE_SIZE

                    # Prevent returning negative or out-of-bounds positions
                    if cand_x < 0 or cand_y < 0:
                        continue

                    rect.x = cand_x
                    rect.y = cand_y

                    if not _is_colliding(rect, obstacles):
                        return (rect.x, rect.y)

    return None

def find_random_free_tile(rect, obstacles, items_on_ground):
    rect.x = random.randint(0, (GAME_WIDTH // TILE_SIZE) - 1) * TILE_SIZE
    rect.y = random.randint(0, (GAME_HEIGHT // TILE_SIZE) - 1) * TILE_SIZE

    max_attempts = (GAME_WIDTH // TILE_SIZE) * (GAME_HEIGHT // TILE_SIZE)

    for _ in range(max_attempts):
        collision = _is_colliding(rect, obstacles) or any(rect.colliderect(item.rect) for item in items_on_ground)
        if not collision:
            return (rect.x, rect.y)

        rect.x += TILE_SIZE
        if rect.x >= GAME_WIDTH:
            rect.x = 0
            rect.y += TILE_SIZE
            if rect.y >= GAME_HEIGHT:
                rect.y = 0

    return None