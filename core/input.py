import pygame
import sys
import uuid
import random
import math

from data.config import *
from core.entities.item import Item, Projectile
from core.entities.corpse import Corpse
from core.update import player_hit_zombie, handle_zombie_death
from ui.helpers import get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect, get_container_slot_rect, draw_status_button, draw_inventory_button

def handle_input(game):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.VIDEORESIZE:
            game.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

        mouse_pos = game._get_scaled_mouse_pos()

        if game.game_state == 'PLAYING':
            handle_playing_input(game, event, mouse_pos)

def handle_playing_input(game, event, mouse_pos):
    keys = pygame.key.get_pressed()
    current_speed = PLAYER_SPEED
    if game.player.stamina <= 0:
        current_speed = PLAYER_SPEED / 2

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        game.player.vy = -current_speed
    elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
        game.player.vy = current_speed
    else:
        game.player.vy = 0

    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        game.player.vx = -current_speed
    elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        game.player.vx = current_speed
    else:
        game.player.vx = 0

    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_i:
            toggle_inventory_modal(game)

        if event.key == pygame.K_h:
            toggle_status_modal(game)
        
        if event.key == pygame.K_r:
            game.player.reload_active_weapon()

        if event.key == pygame.K_e:
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
                    game.player.active_weapon = item
                    print(f"Equipped {item.name}.")
            else:
                game.player.active_weapon = None
                print(f"Belt slot {slot_index + 1} is empty. Unequipped.")

    if event.type == pygame.MOUSEBUTTONDOWN:
        handle_mouse_down(game, event, mouse_pos)

    if event.type == pygame.MOUSEBUTTONUP:
        handle_mouse_up(game, event, mouse_pos)

    if event.type == pygame.MOUSEMOTION:
        handle_mouse_motion(game, event, mouse_pos)

def try_grab_item(game):
    # Find the closest item on the ground to the player
    closest_item = None
    closest_dist = float('inf')
    for item in game.items_on_ground:
        dist = math.hypot(item.rect.centerx - game.player.rect.centerx, item.rect.centery - game.player.rect.centery)
        if dist < closest_dist:
            closest_dist = dist
            closest_item = item

    # If an item is found within a certain distance, try to pick it up
    if closest_item and closest_dist < TILE_SIZE * 1.5:
        # prefer backpack if container modal of backpack is open
        target_inventory = game.player.inventory
        target_capacity = game.player.base_inventory_slots
        if game.player.backpack and any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals):
            target_inventory = game.player.backpack.inventory
            target_capacity = game.player.backpack.capacity or 0
        if len(target_inventory) < target_capacity:
            target_inventory.append(closest_item)
            game.items_on_ground.remove(closest_item)
            print(f"Grabbed {closest_item.name}.")
        elif len(game.player.inventory) < game.player.get_total_inventory_slots():
            game.player.inventory.append(closest_item)
            game.items_on_ground.remove(closest_item)
            print(f"Grabbed {closest_item.name} into inventory.")
        else:
            print("No space to grab the item.")

def handle_mouse_down(game, event, mouse_pos):
    if event.button == 1:
        if game.status_button_rect and game.status_button_rect.collidepoint(mouse_pos):
            toggle_status_modal(game)
            return
        if game.inventory_button_rect and game.inventory_button_rect.collidepoint(mouse_pos):
            toggle_inventory_modal(game)
            return

        for modal in game.modals:
            if modal['type'] == 'inventory':
                backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                if backpack_slot_rect.collidepoint(mouse_pos) and game.player.backpack:
                    modal_exists = any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals)
                    if not modal_exists:
                        new_container_modal = {
                            'id': uuid.uuid4(),
                            'type': 'container',
                            'item': game.player.backpack,
                            'position': game.last_modal_positions['container'],
                            'is_dragging': False, 'drag_offset': (0, 0),
                            'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300)
                        }
                        game.modals.append(new_container_modal)
                    return

    # --- Modal Drag Logic ---
    for modal in game.modals:
        modal_header_rect = pygame.Rect(modal['position'][0], modal['position'][1], 300, 35)
        if event.button == 1 and modal_header_rect.collidepoint(mouse_pos):
            modal['is_dragging'] = True
            modal['drag_offset'] = (mouse_pos[0] - modal['position'][0], mouse_pos[1] - modal['position'][1])
            game.modals.remove(modal)
            game.modals.append(modal)
            return

    # --- Context Menu & Left-Click Action Logic ---
    if game.context_menu['active'] and event.button == 1:
        handle_context_menu_click(game, mouse_pos)
        return

    # --- Right-Click Logic to OPEN Context Menu ---
    if event.button == 3:
        handle_right_click(game, mouse_pos)
        return

    # --- Left-click press - Identify a drag candidate ---
    if event.button == 1:
        handle_left_click_drag_candidate(game, mouse_pos)

    # --- Attack Logic ---
    if event.button == 1 and (pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]):
        handle_attack(game, mouse_pos)

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
            'rect': pygame.Rect(game.last_modal_positions['inventory'][0], game.last_modal_positions['inventory'][1], 300, 620)
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
            'rect': pygame.Rect(game.last_modal_positions['status'][0], game.last_modal_positions['status'][1], 300, 400)
        }
        game.modals.append(new_status_modal)

