import pygame
from config import *

def get_inventory_slot_rect(i):
    """Calculates the screen rect for an inventory slot."""
    inv_start_x = VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH
    slot_y = 60 + i * 70
    return pygame.Rect(inv_start_x + 5, slot_y, 200, 65)

def get_belt_slot_rect(i):
    """Calculates the screen rect for a belt slot."""
    belt_start_x = GAME_OFFSET_X + GAME_WIDTH // 2 - (5 * 60) // 2
    x = belt_start_x + i * 70
    y = GAME_HEIGHT - 50
    return pygame.Rect(x, y, 60, 40)

def get_backpack_slot_rect():
    """Calculates the screen rect for the backpack slot."""
    inv_start_x = VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH
    slot_y = GAME_HEIGHT - 60 # Position it at the bottom of the inventory panel
    return pygame.Rect(inv_start_x + 5, slot_y, 200, 50)

def get_container_slot_rect(container_pos, i):
    """Calculates the screen rect for a slot inside a container modal."""
    rows, cols = 4, 4
    slot_size = 60
    padding = 10
    start_x = container_pos[0] + padding
    start_y = container_pos[1] + 40
    row = i // cols
    col = i % cols
    return pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)

def draw_inventory(surface, player, dragged_item, drag_pos):
    """Draws all UI panels (Inventory, Belt)."""
    
    # 1. Draw INVENTORY Panel (Right Column)
    inv_start_x = VIRTUAL_SCREEN_WIDTH - INVENTORY_PANEL_WIDTH
    inv_rect = pygame.Rect(inv_start_x, 0, INVENTORY_PANEL_WIDTH, GAME_HEIGHT)
    pygame.draw.rect(surface, PANEL_COLOR, inv_rect)
    surface.blit(font.render("INVENTORY", True, WHITE), (inv_start_x + 10, 15))

    # Draw Inventory Slots
    for i in range(player.base_inventory_slots):
        slot_rect = get_inventory_slot_rect(i)
        
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = slot_rect.collidepoint(mouse_pos) and not dragged_item
        
        slot_color = (60, 60, 60) if is_hovered else (40, 40, 40)
        pygame.draw.rect(surface, slot_color, slot_rect, 0, 3)

        # Check if there is an item for this slot
        item = None
        if i < len(player.inventory):
            item = player.inventory[i]

        if item: # If an item exists, draw it
            pygame.draw.rect(surface, item.color, slot_rect, 2, 3)

            if item.image:
                # Scale sprite to fit slot height while maintaining aspect ratio
                img_h = slot_rect.height - 10
                img_w = int(item.image.get_width() * (img_h / item.image.get_height()))
                scaled_sprite = pygame.transform.scale(item.image, (img_w, img_h))
                sprite_rect = scaled_sprite.get_rect(centery=slot_rect.centery, left=slot_rect.left + 5)
                surface.blit(scaled_sprite, sprite_rect)
                text_x_offset = sprite_rect.right + 10
            else: # Fallback for items without sprites
                text_x_offset = slot_rect.left + 10

            item_name_text = font.render(f"{item.name.split('(')[0]}", True, item.color)
            surface.blit(item_name_text, (text_x_offset, slot_rect.top + 5))
            
            # Display secondary info (stack/durability)
            info_text = None
            if item.load is not None and item.capacity is not None and item.item_type == 'consumable':
                info_text = font.render(f"Stack: {item.load:.0f}/{item.capacity:.0f}", True, WHITE)
            elif item.durability is not None:
                info_text = font.render(f"Dur: {item.durability:.0f}%", True, WHITE)
            elif item.item_type == 'weapon' and item.load is not None:
                 info_text = font.render(f"Ammo: {item.load:.0f}/{item.capacity:.0f}", True, WHITE)

            if info_text:
                surface.blit(info_text, (text_x_offset, slot_rect.top + 25))
        else: # If no item, draw an empty slot
            pygame.draw.rect(surface, GRAY, slot_rect, 1, 3)

    # Draw Backpack Slot
    backpack_slot_rect = get_backpack_slot_rect()
    is_hovered = backpack_slot_rect.collidepoint(mouse_pos) and not dragged_item
    slot_color = (60, 60, 60) if is_hovered else (40, 40, 40)
    pygame.draw.rect(surface, slot_color, backpack_slot_rect, 0, 3)
    surface.blit(font.render("Backpack", True, WHITE), (backpack_slot_rect.x + 5, backpack_slot_rect.y - 20))

    backpack = player.backpack
    if backpack:
        pygame.draw.rect(surface, backpack.color, backpack_slot_rect, 2, 3)
        if backpack.image:
            img_h = backpack_slot_rect.height - 10
            img_w = int(backpack.image.get_width() * (img_h / backpack.image.get_height()))
            scaled_sprite = pygame.transform.scale(backpack.image, (img_w, img_h))
            sprite_rect = scaled_sprite.get_rect(centery=backpack_slot_rect.centery, left=backpack_slot_rect.left + 5)
            surface.blit(scaled_sprite, sprite_rect)
            text_x_offset = sprite_rect.right + 10
        else:
            text_x_offset = backpack_slot_rect.left + 10

        item_name_text = font.render(f"{backpack.name}", True, backpack.color)
        surface.blit(item_name_text, (text_x_offset, backpack_slot_rect.top + 5))

        info_text = font.render(f"Slots: +{backpack.capacity or 0}", True, WHITE)
        surface.blit(info_text, (text_x_offset, backpack_slot_rect.top + 25))
    else:
        pygame.draw.rect(surface, GRAY, backpack_slot_rect, 1, 3)





    # 3. Draw BELT (Quick Slots 1-5, Centered in Game Box)
    for i in range(5):
        item = player.belt[i]
        slot_rect = get_belt_slot_rect(i)
        
        pygame.draw.rect(surface, DARK_GRAY, slot_rect, 0, 5)
        pygame.draw.rect(surface, WHITE, slot_rect, 2, 5)
        surface.blit(font.render(str(i + 1), True, WHITE), (slot_rect.x + 5, slot_rect.y - 20))
        
        if item and item.image:
            # Scale sprite to fit slot and blit it
            img_h = slot_rect.height - 4
            img_w = int(item.image.get_width() * (img_h / item.image.get_height()))
            scaled_sprite = pygame.transform.scale(item.image, (img_w, img_h))
            sprite_rect = scaled_sprite.get_rect(center=slot_rect.center)
            surface.blit(scaled_sprite, sprite_rect)

    # 4. Draw DRAGGED ITEM (On Top)
    if dragged_item:
        drag_rect = (drag_pos[0], drag_pos[1], 100, 60)
        pygame.draw.rect(surface, (50, 50, 50, 150), drag_rect, 0, 5)
        pygame.draw.rect(surface, dragged_item.color, drag_rect, 2, 5)
        
        name_text = font.render(dragged_item.name.split('(')[0], True, dragged_item.color)
        surface.blit(name_text, (drag_pos[0] + 5, drag_pos[1] + 5))
        
        if dragged_item.load is not None:
             load_text = font.render(f"Load: {dragged_item.load:.0f}", True, WHITE)
             surface.blit(load_text, (drag_pos[0] + 5, drag_pos[1] + 25))

