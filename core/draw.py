import pygame
import math
from data.config import *
from core.ui.helpers import draw_menu, draw_game_over
from core.ui.inventory import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect
from core.ui.container import draw_container_view, get_container_slot_rect
from core.ui.status import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.ui.nearby import draw_nearby_modal
from core.ui.helpers import draw_inventory_button, draw_status_button, draw_nearby_button
from core.ui.tooltip import draw_tooltip


def draw_game(game):
    # Clear the main screen that holds the game and UI panels
    game.virtual_screen.fill(PANEL_COLOR)

    # --- World Rendering with Pixelated Zoom ---

    # 1. Create a temporary surface for the world view.
    # Its size is the virtual screen size divided by the zoom level.
    zoom = game.zoom_level
    view_w = int(VIRTUAL_SCREEN_WIDTH / zoom)
    view_h = int(VIRTUAL_GAME_HEIGHT / zoom)
    world_view_surface = pygame.Surface((view_w, view_h))
    world_view_surface.fill(GAME_BG_COLOR) # Set the world background color

    # 2. Calculate a single camera offset to center the player.
    offset_x = view_w / 2 - game.player.rect.centerx
    offset_y = view_h / 2 - game.player.rect.centery



    # 3. Draw all world objects onto the temporary surface at 1:1 scale.
    for image, rect in game.renderable_tiles:
        world_view_surface.blit(image, rect.move(offset_x, offset_y))

    for item in game.items_on_ground:
        draw_pos = item.rect.move(offset_x, offset_y)
        if getattr(item, 'image', None):
            world_view_surface.blit(item.image, draw_pos)
        else:
            pygame.draw.rect(world_view_surface, getattr(item, 'color', WHITE), draw_pos)

    for p in game.projectiles:
        p.draw(world_view_surface, offset_x, offset_y)

    for zombie in game.zombies:
        zombie.draw(world_view_surface, offset_x, offset_y)

    game.player.draw(world_view_surface, offset_x, offset_y)

    # 4. Scale the entire world view surface up to the final game size.
    scaled_world = pygame.transform.scale(world_view_surface, (GAME_WIDTH, GAME_HEIGHT))

    # 5. Blit the scaled world onto the main virtual screen.
    game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
    game.virtual_screen.blit(scaled_world, game_rect)

    # --- UI & Effects Rendering (Unaffected by Zoom) ---
    # These elements are drawn on top of the scaled world, so they remain sharp.

    # Gun flash effect is drawn relative to the screen center, where the player is.
    if game.player.gun_flash_timer > 0:
        center_x = GAME_OFFSET_X + GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        flash_radius = (TILE_SIZE // 2) * zoom # Scale flash size with zoom
        pygame.draw.circle(game.virtual_screen, YELLOW, (center_x, center_y), flash_radius)
        game.player.gun_flash_timer -= 1

    top_tooltip = None
    game.modal_buttons = []
    for modal in game.modals:
        if modal['type'] == 'status':
            buttons = draw_status_modal(game.virtual_screen, game.player, modal, game.assets, game.zombies_killed)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'inventory':
            tooltip, *buttons = draw_inventory_modal(game.virtual_screen, game.player, modal, game.assets, game._get_scaled_mouse_pos())
            top_tooltip = tooltip or top_tooltip
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'container':
            buttons = draw_container_view(game.virtual_screen, game, modal['item'], modal, game.assets)
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'nearby':
            buttons = draw_nearby_modal(game.virtual_screen, game, modal, game.assets)
            game.modal_buttons.extend(buttons)
    
    game.status_button_rect = draw_status_button(game.virtual_screen)
    game.inventory_button_rect = draw_inventory_button(game.virtual_screen)
    game.nearby_button_rect = draw_nearby_button(game.virtual_screen)

    highlighted_rect = None
    highlighted_allowed = False
    if (game.is_dragging and game.dragged_item) or (game.drag_candidate and game.drag_candidate[0]):
        preview_item = game.dragged_item if game.is_dragging else game.drag_candidate[0]
        for modal in reversed(game.modals):
            if modal['type'] == 'inventory':
                for i in range(len(game.player.belt)):
                    slot = get_belt_slot_rect_in_modal(i, modal['position'])
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = (preview_item.item_type != 'backpack')
                        break
                if highlighted_rect:
                    break
                for i in range(5):
                    slot = get_inventory_slot_rect(i, modal['position'])
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = True
                        break
                if highlighted_rect:
                    break
                slot = get_backpack_slot_rect(modal['position'])
                if slot.collidepoint(game._get_scaled_mouse_pos()):
                    highlighted_rect = slot
                    highlighted_allowed = (preview_item.item_type == 'backpack')
                    break
            elif modal['type'] == 'container':
                cont = modal['item']
                for i in range(min(cont.capacity, len(cont.inventory) + 16)):
                    slot = get_container_slot_rect(modal['position'], i)
                    if slot.collidepoint(game._get_scaled_mouse_pos()):
                        highlighted_rect = slot
                        highlighted_allowed = (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                        break
                if highlighted_rect:
                    break

        if highlighted_rect:
            overlay = pygame.Surface((highlighted_rect.width, highlighted_rect.height), pygame.SRCALPHA)
            color = (50, 220, 50, 80) if highlighted_allowed else (220, 50, 50, 80)
            overlay.fill(color)
            game.virtual_screen.blit(overlay, highlighted_rect.topleft)
            pygame.draw.rect(game.virtual_screen, YELLOW if highlighted_allowed else RED, highlighted_rect, 2)

        if preview_item and getattr(preview_item, 'image', None):
            img = pygame.transform.scale(preview_item.image, (int(highlighted_rect.height * 0.9) if highlighted_rect else 40, int(highlighted_rect.height * 0.9) if highlighted_rect else 40))
            img_rect = img.get_rect()
            img_rect.topleft = (game._get_scaled_mouse_pos()[0] - game.drag_offset[0], game._get_scaled_mouse_pos()[1] - game.drag_offset[1])
            game.virtual_screen.blit(img, img_rect)
        elif preview_item:
            rect_w, rect_h = (int(highlighted_rect.width * 0.8), int(highlighted_rect.height * 0.8)) if highlighted_rect else (40, 40)
            preview_rect = pygame.Rect(game._get_scaled_mouse_pos()[0] - rect_w//2, game._get_scaled_mouse_pos()[1] - rect_h//2, rect_w, rect_h)
            s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            s.fill((*preview_item.color, 180))
            game.virtual_screen.blit(s, preview_rect.topleft)

    if top_tooltip:
        tip_rect = top_tooltip['rect']
        item = top_tooltip['item']
        frac = top_tooltip['frac']
        bar_color = top_tooltip['bar_color']

        tip_s = pygame.Surface((tip_rect.width, tip_rect.height), pygame.SRCALPHA)
        tip_s.fill((10, 10, 10, 220))
        game.virtual_screen.blit(tip_s, tip_rect.topleft)
        pygame.draw.rect(game.virtual_screen, WHITE, tip_rect, 1)

        name_surf = game.assets['font'].render(f"{item.name}", True, WHITE)
        type_surf = game.assets['font'].render(f"Type: {item.item_type}", True, GRAY)
        game.virtual_screen.blit(name_surf, (tip_rect.x + 8, tip_rect.y + 6))
        game.virtual_screen.blit(type_surf, (tip_rect.x + 8, tip_rect.y + 26))

        bar_x = tip_rect.x + 8
        bar_y = tip_rect.y + 42
        bar_w = tip_rect.width - 16
        bar_h = 10
        pygame.draw.rect(game.virtual_screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
        fill_w = int(max(0.0, min(1.0, frac)) * bar_w)
        pygame.draw.rect(game.virtual_screen, bar_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(game.virtual_screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

    if game.hovered_item and not game.context_menu['active']:
        draw_tooltip(game.virtual_screen, game.hovered_item, game._get_scaled_mouse_pos())

    if game.context_menu['active']:
        draw_context_menu(game.virtual_screen, game.context_menu, game._get_scaled_mouse_pos())

    # Set cursor
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
        pygame.mouse.set_cursor(game.assets.get('aim_cursor') or pygame.cursors.arrow)
    else:
        pygame.mouse.set_cursor(game.assets.get('custom_cursor') or pygame.cursors.arrow)