def handle_context_menu_click(game, mouse_pos):
    clicked_on_menu = False
    for i, rect in enumerate(game.context_menu['rects']):
        if rect.collidepoint(mouse_pos):
            option = game.context_menu['options'][i]
            item = game.context_menu['item']
            source = game.context_menu['source']
            index = game.context_menu['index']
            container_item = game.context_menu.get('container_item')

            print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")

            # --- Handle Actions ---
            if option == 'Use':
                game.player.consume_item(item, source, index, container_item)

            elif option == 'Reload':
                game.player.reload_active_weapon()

            elif option == 'Equip':
                # Equip behavior:
                # - Backpacks equip to backpack slot (swap if needed)
                # - Weapons/tools equip to belt (or first free belt slot)
                if getattr(item, 'item_type', None) == 'backpack':
                    # remove item from its source
                    def remove_from_source(src, idx, c_item=None):
                        if src == 'inventory' and 0 <= idx < len(game.player.inventory):
                            return game.player.inventory.pop(idx)
                        if src == 'belt' and 0 <= idx < len(game.player.belt):
                            it = game.player.belt[idx]
                            game.player.belt[idx] = None
                            return it
                        if src == 'container' and c_item and 0 <= idx < len(c_item.inventory):
                            return c_item.inventory.pop(idx)
                        if src == 'ground' and 0 <= idx < len(game.items_on_ground):
                            return game.items_on_ground.pop(idx)
                        return None

                    # perform equip (swap if backpack already equipped)
                    old_backpack = game.player.backpack
                    # remove selected backpack from its source
                    removed = remove_from_source(source, index, container_item)
                    game.player.backpack = item
                    print(f"Equipped {item.name} as backpack.")

                    # try to return old_backpack to same source (or fall back to inventory or ground)
                    if old_backpack:
                        placed = False
                        if source == 'inventory':
                            game.player.inventory.insert(index if 0 <= index <= len(game.player.inventory) else len(game.player.inventory), old_backpack)
                            placed = True
                        elif source == 'belt':
                            # place in same belt slot if empty, else first empty
                            if 0 <= index < len(game.player.belt) and game.player.belt[index] is None:
                                game.player.belt[index] = old_backpack
                                placed = True
                            else:
                                for bi in range(len(game.player.belt)):
                                    if game.player.belt[bi] is None:
                                        game.player.belt[bi] = old_backpack
                                        placed = True
                                        break
                        elif source == 'container' and container_item:
                            container_item.inventory.insert(index if 0 <= index <= len(container_item.inventory) else len(container_item.inventory), old_backpack)
                            placed = True
                        if not placed:
                            # fallback to main inventory if space, otherwise drop to ground
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(old_backpack)
                            else:
                                old_backpack.rect.center = game.player.rect.center
                                game.items_on_ground.append(old_backpack)
                                print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")

                else:
                    # standard weapon/tool equip flows
                    if source == 'ground':
                        placed = False
                        # try to equip to first empty belt slot
                        for bi, slot in enumerate(game.player.belt):
                            if slot is None and getattr(item, 'item_type', None) in ('weapon', 'tool'):
                                game.player.belt[bi] = item
                                # remove from ground list
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up and equipped {item.name} to belt slot {bi+1}.")
                                placed = True
                                break
                        if not placed:
                            # fallback: put into inventory if space and equip as active weapon if applicable
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(item)
                                if 0 <= index < len(game.items_on_ground):
                                    game.items_on_ground.pop(index)
                                print(f"Picked up {item.name} into inventory.")
                            else:
                                print("No space to equip or pick up the item.")
                        if getattr(item, 'item_type', None) == 'weapon':
                            game.player.active_weapon = item
                    else:
                        # equip from inventory/container/belt
                        game.player.equip_item_to_belt(item, source, index, container_item)

            elif option == 'Drop':
                dropped_item = game.player.drop_item(source, index, container_item)
                if dropped_item:
                    dropped_item.rect.center = game.player.rect.center
                    game.items_on_ground.append(dropped_item)

            elif option == 'Open':
                # Open container modal if not already open
                modal_exists = any(m['type'] == 'container' and m['item'] == item for m in game.modals)
                if not modal_exists:
                    new_container_modal = {
                        'id': uuid.uuid4(),
                        'type': 'container',
                        'item': item,
                        'position': game.last_modal_positions['container'],
                        'is_dragging': False, 'drag_offset': (0, 0),
                        'rect': pygame.Rect(game.last_modal_positions['container'][0], game.last_modal_positions['container'][1], 300, 300)
                    }
                    game.modals.append(new_container_modal)

            elif option == 'Unequip':
                if source == 'belt':
                    if 0 <= index < len(game.player.belt) and game.player.belt[index] == item:
                        game.player.belt[index] = None
                    if game.player.active_weapon == item:
                        game.player.active_weapon = None
                    # move to inventory or drop if full
                    if len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(item)
                        print(f"Unequipped {item.name} -> Inventory")
                    else:
                        item.rect.center = game.player.rect.center
                        game.items_on_ground.append(item)
                        print(f"Unequipped {item.name} -> Dropped on ground (inventory full)")
                else:
                    print("Unequip is only available for belt items.")

            # Ground-specific actions
            elif source == 'ground' and option == 'Grab':
                ground_idx = index
                if 0 <= ground_idx < len(game.items_on_ground):
                    ground_item = game.items_on_ground[ground_idx]
                    # prefer backpack if container modal of backpack is open
                    target_inventory = game.player.inventory
                    target_capacity = game.player.base_inventory_slots
                    if game.player.backpack and any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals):
                        target_inventory = game.player.backpack.inventory
                        target_capacity = game.player.backpack.capacity or 0
                    if len(target_inventory) < target_capacity:
                        target_inventory.append(ground_item)
                        game.items_on_ground.pop(ground_idx)
                        print(f"Grabbed {ground_item.name}.")
                    elif len(game.player.inventory) < game.player.get_total_inventory_slots():
                        game.player.inventory.append(ground_item)
                        game.items_on_ground.pop(ground_idx)
                        print(f"Grabbed {ground_item.name} into inventory.")
                    else:
                        print("No space to grab the item.")

            elif source == 'ground' and option == 'Place on Backpack':
                if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None:
                    ground_idx = index
                    if 0 <= ground_idx < len(game.items_on_ground):
                        ground_item = game.items_on_ground[ground_idx]
                        if len(game.player.backpack.inventory) < (game.player.backpack.capacity or 0):
                            game.player.backpack.inventory.append(ground_item)
                            game.items_on_ground.pop(ground_idx)
                            print(f"Placed {ground_item.name} into backpack.")
                        else:
                            print("Backpack is full.")
                else:
                    print("No backpack equipped.")

            clicked_on_menu = True
            break

    game.context_menu['active'] = False
    if clicked_on_menu:
        return # Consume the click

