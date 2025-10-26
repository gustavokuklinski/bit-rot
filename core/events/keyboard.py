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
