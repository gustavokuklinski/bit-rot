import pygame
from core.data.config import GAME_WIDTH, GAME_HEIGHT, WHITE, GRAY, font_12
from core.draw import draw_game
from core.events.mouse import handle_mouse_down, handle_right_click
from core.events.mouse_drag import handle_mouse_up, handle_mouse_motion
from core.data.localization import tr

def run_paused(game):
    if not getattr(game, 'is_mixer_paused', False):
        pygame.mixer.pause()
        pygame.mixer.music.pause()
        game.is_mixer_paused = True

    allowed_modals = ['status', 'messages', 'nearby', 'inventory', 'gear', 'container', 'belt', 'slots', 'mobile']
    game.modals = [m for m in game.modals if m.get('type') in allowed_modals]

    draw_game(game)

    # --- 1. PRE-RENDER TEXTS TO CALCULATE TOTAL WIDTH ---
    # We render these first so we know how wide the total banner needs to be
    txt_paused = font_12.render(tr('ui', "PAUSED"), False, (220, 70, 70))
    txt_sep = font_12.render("-", False, GRAY)
    txt_cont = font_12.render(tr('ui', "Continue"), False, WHITE)
    txt_save = font_12.render(tr('ui', "Save"), False, WHITE)
    txt_exit = font_12.render(tr('ui', "Exit"), False, WHITE)

    spacing = 12  # Space between elements
    # Total width = (PAUSED) + (sep) + (Continue) + (sep) + (Save) + (sep) + (Exit) + (paddings)
    total_content_width = (
        txt_paused.get_width() + 
        (txt_sep.get_width() * 3) + 
        txt_cont.get_width() + 
        txt_save.get_width() + 
        txt_exit.get_width() + 
        (spacing * 6) + 20 # 20 for left/right padding
    )

    # --- 2. CALCULATE STARTING X FOR CENTERING ---
    start_x = (GAME_WIDTH - total_content_width) // 2
    banner_height = 28
    
    # Draw Dark Gray Background Banner
    banner_rect = pygame.Rect(start_x, 0, total_content_width, banner_height)
    pygame.draw.rect(game.game_screen, (30, 30, 30, 240), banner_rect) # Darker gray
    pygame.draw.line(game.game_screen, (60, 60, 60), (start_x, banner_height), (start_x + total_content_width, banner_height), 1)

    # --- 3. DRAW ELEMENTS AND DEFINE HITBOXES ---
    current_x = start_x + 10
    y_offset = (banner_height - font_12.get_linesize()) // 2 # Vertical centering

    # Draw "PAUSED"
    game.game_screen.blit(txt_paused, (current_x, y_offset))
    current_x += txt_paused.get_width() + spacing

    # Helper to draw separator and return new X
    def draw_sep(x):
        game.game_screen.blit(txt_sep, (x, y_offset))
        return x + txt_sep.get_width() + spacing

    current_x = draw_sep(current_x)

    # Logic for Buttons (Hitboxes)
    # We create a Rect based on the text width for precise clicking
    btn_continue = pygame.Rect(current_x, 4, txt_cont.get_width(), 20)
    btn_save = pygame.Rect(current_x, 4, txt_save.get_width(), 20) # X will be set below
    btn_exit = pygame.Rect(current_x, 4, txt_exit.get_width(), 20) # X will be set below

    def draw_banner_btn(rect, text_surf):
        mouse_pos = game._get_scaled_mouse_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        color = WHITE if is_hovered else (150, 150, 150)
        
        # Render text with hover color
        txt_render = font_12.render(text_surf.get_text() if hasattr(text_surf, 'get_text') else tr('ui', "Continue"), False, color) 
        # Since we pre-rendered for width, we just render again for color
        # (Alternatively, use a variable to store the translation key)
        
        # To keep it simple, we use the pre-rendered one but tint it or just re-render:
        # We use a small trick: we know which text we are drawing
        game.game_screen.blit(txt_render, (rect.x, rect.y + (rect.height - txt_render.get_height())//2))
        return is_hovered

    # Modified draw_banner_btn to take the actual translation key
    def draw_btn_with_key(rect, key, hover_color, normal_color):
        mouse_pos = game._get_scaled_mouse_pos()
        is_hovered = rect.collidepoint(mouse_pos)
        color = hover_color if is_hovered else normal_color
        surf = font_12.render(tr('ui', key), False, color)
        game.game_screen.blit(surf, (rect.x, rect.y + (rect.height - surf.get_height())//2))
        return is_hovered

    # Drawing and Positioning Buttons
    hover_cont = draw_btn_with_key(btn_continue, "Continue", WHITE, (150, 150, 150))
    current_x += btn_continue.width + spacing
    
    current_x = draw_sep(current_x)
    
    btn_save.x = current_x
    hover_save = draw_btn_with_key(btn_save, "Save", WHITE, (150, 150, 150))
    current_x += btn_save.width + spacing
    
    current_x = draw_sep(current_x)
    
    btn_exit.x = current_x
    hover_exit = draw_btn_with_key(btn_exit, "Exit", WHITE, (150, 150, 150))

    # --- 4. EVENT HANDLING ---
    mouse_pos = game._get_scaled_mouse_pos()
    events = game.get_events()

    for event in events:
        if getattr(game, 'joystick_handler', None):
            game.joystick_handler.process_event(event)

        if event.type == pygame.QUIT:
            game.running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()
            game.is_mixer_paused = False
            game.game_state = 'PLAYING'
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if btn_continue.collidepoint(mouse_pos):
                    pygame.mixer.unpause()
                    pygame.mixer.music.unpause()
                    game.is_mixer_paused = False
                    game.game_state = 'PLAYING'
                elif btn_save.collidepoint(mouse_pos):
                    game.save_game()
                elif btn_exit.collidepoint(mouse_pos):
                    pygame.mixer.unpause()
                    pygame.mixer.music.unpause()
                    game.is_mixer_paused = False
                    if hasattr(game, 'world_time') and game.world_time:
                        game.world_time.stop_all_sounds()
                    game.game_state = 'MENU'
                else:
                    handle_mouse_down(game, event, mouse_pos)
            elif event.button in [4, 5]:
                handle_mouse_down(game, event, mouse_pos)
            elif event.button == 3:
                handle_right_click(game, mouse_pos)
                
        elif event.type == pygame.MOUSEBUTTONUP:
            handle_mouse_up(game, event, mouse_pos)
        elif event.type == pygame.MOUSEMOTION:
            handle_mouse_motion(game, event, mouse_pos)

    game._update_screen()