def handle_right_click(game, mouse_pos):
    game.context_menu['active'] = False # Close any existing menu
    clicked_item = None
    click_source = None
    click_index = -1
    click_container_item = None

    # Check modals in reverse order (top-most first)
    for modal in reversed(game.modals):
        if not modal['rect'].collidepoint(mouse_pos): continue

        if modal['type'] == 'inventory':
            # Check main inventory slots
            for i, item in enumerate(game.player.inventory):
                if item and get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index = item, 'inventory', i; break
            # Check belt slots
            if not clicked_item:
                for i, item in enumerate(game.player.belt):
                    if item and get_belt_slot_rect_in_modal(i, modal['position']).collidepoint(mouse_pos):
                        clicked_item, click_source, click_index = item, 'belt', i; break
            # Check backpack slot
            if not clicked_item:
                if game.player.backpack and get_backpack_slot_rect(modal['position']).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index = game.player.backpack, 'backpack', 0
        
        elif modal['type'] == 'container':
            container = modal['item']
            for i, item in enumerate(container.inventory):
                if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                    clicked_item, click_source, click_index, click_container_item = item, 'container', i, container; break
        
        if clicked_item: break

    # If nothing in modals was clicked, check ground items
    if not clicked_item:
        for i, ground_item in enumerate(game.items_on_ground):
            # account for GAME_OFFSET_X when checking mouse vs item rect
            item_rect_world = ground_item.rect.move(GAME_OFFSET_X, 0)
            if item_rect_world.collidepoint(mouse_pos):
                clicked_item = ground_item
                click_source = 'ground'
                click_index = i
                click_container_item = None
                break

    if clicked_item:
        game.context_menu['active'] = True
        game.context_menu['item'] = clicked_item
        game.context_menu['source'] = click_source
        game.context_menu['index'] = click_index
        game.context_menu['container_item'] = click_container_item
        game.context_menu['position'] = mouse_pos
        # Base options from player
        options = game.player.get_item_context_options(clicked_item) if click_source != 'ground' else []
        # If clicked from belt, allow unequip and remove 'Equip'
        if click_source == 'belt':
            if 'Unequip' not in options:
                options.append('Unequip')
            # Ensure 'Equip' is not shown for an item that's already on the belt
            options = [o for o in options if o != 'Equip']
        # If ground item, show ground menu options
        if click_source == 'ground':
            options = []
            # Corpses cannot be grabbed; they are lootable via Open
            if not isinstance(clicked_item, Corpse):
                options.append('Grab')
            # Weapons/tools on ground can be equipped
            if getattr(clicked_item, 'item_type', None) in ('weapon', 'tool'):
                options.append('Equip')
            # allow place on backpack if player has a backpack (slot) and it can hold items
            if game.player.backpack and getattr(game.player.backpack, 'inventory', None) is not None:
                options.append('Place on Backpack')
            # If ground item exposes an inventory (corpse/container), allow Open
            if getattr(clicked_item, 'inventory', None) is not None:
                options.append('Open')
        game.context_menu['options'] = options
        game.context_menu['rects'] = [] # Will be populated by draw_context_menu
        return # Consume the right-click