def draw_menu(screen):
    """Draws the main menu."""
    screen.fill(GAME_BG_COLOR)
    
    title_text = title_font.render("Bit Rot", True, RED)
    title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
    screen.blit(title_text, title_rect)

    start_text = large_font.render("START", True, WHITE)
    start_rect = start_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2))
    
    quit_text = large_font.render("QUIT", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 60))

    # Highlight on hover
    mouse_pos = pygame.mouse.get_pos()
    # We need to scale mouse_pos for menu interaction if the screen is resized
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)

    if start_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, start_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))

    screen.blit(start_text, start_rect)
    screen.blit(quit_text, quit_rect)
    
    return start_rect, quit_rect

def draw_game_over(screen, zombies_killed):
    """Draws the game over screen."""
    screen.fill(GAME_BG_COLOR)
    
    title_text = title_font.render("YOU DIED", True, RED)
    title_rect = title_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 4))
    screen.blit(title_text, title_rect)

    score_text = large_font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    score_rect = score_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 - 60))
    screen.blit(score_text, score_rect)

    restart_text = large_font.render("Restart", True, WHITE)
    restart_rect = restart_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 20))
    
    quit_text = large_font.render("Quit", True, WHITE)
    quit_rect = quit_text.get_rect(center=(VIRTUAL_SCREEN_WIDTH // 2, VIRTUAL_GAME_HEIGHT // 2 + 80))

    # Highlight on hover
    mouse_pos = pygame.mouse.get_pos()
    scale_x = VIRTUAL_SCREEN_WIDTH / screen.get_width()
    scale_y = VIRTUAL_GAME_HEIGHT / screen.get_height()
    scaled_mouse_pos = (mouse_pos[0] * scale_x, mouse_pos[1] * scale_y)

    if restart_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, restart_rect.inflate(20, 10))
    if quit_rect.collidepoint(scaled_mouse_pos):
        pygame.draw.rect(screen, GRAY, quit_rect.inflate(20, 10))

    screen.blit(restart_text, restart_rect)
    screen.blit(quit_text, quit_rect)
    
    return restart_rect, quit_rect

def draw_container_view(surface, container_item, position):
    """Draws a modal view for a container's inventory (e.g., a backpack)."""
    if not container_item or not hasattr(container_item, 'inventory'):
        return

    # Modal background
    modal_w, modal_h = 300, 300
    modal_x, modal_y = position
    modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
    
    # Semi-transparent background
    s = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    s.fill((20, 20, 20, 200))
    surface.blit(s, (modal_x, modal_y))
    pygame.draw.rect(surface, WHITE, modal_rect, 1, 4)

    # --- Draggable Header ---
    header_h = 35
    header_rect = pygame.Rect(modal_x, modal_y, modal_w, header_h)
    pygame.draw.rect(surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)

    # Title
    title_text = font.render(f"{container_item.name} Contents", True, WHITE)
    surface.blit(title_text, (modal_x + 10, modal_y + 10))

    # Close instruction
    close_text = font.render("ESC to close", True, GRAY)
    surface.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))

    # Draw item slots
    rows, cols = 4, 4 # Example layout
    slot_size = 60
    padding = 10
    start_x = modal_x + padding
    start_y = modal_y + 40

    # Calculate how many rows can fit in the modal
    # modal_h - (header_h + padding_bottom) / (slot_size + padding)
    max_visible_rows = int((modal_h - header_h - padding) / (slot_size + padding))
    max_visible_slots = max_visible_rows * cols

    for i in range(min(container_item.capacity, max_visible_slots)):
        row = i // cols
        col = i % cols
        slot_rect = pygame.Rect(start_x + col * (slot_size + padding), start_y + row * (slot_size + padding), slot_size, slot_size)
        pygame.draw.rect(surface, (40, 40, 40), slot_rect, 1, 3)
        if i < len(container_item.inventory):
            item = container_item.inventory[i]
            if item.image:
                surface.blit(pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8)), slot_rect.move(4, 4))
            else:
                pygame.draw.rect(surface, item.color, slot_rect.inflate(-8, -8))

    # Add a "More items..." indicator if there are more items than visible slots
    if container_item.capacity > max_visible_slots:
        more_text = font.render(f"... {container_item.capacity - max_visible_slots} more items ...", True, GRAY)
        surface.blit(more_text, (modal_x + padding, modal_y + modal_h - padding - more_text.get_height()))

