import pygame
from core.data.config import *
from core.data.localization import tr

def draw_clock_tab(surface, game, modal, assets):
    # Adjust offsets to start inside the mobile screen area
    y_offset = modal['rect'].y + 80 
    center_x = modal['rect'].centerx

    # --- 1. Day/Night Icon & Label ---
    # Update logic: Day icon only during full day or transition to night (dusk)
    current_state = game.world_time.state
    is_day_icon = current_state in ["DAY", "TRANSITION_TO_NIGHT", "TRANSITION_TO_DAY"]
    
    # Select Icon
    icon = assets.get('day_icon') if is_day_icon else assets.get('night_icon')
    
    # Label Logic
    if current_state == "DAY":
        label_text = tr('ui', "Daylight")
    elif current_state == "NIGHT":
        label_text = tr('ui', "Darkness")
    elif current_state == "TRANSITION_TO_NIGHT":
        label_text = tr('ui', "Twilight")
    else:
        label_text = tr('ui', "Sunrise")
    
    # Draw Icon
    if icon:
        icon_rect = icon.get_rect(center=(center_x - 40, y_offset))
        surface.blit(icon, icon_rect)
        
        # Draw Label next to icon
        label_surf = font.render(label_text, True, WHITE)
        label_rect = label_surf.get_rect(midleft=(icon_rect.right + 10, icon_rect.centery))
        surface.blit(label_surf, label_rect)
    else:
        # Fallback text if icons fail
        label_surf = font.render(label_text, True, WHITE)
        label_rect = label_surf.get_rect(center=(center_x, y_offset))
        surface.blit(label_surf, label_rect)

    y_offset += 40

    # --- 2. Large Digital Clock ---
    try:
        # Calculate exact time from game_time_ms
        day_progress = game.world_time.game_time_ms / game.world_time.day_length_ms
        total_minutes_in_day = int(day_progress * 24 * 60)
        
        hour = (total_minutes_in_day // 60) % 24
        raw_minute = total_minutes_in_day % 60
        minute = raw_minute - (raw_minute % 10)
        
        time_str = f"{hour:02d}:{minute:02d}"
    except Exception:
        time_str = "00:00"
    
    # Render Large Text
    base_time_surf = font_14.render(time_str, True, WHITE)
    # Scale up by 1.8x for visibility
    scaled_w = int(base_time_surf.get_width() * 1.8)
    scaled_h = int(base_time_surf.get_height() * 1.8)
    time_surf = pygame.transform.scale(base_time_surf, (scaled_w, scaled_h))
    
    time_rect = time_surf.get_rect(center=(center_x, y_offset))
    surface.blit(time_surf, time_rect)
    
    y_offset += time_rect.height + 20

    # --- 3. Stats (Kills) ---
    zombies_killed = game.zombies_killed
    kills_text = f"{tr('ui', 'Kills:')} {zombies_killed}"
    kills_surf = font.render(kills_text, True, WHITE) 
    kills_rect = kills_surf.get_rect(center=(center_x, y_offset))
    surface.blit(kills_surf, kills_rect)

    y_offset += 20

    # --- 4. Time Survived (In-Game Time) ---
    try:
        days_survived = game.world_time.day_count
        # Calculate hours passed today
        hours_today = (total_minutes_in_day // 60)
        
        alive_text = f"{tr('ui', 'Survived:')} {days_survived} {tr('ui', 'Days')}"
    except Exception:
        alive_text = f"{tr('ui', 'Survived:')} --"
        
    alive_surf = font.render(alive_text, True, WHITE)
    alive_rect = alive_surf.get_rect(center=(center_x, y_offset))
    surface.blit(alive_surf, alive_rect)

    y_offset += 20

    # --- 5. Weather Info ---
    try:
        current_weather = getattr(game.world_time, 'weather', 'CLEAR')
        weather_timer_ms = getattr(game.world_time, 'weather_timer', 0)
        
        # Convert ms to in-game minutes remaining
        timer_in_game_minutes = int((weather_timer_ms / game.world_time.day_length_ms) * 24 * 60)
        
        timer_hours = timer_in_game_minutes // 60
        timer_minutes = timer_in_game_minutes % 60
        
        if current_weather == 'CLEAR':
            weather_text = f"{tr('ui', 'Weather: Clear')} ({tr('ui', 'Rain in')} {timer_hours}h)"
        else:
            weather_text = tr('ui', "Weather: Raining")
    except Exception:
        weather_text = tr('ui', "Weather: Unknown")
        
    weather_surf = font.render(weather_text, True, WHITE)
    weather_rect = weather_surf.get_rect(center=(center_x, y_offset))
    surface.blit(weather_surf, weather_rect)