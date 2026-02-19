import pygame
import uuid
import math
from core.data.config import *
from core.events.game_actions import try_grab_item
from core.ui.crafting_modal import CraftingModal

# ... (Previous toggle functions remain unchanged) ...
def toggle_inventory_modal(game):
    inventory_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'inventory':
            game.modals.remove(modal)
            inventory_modal_exists = True
            break
    if not inventory_modal_exists:
        # [FIX] Ensure saved modals are cleared if user opens new one, or just proceed
        # game.saved_modals = []  # Optional: clear stack if user interacts
        
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

def toggle_crafting_modal(game):
    crafting_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'crafting':
            game.modals.remove(modal)
            crafting_modal_exists = True
            break
    if not crafting_modal_exists:
        modal_data = {
            'id': uuid.uuid4(),
            'type': 'crafting',
            'position': game.last_modal_positions.get('crafting', (300, 100)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(
                game.last_modal_positions.get('crafting', (300, 100))[0], 
                game.last_modal_positions.get('crafting', (300, 100))[1], 
                CRAFTING_MODAL_WIDTH, CRAFTING_MODAL_HEIGHT
            ),
            'minimized': False
        }
        
        screen = getattr(game, 'screen', pygame.display.get_surface())
        assets = getattr(game, 'assets', {})
        
        crafting_instance = CraftingModal(screen, modal_data, assets, game)
        modal_data['instance'] = crafting_instance
        
        game.modals.append(modal_data)

def find_closest_vehicle(game):
    closest_vehicle = None
    closest_dist = float('inf')
    
    if not game.player: return None
    
    for entity in game.containers: 
        if hasattr(entity, 'item_type') and entity.item_type == 'vehicle':
            dist = math.hypot(game.player.rect.centerx - entity.rect.centerx, game.player.rect.centery - entity.rect.centery)
            if dist < closest_dist:
                closest_dist = dist
                closest_vehicle = entity
                
    if closest_vehicle and closest_dist <= TILE_SIZE * 1.5: 
        return closest_vehicle
    return None

def toggle_pause(game):
    if game.game_state == 'PLAYING':
        game.game_state = 'PAUSED'
        game.capture_pause_screen()
        game.save_game()
    elif game.game_state == 'PAUSED':
        game.game_state = 'PLAYING'


def handle_keyboard_events(game, event):
    if event.type == pygame.KEYDOWN:
        # [UPDATED] Toggle UI Visibility with TAB (Close/Restore Logic)
        if event.key == pygame.K_TAB:
            # Ensure storage exists if not added to game.py yet (safe fallback)
            if not hasattr(game, 'saved_modals'):
                game.saved_modals = []

            if game.modals:
                # If modals are active: Save them and Close them
                game.saved_modals = game.modals[:] 
                game.modals.clear()
            else:
                # If no modals active: Restore from saved if available
                if game.saved_modals:
                    game.modals = game.saved_modals[:]
                    game.saved_modals = [] 
            return

        # [ADDED] Check if a top modal wants to handle the event (e.g. Search Bar)
        # Ensure we don't handle events for hidden modals
        if game.modals and not getattr(game, 'hide_modals', False):
            top_modal = game.modals[-1]
            if 'instance' in top_modal and hasattr(top_modal['instance'], 'handle_event'):
                if top_modal['instance'].handle_event(event):
                    return

        # --- Global Keys ---
        if event.key == pygame.K_F2:
            toggle_pause(game)
            return

        if event.key == pygame.K_ESCAPE:
            if game.modals:
                game.modals.pop()
                return
            else:
                toggle_pause(game)
                return
        
        if event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()

        if event.key == pygame.K_F3:
            game.is_fast_forwarding = not game.is_fast_forwarding
            return

        # --- 1. ACTIVE CHAT HANDLING ---
        if game.chat_active:
            if event.key == pygame.K_RETURN:
                if game.chat_input_text.strip():
                    game.player.chat_text = game.chat_input_text
                    game.player.chat_timer = game.player.chat_duration
                    
                    from core.messages import display_message_player
                    display_message_player(game, f"{game.player.name}: {game.chat_input_text}")
                
                game.chat_input_text = ""
                game.chat_active = False

            elif event.key == pygame.K_BACKSPACE:
                game.chat_input_text = game.chat_input_text[:-1]
            
            elif event.key == pygame.K_ESCAPE:
                game.chat_active = False
                
            else:
                if len(game.chat_input_text) < 50:
                    game.chat_input_text += event.unicode
            
            return 

        # --- 2. GAMEPLAY KEYS (Only if Chat is NOT active) ---
        if game.game_state == 'PLAYING':
            
            if event.key == pygame.K_RETURN or event.key == pygame.K_t:
                game.chat_active = True
                if not any(m['type'] == 'messages' for m in game.modals):
                    toggle_messages_modal(game)
                return

            if event.key == pygame.K_i:
                toggle_inventory_modal(game)
            if event.key == pygame.K_h:
                toggle_status_modal(game)
            if event.key == pygame.K_g:
                toggle_gear_modal(game)
            if event.key == pygame.K_n:
                toggle_nearby_modal(game)
            if event.key == pygame.K_m:
                toggle_messages_modal(game)
            if event.key == pygame.K_c:
                toggle_crafting_modal(game)

            if event.key == pygame.K_r:
                if game.player:
                    game.player.reload_active_weapon(game=game)

            if event.key == pygame.K_q:
                vehicle_found = find_closest_vehicle(game)
                for modal in game.modals:
                    if modal['type'] == 'vehicle':
                        vehicle_found = modal['vehicle']
                        break
                
                if vehicle_found:
                    vehicle_found.toggle_engine()
                else:
                    print("No vehicle nearby.")
            
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
                            game.player.consume_item(item, 'belt', slot_index,game=game)
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

            zoom_step = 0.1
            if event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS: 
                game.zoom_level += zoom_step
                game.zoom_level = min(game.zoom_level, NEAR_ZOOM) 
            elif event.key == pygame.K_MINUS: 
                game.zoom_level -= zoom_step
                game.zoom_level = max(FAR_ZOOM, game.zoom_level)