# --- New UI Functions for Status Modal ---
status_button_image = None
def draw_status_button(surface):
    global status_button_image
    if status_button_image is None:
        try:
            status_button_image = pygame.image.load('game/ui/status.png').convert_alpha()
            status_button_image = pygame.transform.scale(status_button_image, (40, 40))
        except pygame.error as e:
            print(f"Warning: Could not load status button image: {e}")
            status_button_image = pygame.Surface((40, 40), pygame.SRCALPHA)
            status_button_image.fill(GRAY) # Fallback

    button_rect = pygame.Rect(10, 10, 40, 40) # Top-left corner
    surface.blit(status_button_image, button_rect)
    return button_rect

def draw_status_modal(surface, player, position, zombies_killed):
    modal_w, modal_h = 300, 400 # Slightly taller for more stats
    modal_x, modal_y = position
    modal_rect = pygame.Rect(modal_x, modal_y, modal_w, modal_h)
    
    s = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    s.fill((20, 20, 20, 200))
    surface.blit(s, (modal_x, modal_y))
    pygame.draw.rect(surface, WHITE, modal_rect, 1, 4)

    header_h = 35
    header_rect = pygame.Rect(modal_x, modal_y, modal_w, header_h)
    pygame.draw.rect(surface, (60, 60, 60), header_rect, 0, border_top_left_radius=4, border_top_right_radius=4)
    pygame.draw.rect(surface, WHITE, header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)

    title_text = font.render("Player Status", True, WHITE)
    surface.blit(title_text, (modal_x + 10, modal_y + 10))

    close_text = font.render("ESC to close", True, GRAY)
    surface.blit(close_text, (modal_x + modal_w - close_text.get_width() - 10, modal_y + 10))

    # Display Player Stats
    y_offset = modal_y + header_h + 10
    x_offset = modal_x + 10

    # Health/Infection/Resource Bars
    stats = [
        ("HP", player.health, RED), 
        ("Stamina", player.stamina, GRAY),
        ("Water", player.water, BLUE), 
        ("Food", player.food, GREEN), 
        ("Infection", player.infection, YELLOW),
        ("XP", player.experience, YELLOW)
    ]
    
    for i, (name, value, color) in enumerate(stats):
        y_pos = y_offset + i * 28
        text = font.render(f"{name}:", True, WHITE)
        surface.blit(text, (x_offset, y_pos))
        
        bar_width = int(100 * (value / 100))
        bar_rect = pygame.Rect(x_offset + 110, y_pos + 5, bar_width, 10)
        pygame.draw.rect(surface, color, bar_rect)
        pygame.draw.rect(surface, WHITE, (x_offset + 110, y_pos + 5, 100, 10), 1)

    # Skills Display
    skill_y = y_pos + 35 # Continue from last stat bar
    surface.blit(font.render(f"Ranged Skill: {player.skill_ranged}/10", True, WHITE), (x_offset, skill_y))
    surface.blit(font.render(f"Melee Skill: {player.skill_melee}/10", True, WHITE), (x_offset, skill_y + 20))
    
    # Display Weight
    weight_text = font.render(f"Weight: {player.get_inventory_weight():.1f}/{player.max_carry_weight:.1f}", True, WHITE)
    surface.blit(weight_text, (x_offset, skill_y + 50))

    # Display Zombies Killed
    zombies_killed_text = font.render(f"Zombies Killed: {zombies_killed}", True, WHITE)
    surface.blit(zombies_killed_text, (x_offset, skill_y + 80))

    # Equipped Weapon
    active_weapon_text = "None (Hands)"
    if player.active_weapon:
         active_weapon_text = f"Equipped: {player.active_weapon.name.split('(')[0]}"
         if player.active_weapon.durability is not None:
            active_weapon_text += f" | Dur: {player.active_weapon.durability:.0f}%"
         if player.active_weapon.item_type == 'weapon' and player.active_weapon.load is not None:
            active_weapon_text += f" | Ammo: {player.active_weapon.load:.0f}/{player.active_weapon.capacity:.0f}"
            
    status_text = font.render(active_weapon_text, True, YELLOW)
    surface.blit(status_text, (x_offset, skill_y + 110))
