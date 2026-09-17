# core/states/chunk_loading.py

import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, WHITE, font_16
from core.data.localization import tr

def run_chunk_loading(game):
    current_time = pygame.time.get_ticks()

    # 1. Initialize timer on first frame of entering the chunk loading state
    if not hasattr(game, '_chunk_load_timer') or game._chunk_load_timer is None:
        game._chunk_load_timer = current_time

    # Duration to show the loading screen (2000 ms = 2 seconds)
    LOADING_DURATION_MS = 2000

    # 2. Clean dark backdrop
    game.game_screen.fill((20, 20, 20))

    center_x = GAME_WIDTH // 2
    center_y = GAME_HEIGHT // 2

    # 3. Centered "Loading Chunk" message with animated dots
    dots = "." * ((current_time // 400) % 4)
    loading_text = f"{tr('ui', 'Loading Chunk')}{dots}"
    
    title_surf = font_16.render(loading_text, False, WHITE)
    title_rect = title_surf.get_rect(center=(center_x, center_y))
    game.game_screen.blit(title_surf, title_rect)

    # 4. Handle events (keep window responsive and handle exit)
    for event in game.get_events():
        if event.type == pygame.QUIT:
            game.running = False
            return

    # 5. Automatically resume game after the timer expires
    elapsed = current_time - game._chunk_load_timer
    if elapsed >= LOADING_DURATION_MS:
        game._chunk_load_timer = None
        game.game_state = 'PLAYING'
        
        # Reset frame delta time to prevent physics/movement lag spikes
        game.dt_ms = 16
        game.dt_mult = 1.0
        game.clock.tick(60)
        return

    game._update_screen()