import pygame
import uuid
import math
import random # Added for %rot vehicle
from core.data.config import *
from core.events.game_actions import try_grab_item
from core.ui.crafting_modal import CraftingModal
from core.data.localization import tr

def toggle_inventory_modal(game):
    inventory_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'inventory':
            # Save position before closing
            game.last_modal_positions['inventory'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            inventory_modal_exists = True
            break
    if not inventory_modal_exists:
        # game.saved_modals = []  # REMOVE this line so it doesn't break our new saving system!
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
            game.last_modal_positions['status'] = (modal['rect'].x, modal['rect'].y) # Add this
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
            'rect': pygame.Rect(game.last_modal_positions['status'][0], game.last_modal_positions['status'][1], STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)
        }
        game.modals.append(new_status_modal)

def toggle_nearby_modal(game):
    nearby_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'nearby':
            game.last_modal_positions['nearby'] = (modal['rect'].x, modal['rect'].y) # Add this
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
            'rect': pygame.Rect(game.last_modal_positions['nearby'][0], game.last_modal_positions['nearby'][1], NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)
        }
        game.modals.append(new_nearby_modal)

def toggle_messages_modal(game):
    messages_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'messages':
            game.last_modal_positions['messages'] = (modal['rect'].x, modal['rect'].y) # Add this
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
            'rect': pygame.Rect(game.last_modal_positions['messages'][0], game.last_modal_positions['messages'][1], MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT)
        }
        game.modals.append(new_messages_modal)

def toggle_gear_modal(game):
    gear_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'gear':
            game.last_modal_positions['gear'] = (modal['rect'].x, modal['rect'].y) # Add this
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
                                GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)
        }
        game.modals.append(new_gear_modal)

def toggle_crafting_modal(game):
    crafting_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'crafting':
            game.last_modal_positions['crafting'] = (modal['rect'].x, modal['rect'].y) # Add this
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
            )
        }
        
        screen = getattr(game, 'screen', pygame.display.get_surface())
        assets = getattr(game, 'assets', {})
        
        crafting_instance = CraftingModal(screen, modal_data, assets, game)
        modal_data['instance'] = crafting_instance
        
        game.modals.append(modal_data)

