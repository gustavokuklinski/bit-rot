import pygame
from data.config import *

def draw_clock_tab(surface, game, modal, assets):
    y_offset = modal['rect'].y + 80 # Position below header and tabs
    x_offset = modal['rect'].x + 20

    # 1. Get Current Hour
    try:
        current_hour = game.world_time.current_hour
        hour_text = f"{current_hour:02d}:00"
    except Exception:
        hour_text = "Unknown"
    
    hour_surf = large_font.render(hour_text, True, WHITE)
    hour_rect = hour_surf.get_rect(centerx=modal['rect'].centerx, y=y_offset)
    surface.blit(hour_surf, hour_rect)
    
    y_offset += hour_surf.get_height() + 30

    # 2. Get Zombies Killed
    zombies_killed = game.zombies_killed
    kills_text = f"Kills: {zombies_killed}"
    kills_surf = font.render(kills_text, True, WHITE)
    kills_rect = kills_surf.get_rect(centerx=modal['rect'].centerx, y=y_offset)
    surface.blit(kills_surf, kills_rect)

    y_offset += kills_surf.get_height() + 10

    # 3. Get Time Alive
    try:
        time_alive_ms = pygame.time.get_ticks() - game.game_start_time
        total_seconds = time_alive_ms // 1000
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        alive_text = f"Survived: {days}d {hours}h {minutes}m"
    except Exception:
        alive_text = "Survived: --"
        
    alive_surf = font.render(alive_text, True, WHITE)
    alive_rect = alive_surf.get_rect(centerx=modal['rect'].centerx, y=y_offset)
    surface.blit(alive_surf, alive_rect)