def handle_left_click_drag_candidate(game, mouse_pos):
    # First, check if we are clicking an item in an open container
    # Iterate through modals in reverse to check topmost first
    for modal in reversed(game.modals):
        if modal['type'] == 'container':
            container_item = modal['item']
            for i, item in enumerate(container_item.inventory):
                slot_rect = get_container_slot_rect(modal['position'], i)
                if slot_rect.collidepoint(mouse_pos):
                    game.drag_candidate = (item, (i, 'container', container_item, modal['id'])) # Pass modal ID
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    break
            if game.drag_candidate: break # Found a drag candidate in a container
    if game.drag_candidate: return

    # If no candidate from container, check inventory modal, belt, etc.
    for modal in reversed(game.modals):
        if modal['type'] == 'inventory':
            for i, item in enumerate(game.player.inventory):
                if item:
                    slot_rect = get_inventory_slot_rect(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'inventory'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        break
            if game.drag_candidate: break
    if game.drag_candidate: return

    # Check belt (only if an inventory modal is open)
    for modal in reversed(game.modals):
        if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
            for i, item in enumerate(game.player.belt):
                if item:
                    slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
                    if slot_rect.collidepoint(mouse_pos):
                        game.drag_candidate = (item, (i, 'belt'))
                        game.drag_start_pos = mouse_pos
                        game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                        break
            if game.drag_candidate: break

    # Check backpack slot
    for modal in reversed(game.modals):
        if modal['type'] == 'inventory':
            if game.player.backpack:
                slot_rect = get_backpack_slot_rect(modal['position'])
                if slot_rect.collidepoint(mouse_pos):
                    game.drag_candidate = (game.player.backpack, (0, 'backpack'))
                    game.drag_start_pos = mouse_pos
                    game.drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                    break

def handle_attack(game, mouse_pos):
    # If any modal is currently being dragged, do not process attack
    if any(modal['is_dragging'] for modal in game.modals):
        return

    # Check if click is inside any open modal (excluding header for drag)
    click_in_modal = False
    for modal in reversed(game.modals): # Check topmost modal first
        modal_rect = modal['rect']
        if modal_rect.collidepoint(mouse_pos):
            click_in_modal = True
            break
    if click_in_modal:
        return # Consume the click if it's inside a modal

    # ... (attack logic using scaled mouse_pos)
    if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
        weapon = game.player.active_weapon
        if game.player.is_reloading:
            print("Cannot shoot while reloading.")
            return

        # Check for any ranged weapon (a weapon that uses ammo)
        if weapon and weapon.item_type == 'weapon' and weapon.ammo_type:
            if weapon.load > 0 and weapon.durability > 0:
                # Base direction towards the mouse
                base_target_x = mouse_pos[0] - GAME_OFFSET_X
                base_target_y = mouse_pos[1]
                
                # Calculate base angle
                dx = base_target_x - game.player.rect.centerx
                dy = base_target_y - game.player.rect.centery
                base_angle = math.atan2(dy, dx)

                for _ in range(weapon.pellets):
                    # Apply spread
                    spread = math.radians(random.uniform(-weapon.spread_angle / 2, weapon.spread_angle / 2))
                    angle = base_angle + spread
                    
                    # Calculate new target based on spread angle (at a fixed distance)
                    target_x = game.player.rect.centerx + math.cos(angle) * 1000
                    target_y = game.player.rect.centery + math.sin(angle) * 1000

                    game.projectiles.append(Projectile(game.player.rect.centerx, game.player.rect.centery, target_x, target_y))

                weapon.load -= 1
                weapon.durability = max(0, weapon.durability - 0.5)
                game.player.gun_flash_timer = 5
                if weapon.durability <= 0:
                    for i, item in enumerate(game.player.belt):
                        if item == weapon: game.player.belt[i] = None; break
                    game.player.active_weapon = None
            elif weapon.load <= 0: print(f"**CLICK!** {weapon.name} is out of ammo.")
            else: print(f"**CLUNK!** {weapon.name} is broken.")
        else:
            if game.player.stamina >= 10:
                game.player.stamina -= 10
                game.player.melee_swing_timer = 10
                player_screen_x = game.player.rect.centerx + GAME_OFFSET_X
                player_screen_y = game.player.rect.centery
                dx_swing = mouse_pos[0] - player_screen_x
                dy_swing = mouse_pos[1] - player_screen_y
                game.player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
                hit_a_zombie = False
                for zombie in game.zombies:
                    if game.player.rect.colliderect(zombie.rect.inflate(20, 20)):
                        if player_hit_zombie(game.player, zombie):
                            handle_zombie_death(game.player, zombie, game.items_on_ground, game.obstacles)
                            game.zombies.remove(zombie)
                            game.zombies_killed += 1
                        hit_a_zombie = True
                        break
                if not hit_a_zombie: print("Swung and missed!")
            else: print("Too tired to swing!")

def handle_mouse_up(game, event, mouse_pos):
    # Stop dragging for all modals
    for modal in game.modals:
        modal['is_dragging'] = False

    if event.button == 1:  # Left-click release
        # If a drag was in progress OR if we have a drag candidate (for quick clicks)
        if game.is_dragging or game.drag_candidate:
            # If it was a quick click, initialize the drag variables and remove from source
            if not game.is_dragging and game.drag_candidate:
                game.dragged_item, game.drag_origin = game.drag_candidate
                game.drag_candidate = None
                # Remove item from its source now (keep consistent state for drop logic)
                try:
                    i_temp, type_temp, *container_temp = game.drag_origin
                except Exception:
                    i_temp = None; type_temp = None; container_temp = []
                if type_temp == 'inventory' and i_temp is not None:
                    if 0 <= i_temp < len(game.player.inventory):
                        game.player.inventory.pop(i_temp)
                elif type_temp == 'belt' and i_temp is not None:
                    if 0 <= i_temp < len(game.player.belt):
                        # unequip active weapon if needed
                        if game.player.active_weapon == game.player.belt[i_temp]:
                            game.player.active_weapon = None
                        game.player.belt[i_temp] = None
                elif type_temp == 'backpack':
                    game.player.backpack = None
                elif type_temp == 'container' and container_temp:
                    cont_obj = container_temp[0]
                    if 0 <= i_temp < len(cont_obj.inventory):
                        cont_obj.inventory.pop(i_temp)

            # Ensure drag_origin exists before unpacking (attempt to infer it)
            if game.drag_origin is None and game.dragged_item:
                inferred = resolve_drag_origin_from_item(game.dragged_item, game.player, game.modals)
                if inferred:
                    if len(inferred) == 2:
                        game.drag_origin = (inferred[0], inferred[1])
                    else:
                        game.drag_origin = (inferred[0], inferred[1], inferred[2])
                else:
                    game.drag_origin = (0, 'inventory')

            # Unpack normalized drag_origin
            i_orig, type_orig, *container_info = game.drag_origin
            container_obj = container_info[0] if type_orig == 'container' and container_info else None

            dropped_successfully = False

            # Try placing on belt (if mouse over any belt slot)
            for i_target in range(len(game.player.belt)):
                if any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in game.modals):
                    # Prevent backpacks on belt
                    if getattr(game.dragged_item, 'item_type', None) == 'backpack':
                        print("Cannot place backpacks on the belt.")
                        dropped_successfully = False
                        break
                    # place or swap
                    if game.player.belt[i_target] is None:
                        game.player.belt[i_target] = game.dragged_item
                    else:
                        item_to_swap = game.player.belt[i_target]
                        # Return swapped item to origin
                        if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                            game.player.inventory.insert(i_orig, item_to_swap)
                        elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                            game.player.belt[i_orig] = item_to_swap
                        elif type_orig == 'container' and container_obj is not None and 0 <= i_orig <= len(container_obj.inventory):
                            container_obj.inventory.insert(i_orig, item_to_swap)
                        else:
                            # fallback: put into inventory or drop
                            if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                game.player.inventory.append(item_to_swap)
                            else:
                                item_to_swap.rect.center = game.player.rect.center
                                game.items_on_ground.append(item_to_swap)
                        game.player.belt[i_target] = game.dragged_item
                    dropped_successfully = True
                    break

            # If not placed on belt, try backpack slot (equip/swap) — after inventory/belt checks
            if not dropped_successfully:
                for modal in game.modals:
                    if modal['type'] == 'inventory':
                        backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                        if backpack_slot_rect.collidepoint(mouse_pos):
                            # Accept backpacks/containers or anything that actually has an inventory
                            is_backpack_like = (getattr(game.dragged_item, 'item_type', None) in ('backpack', 'container')) or hasattr(game.dragged_item, 'inventory')
                            if not is_backpack_like:
                                # Not a backpack-like item — cannot equip here
                                # do not treat as a fatal error; allow other placement attempts
                                break

                            # Ensure the dragged instance is removed from any source (defensive)
                            try:
                                if game.dragged_item in game.player.inventory:
                                    game.player.inventory.remove(game.dragged_item)
                                if game.dragged_item in game.player.belt:
                                    for bi, it in enumerate(game.player.belt):
                                        if it is game.dragged_item:
                                            game.player.belt[bi] = None
                                if game.dragged_item in game.items_on_ground:
                                    game.items_on_ground.remove(game.dragged_item)
                            except Exception:
                                pass

                            old_backpack = game.player.backpack
                            # Equip the new backpack
                            game.player.backpack = game.dragged_item
                            print(f"Equipped {game.dragged_item.name} as backpack via drag.")

                            # Return old backpack to a sensible place (inventory preferred)
                            if old_backpack:
                                returned = False
                                # Try to put old backpack into the player's main inventory if there's room
                                if len(game.player.inventory) < game.player.get_total_inventory_slots():
                                    game.player.inventory.append(old_backpack)
                                    returned = True
                                else:
                                    # Try to place in first empty belt slot
                                    for bi in range(len(game.player.belt)):
                                        if game.player.belt[bi] is None:
                                            game.player.belt[bi] = old_backpack
                                            returned = True
                                            break
                                if not returned:
                                    # Last resort: drop on ground next to player
                                    old_backpack.rect.center = game.player.rect.center
                                    game.items_on_ground.append(old_backpack)
                                    print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")

                            dropped_successfully = True
                            break
                # end for modal

            # If not placed on belt or backpack, try placing into inventory modal (5 visible slots)
            if not dropped_successfully:
                for modal in reversed(game.modals):
                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                        target_index = -1
                        # check visible 5 slots
                        for i in range(5):
                            if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                target_index = i
                                break
                        if target_index == -1:
                            # append to end of inventory
                            target_index = len(game.player.inventory)
                        game.player.inventory.insert(target_index, game.dragged_item)
                        dropped_successfully = True
                        break

            # If still not placed, attempt to drop into any open container under mouse
            if not dropped_successfully:
                for modal in reversed(game.modals):
                    if modal['type'] == 'container' and modal['rect'].collidepoint(mouse_pos):
                        container = modal['item']
                        # Prevent placing a container/backpack into itself
                        if game.dragged_item is container:
                            print("Cannot place a container inside itself.")
                            continue

                        # Prevent placing the equipped backpack into its own open inventory
                        if game.dragged_item is game.player.backpack and container is game.player.backpack:
                            print("Cannot move the equipped backpack into its own contents.")
                            continue

                        if len(container.inventory) < (container.capacity or 0):
                            container.inventory.append(game.dragged_item)
                            print(f"Moved {game.dragged_item.name} to {container.name}")
                            dropped_successfully = True
                            break
                        else:
                            print(f"{container.name} is full.")
                # end for container modals

            # If still not placed, drop to world if mouse over game area
            if not dropped_successfully:
                game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
                if game_world_rect.collidepoint(mouse_pos):
                    # Drop item on the floor
                    game.dragged_item.rect.x = game.player.rect.centerx
                    game.dragged_item.rect.y = game.player.rect.centery + TILE_SIZE
                    game.items_on_ground.append(game.dragged_item)
                    print(f"Dropped {game.dragged_item.name} by dragging.")
                else:
                    # Snap back to original location as last resort
                    if type_orig == 'inventory' and 0 <= i_orig <= len(game.player.inventory):
                        game.player.inventory.insert(i_orig, game.dragged_item)
                    elif type_orig == 'belt' and 0 <= i_orig < len(game.player.belt):
                        game.player.belt[i_orig] = game.dragged_item
                    elif type_orig == 'backpack':
                        game.player.backpack = game.dragged_item
                    elif type_orig == 'container' and container_obj is not None:
                        container_obj.inventory.insert(i_orig, game.dragged_item)

            # Clean None holes
            game.player.inventory = [item for item in game.player.inventory if item is not None]

        # Reset drag state
        game.is_dragging = False
        game.dragged_item = None
        game.drag_origin = None
        game.drag_candidate = None

