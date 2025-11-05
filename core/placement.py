import random
from data.config import GAME_WIDTH, GAME_HEIGHT, TILE_SIZE

def find_free_tile(rect, obstacles, items_on_ground, initial_pos=None, max_radius=10):
    """
    Finds a free tile for the given rect, avoiding obstacles and other items.
    The position is snapped to the grid.
    If initial_pos is provided, it searches outwards from that position.
    Otherwise, it searches for a random free tile.
    """
    if initial_pos:
        start_x = (initial_pos[0] // TILE_SIZE) * TILE_SIZE
        start_y = (initial_pos[1] // TILE_SIZE) * TILE_SIZE
    else:
        start_x = random.randint(0, (GAME_WIDTH // TILE_SIZE) - 1) * TILE_SIZE
        start_y = random.randint(0, (GAME_HEIGHT // TILE_SIZE) - 1) * TILE_SIZE

    rect.x = start_x
    rect.y = start_y

    # Check if the initial position is free
    collision = False
    for ob in obstacles:
        if rect.colliderect(ob):
            collision = True
            break
    if not collision:
        for item in items_on_ground:
            if rect.colliderect(item.rect):
                collision = True
                break
    if not collision:
        return True

    # If not, and we have an initial position, search outwards
    if initial_pos:
        for radius in range(1, max_radius + 1): # Search in a <max_radius>-tile radius
            for i in range(-radius, radius + 1):
                for j in range(-radius, radius + 1):
                    if abs(i) < radius and abs(j) < radius:
                        continue

                    rect.x = start_x + i * TILE_SIZE
                    rect.y = start_y + j * TILE_SIZE

                    if not (0 <= rect.x < GAME_WIDTH and 0 <= rect.y < GAME_HEIGHT):
                        continue

                    collision = False
                    for ob in obstacles:
                        if rect.colliderect(ob):
                            collision = True
                            break
                    if not collision:
                        for item in items_on_ground:
                            if rect.colliderect(item.rect):
                                collision = True
                                break
                    
                    if not collision:
                        return True # Found a free tile

    # If no free tile was found within the radius, return False
    return False

def find_random_free_tile(rect, obstacles, items_on_ground):
    rect.x = random.randint(0, (GAME_WIDTH // TILE_SIZE) - 1) * TILE_SIZE
    rect.y = random.randint(0, (GAME_HEIGHT // TILE_SIZE) - 1) * TILE_SIZE

    attempts = 0
    max_attempts = (GAME_WIDTH // TILE_SIZE) * (GAME_HEIGHT // TILE_SIZE)

    while attempts < max_attempts:
        collision = False
        for ob in obstacles:
            if rect.colliderect(ob):
                collision = True
                break
        if not collision:
            for item in items_on_ground:
                if rect.colliderect(item.rect):
                    collision = True
                    break
        
        if not collision:
            return True

        rect.x += TILE_SIZE
        if rect.x >= GAME_WIDTH:
            rect.x = 0
            rect.y += TILE_SIZE
            if rect.y >= GAME_HEIGHT:
                rect.y = 0
        
        attempts += 1

    return False
