import pygame
from core.data.config import PANEL_COLOR
from core.draw.camera import update_camera
from core.draw.world import draw_world
from core.draw.lighting import draw_lighting
from core.draw.entities import draw_entities
from core.draw.effects import draw_world_effects, draw_screen_effects
from core.draw.ui import draw_hovers, draw_ui

def draw_game(game):
    game.game_screen.fill(PANEL_COLOR)

    # 1. Camera & Viewport Calculations
    view_w, view_h, zoom, final_w, final_h, offset_x, offset_y, screen_rect = update_camera(game)

    # Surface Caching Initialization
    if not hasattr(game, 'cached_view_surface') or game.cached_view_surface.get_size() != (view_w, view_h):
        game.cached_view_surface = pygame.Surface((view_w, view_h)).convert()
        game.particle_scratch = pygame.Surface((16, 16), pygame.SRCALPHA).convert_alpha()
    
    world_view_surface = game.cached_view_surface
    world_view_surface.fill((20, 20, 20))

    # --- THE RENDER PIPELINE ---
    
    # 2. Render Environment
    draw_world(game, world_view_surface, offset_x, offset_y, view_w, view_h)

    # 3. Render Characters, Items, and Vehicles
    draw_entities(game, world_view_surface, offset_x, offset_y, view_w, view_h, screen_rect, zoom)

    # 4. Render World-Bound Effects (Roofs & Splashes)
    draw_world_effects(game, world_view_surface, offset_x, offset_y, view_w, view_h)

    # 5. Render Object Hovers
    target_world_rect = draw_hovers(game, world_view_surface, offset_x, offset_y, screen_rect, zoom)

    # 6. Apply Lighting & FOW
    draw_lighting(game, world_view_surface, offset_x, offset_y, view_w, view_h)

    # 7. Blit the World onto the Screen (handling zoom)
    game_rect = pygame.Rect(game.viewport_left_offset, 0, final_w, final_h)
    if zoom == 1.0:
        game.game_screen.blit(world_view_surface, game_rect)
    else:
        if not hasattr(game, 'scaled_world_cache') or game.scaled_world_cache.get_size() != (final_w, final_h):
            game.scaled_world_cache = pygame.Surface((final_w, final_h)).convert()
        pygame.transform.scale(world_view_surface, (final_w, final_h), game.scaled_world_cache)
        game.game_screen.blit(game.scaled_world_cache, game_rect)

    # 8. Overlay Screen Effects (CRT, Rain, Gun Flash, Chat)
    draw_screen_effects(game, offset_x, offset_y, zoom)

    # 9. Draw UI, Modals, and Tooltips
    draw_ui(game, offset_x, offset_y, zoom, final_h, screen_rect, target_world_rect)