def handle_mouse_motion(game, event, mouse_pos):
    if game.context_menu['active']:
        # We don't need to do anything here for hover, draw_context_menu will handle it
        pass

    if game.drag_candidate and not game.is_dragging:
        dist = math.hypot(mouse_pos[0] - game.drag_start_pos[0], mouse_pos[1] - game.drag_start_pos[1])
        if dist > game.DRAG_THRESHOLD:
            game.is_dragging = True
            game.dragged_item, game.drag_origin = game.drag_candidate
            game.drag_candidate = None
            
            # Remove item from its original location now that drag is confirmed
            i_orig, type_orig, *container_info = game.drag_origin
            if type_orig == 'inventory':
                game.player.inventory.pop(i_orig)
            elif type_orig == 'belt':
                if game.player.active_weapon == game.player.belt[i_orig]:
                    game.player.active_weapon = None
                game.player.belt[i_orig] = None
            elif type_orig == 'backpack':
                game.player.backpack = None
            elif type_orig == 'container':
                container_obj = container_info[0]
                container_obj.inventory.pop(i_orig)

    for modal in game.modals:
        if modal['is_dragging']:
            modal['position'] = (mouse_pos[0] - modal['drag_offset'][0], mouse_pos[1] - modal['drag_offset'][1])
            # Update the rect as well for collision detection
            modal['rect'].topleft = modal['position']

def resolve_drag_origin_from_item(item, player, modals):
    # search player's inventory
    if item is None:
        return None
    try:
        if item in player.inventory:
            return (player.inventory.index(item), 'inventory')
        if item in player.belt:
            return (player.belt.index(item), 'belt')
        if player.backpack is item:
            return (0, 'backpack')
        # search open container modals for the item
        for modal in modals:
            if modal.get('type') == 'container' and modal.get('item') and hasattr(modal['item'], 'inventory'):
                cont = modal['item']
                if item in cont.inventory:
                    return (cont.inventory.index(item), 'container', cont)
    except Exception:
        pass
    return None