def toggle_slots_modal(game):
    slots_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'slots':
            game.last_modal_positions['slots'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            slots_modal_exists = True
            break
    if not slots_modal_exists:
        new_slots_modal = {
            'id': uuid.uuid4(),
            'type': 'slots',
            'position': game.last_modal_positions.get('slots', (100, 100)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(
                game.last_modal_positions.get('slots', (100, 100))[0],
                game.last_modal_positions.get('slots', (100, 100))[1],
                SLOTS_MODAL_WIDTH, SLOTS_MODAL_HEIGHT)
        }
        game.modals.append(new_slots_modal)

def toggle_help_modal(game):
    help_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'help':
            game.last_modal_positions['help'] = (modal['rect'].x, modal['rect'].y) # Add this
            game.modals.remove(modal)
            help_modal_exists = True
            break
    if not help_modal_exists:
        new_help_modal = {
            'id': uuid.uuid4(),
            'type': 'help',
            'position': (GAME_WIDTH / 2 - HELP_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - HELP_MODAL_HEIGHT / 2), # Centered
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(0, 0, HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT),
            'scroll_offset_y': 0
        }
        # Realize rect bounds
        new_help_modal['rect'].topleft = new_help_modal['position']
        game.modals.append(new_help_modal)

def find_closest_vehicle(game):
    closest_vehicle = None
    closest_dist_sq = float('inf')

    if not game.player: return None

    for entity in game.containers:
        if hasattr(entity, 'item_type') and entity.item_type == 'vehicle':
            dx = game.player.rect.centerx - entity.rect.centerx
            dy = game.player.rect.centery - entity.rect.centery
            dist_sq = dx*dx + dy*dy
            if dist_sq < closest_dist_sq:
                closest_dist_sq = dist_sq
                closest_vehicle = entity

    if closest_vehicle and closest_dist_sq <= (TILE_SIZE * 1.5) ** 2:
        return closest_vehicle
    return None

def toggle_pause(game):
    if game.game_state == 'PLAYING':
        game.game_state = 'PAUSED'
        game.capture_pause_screen()
        game.save_game()
    elif game.game_state == 'PAUSED':
        game.game_state = 'PLAYING'

def process_chat_command(game, text):
    """Processes potential cheat commands entered in chat."""
    from core.messages import display_message
    import re
    
    text = text.strip()
    if not text.startswith("%rot "):
        return False
        
    command = text[5:].strip()
    
    # --- GOD MODE ---
    if command == "god" or command == "godzen":
        if game.player:
            # Stats to max
            game.player.health = 100.0
            game.player.max_health = 100.0
            game.player.water = 100.0
            game.player.food = 100.0
            game.player.stamina = 100.0
            game.player.max_stamina = 100.0
            game.player.tireness = 100.0
            game.player.max_tireness = 100.0
            game.player.infection = 0.0
            game.player.anxiety = 0.0
            
            for part in game.player.body_parts.values():
                part['value'] = 100.0
                
            # Attributes to 10
            for attr in game.player.attributes.keys():
                game.player.progression.add_xp(game.player, attr, 999999) # Add lots of XP
                
            game.player.god_mode = True
            
            if command == "godzen":
                game.player.godzen_mode = True
                display_message(game, tr('msg', "GODZEN Mode Activated: Invincible and Invisible."))
            else:
                 game.player.godzen_mode = False
                 display_message(game, tr('msg', "GOD Mode Activated: Invincible."))
        return True

    # --- ITEM SPAWN ---
    # Matches %rot item "Item Name" [qty]
    item_match = re.match(r'item\s+"([^"]+)"(?:\s+(\d+))?', command)
    if item_match:
        item_name = item_match.group(1)
        qty = int(item_match.group(2)) if item_match.group(2) else 1
        
        from core.entities.item.item import Item
        spawned = 0
        for _ in range(qty):
            new_item = Item.create_from_name(item_name)
            if new_item:
                if len(game.player.inventory) < game.player.base_inventory_slots:
                    game.player.inventory.append(new_item)
                    spawned += 1
                else:
                    break
        
        if spawned > 0:
            display_message(game, f"{tr('msg', 'Spawned')} {spawned}x '{item_name}' {tr('msg', 'into inventory.')}")
        else:
            display_message(game, f"{tr('msg', 'Could not spawn cloth')} '{cloth_name}'.")
        return True

    # --- CLOTH SPAWN ---
    cloth_match = re.match(r'cloth\s+"([^"]+)"(?:\s+(\d+))?', command)
    if cloth_match:
        cloth_name = cloth_match.group(1)
        qty = int(cloth_match.group(2)) if cloth_match.group(2) else 1
        
        from core.entities.item.item import Item
        spawned = 0
        for _ in range(qty):
            new_cloth = Item.create_from_name(cloth_name)
            if new_cloth:
                if len(game.player.inventory) < game.player.base_inventory_slots:
                    game.player.inventory.append(new_cloth)
                    spawned += 1
                else:
                    break
        
        if spawned > 0:
            display_message(game, f"Spawned {spawned}x '{cloth_name}' into inventory.")
        else:
            display_message(game, f"Could not spawn cloth '{cloth_name}'.")
        return True
        
    # --- VEHICLE SPAWN ---
    veh_match = re.match(r'vehicle\s+"([^"]+)"', command)
    if veh_match:
        veh_name = veh_match.group(1)
        from core.entities.vehicle.vehicle_loader import VehicleLoader
        from core.entities.vehicle.vehicle import Vehicle
        
        loader = VehicleLoader()
        veh_def = loader.get_definition_by_name(veh_name)
        
        if veh_def and game.player:
            # Spawn 1 tile away in a random direction
            directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            dx, dy = random.choice(directions)
            spawn_x = game.player.rect.centerx + (dx * TILE_SIZE * 2)
            spawn_y = game.player.rect.centery + (dy * TILE_SIZE * 2)
            
            new_vehicle = Vehicle(
                name=veh_def['name'],
                x=spawn_x,
                y=spawn_y,
                width=veh_def.get('images', {}).get('right', pygame.Surface((32,32))).get_width(),
                height=veh_def.get('images', {}).get('right', pygame.Surface((32,32))).get_height(),
                image=veh_def['images'],
                stats=veh_def.get('stats', {}),
                capacity=veh_def.get('capacity', 20),
                loot_table=veh_def.get('loot_table', [])
            )
            
            game.containers.append(new_vehicle)
            game.rebuild_container_grid() # Update grid
            display_message(game, f"Spawned vehicle '{veh_name}' nearby.")
        else:
            display_message(game, f"{tr('msg', 'Could not find vehicle')} '{veh_name}'.")
        return True

    return False


def toggle_default_ui(game):
    """
    Acts as a UI Hide/Restore toggle button.
    - If modals are currently open, it saves their state/positions and clears the screen.
    - If the UI is hidden, it restores the saved modals exactly where they were.
    - If there is no saved state, it brings up the default layout.
    """
    # 1. If modals are currently on screen, save them and hide
    if game.modals:
        game.saved_modals = []
        for modal in game.modals:
            # Save their exact current position before hiding
            if 'rect' in modal:
                game.last_modal_positions[modal['type']] = (modal['rect'].x, modal['rect'].y)
            game.saved_modals.append(modal)
        
        # Clear the screen for an immersive view
        game.modals.clear()
        
    # 2. If the screen is clear, check if we have a saved state to restore
    elif getattr(game, 'saved_modals', None):
        for modal in game.saved_modals:
            # Ensure they get their last known positions updated safely
            if modal['type'] in game.last_modal_positions:
                pos = game.last_modal_positions[modal['type']]
                modal['position'] = pos
                if 'rect' in modal:
                    modal['rect'].topleft = pos
            game.modals.append(modal)
            
        # Clear saved state so we don't duplicate on next toggle
        game.saved_modals.clear()
        
    # 3. If there is no saved state, load default perfect layout
    else:
        default_positions = {
            'gear': (GAME_WIDTH - GEAR_MODAL_WIDTH, 0),
            'inventory': (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
            'nearby': (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT),
            'messages': (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT),
            'status': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - STATUS_MODAL_HEIGHT)
        }
        game.last_modal_positions.update(default_positions)
        
        toggle_gear_modal(game)
        toggle_inventory_modal(game)
        toggle_nearby_modal(game)
        toggle_messages_modal(game)
        toggle_status_modal(game)

def handle_keyboard_events(game, event):

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_TAB:
            toggle_default_ui(game)
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
                    is_command = process_chat_command(game, game.chat_input_text)
                    
                    if not is_command:
                        game.player.chat_text = game.chat_input_text
                        game.player.chat_timer = game.player.chat_duration
                        
                        from core.messages import display_message
                        display_message(game, f"{game.player.name}: {game.chat_input_text}")
                
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
            if event.key == pygame.K_y:
                toggle_slots_modal(game)
            if event.unicode == '?' or event.key == pygame.K_SLASH:
                toggle_help_modal(game)
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
                                print(f"Unequipped {tr('item', item.name)}.")
                            else:
                                game.player.active_weapon = item
                                print(f"Equipped {tr('item', item.name)}.")
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