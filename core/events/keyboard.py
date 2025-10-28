import pygame
import uuid
from data.config import *

def toggle_inventory_modal(game):
    inventory_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'inventory':
            game.modals.remove(modal)
            inventory_modal_exists = True
            break
    if not inventory_modal_exists:
        new_inventory_modal = {
            'id': uuid.uuid4(),
            'type': 'inventory',
            'item': None,
            'position': game.last_modal_positions['inventory'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(game.last_modal_positions['inventory'][0], game.last_modal_positions['inventory'][1], INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT),            'minimized': False
        }
        game.modals.append(new_inventory_modal)

def toggle_status_modal(game):
    status_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'status':
            game.modals.remove(modal)
            status_modal_exists = True
            break
    if not status_modal_exists:
        new_status_modal = {
            'id': uuid.uuid4(),
            'type': 'status',
            'item': None,
            'position': game.last_modal_positions['status'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(game.last_modal_positions['status'][0], game.last_modal_positions['status'][1], STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT),
            'minimized': False
        }
        game.modals.append(new_status_modal)

def toggle_nearby_modal(game):
    nearby_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'nearby':
            game.modals.remove(modal)
            nearby_modal_exists = True
            break
    if not nearby_modal_exists:
        new_nearby_modal = {
            'id': uuid.uuid4(),
            'type': 'nearby',
            'item': None,
            'position': game.last_modal_positions['nearby'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(game.last_modal_positions['nearby'][0], game.last_modal_positions['nearby'][1], NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT),
            'minimized': False
        }
        game.modals.append(new_nearby_modal)

def toggle_messages_modal(game):
    messages_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'messages':
            game.modals.remove(modal)
            messages_modal_exists = True
            break
    if not messages_modal_exists:
        new_messages_modal = {
            'id': uuid.uuid4(),
            'type': 'messages',
            'item': None,
            'position': game.last_modal_positions['messages'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(game.last_modal_positions['messages'][0], game.last_modal_positions['messages'][1], MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT),
            'minimized': False
        }
        game.modals.append(new_messages_modal)

def toggle_pause(game):
    if game.game_state == 'PLAYING':
        game.game_state = 'PAUSED'
    elif game.game_state == 'PAUSED':
        game.game_state = 'PLAYING'

def handle_keyboard_events(game, event):
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_F2:
            toggle_pause(game)

        if event.key == pygame.K_i:
            toggle_inventory_modal(game)

        if event.key == pygame.K_h:
            toggle_status_modal(game)
        
        if event.key == pygame.K_n:
            toggle_nearby_modal(game)
        
        if event.key == pygame.K_m:
            toggle_messages_modal(game)
        
        if event.key == pygame.K_r:
            game.player.reload_active_weapon()

        if event.key == pygame.K_e:
            from core.events.game_actions import try_grab_item
            try_grab_item(game)

        if event.key == pygame.K_ESCAPE:
            if game.modals:
                game.modals.pop()

        if pygame.K_1 <= event.key <= pygame.K_5:
            slot_index = event.key - pygame.K_1
            item = game.player.belt[slot_index]
            if item:
                if item.item_type == 'consumable':
                    game.player.consume_item(item, 'belt', slot_index)
                elif item.item_type == 'weapon' or item.item_type == 'tool':
                    if game.player.active_weapon == item:
                        game.player.active_weapon = None
                        print(f"Unequipped {item.name}.")
                    else:
                        game.player.active_weapon = item
                        print(f"Equipped {item.name}.")
            else:
                game.player.active_weapon = None
                print(f"Belt slot {slot_index + 1} is empty. Unequipped.")

        zoom_step = 1
        if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS: # Handles '+' (often requires shift=equals)
            game.zoom_level += zoom_step
            game.zoom_level = min(game.zoom_level, NEAR_ZOOM) # Clamp to max zoom
        elif event.key == pygame.K_MINUS: # Handles '-'
            game.zoom_level -= zoom_step
            game.zoom_level = max(FAR_ZOOM, game.zoom_level) # Clamp to min zoom
