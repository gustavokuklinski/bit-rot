import pygame
import uuid
import math
import random 
from core.data.config import *
from core.events.game_actions import try_grab_item
from core.ui.crafting_modal import CraftingModal
from core.data.localization import tr
from core.ui.helpers.keybinds import keybind_manager
from core.messages import display_message
from core.systems.utils import get_targeted_interactable
from core.map.world_layers import set_active_layer

def toggle_inventory_modal(game):
    inventory_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'inventory':
            game.last_modal_positions['inventory'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            inventory_modal_exists = True
            break
    if not inventory_modal_exists:
        new_inventory_modal = {
            'id': uuid.uuid4(),
            'type': 'inventory',
            'item': None,
            'position': getattr(game, 'last_modal_positions', {}).get('inventory', (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(getattr(game, 'last_modal_positions', {}).get('inventory', (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT))[0], 
                                getattr(game, 'last_modal_positions', {}).get('inventory', (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT))[1], 
                                INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT)
        }
        game.modals.append(new_inventory_modal)

def toggle_status_modal(game):
    status_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'status':
            game.last_modal_positions['status'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            status_modal_exists = True
            break
    if not status_modal_exists:
        new_status_modal = {
            'id': uuid.uuid4(),
            'type': 'status',
            'item': None,
            'position': getattr(game, 'last_modal_positions', {}).get('status', (0, 0)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(getattr(game, 'last_modal_positions', {}).get('status', (0, 0))[0], 
                                getattr(game, 'last_modal_positions', {}).get('status', (0, 0))[1], 
                                STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)
        }
        game.modals.append(new_status_modal)

def toggle_nearby_modal(game):
    nearby_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'nearby':
            game.last_modal_positions['nearby'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            nearby_modal_exists = True
            break
    if not nearby_modal_exists:
        new_nearby_modal = {
            'id': uuid.uuid4(),
            'type': 'nearby',
            'item': None,
            'position': getattr(game, 'last_modal_positions', {}).get('nearby', (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(getattr(game, 'last_modal_positions', {}).get('nearby', (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT))[0], 
                                getattr(game, 'last_modal_positions', {}).get('nearby', (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT))[1], 
                                NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)
        }
        game.modals.append(new_nearby_modal)

def toggle_messages_modal(game):
    messages_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'messages':
            game.last_modal_positions['messages'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            messages_modal_exists = True
            break
    if not messages_modal_exists:
        new_messages_modal = {
            'id': uuid.uuid4(),
            'type': 'messages',
            'item': None,
            'position': getattr(game, 'last_modal_positions', {}).get('messages', (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(getattr(game, 'last_modal_positions', {}).get('messages', (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT))[0], 
                                getattr(game, 'last_modal_positions', {}).get('messages', (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT))[1], 
                                MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT)
        }
        game.modals.append(new_messages_modal)

def toggle_gear_modal(game):
    gear_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'gear':
            game.last_modal_positions['gear'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            gear_modal_exists = True
            break
    if not gear_modal_exists:
        new_gear_modal = {
            'id': uuid.uuid4(),
            'type': 'gear',
            'item': None,
            'position': getattr(game, 'last_modal_positions', {}).get('gear', (GAME_WIDTH - GEAR_MODAL_WIDTH, 0)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(getattr(game, 'last_modal_positions', {}).get('gear', (GAME_WIDTH - GEAR_MODAL_WIDTH, 0))[0], 
                                getattr(game, 'last_modal_positions', {}).get('gear', (GAME_WIDTH - GEAR_MODAL_WIDTH, 0))[1], 
                                GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)
        }
        game.modals.append(new_gear_modal)

def toggle_crafting_modal(game):
    crafting_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'crafting':
            game.last_modal_positions['crafting'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            crafting_modal_exists = True
            break
    if not crafting_modal_exists:
        modal_data = {
            'id': uuid.uuid4(),
            'type': 'crafting',
            'position': getattr(game, 'last_modal_positions', {}).get('crafting', (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(
                getattr(game, 'last_modal_positions', {}).get('crafting', (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2))[0], 
                getattr(game, 'last_modal_positions', {}).get('crafting', (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2))[1], 
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
            'position': getattr(game, 'last_modal_positions', {}).get('slots', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT)),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(
                getattr(game, 'last_modal_positions', {}).get('slots', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT))[0],
                getattr(game, 'last_modal_positions', {}).get('slots', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT))[1],
                SLOTS_MODAL_WIDTH, SLOTS_MODAL_HEIGHT)
        }
        game.modals.append(new_slots_modal)

def toggle_help_modal(game):
    help_modal_exists = False
    for modal in game.modals:
        if modal['type'] == 'help':
            game.last_modal_positions['help'] = (modal['rect'].x, modal['rect'].y)
            game.modals.remove(modal)
            help_modal_exists = True
            break
    if not help_modal_exists:
        new_help_modal = {
            'id': uuid.uuid4(),
            'type': 'help',
            'position': (GAME_WIDTH / 2 - HELP_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - HELP_MODAL_HEIGHT / 2),
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(0, 0, HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT),
            'scroll_offset_y': 0
        }
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
    import re
    text = text.strip()
    if not text.startswith("%rot "):
        return False
        
    command = text[5:].strip()
    
    # --- GOD MODE ---
    if command == "god" or command == "godzen":
        if game.player:
            game.player.health = 100.0
            game.player.max_health = 100.0
            game.player.water = 100.0
            game.player.food = 100.0
            game.player.stamina = 100.0
            game.player.max_stamina = 100.0
            game.player.infection = 0.0
            game.player.anxiety = 0.0
            
            for part in game.player.body_parts.values():
                part['value'] = 100.0
                
            for attr in game.player.attributes.keys():
                game.player.progression.add_xp(game.player, attr, 999999)
                
            game.player.god_mode = True
            
            if command == "godzen":
                game.player.godzen_mode = True
                display_message(game, tr('msg', "GODZEN Mode Activated: Invincible and Invisible."))
            else:
                 game.player.godzen_mode = False
                 display_message(game, tr('msg', "GOD Mode Activated: Invincible."))
        return True

    # --- ITEM SPAWN ---
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
            display_message(game, f"{tr('msg', 'Could not spawn item')} '{item_name}'.")
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
            game.rebuild_container_grid()
            display_message(game, f"Spawned vehicle '{veh_name}' nearby.")
        else:
            display_message(game, f"{tr('msg', 'Could not find vehicle')} '{veh_name}'.")
        return True

    return False

def reset_modal_positions(game):
    default_positions = {
        'gear': (GAME_WIDTH - GEAR_MODAL_WIDTH, 0),
        'inventory': (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
        'nearby': (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT),
        'messages': (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT),
        'status': (0, 0),
        'slots': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
        'container': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
        'text': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
        'mobile': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
        'vehicle': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - STATUS_MODAL_HEIGHT),
        'crafting': (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2),
        'help': (GAME_WIDTH / 2 - 200, GAME_HEIGHT / 2 - 200),
    }
    if hasattr(game, 'last_modal_positions'):
        game.last_modal_positions.update(default_positions)
    game.modals.clear()
    if hasattr(game, 'saved_modals'):
        game.saved_modals.clear()
    toggle_default_ui(game)

def toggle_default_ui(game):
    if game.modals:
        game.saved_modals = []
        for modal in game.modals:
            if 'rect' in modal:
                game.last_modal_positions[modal['type']] = (modal['rect'].x, modal['rect'].y)
            game.saved_modals.append(modal)
        game.modals.clear()
    elif getattr(game, 'saved_modals', None):
        for modal in game.saved_modals:
            if modal['type'] in game.last_modal_positions:
                pos = game.last_modal_positions[modal['type']]
                modal['position'] = pos
                if 'rect' in modal:
                    modal['rect'].topleft = pos
            game.modals.append(modal)
        game.saved_modals.clear()
    else:
        default_positions = {
            'gear': (GAME_WIDTH - GEAR_MODAL_WIDTH, 0),
            'inventory': (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
            'nearby': (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT),
            'messages': (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT),
            'status': (0,0),
            'slots': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT)
        }
        game.last_modal_positions.update(default_positions)
        toggle_gear_modal(game)
        toggle_inventory_modal(game)
        toggle_nearby_modal(game)
        toggle_messages_modal(game)
        toggle_status_modal(game)
        toggle_slots_modal(game)

def handle_keyboard_events(game, event, action_triggered=None):
    
    # --- 1. KEYBOARD-ONLY UI & CHAT HANDLING (Strictly KEYDOWN) ---
    if event.type == pygame.KEYDOWN:
        
        if getattr(game, 'chat_active', False):
            if event.key == pygame.K_RETURN:
                if getattr(game, 'chat_input_text', '').strip():
                    if not hasattr(game, 'chat_history'):
                        game.chat_history = []
                    game.chat_history.append(game.chat_input_text)
                    game.chat_history_index = len(game.chat_history)
                    
                    is_command = process_chat_command(game, game.chat_input_text)
                    
                    if not is_command:
                        game.player.chat_text = game.chat_input_text
                        game.player.chat_timer = game.player.chat_duration
                        display_message(game, f"{game.player.name}: {game.chat_input_text}")
                
                game.chat_input_text = ""
                game.chat_active = False

            elif event.key == pygame.K_BACKSPACE:
                if len(getattr(game, 'chat_input_text', '')) > 0:
                    game.chat_input_text = game.chat_input_text[:-1]
            
            elif event.key == pygame.K_ESCAPE:
                game.chat_active = False
                
            elif event.key == pygame.K_UP:
                if hasattr(game, 'chat_history') and game.chat_history:
                    if not hasattr(game, 'chat_history_index'):
                        game.chat_history_index = len(game.chat_history)
                    game.chat_history_index = max(0, game.chat_history_index - 1)
                    game.chat_input_text = game.chat_history[game.chat_history_index]
                    
            elif event.key == pygame.K_DOWN:
                if hasattr(game, 'chat_history') and game.chat_history:
                    if not hasattr(game, 'chat_history_index'):
                        game.chat_history_index = len(game.chat_history)
                    game.chat_history_index = min(len(game.chat_history), game.chat_history_index + 1)
                    if game.chat_history_index < len(game.chat_history):
                        game.chat_input_text = game.chat_history[game.chat_history_index]
                    else:
                        game.chat_input_text = ""
            else:
                if len(getattr(game, 'chat_input_text', '')) < 50 and getattr(event, 'unicode', ''):
                    game.chat_input_text += event.unicode
            return 
            
        if event.key == pygame.K_TAB:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                reset_modal_positions(game)
            else:
                toggle_default_ui(game)
            return

        if game.modals and not getattr(game, 'hide_modals', False):
            top_modal = game.modals[-1]
            if 'instance' in top_modal and hasattr(top_modal['instance'], 'handle_event'):
                if top_modal['instance'].handle_event(event):
                    return

        if event.key == pygame.K_F2 or event.key == pygame.K_ESCAPE:
            toggle_pause(game)
            return
        
        if event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()


        # Hardcoded Hotbar & Zoom bindings
        if game.game_state == 'PLAYING':
            if pygame.K_1 <= event.key <= pygame.K_5:
                slot_index = event.key - pygame.K_1
                if game.player:
                    item = game.player.belt[slot_index]
                    if item:
                        if item.item_type.startswith('consumable'):
                            game.player.consume_item(item, 'belt', slot_index, game=game)
                        elif item.item_type in ['weapon_melee', 'weapon_ranged', 'weapon_throw', 'tool']:
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

    # --- 2. UNIFIED GAMEPLAY ACTIONS (Any Input Device) ---
    if action_triggered and game.game_state == 'PLAYING' and not getattr(game, 'chat_active', False):
        
        if action_triggered == 'chat':
            game.chat_active = True
            if not any(m['type'] == 'messages' for m in game.modals):
                toggle_messages_modal(game)
            return
            
        elif action_triggered == 'toggle_inventory': toggle_inventory_modal(game)
        elif action_triggered == 'toggle_status': toggle_status_modal(game)
        elif action_triggered == 'toggle_gear': toggle_gear_modal(game)
        elif action_triggered == 'toggle_nearby': toggle_nearby_modal(game)
        elif action_triggered == 'toggle_messages': toggle_messages_modal(game)
        elif action_triggered == 'toggle_crafting': toggle_crafting_modal(game)
        elif action_triggered == 'toggle_slots': toggle_slots_modal(game)
        elif action_triggered == 'reload':
            if game.player:
                game.player.reload_active_weapon(game=game)
                
        elif action_triggered == 'vehicle_engine':
            vehicle_found = find_closest_vehicle(game)
            for modal in game.modals:
                if modal['type'] == 'vehicle':
                    vehicle_found = modal['vehicle']
                    break
            if vehicle_found:
                vehicle_found.toggle_engine()
            else:
                print("No vehicle nearby.")
                
        elif action_triggered == 'action_shove':
            if getattr(game.player, 'vehicle', None):
                game.player.vehicle.brake(brake_force=0.6, game=game)
            
            elif game.player and game.player.stamina > 0 and not getattr(game.player, 'is_reloading', False):
                shove_range = TILE_SIZE * 1.5
                closest_zombie = None
                min_dist = shove_range
                
                for zombie in game.zombies:
                    if getattr(zombie, 'is_dead', False): continue
                    dist = math.hypot(zombie.rect.centerx - game.player.rect.centerx, zombie.rect.centery - game.player.rect.centery)
                    if dist <= min_dist:
                        min_dist = dist
                        closest_zombie = zombie
                        
                if closest_zombie:
                    dx_kb = closest_zombie.rect.centerx - game.player.rect.centerx
                    dy_kb = closest_zombie.rect.centery - game.player.rect.centery
                    kb_angle = math.atan2(dy_kb, dx_kb)
                    
                    force = 10
                    closest_zombie.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                    closest_zombie.knockback_timer = 300
                    
                    game.player.stamina = max(0.0, game.player.stamina - 2.0)
                    game.player.melee_swing_timer = 10
                    game.player.melee_swing_angle = kb_angle
                    
                    print("You pushed the enemy!")
                    display_message(game, f"{tr('msg', 'You pushed an enemy away!')}")

        elif action_triggered == 'interact':
            if getattr(game.player, 'vehicle', None):
                game.player.exit_vehicle(game)
            else:
                target = get_targeted_interactable(game)
                if target:
                    if target['type'] == 'npc':
                        found_npc = target['entity']
                        if not any(m['type'] == 'npc_dialog' for m in game.modals):
                            pos_x = (GAME_WIDTH // 2) - (NPC_DIALOG_MODAL_WIDTH // 2)
                            pos_y = (GAME_HEIGHT // 2) - (NPC_DIALOG_MODAL_HEIGHT // 2)
                            game.modals.append({
                                'id': str(uuid.uuid4()),
                                'type': 'npc_dialog',
                                'npc': found_npc,
                                'dialogs': found_npc.get_dialog_options(), 
                                'active_dialog_index': -1,                 
                                'position': (pos_x, pos_y),
                                'rect': pygame.Rect(pos_x, pos_y, NPC_DIALOG_MODAL_WIDTH, NPC_DIALOG_MODAL_HEIGHT),
                                'is_dragging': False,
                                'drag_offset': (0, 0)
                            })
                    elif target['type'] == 'vehicle':
                        found_vehicle = target['entity']
                        game.player.enter_vehicle(found_vehicle, game)
                        if not any(m['type'] == 'vehicle' for m in game.modals):
                            default_pos = (GAME_WIDTH // 2 - 200, GAME_HEIGHT // 2 + 120)
                            pos = getattr(game, 'last_modal_positions', {}).get('vehicle', default_pos)
                            
                            new_modal = {
                                'id': str(uuid.uuid4()),
                                'type': 'vehicle',
                                'vehicle': found_vehicle,
                                'position': pos,
                                'rect': pygame.Rect(pos[0], pos[1], VEHICLE_MODAL_WIDTH, VEHICLE_MODAL_HEIGHT),
                                'is_dragging': False, 
                                'drag_offset': (0, 0), 
                                'active_tab': 'Info'
                            }
                            game.modals.append(new_modal)
                    elif target['type'] == 'stair':
                        px, py = target['entity']
                        current_tile_char = game.map_data[py][px]
                        current_tile_def = game.tile_manager.definitions.get(current_tile_char)
                        if current_tile_def and current_tile_def.get('is_stair'):
                            target_layer = current_tile_def.get('target_layer')
                            if game.player.layer_switch_cooldown <= 0:
                                if set_active_layer(game, target_layer):
                                    game.player.layer_switch_cooldown = 30
                    elif target['type'] == 'tile':
                        tx, ty = target['entity']
                        tile = game.map_manager.get_tile_at(tx, ty)
                        if tile and tile.get('is_statable') and tile.get('type') == 'maptile':
                            game.map_manager.toggle_door_state(tx, ty)
                        #elif tile and tile.get('is_stair'):
                        #    target_layer = tile.get('target_layer')
                        #    if game.player.layer_switch_cooldown <= 0:
                        #        if set_active_layer(game, target_layer):
                        #            game.player.layer_switch_cooldown = 30
                    
                    elif target['type'] == 'container':
                        found_container = target['entity']
                        
                        # Only open the modal if it isn't already active for this specific container
                        modal_exists = False
                        for modal in game.modals:
                            if modal['type'] == 'container' and modal.get('item') == found_container:
                                modal_exists = True
                                break
                                
                        if not modal_exists:
                            default_pos = getattr(game, 'last_modal_positions', {}).get('container', (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT))
                            
                            new_modal = {
                                'id': uuid.uuid4(),
                                'type': 'container',
                                'item': found_container,
                                'position': default_pos,
                                'rect': pygame.Rect(default_pos[0], default_pos[1], CONTAINER_MODAL_WIDTH, CONTAINER_MODAL_HEIGHT),
                                'is_dragging': False,
                                'drag_offset': (0, 0)
                            }
                            game.modals.append(new_modal)