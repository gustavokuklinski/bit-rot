import pygame
import random
import time
import math

from config import *
from entities import Player, Zombie, Item, Projectile
from ui import draw_inventory, draw_menu, draw_game_over, get_belt_slot_rect, get_inventory_slot_rect, get_backpack_slot_rect, draw_container_view
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
            base_damage = 15
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

    # RANGED WEAPON DURABILITY CHECK (Occurs during hit, but should also occur on fire)
    # The durability loss for the gun is now primarily handled in the MOUSEBUTTONDOWN (shooting) event.
    
    # PISTOL FIX: Add a check to ensure the active weapon is not None before proceeding
    if active_weapon is None:
        # No weapon equipped, so no durability loss
        pass

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

def handle_zombie_death(player, zombie, items_on_ground_list):
    """Processes loot drops when a zombie dies."""
    print(f"A {zombie.name} died. Checking for loot...")
    if hasattr(zombie, 'loot_table'):
        for drop in zombie.loot_table:
            if random.random() < drop['chance']:
                print(f"It dropped {drop['item']}!")
                # The Item class needs to be able to be created by name.
                # We will modify the Item class in the next step.
                new_item = Item.create_from_name(drop['item'])
                if new_item:
                    new_item.rect.center = zombie.rect.center
                    items_on_ground_list.append(new_item)
                else:
                    print(f"Failed to create item: {drop['item']}")
    
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

    # Generate obstacles from the predefined map layout
    obstacles = create_obstacles_from_map(MAP_LAYOUT)
    
    items_on_ground = [Item.generate_random() for _ in range(5)]
    for item in items_on_ground:
        # Ensure items don't spawn inside obstacles
        while any(item.rect.colliderect(ob) for ob in obstacles):
            item.rect.x = random.randint(0, GAME_WIDTH - 20) 
            item.rect.y = random.randint(100, GAME_HEIGHT - 100)

    zombies = [Zombie.create_random(random.randint(50, GAME_WIDTH-50), random.randint(50, GAME_HEIGHT-50)) for _ in range(3)]
    projectiles = [] 

    # Drag-and-Drop State Variables
    is_dragging = False
    dragged_item = None
    drag_origin = None 
    drag_offset = (0, 0)
    
    inspecting_item = None # The item being inspected (e.g., a backpack on the ground)
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

        if game_state == 'MENU':
            draw_menu(VIRTUAL_SCREEN)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE:
                    SCREEN = pygame.display.set_mode(event.size, pygame.RESIZABLE)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    start_button, quit_button = draw_menu(VIRTUAL_SCREEN) # Get rects for collision
                    if start_button.collidepoint(mouse_pos):
                        player_data = parse_player_data()
                        # Reset game variables for a new game
                        player = Player(player_data=player_data)
                        # --- Initialize inventory from parsed data ---
                        player.inventory = [Item.create_from_name(name) for name in player_data['initial_loot'] if Item.create_from_name(name)]
                        player.inventory_slots = 3 # 3 main slots
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
                        player.inventory_slots = 3 # 3 main slots
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

            player.update_position(dx, dy, obstacles)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.VIDEORESIZE:
                    SCREEN = pygame.display.set_mode(event.size, pygame.RESIZABLE)

                # --- All other event logic for PLAYING state ---
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_e:
                        # ... (pickup logic)
                        picked_up = False
                        for item in items_on_ground[:]: 
                            if player.rect.colliderect(item.rect): 
                                found_stack = False 
                                if item.item_type == 'consumable' and item.capacity is not None:
                                    for existing_item in player.inventory:
                                        if existing_item.name == item.name and existing_item.load < existing_item.capacity:
                                            transfer_amount = min(item.load, existing_item.capacity - existing_item.load)
                                            existing_item.load += transfer_amount
                                            item.load -= transfer_amount
                                            found_stack = True
                                            print(f"Stacked {transfer_amount:.0f} {item.name}. New load: {existing_item.load:.0f}.")
                                            break
                                if (item.load is not None and item.load > 0) or not found_stack:
                                    # --- Inventory Weight Check ---
                                    if player.get_inventory_weight() + item.weight > player.max_carry_weight:
                                        print("You are carrying too much to pick that up!")
                                    elif len(player.inventory) < player.get_total_inventory_slots(): 
                                        player.inventory.append(item)
                                        items_on_ground.remove(item)
                                        print(f"Picked up {item.name}.")
                                        picked_up = True
                                        break
                                    else:
                                        print("Inventory is full!")
                                elif (item.load is not None and item.load <= 0) and found_stack:
                                    items_on_ground.remove(item)
                                    picked_up = True
                                    break
                        if not picked_up:
                            print("No items nearby.")

                    if event.key == pygame.K_g: # Drop item
                        item_to_drop, source, index = player.find_item_at_mouse(mouse_pos)
                        if item_to_drop:
                            dropped_item = player.drop_item(source, index)
                            if dropped_item:
                                # Position the item in front of the player
                                dropped_item.rect.x = player.rect.centerx
                                dropped_item.rect.y = player.rect.centery + TILE_SIZE
                                items_on_ground.append(dropped_item)
                                player.drop_cooldown = 10 # Prevent spam dropping
                                print(f"Dropped {dropped_item.name}.")
                        else:
                            print("No item selected to drop.")

                    if event.key == pygame.K_r:
                        player.reload_active_weapon()

                    if event.key == pygame.K_ESCAPE:
                        if inspecting_item:
                            inspecting_item = None # Close container view
                        # If we were inspecting the player's backpack and moved, close it.
                        if inspecting_item and not isinstance(inspecting_item, Item):
                            inspecting_item = None

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
                    if event.button == 3: # Right-click drag
                        # Check for inspecting item on the ground
                        if not is_dragging and not inspecting_item:
                            for item in items_on_ground:
                                if item.rect.move(GAME_OFFSET_X, 0).collidepoint(mouse_pos) and item.item_type == 'backpack':
                                    inspecting_item = item
                                    print(f"Inspecting {item.name} on the ground.")
                                    break
                        if inspecting_item: continue # Don't start a drag if inspecting
                        # ... (drag logic using scaled mouse_pos)
                        if not is_dragging:
                            inv_start_x = VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH
                            for i, item in enumerate(player.inventory):
                                slot_rect = get_inventory_slot_rect(i)
                                if slot_rect.collidepoint(mouse_pos):
                                    is_dragging = True
                                    dragged_item = item
                                    drag_origin = (i, 'inventory')
                                    drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                    player.inventory[i] = None 
                                    break
                            if not is_dragging:
                                for i, item in enumerate(player.belt):
                                    if item:
                                        slot_rect = get_belt_slot_rect(i)
                                        if slot_rect.collidepoint(mouse_pos):
                                            is_dragging = True
                                            dragged_item = item
                                            drag_origin = (i, 'belt')
                                            drag_offset = (mouse_pos[0] - slot_rect.x, mouse_pos[1] - slot_rect.y)
                                            if player.active_weapon == item:
                                                player.active_weapon = None
                                            player.belt[i] = None
                                            break
                            if not is_dragging:
                                if player.backpack:
                                    slot_rect = get_backpack_slot_rect()
                                    if slot_rect.collidepoint(mouse_pos):
                                        is_dragging = True
                                        dragged_item = player.backpack
                                        drag_origin = (0, 'backpack')
                                        player.backpack = None

                    elif event.button == 1: # Left-click attack
                        # If container view is open, handle clicks inside it
                        if inspecting_item:
                            # This is where you'd handle clicks inside the container modal
                            # For now, we'll just let it block other actions
                            continue

                        # ... (attack logic using scaled mouse_pos)
                        consumable_item, inv_index = player.find_consumable_at_mouse(mouse_pos)
                        if consumable_item:
                            if 'Ammo' not in consumable_item.name:
                                player.consume_item(consumable_item, 'inventory', inv_index)
                                continue
                        # Check for clicking on equipped backpack
                        if player.backpack and get_backpack_slot_rect().collidepoint(mouse_pos):
                            inspecting_item = player # Use player object as a sentinel for their own backpack
                            print("Opening backpack.")
                        elif GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
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
                                                handle_zombie_death(player, zombie, items_on_ground)
                                                zombies.remove(zombie)
                                                zombies_killed += 1
                                            hit_a_zombie = True
                                            break
                                    if not hit_a_zombie: print("Swung and missed!")
                                else: print("Too tired to swing!")

                if event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 3 and is_dragging: # Right-click drop
                        # Handle dropping into an open container
                        if inspecting_item:
                            container_rect = pygame.Rect(VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150, 300, 300)
                            if container_rect.collidepoint(mouse_pos):
                                container = inspecting_item if isinstance(inspecting_item, Item) else player.backpack
                                if len(container.inventory) < container.capacity:
                                    container.inventory.append(dragged_item)
                                    print(f"Moved {dragged_item.name} to {container.name}")
                                    # Finalize drag
                                    player.inventory = [item for item in player.inventory if item is not None]
                                    player.inventory_slots = player.get_total_inventory_slots()
                                    dragged_item = None; drag_origin = None; is_dragging = False
                                    continue
                                else:
                                    print(f"{container.name} is full.")
                            # If not dropped in container, the rest of the logic will handle it



                        # ... (drop logic using scaled mouse_pos)
                        i_orig, type_orig = drag_origin
                        dropped_successfully = False
                        for i_target in range(5):
                            if get_belt_slot_rect(i_target).collidepoint(mouse_pos):
                                if player.belt[i_target] is None: player.belt[i_target] = dragged_item
                                else:
                                    item_to_swap = player.belt[i_target]
                                    if type_orig == 'inventory':
                                        temp_inv = [item for item in player.inventory if item is not None]
                                        temp_inv.insert(i_orig, item_to_swap)
                                        player.inventory = temp_inv
                                    elif type_orig == 'belt': player.belt[i_orig] = item_to_swap 
                                    player.belt[i_target] = dragged_item
                                    if player.active_weapon == item_to_swap: player.active_weapon = dragged_item
                                dropped_successfully = True
                                break
                        # Check for drop in backpack slot
                        if not dropped_successfully and get_backpack_slot_rect().collidepoint(mouse_pos):
                            if dragged_item.item_type == 'backpack':
                                if player.backpack is None:
                                    player.backpack = dragged_item
                                else: # Swap backpacks
                                    item_to_swap = player.backpack
                                    player.backpack = dragged_item
                                    # Place old backpack back where the new one came from
                                    if type_orig == 'inventory':
                                        player.inventory.insert(i_orig, item_to_swap)
                                    elif type_orig == 'belt':
                                        player.belt[i_orig] = item_to_swap
                                dropped_successfully = True
                            else:
                                print("Only backpacks can be equipped here.")


                        inv_area_rect = pygame.Rect(VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH, 0, INVENTORY_PANEL_WIDTH, VIRTUAL_GAME_HEIGHT)
                        if not dropped_successfully and inv_area_rect.collidepoint(mouse_pos):
                            target_index = -1
                            for i in range(len(player.inventory) + 1):
                                if get_inventory_slot_rect(i).collidepoint(mouse_pos): target_index = i; break
                            if target_index == -1: target_index = len(player.inventory)
                            player.inventory.insert(target_index, dragged_item)
                            player.inventory = [item for item in player.inventory if item is not None]
                            dropped_successfully = True

                        if not dropped_successfully:
                            # Check if dropped in the game world area
                            game_world_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
                            if game_world_rect.collidepoint(mouse_pos):
                                # Drop item on the floor
                                dragged_item.rect.x = player.rect.centerx
                                dragged_item.rect.y = player.rect.centery + TILE_SIZE
                                items_on_ground.append(dragged_item)
                                print(f"Dropped {dragged_item.name} by dragging.")
                            else: # Snap back to original position if not dropped in a valid area
                                if type_orig == 'inventory':
                                    player.inventory.insert(i_orig, dragged_item)
                                elif type_orig == 'belt':
                                    player.belt[i_orig] = dragged_item
                                elif type_orig == 'backpack':
                                    player.backpack = dragged_item

                        player.inventory = [item for item in player.inventory if item is not None]
                        player.inventory_slots = player.get_total_inventory_slots() # Recalculate slots

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
                        handle_zombie_death(player, hit_zombie, items_on_ground)
                        zombies_killed += 1
                    projectiles_to_remove.append(p)
            projectiles = [p for p in projectiles if p not in projectiles_to_remove]
            zombies = [z for z in zombies if z not in zombies_to_remove]

            for zombie in zombies:
                zombie.move_towards(player.rect, obstacles, zombies)
                if player.rect.colliderect(zombie.rect) and time.time() % 1 < 0.1:
                    zombie.attack(player)
            
            if random.random() < 0.005 and len(zombies) < 10:
                zombies.append(Zombie.create_random(random.choice([0, GAME_WIDTH]), random.choice([0, GAME_HEIGHT])))

            # --- Drawing ---
            VIRTUAL_SCREEN.fill(PANEL_COLOR) 
            game_rect = pygame.Rect(GAME_OFFSET_X, 0, GAME_WIDTH, GAME_HEIGHT)
            VIRTUAL_SCREEN.fill(GAME_BG_COLOR, game_rect)

            for obstacle in obstacles:
                draw_rect = obstacle.move(GAME_OFFSET_X, 0)
                pygame.draw.rect(VIRTUAL_SCREEN, DARK_GRAY, draw_rect)

            for item in items_on_ground:
                draw_rect = item.rect.move(GAME_OFFSET_X, 0)
                if item.image:
                    VIRTUAL_SCREEN.blit(item.image, draw_rect)
                else: # Fallback to drawing a colored square
                    pygame.draw.rect(VIRTUAL_SCREEN, item.color, draw_rect)
            
            for zombie in zombies: zombie.draw(VIRTUAL_SCREEN)
            player.draw(VIRTUAL_SCREEN)
            
            if player.gun_flash_timer > 0:
                center_x = player.rect.centerx + GAME_OFFSET_X
                center_y = player.rect.centery
                pygame.draw.circle(VIRTUAL_SCREEN, YELLOW, (center_x, center_y), TILE_SIZE // 4)
                player.gun_flash_timer -= 1

            drag_pos = (mouse_pos[0] - drag_offset[0], mouse_pos[1] - drag_offset[1]) if is_dragging else (0, 0)
            draw_inventory(VIRTUAL_SCREEN, player, dragged_item, drag_pos)
            
            # Draw container view if inspecting an item
            if inspecting_item:
                draw_container_view(VIRTUAL_SCREEN, inspecting_item if isinstance(inspecting_item, Item) else player.backpack)

            for p in projectiles: p.draw(VIRTUAL_SCREEN)
            
            kill_counter_text = font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
            VIRTUAL_SCREEN.blit(kill_counter_text, (GAME_OFFSET_X + 10, 30))

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
