import pygame
import uuid
import core.data.config
from core.data.config import *

# Import game actions (Moved to top for cleaner code, assuming no circular dependency)
# If circular dependency errors occur, move this back inside handle_keyboard_events
from core.events.game_actions import try_grab_item

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
            'rect': pygame.Rect(game.last_modal_positions['inventory'][0], game.last_modal_positions['inventory'][1], INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT),
            'minimized': False
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


def toggle_gear_modal(game):
    gear_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'gear':
            game.modals.remove(modal)
            gear_modal_exists = True
            break
    if not gear_modal_exists:
        new_gear_modal = {
            'id': uuid.uuid4(),
            'type': 'gear',
            'item': None,
            'position': game.last_modal_positions.get('gear', (700, 10)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(game.last_modal_positions.get('gear', (700, 10))[0], 
                                game.last_modal_positions.get('gear', (700, 10))[1], 
                                GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
            'minimized': False
        }
        game.modals.append(new_gear_modal)


def toggle_pause(game):
    if game.game_state == 'PLAYING':
        game.game_state = 'PAUSED'
        # Calls the method we added to Game class in the previous step
        game.capture_pause_screen() 
    elif game.game_state == 'PAUSED':
        game.game_state = 'PLAYING'

def handle_keyboard_events(game, event):
    if event.type == pygame.KEYDOWN:
        # --- Global Keys (Work in Play/Pause) ---
        if event.key == pygame.K_F2:
            toggle_pause(game)
            return # Stop processing other keys if pausing

        if event.key == pygame.K_ESCAPE:
            if game.modals:
                game.modals.pop()
                return
            else:
                toggle_pause(game)
                return

        if event.key == pygame.K_RETURN:
            toggle_messages_modal(game)

        if game.chat_active:
            if event.key == pygame.K_RETURN:
                # Send Message
                if game.chat_input_text.strip():
                    game.player.chat_text = game.chat_input_text
                    game.player.chat_timer = game.player.chat_duration
                    from core.messages import display_message_chat
                    display_message_chat(game, f"{game.player.name}: {game.chat_input_text}")
                
                # Clear and Deactivate
                game.chat_input_text = ""
                game.chat_active = False
                
                # Optional: Close the modal when sending
                # Check if modal is open, if so, close it (toggle)
                # This creates the "Enter closes chat" behavior
                # Remove this if you want the window to stay open.
                for modal in game.modals:
                    if modal['type'] == 'messages':
                        toggle_messages_modal(game)
                        break
            
            elif event.key == pygame.K_BACKSPACE:
                game.chat_input_text = game.chat_input_text[:-1]
            elif event.key == pygame.K_ESCAPE:
                game.chat_active = False
            else:
                if len(game.chat_input_text) < 50:
                    game.chat_input_text += event.unicode
            return

        # --- Play Mode Keys ---
        if game.game_state == 'PLAYING':
            if event.key == pygame.K_RETURN or event.key == pygame.K_t:
                game.chat_active = True
                return

            if event.key == pygame.K_i:
                toggle_inventory_modal(game)

            if event.key == pygame.K_h:
                toggle_status_modal(game)
            
            if event.key == pygame.K_g:
                toggle_gear_modal(game)
            
            if event.key == pygame.K_n:
                toggle_nearby_modal(game)
                        
            if event.key == pygame.K_r:
                if game.player:
                    game.player.reload_active_weapon()

            if event.key == pygame.K_e:
                try_grab_item(game)
            
            if event.key == pygame.K_SPACE:
                if game.player and game.player.is_sleeping:
                    game.player.is_sleeping = False
                    print("You woke up manually.")

            

            if pygame.K_1 <= event.key <= pygame.K_5:
                slot_index = event.key - pygame.K_1
                if game.player:
                    item = game.player.belt[slot_index]
                    if item:
                        if item.item_type.startswith('consumable'):
                            game.player.consume_item(item, 'belt', slot_index)
                        elif item.item_type in ['weapon_melee', 'weapon_ranged', 'tool']:
                            if game.player.active_weapon == item:
                                game.player.active_weapon = None
                                print(f"Unequipped {item.name}.")
                            else:
                                game.player.active_weapon = item
                                print(f"Equipped {item.name}.")
                    else:
                        game.player.active_weapon = None
                        print(f"Belt slot {slot_index + 1} is empty. Unequipped.")

            # Zoom controls
            zoom_step = 0.1
            if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS: 
                game.zoom_level += zoom_step
                game.zoom_level = min(game.zoom_level, core.dataNEAR_ZOOM) 
            elif event.key == pygame.K_MINUS: 
                game.zoom_level -= zoom_step
                game.zoom_level = max(core.dataFAR_ZOOM, game.zoom_level)