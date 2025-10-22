import pygame
import random
import time
import math
import uuid
import os

from config import *

# Global dictionary to store last known positions of modals
last_modal_positions = {
    'status': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 200),
    'inventory': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 200),
    'container': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150)
}

# Updated imports to the new modular structure
from core.player import Player
from core.zombies import Zombie
from core.items import Item, Projectile

# UI and modal functions split:
from ui import draw_menu, draw_game_over, get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect, get_container_slot_rect
from modals import draw_inventory_modal, draw_container_view, draw_inventory_button, draw_status_button, draw_status_modal, draw_context_menu

from xml_parser import parse_player_data

VIRTUAL_SCREEN = pygame.Surface((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT))
SCREEN = pygame.display.set_mode((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Bit Rot")

# --- Player Experience and Leveling ---
def experience_for_level(level):
    """Calculates the experience needed for a given level."""
    return int(100 * (1.5 ** (level - 1)))

# --- 3. UI AND GAME LOGIC FUNCTIONS ---

def player_hit_zombie(player, zombie):
    """Calculates damage and processes the hit."""
    
    active_weapon = player.active_weapon
    base_damage = 1 # Unarmed base damage
    weapon_durability_loss = 0
    
    if active_weapon:
        if 'Gun' in active_weapon.name:
            base_damage = 8  # reduced from 15 -> less one-shot kills
        elif active_weapon.item_type in ['weapon', 'tool']:
            # Damage based on weapon type and player skills
            if 'Axe' in active_weapon.name:
                base_damage = 5 + (player.skill_strength * 0.5)
            elif 'Knife' in active_weapon.name:
                base_damage = 2 + (player.skill_strength * 0.2)
            else: # Generic melee
                base_damage = 3 + (player.skill_strength * 0.3)

            if random.randint(0, 10) < player.skill_melee:
                weapon_durability_loss = 0.5 
            else:
                weapon_durability_loss = 2.0 
    else: # Unarmed
        base_damage = 1 + (player.skill_strength * 0.1)

    # RANGED WEAPON DURABILITY CHECK handled in shooting code

    # MELEE WEAPON DURABILITY CHECK
    if active_weapon and 'Gun' not in active_weapon.name:
        if active_weapon.durability is not None and active_weapon.durability > 0:
            active_weapon.durability -= weapon_durability_loss
            if active_weapon.durability <= 0:
                player.active_weapon = None
                # IMPORTANT: If the broken item was in the belt, also remove it from the belt
                for i, item in enumerate(player.belt):
                    if item == active_weapon:
                        player.belt[i] = None
                        break
                print(f"{active_weapon.name} broke! Unequipped and removed from belt/inventory.")


    is_headshot = False
    damage_multiplier = 1.0
    if active_weapon and 'Gun' in active_weapon.name:
        headshot_chance = 0.1 + (player.skill_ranged * 0.04) 
        if random.random() < headshot_chance:
            is_headshot = True
            damage_multiplier = 2.0
            
    # Apply melee skill multiplier for melee attacks
    if not (active_weapon and 'Gun' in active_weapon.name):
        damage_multiplier *= (1 + player.skill_melee * 0.1)
    final_damage = (base_damage * damage_multiplier)
    
    if zombie.take_damage(final_damage):
        return True 
    
    hit_type = "Headshot" if is_headshot else "Hit"
    print(f"{hit_type}! Dealt {final_damage:.1f} damage.")
    return False 

def create_obstacles_from_map(layout):
    """Creates a list of obstacle Rects from a text-based map layout."""
    obstacles = []
    for y, row in enumerate(layout):
        for x, char in enumerate(row):
            if char == '#':
                obstacles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
    return obstacles

# Simple container object used for dead corpses (lootable)
class Corpse:
    def __init__(self, name="Dead corpse", capacity=8, image_path=None, pos=(0,0)):
        self.name = name
        self.capacity = capacity
        self.inventory = []
        self.weight = 35
        self.image = None
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                # scale to tile size for consistency with item sprites
                self.image = pygame.transform.scale(self.image, (TILE_SIZE, TILE_SIZE))
            except Exception:
                self.image = None
        self.rect = pygame.Rect(0,0,TILE_SIZE, TILE_SIZE)
        self.rect.center = pos
        self.spawn_time = pygame.time.get_ticks()  # for decay
        self.color = DARK_GRAY

def handle_zombie_death(player, zombie, items_on_ground_list, obstacles):
    """Processes loot drops when a zombie dies."""
    print(f"A {zombie.name} died. Creating corpse and checking for loot...")
    # create corpse at zombie position
    dead_sprite_path = os.path.join('game', 'zombies', 'sprites', 'dead.png')
    corpse = Corpse(name="Dead corpse", capacity=32, image_path=dead_sprite_path, pos=zombie.rect.center)
    # build its inventory from the zombie loot table
    if hasattr(zombie, 'loot_table'):
        for drop in zombie.loot_table:
            if random.random() < drop.get('chance', 0):
                item_inst = Item.create_from_name(drop.get('item'))
                if item_inst:
                    corpse.inventory.append(item_inst)
                else:
                    print(f"Failed to create item: {drop.get('item')}")
    # append corpse to world items (it behaves like an item on ground)
    items_on_ground_list.append(corpse)

    # --- Experience Gain ---
    player.experience += zombie.xp_value
    print(f"Gained {zombie.xp_value} experience. Total XP: {player.experience}")
    # --- Level Up Check ---
    xp_needed = experience_for_level(player.level + 1)
    if player.experience >= xp_needed:
        player.level += 1
        player.skill_strength += 1
        player.skill_melee += 1
        player.skill_ranged += 1
        player.max_health += 10
        player.health = player.max_health # Full heal on level up
        print(f"LEVEL UP! You are now level {player.level}!")

# --- 4. MAIN GAME LOOP ---

def run_game():
    global SCREEN # Allow modification of the global SCREEN surface on resize
    zombies_killed = 0
    player_data = parse_player_data()

    # Generate obstacles from the predefined map layout
    obstacles = create_obstacles_from_map(MAP_LAYOUT)
    
    items_on_ground = [Item.generate_random() for _ in range(5)]
    for item in items_on_ground:
        attempts = 0
        max_attempts = 200 # Increased attempts
        original_x, original_y = item.rect.x, item.rect.y # Store original position

        # Ensure items don't spawn inside obstacles or on top of other items
        while (any(item.rect.colliderect(ob) for ob in obstacles) or \
               any(item.rect.colliderect(other_item.rect) for other_item in items_on_ground if other_item is not item)) and attempts < max_attempts:
            item.rect.x = random.randint(0, GAME_WIDTH - TILE_SIZE) 
            item.rect.y = random.randint(0, GAME_HEIGHT - TILE_SIZE)
            attempts += 1
        
        if attempts == max_attempts: # If couldn't find a clear spot, try a small offset from original
            item.rect.x = original_x + random.randint(-TILE_SIZE, TILE_SIZE)
            item.rect.y = original_y + random.randint(-TILE_SIZE, TILE_SIZE)
            # Ensure it's still within bounds after offset
            item.rect.x = max(0, min(item.rect.x, GAME_WIDTH - TILE_SIZE))
            item.rect.y = max(0, min(item.rect.y, GAME_HEIGHT - TILE_SIZE))

    zombies = [Zombie.create_random(random.randint(50, GAME_WIDTH-50), random.randint(50, GAME_HEIGHT-50)) for _ in range(3)]
    projectiles = [] 

    # Drag-and-Drop State Variables
    is_dragging = False
    dragged_item = None
    drag_origin = None 
    drag_offset = (0, 0)
    drag_candidate = None # Stores the item being considered for a drag
    drag_start_pos = (0, 0)
    DRAG_THRESHOLD = 5 # Pixels the mouse must move to initiate a drag
    
    # --- Modal Management ---
    modals = [] # List to hold active modals. Each modal is a dict with {'id', 'type', 'item', 'position', 'is_dragging', 'drag_offset', 'rect'}

    # --- Context Menu State ---
    context_menu = {
        'active': False,
        'item': None,
        'source': None, # e.g., 'inventory', 'belt', 'container'
        'index': -1,
        'options': [],
        'rects': [],
        'position': (0, 0)
    }

    # --- Cursor Setup ---
    try:
        cursor_image = pygame.image.load('game/ui/cursor.png').convert_alpha()
        cursor_hotspot = (0, 0) # The tip of the arrow
        custom_cursor = pygame.cursors.Cursor(cursor_hotspot, cursor_image)
    except pygame.error as e:
        print(f"Error loading cursor: {e}")
        custom_cursor = None # Fallback to default cursor
    try:
        aim_cursor_image = pygame.image.load('game/ui/aim.png').convert_alpha()
        aim_cursor_hotspot = (aim_cursor_image.get_width() // 2, aim_cursor_image.get_height() // 2)
        aim_cursor = pygame.cursors.Cursor(aim_cursor_hotspot, aim_cursor_image)
    except pygame.error as e:
        print(f"Error loading aim cursor: {e}")
        aim_cursor = None # Fallback to default cursor


    game_state = 'MENU' # Can be 'MENU', 'PLAYING', 'GAME_OVER'
    clock = pygame.time.Clock()
    
    while True: # Main loop that manages game states
        # --- Mouse Coordinate Scaling ---
        # All game logic uses VIRTUAL_SCREEN coordinates.
        # We must scale the real mouse position to virtual coordinates.
        real_mouse_pos = pygame.mouse.get_pos()
        screen_w, screen_h = SCREEN.get_size()
        scale_x = VIRTUAL_SCREEN_WIDTH / screen_w
        scale_y = VIRTUAL_GAME_HEIGHT / screen_h
        mouse_pos = (real_mouse_pos[0] * scale_x, real_mouse_pos[1] * scale_y)

        # Helper: when dropping, if drag_origin is missing try to infer it from the dragged item
        def resolve_drag_origin_from_item(item):
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
        attack_mode = pygame.key.get_pressed()[pygame.K_LSHIFT] or pygame.key.get_pressed()[pygame.K_RSHIFT]

        # Set cursor visibility based on game state
        if game_state == 'PLAYING' and not attack_mode and custom_cursor:
            pygame.mouse.set_cursor(custom_cursor)
        elif game_state == 'PLAYING' and attack_mode and aim_cursor:
            pygame.mouse.set_cursor(aim_cursor)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        if game_state == 'MENU':
            start_button, quit_button = draw_menu(VIRTUAL_SCREEN)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE:
                    SCREEN = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if start_button.collidepoint(mouse_pos):
                        player = Player(player_data=player_data)
                        player.x = GAME_WIDTH // 2
                        player.y = GAME_HEIGHT // 2
                        player.rect.topleft = (player.x, player.y)
                        # --- Initialize inventory from parsed data ---
                        player.inventory = [Item.create_from_name(name) for name in player_data['initial_loot'] if Item.create_from_name(name)]
                        player.max_carry_weight = 10 + (player.skill_strength * 5) # Set initial carry weight

                        zombies_killed = 0
                        obstacles = create_obstacles_from_map(MAP_LAYOUT)
                        items_on_ground = [Item.generate_random() for _ in range(5)]
                        for item in items_on_ground:
                            while any(item.rect.colliderect(ob) for ob in obstacles):
                                item.rect.x = random.randint(0, GAME_WIDTH - 20)
                                item.rect.y = random.randint(100, GAME_HEIGHT - 100)
                        zombies = [Zombie.create_random(random.randint(50, GAME_WIDTH-50), random.randint(50, GAME_HEIGHT-50)) for _ in range(3)]
                        projectiles = []
                        game_state = 'PLAYING'
                    elif quit_button.collidepoint(mouse_pos):
                        pygame.quit()
                        return

        elif game_state == 'GAME_OVER':
            draw_game_over(VIRTUAL_SCREEN, zombies_killed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE:
                    SCREEN = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    restart_button, quit_button = draw_game_over(VIRTUAL_SCREEN, zombies_killed)
                    if restart_button.collidepoint(mouse_pos):
                        player_data = parse_player_data()
                        # Reset game variables for a new game
                        player = Player(player_data=player_data)
                        # --- Initialize inventory from parsed data ---
                        player.inventory = [Item.create_from_name(name) for name in player_data['initial_loot'] if Item.create_from_name(name)]
                        player.max_carry_weight = 10 + (player.skill_strength * 5) # Set initial carry weight

                        zombies_killed = 0
                        obstacles = create_obstacles_from_map(MAP_LAYOUT)
                        items_on_ground = [Item.generate_random() for _ in range(5)]
                        for item in items_on_ground:
                            while any(item.rect.colliderect(ob) for ob in obstacles):
                                item.rect.x = random.randint(0, GAME_WIDTH - 20) 
                                item.rect.y = random.randint(100, GAME_HEIGHT - 100)
                        zombies = [Zombie.create_random(random.randint(50, GAME_WIDTH-50), random.randint(50, GAME_HEIGHT-50)) for _ in range(3)]
                        projectiles = []
                        game_state = 'PLAYING'
                    elif quit_button.collidepoint(mouse_pos):
                        pygame.quit()
                        return

        elif game_state == 'PLAYING':
            # --- Input and Event Handling ---
            dx, dy = 0, 0
            keys = pygame.key.get_pressed()
            
            current_speed = PLAYER_SPEED
            if player.stamina <= 0:
                current_speed = PLAYER_SPEED / 2

            if keys[pygame.K_w] or keys[pygame.K_UP]: dy -= current_speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]: dy += current_speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]: dx -= current_speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += current_speed

            player.update_position(dx, dy, obstacles, zombies)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE:
                    SCREEN = pygame.display.set_mode(event.size, pygame.RESIZABLE)

                # --- All other event logic for PLAYING state ---
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e:
                        item_to_pickup = next((item for item in items_on_ground if player.rect.colliderect(item.rect)), None)
                        if item_to_pickup:
                            # --- Weight Check ---
                            if player.get_inventory_weight() + item_to_pickup.weight > player.max_carry_weight:
                                print("You are carrying too much to pick that up!")
                            else:
                                # --- New Pickup Logic ---
                                target_inventory = None
                                target_name = ""

                                # 1. If backpack is open, target the backpack
                                if player.backpack and any(m['type'] == 'container' and m['item'] == player.backpack for m in modals):
                                    target_inventory = player.backpack.inventory
                                    target_capacity = player.backpack.capacity
                                    target_name = player.backpack.name
                                # 2. Otherwise, target the main inventory
                                else:
                                    target_inventory = player.inventory
                                    target_capacity = player.base_inventory_slots
                                    target_name = "Inventory"

                                # Stacking Logic (safe checks to avoid NoneType comparisons)
                                found_stack = False
                                if getattr(item_to_pickup, 'item_type', None) == 'consumable' and getattr(item_to_pickup, 'capacity', None):
                                    # ensure item_to_pickup has a numeric load
                                    if getattr(item_to_pickup, 'load', None) is None:
                                        item_to_pickup.load = 0
                                    for existing_item in list(target_inventory):
                                        if not existing_item:
                                            continue
                                        # only stack consumables of same name that have numeric load/capacity
                                        if getattr(existing_item, 'item_type', None) != 'consumable':
                                            continue
                                        if existing_item.name != item_to_pickup.name:
                                            continue
                                        if getattr(existing_item, 'load', None) is None or getattr(existing_item, 'capacity', None) is None:
                                            continue
                                        if existing_item.load >= existing_item.capacity:
                                            continue
                                        transfer = min(item_to_pickup.load, existing_item.capacity - existing_item.load)
                                        if transfer <= 0:
                                            continue
                                        existing_item.load += transfer
                                        item_to_pickup.load = max(0, item_to_pickup.load - transfer)
                                        found_stack = True
                                        print(f"Stacked {transfer:.0f} {item_to_pickup.name} in {target_name}.")
                                        if item_to_pickup.load <= 0:
                                            try:
                                                items_on_ground.remove(item_to_pickup)
                                            except ValueError:
                                                pass
                                        break
                                
                                # Pickup to empty slot if not stacked or not stackable
                                if not found_stack and (item_to_pickup.load is None or item_to_pickup.load > 0):
                                    if len(target_inventory) < target_capacity:
                                        target_inventory.append(item_to_pickup)
                                        items_on_ground.remove(item_to_pickup)
                                        print(f"Picked up {item_to_pickup.name} to {target_name}.")
                                    else:
                                        print(f"{target_name} is full!")

                        else:
                            print("No items nearby.")

                    # Toggle inventory with 'i'
                    if event.key == pygame.K_i:
                        inventory_modal_exists = False
                        for modal in modals:
                            if modal['type'] == 'inventory':
                                modals.remove(modal)
                                inventory_modal_exists = True
                                break
                        if not inventory_modal_exists:
                            new_inventory_modal = {
                                'id': uuid.uuid4(),
                                'type': 'inventory',
                                'item': None,
                                'position': last_modal_positions['inventory'],
                                'is_dragging': False,
                                'drag_offset': (0, 0),
                                'rect': pygame.Rect(last_modal_positions['inventory'][0], last_modal_positions['inventory'][1], 300, 620)
                            }
                            modals.append(new_inventory_modal)

                    # Toggle status with 'h'
                    if event.key == pygame.K_h:
                        status_modal_exists = False
                        for modal in modals:
                            if modal['type'] == 'status':
                                modals.remove(modal)
                                status_modal_exists = True
                                break
                        if not status_modal_exists:
                            new_status_modal = {
                                'id': uuid.uuid4(),
                                'type': 'status',
                                'item': None,
                                'position': last_modal_positions['status'],
                                'is_dragging': False,
                                'drag_offset': (0, 0),
                                'rect': pygame.Rect(last_modal_positions['status'][0], last_modal_positions['status'][1], 300, 400)
                            }
                            modals.append(new_status_modal)
                    
                    if event.key == pygame.K_r:
                        player.reload_active_weapon()

                    if event.key == pygame.K_ESCAPE:
                        if modals: # If there are any open modals
                            modals.pop() # Close the topmost modal

                    if pygame.K_1 <= event.key <= pygame.K_5:
                        slot_index = event.key - pygame.K_1
                        item = player.belt[slot_index]
                        if item:
                            if item.item_type == 'consumable':
                                player.consume_item(item, 'belt', slot_index)
                            elif item.item_type == 'weapon' or item.item_type == 'tool':
                                player.active_weapon = item
                                print(f"Equipped {item.name}.")
                        else:
                            player.active_weapon = None
                            print(f"Belt slot {slot_index + 1} is empty. Unequipped.")
                

                if event.type == pygame.MOUSEBUTTONDOWN:
                    # --- Status Button Click ---
                    status_button_rect = draw_status_button(VIRTUAL_SCREEN) # Draw to get its rect
                    if event.button == 1 and status_button_rect.collidepoint(mouse_pos):
                        status_modal_exists = False
                        for modal in modals:
                            if modal['type'] == 'status':
                                modals.remove(modal)
                                status_modal_exists = True
                                break
                        
                        if not status_modal_exists:
                            new_status_modal = {
                                'id': uuid.uuid4(),
                                'type': 'status',
                                'item': None, # No item for status modal
                                'position': last_modal_positions['status'], # Use stored position
                                'is_dragging': False,
                                'drag_offset': (0, 0),
                                'rect': pygame.Rect(last_modal_positions['status'][0], last_modal_positions['status'][1], 300, 400) # Initial rect
                            }
                            modals.append(new_status_modal)
                        continue # Consume the click
                    
                    inventory_button_rect = draw_inventory_button(VIRTUAL_SCREEN) # Draw to get its rect
                    if event.button == 1 and inventory_button_rect.collidepoint(mouse_pos):
                        inventory_modal_exists = False
                        for modal in modals:
                            if modal['type'] == 'inventory':
                                modals.remove(modal)
                                inventory_modal_exists = True
                                break
                        
                        if not inventory_modal_exists:
                            new_inventory_modal = {
                                'id': uuid.uuid4(),
                                'type': 'inventory',
                                'item': None, # No item for status modal
                                'position': last_modal_positions['inventory'], # Use stored position
                                'is_dragging': False,
                                'drag_offset': (0, 0),
                                # draw_inventory_modal uses height 620, keep rect consistent so slot hit-tests match visuals
                                'rect': pygame.Rect(last_modal_positions['inventory'][0], last_modal_positions['inventory'][1], 300, 620) # Initial rect
                            }
                            modals.append(new_inventory_modal)
                        continue # Consume the click

                    # --- Modal Drag Logic ---
                    # Check if any modal header is clicked for dragging
                    for modal in modals:
                        modal_header_rect = pygame.Rect(modal['position'][0], modal['position'][1], 300, 35) # Assuming 300 width and 35 header height for all modals
                        if event.button == 1 and modal_header_rect.collidepoint(mouse_pos):
                            modal['is_dragging'] = True
                            modal['drag_offset'] = (mouse_pos[0] - modal['position'][0], mouse_pos[1] - modal['position'][1])
                            # Bring the dragged modal to the front (last in list)
                            modals.remove(modal)
                            modals.append(modal)
                            continue # Consume the click

                    # --- Context Menu & Left-Click Action Logic ---
                    if context_menu['active'] and event.button == 1:
                        clicked_on_menu = False
                        for i, rect in enumerate(context_menu['rects']):
                            if rect.collidepoint(mouse_pos):
                                option = context_menu['options'][i]
                                item = context_menu['item']
                                source = context_menu['source']
                                index = context_menu['index']
                                container_item = context_menu.get('container_item')

                                print(f"Clicked '{option}' on '{getattr(item,'name',str(item))}' (source={source})")

                                # --- Handle Actions ---
                                if option == 'Use':
                                    player.consume_item(item, source, index, container_item)

                                elif option == 'Reload':
                                    player.reload_active_weapon()

                                elif option == 'Equip':
                                    # Equip behavior:
                                    # - Backpacks equip to backpack slot (swap if needed)
                                    # - Weapons/tools equip to belt (or first free belt slot)
                                    if getattr(item, 'item_type', None) == 'backpack':
                                        # remove item from its source
                                        def remove_from_source(src, idx, c_item=None):
                                            if src == 'inventory' and 0 <= idx < len(player.inventory):
                                                return player.inventory.pop(idx)
                                            if src == 'belt' and 0 <= idx < len(player.belt):
                                                it = player.belt[idx]
                                                player.belt[idx] = None
                                                return it
                                            if src == 'container' and c_item and 0 <= idx < len(c_item.inventory):
                                                return c_item.inventory.pop(idx)
                                            if src == 'ground' and 0 <= idx < len(items_on_ground):
                                                return items_on_ground.pop(idx)
                                            return None

                                        # perform equip (swap if backpack already equipped)
                                        old_backpack = player.backpack
                                        # remove selected backpack from its source
                                        removed = remove_from_source(source, index, container_item)
                                        player.backpack = item
                                        print(f"Equipped {item.name} as backpack.")

                                        # try to return old_backpack to same source (or fall back to inventory or ground)
                                        if old_backpack:
                                            placed = False
                                            if source == 'inventory':
                                                player.inventory.insert(index if 0 <= index <= len(player.inventory) else len(player.inventory), old_backpack)
                                                placed = True
                                            elif source == 'belt':
                                                # place in same belt slot if empty, else first empty
                                                if 0 <= index < len(player.belt) and player.belt[index] is None:
                                                    player.belt[index] = old_backpack
                                                    placed = True
                                                else:
                                                    for bi in range(len(player.belt)):
                                                        if player.belt[bi] is None:
                                                            player.belt[bi] = old_backpack
                                                            placed = True
                                                            break
                                            elif source == 'container' and container_item:
                                                container_item.inventory.insert(index if 0 <= index <= len(container_item.inventory) else len(container_item.inventory), old_backpack)
                                                placed = True
                                            if not placed:
                                                # fallback to main inventory if space, otherwise drop to ground
                                                if len(player.inventory) < player.get_total_inventory_slots():
                                                    player.inventory.append(old_backpack)
                                                else:
                                                    old_backpack.rect.center = player.rect.center
                                                    items_on_ground.append(old_backpack)
                                                    print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")

                                    else:
                                        # standard weapon/tool equip flows
                                        if source == 'ground':
                                            placed = False
                                            # try to equip to first empty belt slot
                                            for bi, slot in enumerate(player.belt):
                                                if slot is None and getattr(item, 'item_type', None) in ('weapon', 'tool'):
                                                    player.belt[bi] = item
                                                    # remove from ground list
                                                    if 0 <= index < len(items_on_ground):
                                                        items_on_ground.pop(index)
                                                    print(f"Picked up and equipped {item.name} to belt slot {bi+1}.")
                                                    placed = True
                                                    break
                                            if not placed:
                                                # fallback: put into inventory if space and equip as active weapon if applicable
                                                if len(player.inventory) < player.get_total_inventory_slots():
                                                    player.inventory.append(item)
                                                    if 0 <= index < len(items_on_ground):
                                                        items_on_ground.pop(index)
                                                    print(f"Picked up {item.name} into inventory.")
                                                else:
                                                    print("No space to equip or pick up the item.")
                                            if getattr(item, 'item_type', None) == 'weapon':
                                                player.active_weapon = item
                                        else:
                                            # equip from inventory/container/belt
                                            player.equip_item_to_belt(item, source, index, container_item)

                                elif option == 'Drop':
                                    dropped_item = player.drop_item(source, index, container_item)
                                    if dropped_item:
                                        dropped_item.rect.center = player.rect.center
                                        items_on_ground.append(dropped_item)

                                elif option == 'Open':
                                    # Open container modal if not already open
                                    modal_exists = any(m['type'] == 'container' and m['item'] == item for m in modals)
                                    if not modal_exists:
                                        new_container_modal = {
                                            'id': uuid.uuid4(),
                                            'type': 'container',
                                            'item': item,
                                            'position': last_modal_positions['container'],
                                            'is_dragging': False, 'drag_offset': (0, 0),
                                            'rect': pygame.Rect(last_modal_positions['container'][0], last_modal_positions['container'][1], 300, 300)
                                        }
                                        modals.append(new_container_modal)

                                elif option == 'Unequip':
                                    if source == 'belt':
                                        if 0 <= index < len(player.belt) and player.belt[index] == item:
                                            player.belt[index] = None
                                        if player.active_weapon == item:
                                            player.active_weapon = None
                                        # move to inventory or drop if full
                                        if len(player.inventory) < player.get_total_inventory_slots():
                                            player.inventory.append(item)
                                            print(f"Unequipped {item.name} -> Inventory")
                                        else:
                                            item.rect.center = player.rect.center
                                            items_on_ground.append(item)
                                            print(f"Unequipped {item.name} -> Dropped on ground (inventory full)")
                                    else:
                                        print("Unequip is only available for belt items.")

                                # Ground-specific actions
                                elif source == 'ground' and option == 'Grab':
                                    ground_idx = index
                                    if 0 <= ground_idx < len(items_on_ground):
                                        ground_item = items_on_ground[ground_idx]
                                        if player.get_inventory_weight() + ground_item.weight > player.max_carry_weight:
                                            print("You are carrying too much to pick that up!")
                                        else:
                                            # prefer backpack if container modal of backpack is open
                                            target_inventory = player.inventory
                                            target_capacity = player.base_inventory_slots
                                            if player.backpack and any(m['type'] == 'container' and m['item'] == player.backpack for m in modals):
                                                target_inventory = player.backpack.inventory
                                                target_capacity = player.backpack.capacity or 0
                                            if len(target_inventory) < target_capacity:
                                                target_inventory.append(ground_item)
                                                items_on_ground.pop(ground_idx)
                                                print(f"Grabbed {ground_item.name}.")
                                            elif len(player.inventory) < player.get_total_inventory_slots():
                                                player.inventory.append(ground_item)
                                                items_on_ground.pop(ground_idx)
                                                print(f"Grabbed {ground_item.name} into inventory.")
                                            else:
                                                print("No space to grab the item.")

                                elif source == 'ground' and option == 'Place on Backpack':
                                    if player.backpack and getattr(player.backpack, 'inventory', None) is not None:
                                        ground_idx = index
                                        if 0 <= ground_idx < len(items_on_ground):
                                            ground_item = items_on_ground[ground_idx]
                                            if len(player.backpack.inventory) < (player.backpack.capacity or 0):
                                                player.backpack.inventory.append(ground_item)
                                                items_on_ground.pop(ground_idx)
                                                print(f"Placed {ground_item.name} into backpack.")
                                            else:
                                                print("Backpack is full.")
                                    else:
                                        print("No backpack equipped.")

                                clicked_on_menu = True
                                break

                        context_menu['active'] = False
                        if clicked_on_menu:
                            continue # Consume the click

                    # --- Right-Click Logic to OPEN Context Menu ---
                    if event.button == 3: # Right-click
                        context_menu['active'] = False # Close any existing menu
                        clicked_item = None
                        click_source = None
                        click_index = -1
                        click_container_item = None

                        # Check modals in reverse order (top-most first)
                        for modal in reversed(modals):
                            if not modal['rect'].collidepoint(mouse_pos): continue

                            if modal['type'] == 'inventory':
                                # Check main inventory slots
                                for i, item in enumerate(player.inventory):
                                    if item and get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                        clicked_item, click_source, click_index = item, 'inventory', i; break
                                # Check belt slots
                                if not clicked_item:
                                    for i, item in enumerate(player.belt):
                                        if item and get_belt_slot_rect_in_modal(i, modal['position']).collidepoint(mouse_pos):
                                            clicked_item, click_source, click_index = item, 'belt', i; break
                                # Check backpack slot
                                if not clicked_item:
                                    clicked_item, click_source, click_index = player.backpack, 'backpack', 0
                            
                            elif modal['type'] == 'container':
                                container = modal['item']
                                for i, item in enumerate(container.inventory):
                                    if item and get_container_slot_rect(modal['position'], i).collidepoint(mouse_pos):
                                        clicked_item, click_source, click_index, click_container_item = item, 'container', i, container; break
                            
                            if clicked_item: break

                        # If nothing in modals was clicked, check ground items
                        if not clicked_item:
                            for i, ground_item in enumerate(items_on_ground):
                                # account for GAME_OFFSET_X when checking mouse vs item rect
                                item_rect_world = ground_item.rect.move(GAME_OFFSET_X, 0)
                                if item_rect_world.collidepoint(mouse_pos):
                                    clicked_item = ground_item
                                    click_source = 'ground'
                                    click_index = i
                                    click_container_item = None
                                    break

                        if clicked_item:
                            context_menu['active'] = True
                            context_menu['item'] = clicked_item
                            context_menu['source'] = click_source
                            context_menu['index'] = click_index
                            context_menu['container_item'] = click_container_item
                            context_menu['position'] = mouse_pos
                            # Base options from player
                            options = player.get_item_context_options(clicked_item) if click_source != 'ground' else []
                            # If clicked from belt, allow unequip and remove 'Equip'
                            if click_source == 'belt':
                                if 'Unequip' not in options:
                                    options.append('Unequip')
                                # Ensure 'Equip' is not shown for an item that's already on the belt
                                options = [o for o in options if o != 'Equip']
                            # If ground item, show ground menu options
                            if click_source == 'ground':
                                options = ['Grab']
                                if getattr(clicked_item, 'item_type', None) in ('weapon', 'tool'):
                                    options.append('Equip')
                                # allow place on backpack if player has a backpack (slot) and it can hold items
                                if player.backpack and getattr(player.backpack, 'inventory', None) is not None:
                                    options.append('Place on Backpack')
                                # If ground item exposes an inventory (corpse/container), allow Open
                                if getattr(clicked_item, 'inventory', None) is not None:
                                    options.append('Open')
                            context_menu['options'] = options
                            context_menu['rects'] = [] # Will be populated by draw_context_menu
                            continue # Consume the right-click




                    if event.button == 1: # Left-click press - Identify a drag candidate
                        # First, check if we are clicking an item in an open container
                        # Iterate through modals in reverse to check topmost first
                        for modal in reversed(modals):
                            if modal['type'] == 'container':
                                container_item = modal['item']
                                for i, item in enumerate(container_item.inventory):
                                    slot_rect = get_container_slot_rect(modal['position'], i)
                                    if slot_rect.collidepoint(mouse_pos):
                                        drag_candidate = (item, (i, 'container', container_item, modal['id'])) # Pass modal ID
                                        drag_start_pos = mouse_pos
                                        drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                        break
                                if drag_candidate: break # Found a drag candidate in a container
                        if drag_candidate: continue

                        # If no candidate from container, check inventory modal, belt, etc.
                        for modal in reversed(modals):
                            if modal['type'] == 'inventory':
                                for i, item in enumerate(player.inventory):
                                    if item:
                                        slot_rect = get_inventory_slot_rect(i, modal['position'])
                                        if slot_rect.collidepoint(mouse_pos):
                                            drag_candidate = (item, (i, 'inventory'))
                                            drag_start_pos = mouse_pos
                                            drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                            break
                                if drag_candidate: break
                        if drag_candidate: continue

                        # Check belt (only if an inventory modal is open)
                        for modal in reversed(modals):
                            if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                                for i, item in enumerate(player.belt):
                                    if item:
                                        slot_rect = get_belt_slot_rect_in_modal(i, modal['position'])
                                        if slot_rect.collidepoint(mouse_pos):
                                            drag_candidate = (item, (i, 'belt'))
                                            drag_start_pos = mouse_pos
                                            drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                            break
                                if drag_candidate: break

                        # Check backpack slot
                        for modal in reversed(modals):
                            if modal['type'] == 'inventory':
                                if player.backpack:
                                    slot_rect = get_backpack_slot_rect(modal['position'])
                                    if slot_rect.collidepoint(mouse_pos):
                                        drag_candidate = (player.backpack, (0, 'backpack'))
                                        drag_start_pos = mouse_pos
                                        drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                        break

                    if event.button == 1 and attack_mode: # Left-click attack only in attack mode
                        # If any modal is currently being dragged, do not process attack
                        if any(modal['is_dragging'] for modal in modals):
                            continue

                        # Check if click is inside any open modal (excluding header for drag)
                        click_in_modal = False
                        for modal in reversed(modals): # Check topmost modal first
                            modal_rect = modal['rect']
                            if modal_rect.collidepoint(mouse_pos):
                                click_in_modal = True
                                break
                        if click_in_modal:
                            continue # Consume the click if it's inside a modal

                        # ... (attack logic using scaled mouse_pos)
                        if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
                            weapon = player.active_weapon
                            if player.is_reloading:
                                print("Cannot shoot while reloading.")
                                continue

                            # Check for any ranged weapon (a weapon that uses ammo)
                            if weapon and weapon.item_type == 'weapon' and weapon.ammo_type:
                                if weapon.load > 0 and weapon.durability > 0:
                                    # Base direction towards the mouse
                                    base_target_x = mouse_pos[0] - GAME_OFFSET_X
                                    base_target_y = mouse_pos[1]
                                    
                                    # Calculate base angle
                                    dx = base_target_x - player.rect.centerx
                                    dy = base_target_y - player.rect.centery
                                    base_angle = math.atan2(dy, dx)

                                    for _ in range(weapon.pellets):
                                        # Apply spread
                                        spread = math.radians(random.uniform(-weapon.spread_angle / 2, weapon.spread_angle / 2))
                                        angle = base_angle + spread
                                        
                                        # Calculate new target based on spread angle (at a fixed distance)
                                        target_x = player.rect.centerx + math.cos(angle) * 1000
                                        target_y = player.rect.centery + math.sin(angle) * 1000

                                        projectiles.append(Projectile(player.rect.centerx, player.rect.centery, target_x, target_y))

                                    weapon.load -= 1
                                    weapon.durability = max(0, weapon.durability - 0.5)
                                    player.gun_flash_timer = 5
                                    if weapon.durability <= 0:
                                        for i, item in enumerate(player.belt):
                                            if item == weapon: player.belt[i] = None; break
                                        player.active_weapon = None
                                elif weapon.load <= 0: print(f"**CLICK!** {weapon.name} is out of ammo.")
                                else: print(f"**CLUNK!** {weapon.name} is broken.")
                            else:
                                if player.stamina >= 10:
                                    player.stamina -= 10
                                    player.melee_swing_timer = 10
                                    player_screen_x = player.rect.centerx + GAME_OFFSET_X
                                    player_screen_y = player.rect.centery
                                    dx_swing = mouse_pos[0] - player_screen_x
                                    dy_swing = mouse_pos[1] - player_screen_y
                                    player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
                                    hit_a_zombie = False
                                    for zombie in zombies:
                                        if player.rect.colliderect(zombie.rect.inflate(20, 20)):
                                            if player_hit_zombie(player, zombie): 
                                                handle_zombie_death(player, zombie, items_on_ground, obstacles)
                                                zombies.remove(zombie)
                                                zombies_killed += 1
                                            hit_a_zombie = True
                                            break
                                    if not hit_a_zombie: print("Swung and missed!")
                                else: print("Too tired to swing!")

                if event.type == pygame.MOUSEBUTTONUP:
                    # Stop dragging for all modals
                    for modal in modals:
                        modal['is_dragging'] = False

                    if event.button == 1:  # Left-click release
                        # If a drag was in progress OR if we have a drag candidate (for quick clicks)
                        if is_dragging or drag_candidate:
                            # If it was a quick click, initialize the drag variables and remove from source
                            if not is_dragging and drag_candidate:
                                dragged_item, drag_origin = drag_candidate
                                drag_candidate = None
                                # Remove item from its source now (keep consistent state for drop logic)
                                try:
                                    i_temp, type_temp, *container_temp = drag_origin
                                except Exception:
                                    i_temp = None; type_temp = None; container_temp = []
                                if type_temp == 'inventory' and i_temp is not None:
                                    if 0 <= i_temp < len(player.inventory):
                                        player.inventory.pop(i_temp)
                                elif type_temp == 'belt' and i_temp is not None:
                                    if 0 <= i_temp < len(player.belt):
                                        # unequip active weapon if needed
                                        if player.active_weapon == player.belt[i_temp]:
                                            player.active_weapon = None
                                        player.belt[i_temp] = None
                                elif type_temp == 'backpack':
                                    player.backpack = None
                                elif type_temp == 'container' and container_temp:
                                    cont_obj = container_temp[0]
                                    if 0 <= i_temp < len(cont_obj.inventory):
                                        cont_obj.inventory.pop(i_temp)

                            # Ensure drag_origin exists before unpacking (attempt to infer it)
                            if drag_origin is None and dragged_item:
                                inferred = resolve_drag_origin_from_item(dragged_item)
                                if inferred:
                                    if len(inferred) == 2:
                                        drag_origin = (inferred[0], inferred[1])
                                    else:
                                        drag_origin = (inferred[0], inferred[1], inferred[2])
                                else:
                                    drag_origin = (0, 'inventory')

                            # Unpack normalized drag_origin
                            i_orig, type_orig, *container_info = drag_origin
                            container_obj = container_info[0] if type_orig == 'container' and container_info else None

                            dropped_successfully = False

                            # Try placing on belt (if mouse over any belt slot)
                            for i_target in range(len(player.belt)):
                                if any(modal['type'] == 'inventory' and get_belt_slot_rect_in_modal(i_target, modal['position']).collidepoint(mouse_pos) for modal in modals):
                                    # Prevent backpacks on belt
                                    if getattr(dragged_item, 'item_type', None) == 'backpack':
                                        print("Cannot place backpacks on the belt.")
                                        dropped_successfully = False
                                        break
                                    # place or swap
                                    if player.belt[i_target] is None:
                                        player.belt[i_target] = dragged_item
                                    else:
                                        item_to_swap = player.belt[i_target]
                                        # Return swapped item to origin
                                        if type_orig == 'inventory' and 0 <= i_orig <= len(player.inventory):
                                            player.inventory.insert(i_orig, item_to_swap)
                                        elif type_orig == 'belt' and 0 <= i_orig < len(player.belt):
                                            player.belt[i_orig] = item_to_swap
                                        elif type_orig == 'container' and container_obj is not None and 0 <= i_orig <= len(container_obj.inventory):
                                            container_obj.inventory.insert(i_orig, item_to_swap)
                                        else:
                                            # fallback: put into inventory or drop
                                            if len(player.inventory) < player.get_total_inventory_slots():
                                                player.inventory.append(item_to_swap)
                                            else:
                                                item_to_swap.rect.center = player.rect.center
                                                items_on_ground.append(item_to_swap)
                                        player.belt[i_target] = dragged_item
                                    dropped_successfully = True
                                    break

                            # If not placed on belt, try placing into inventory modal (5 visible slots)
                            if not dropped_successfully:
                                for modal in reversed(modals):
                                    if modal['type'] == 'inventory' and modal['rect'].collidepoint(mouse_pos):
                                        target_index = -1
                                        # check visible 5 slots
                                        for i in range(5):
                                            if get_inventory_slot_rect(i, modal['position']).collidepoint(mouse_pos):
                                                target_index = i
                                                break
                                        if target_index == -1:
                                            # append to end of inventory
                                            target_index = len(player.inventory)
                                        player.inventory.insert(target_index, dragged_item)
                                        dropped_successfully = True
                                        break

                            # If still not placed, try backpack slot (equip/swap) — after inventory/belt checks
                            if not dropped_successfully:
                                for modal in modals:
                                    if modal['type'] == 'inventory':
                                        backpack_slot_rect = get_backpack_slot_rect(modal['position'])
                                        if backpack_slot_rect.collidepoint(mouse_pos):
                                            # Accept backpacks/containers or anything that actually has an inventory
                                            is_backpack_like = (getattr(dragged_item, 'item_type', None) in ('backpack', 'container')) or hasattr(dragged_item, 'inventory')
                                            if not is_backpack_like:
                                                # Not a backpack-like item — cannot equip here
                                                # do not treat as a fatal error; allow other placement attempts
                                                break

                                            # Ensure the dragged instance is removed from any source (defensive)
                                            try:
                                                if dragged_item in player.inventory:
                                                    player.inventory.remove(dragged_item)
                                                if dragged_item in player.belt:
                                                    for bi, it in enumerate(player.belt):
                                                        if it is dragged_item:
                                                            player.belt[bi] = None
                                                if dragged_item in items_on_ground:
                                                    items_on_ground.remove(dragged_item)
                                            except Exception:
                                                pass

                                            old_backpack = player.backpack
                                            # Equip the new backpack
                                            player.backpack = dragged_item
                                            print(f"Equipped {dragged_item.name} as backpack via drag.")

                                            # Return old backpack to a sensible place (inventory preferred)
                                            if old_backpack:
                                                returned = False
                                                # Try to put old backpack into the player's main inventory if there's room
                                                if len(player.inventory) < player.get_total_inventory_slots():
                                                    player.inventory.append(old_backpack)
                                                    returned = True
                                                else:
                                                    # Try to place in first empty belt slot
                                                    for bi in range(len(player.belt)):
                                                        if player.belt[bi] is None:
                                                            player.belt[bi] = old_backpack
                                                            returned = True
                                                            break
                                                if not returned:
                                                    # Last resort: drop on ground next to player
                                                    old_backpack.rect.center = player.rect.center
                                                    items_on_ground.append(old_backpack)
                                                    print(f"No space to return old backpack; dropped {old_backpack.name} on ground.")

                                            dropped_successfully = True
                                            break
                                # end for modal

                            # If still not placed, attempt to drop into any open container under mouse
                            if not dropped_successfully:
                                for modal in reversed(modals):
                                    if modal['type'] == 'container' and modal['rect'].collidepoint(mouse_pos):
                                        container = modal['item']
                                        # Prevent placing a container/backpack into itself
                                        if dragged_item is container:
                                            print("Cannot place a container inside itself.")
                                            continue

                                        # Prevent placing the equipped backpack into its own open inventory
                                        if dragged_item is player.backpack and container is player.backpack:
                                            print("Cannot move the equipped backpack into its own contents.")
                                            continue

                                        if len(container.inventory) < (container.capacity or 0):
                                            container.inventory.append(dragged_item)
                                            print(f"Moved {dragged_item.name} to {container.name}")
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
                                    dragged_item.rect.x = player.rect.centerx
                                    dragged_item.rect.y = player.rect.centery + TILE_SIZE
                                    items_on_ground.append(dragged_item)
                                    print(f"Dropped {dragged_item.name} by dragging.")
                                else:
                                    # Snap back to original location as last resort
                                    if type_orig == 'inventory' and 0 <= i_orig <= len(player.inventory):
                                        player.inventory.insert(i_orig, dragged_item)
                                    elif type_orig == 'belt' and 0 <= i_orig < len(player.belt):
                                        player.belt[i_orig] = dragged_item
                                    elif type_orig == 'backpack':
                                        player.backpack = dragged_item
                                    elif type_orig == 'container' and container_obj is not None:
                                        container_obj.inventory.insert(i_orig, dragged_item)

                            # Clean None holes
                            player.inventory = [item for item in player.inventory if item is not None]

                        # Reset drag state
                        is_dragging = False
                        dragged_item = None
                        drag_origin = None
                        drag_candidate = None

                if event.type == pygame.MOUSEMOTION:
                    if context_menu['active']:
                        # We don't need to do anything here for hover, draw_context_menu will handle it
                        pass

                    if drag_candidate and not is_dragging:
                        dist = math.hypot(mouse_pos[0] - drag_start_pos[0], mouse_pos[1] - drag_start_pos[1])
                        if dist > DRAG_THRESHOLD:
                            is_dragging = True
                            dragged_item, drag_origin = drag_candidate
                            drag_candidate = None
                            
                            # Remove item from its original location now that drag is confirmed
                            i_orig, type_orig, *container_info = drag_origin
                            if type_orig == 'inventory':
                                player.inventory.pop(i_orig)
                            elif type_orig == 'belt':
                                if player.active_weapon == player.belt[i_orig]:
                                    player.active_weapon = None
                                player.belt[i_orig] = None
                            elif type_orig == 'backpack':
                                player.backpack = None
                            elif type_orig == 'container':
                                container_obj = container_info[0]
                                container_obj.inventory.pop(i_orig)

                    for modal in modals:
                        if modal['is_dragging']:
                            modal['position'] = (mouse_pos[0] - modal['drag_offset'][0], mouse_pos[1] - modal['drag_offset'][1])
                            # Update the rect as well for collision detection
                            modal['rect'].topleft = modal['position']

            # --- Game State Updates ---
            if player.update_stats(): game_state = 'GAME_OVER'
            
            projectiles_to_remove = []
            zombies_to_remove = []
            for p in projectiles:
                if p.update() or any(p.rect.colliderect(ob) for ob in obstacles):
                    projectiles_to_remove.append(p)
                    continue
                hit_zombie = next((z for z in zombies if p.rect.colliderect(z.rect)), None)
                if hit_zombie:
                    if player_hit_zombie(player, hit_zombie):
                        zombies_to_remove.append(hit_zombie)
                        handle_zombie_death(player, hit_zombie, items_on_ground, obstacles)
                        zombies_killed += 1
                    projectiles_to_remove.append(p)
            projectiles = [p for p in projectiles if p not in projectiles_to_remove]
            zombies = [z for z in zombies if z not in zombies_to_remove]

            for zombie in zombies:
                zombie.move_towards(player.rect, obstacles, zombies)
                # Zombie attack logic
                distance_to_player = math.hypot(player.rect.centerx - zombie.rect.centerx, player.rect.centery - zombie.rect.centery)
                if distance_to_player < zombie.attack_range:
                    # Implement a simple cooldown for zombie attacks
                    current_time = pygame.time.get_ticks() # Get milliseconds since pygame.init()
                    if current_time - zombie.last_attack_time > 500: # 500ms cooldown
                        zombie.attack(player)
                        zombie.last_attack_time = current_time
            
            if random.random() < 0.005 and len(zombies) < 10:
                zombies.append(Zombie.create_random(random.choice([0, GAME_WIDTH]), random.choice([0, GAME_HEIGHT])))

            # --- Drawing ---
            VIRTUAL_SCREEN.fill(PANEL_COLOR) 
            game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
            VIRTUAL_SCREEN.fill(GAME_BG_COLOR, game_rect)

            for obstacle in obstacles:
                draw_rect = obstacle.move(GAME_OFFSET_X, 0)
                pygame.draw.rect(VIRTUAL_SCREEN, DARK_GRAY, draw_rect)

            # remove expired corpses (160 seconds = 160000 ms)
            now_ms = pygame.time.get_ticks()
            for ground_item in list(items_on_ground):
                if getattr(ground_item, 'spawn_time', None) is not None:
                    if now_ms - ground_item.spawn_time > 160000:
                        print(f"{getattr(ground_item,'name','Corpse')} decayed.")
                        try:
                            items_on_ground.remove(ground_item)
                        except ValueError:
                            pass

            for item in items_on_ground:
                draw_rect = item.rect.move(GAME_OFFSET_X, 0)
                if getattr(item, 'image', None):
                    VIRTUAL_SCREEN.blit(item.image, draw_rect)
                else: # Fallback to drawing a colored square
                    pygame.draw.rect(VIRTUAL_SCREEN, getattr(item, 'color', WHITE), draw_rect)
            
            # Draw projectiles so bullets are visible (draw after ground items)
            for p in projectiles:
                try:
                    p.draw(VIRTUAL_SCREEN, GAME_OFFSET_X)
                except Exception:
                    pass

            for zombie in zombies: zombie.draw(VIRTUAL_SCREEN)
            player.draw(VIRTUAL_SCREEN)
            
            if player.gun_flash_timer > 0:
                center_x = player.rect.centerx + GAME_OFFSET_X
                center_y = player.rect.centery
                pygame.draw.circle(VIRTUAL_SCREEN, YELLOW, (center_x, center_y), TILE_SIZE // 4)
                player.gun_flash_timer -= 1

            # Draw all active modals
            top_tooltip = None
            for modal in modals:
                if modal['type'] == 'status':
                    draw_status_modal(VIRTUAL_SCREEN, player, modal['position'], zombies_killed)
                elif modal['type'] == 'inventory':
                    # collect tooltip info to draw later on top
                    top_tooltip = draw_inventory_modal(VIRTUAL_SCREEN, player, modal['position'], mouse_pos) or top_tooltip
                elif modal['type'] == 'container':
                    draw_container_view(VIRTUAL_SCREEN, modal['item'], modal['position'])
            
            # Draw UI buttons on top of modals
            status_button_rect = draw_status_button(VIRTUAL_SCREEN)
            inventory_button_rect = draw_inventory_button(VIRTUAL_SCREEN)

            # Draw context menu on top of everything else if active
            if context_menu['active']:
                draw_context_menu(VIRTUAL_SCREEN, context_menu, mouse_pos)

            # --- Drag preview and slot highlight ---
            highlighted_rect = None
            highlighted_allowed = False
            if (is_dragging and dragged_item) or (drag_candidate and drag_candidate[0]):
                preview_item = dragged_item if is_dragging else drag_candidate[0]
                # Search for a target slot under the mouse (top-most modal first)
                for modal in reversed(modals):
                    if modal['type'] == 'inventory':
                        # Belt slots
                        for i in range(len(player.belt)):
                            slot = get_belt_slot_rect_in_modal(i, modal['position'])
                            if slot.collidepoint(mouse_pos):
                                highlighted_rect = slot
                                # belts cannot hold backpacks
                                highlighted_allowed = (preview_item.item_type != 'backpack')
                                break
                        if highlighted_rect:
                            break
                        # Inventory slots: FIX use exact 5 slots shown in UI
                        for i in range(5):
                            slot = get_inventory_slot_rect(i, modal['position'])
                            if slot.collidepoint(mouse_pos):
                                highlighted_rect = slot
                                highlighted_allowed = True
                                break
                        if highlighted_rect:
                            break
                        # Backpack equip slot (only one)
                        slot = get_backpack_slot_rect(modal['position'])
                        if slot.collidepoint(mouse_pos):
                            highlighted_rect = slot
                            highlighted_allowed = (preview_item.item_type == 'backpack')
                            break
                    elif modal['type'] == 'container':
                        cont = modal['item']
                        for i in range(min(cont.capacity, len(cont.inventory) + 16)):
                            slot = get_container_slot_rect(modal['position'], i)
                            if slot.collidepoint(mouse_pos):
                                highlighted_rect = slot
                                highlighted_allowed = (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                                break
                        if highlighted_rect:
                            break

                # Draw translucent highlight
                if highlighted_rect:
                    overlay = pygame.Surface((highlighted_rect.width, highlighted_rect.height), pygame.SRCALPHA)
                    color = (50, 220, 50, 80) if highlighted_allowed else (220, 50, 50, 80)
                    overlay.fill(color)
                    VIRTUAL_SCREEN.blit(overlay, highlighted_rect.topleft)
                    pygame.draw.rect(VIRTUAL_SCREEN, YELLOW if highlighted_allowed else RED, highlighted_rect, 2)

                # Draw preview sprite
                if preview_item and getattr(preview_item, 'image', None):
                    img = pygame.transform.scale(preview_item.image, (int(highlighted_rect.height * 0.9) if highlighted_rect else 40, int(highlighted_rect.height * 0.9) if highlighted_rect else 40))
                    img_rect = img.get_rect()
                    # position the preview at mouse with offset
                    img_rect.topleft = (mouse_pos[0] - drag_offset[0], mouse_pos[1] - drag_offset[1])
                    VIRTUAL_SCREEN.blit(img, img_rect)
                elif preview_item:
                    # simple colored rect preview if no sprite
                    rect_w, rect_h = (int(highlighted_rect.width * 0.8), int(highlighted_rect.height * 0.8)) if highlighted_rect else (40, 40)
                    preview_rect = pygame.Rect(mouse_pos[0] - rect_w//2, mouse_pos[1] - rect_h//2, rect_w, rect_h)
                    s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
                    s.fill((*preview_item.color, 180))
                    VIRTUAL_SCREEN.blit(s, preview_rect.topleft)

            # --- Draw inventory tooltip on top of everything (if any) ---
            if top_tooltip:
                tip_rect = top_tooltip['rect']
                item = top_tooltip['item']
                frac = top_tooltip['frac']
                bar_color = top_tooltip['bar_color']

                tip_s = pygame.Surface((tip_rect.width, tip_rect.height), pygame.SRCALPHA)
                tip_s.fill((10, 10, 10, 220))
                VIRTUAL_SCREEN.blit(tip_s, tip_rect.topleft)
                pygame.draw.rect(VIRTUAL_SCREEN, WHITE, tip_rect, 1)

                name_surf = font.render(f"{item.name}", True, WHITE)
                type_surf = font.render(f"Type: {item.item_type}", True, GRAY)
                VIRTUAL_SCREEN.blit(name_surf, (tip_rect.x + 8, tip_rect.y + 6))
                VIRTUAL_SCREEN.blit(type_surf, (tip_rect.x + 8, tip_rect.y + 26))

                bar_x = tip_rect.x + 8
                bar_y = tip_rect.y + 42
                bar_w = tip_rect.width - 16
                bar_h = 10
                pygame.draw.rect(VIRTUAL_SCREEN, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
                fill_w = int(max(0.0, min(1.0, frac)) * bar_w)
                pygame.draw.rect(VIRTUAL_SCREEN, bar_color, (bar_x, bar_y, fill_w, bar_h))
                pygame.draw.rect(VIRTUAL_SCREEN, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

        # --- Final Screen Scaling and Flip ---
        # Scale the virtual screen to the actual screen size and blit it.
        current_w, current_h = SCREEN.get_size()
        scale = min(current_w / VIRTUAL_SCREEN_WIDTH, current_h / VIRTUAL_GAME_HEIGHT)
        scaled_w, scaled_h = int(VIRTUAL_SCREEN_WIDTH * scale), int(VIRTUAL_GAME_HEIGHT * scale)
        scaled_surf = pygame.transform.scale(VIRTUAL_SCREEN, (scaled_w, scaled_h))

        # Center the scaled surface on the main screen
        blit_x = (current_w - scaled_w) // 2
        blit_y = (current_h - scaled_h) // 2

        SCREEN.fill(BLACK) # Black bars for aspect ratio
        SCREEN.blit(scaled_surf, (blit_x, blit_y))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == '__main__':
    pygame.init()
    run_game()