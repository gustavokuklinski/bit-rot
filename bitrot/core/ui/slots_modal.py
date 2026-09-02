import pygame
import math
from core.data.config import *
from core.ui.modals import BaseModal, draw_scrollbar
from core.ui.container_modal import _draw_slots
from core.ui.tooltip import draw_tooltip
from core.data.localization import tr

def draw_slots_modal(surface, game, player, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, "Slots Overview")
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    # --- 1. Gather All Containers ---
    containers = []
    
    def get_safe_capacity(obj):
        cap = getattr(obj, 'capacity', 0)
        return cap if cap is not None else 0

    # ONLY allow explicitly defined containers and clothes
    valid_types = ['container', 'cloth']

    if hasattr(player, 'clothes') and player.clothes:
        for slot_name, item in player.clothes.items():
            if item and getattr(item, 'item_type', '') in valid_types and get_safe_capacity(item) > 0:
                bc = f"Gear > {str(slot_name).capitalize()} > {tr('item', getattr(item, 'name', 'Unknown'))}"
                containers.append((item, bc))
                
    if hasattr(player, 'belt') and player.belt:
        for i, item in enumerate(player.belt):
            if item and getattr(item, 'item_type', '') in valid_types and get_safe_capacity(item) > 0:
                bc = f"Belt > Slot {i+1} > {tr('item', getattr(item, 'name', 'Unknown'))}"
                containers.append((item, bc))
                
    if hasattr(player, 'inventory') and player.inventory:
        for item in player.inventory:
            if item and getattr(item, 'item_type', '') in valid_types and get_safe_capacity(item) > 0:
                bc = f"Inventory > {tr('item', getattr(item, 'name', 'Unknown'))}"
                containers.append((item, bc))

    # --- 2. Set Dimensions & Spacing ---
    padding = 10
    start_x = base_modal.modal_x + padding
    content_y = base_modal.modal_y + 40
    view_h = base_modal.modal_h - 40 - padding

    slot_size = 40
    gap = 6
    header_height = 30
    
    total_height = 0
    for c, _ in containers:
        cap = get_safe_capacity(c)
        rows = math.ceil(cap / 5.0)
        total_height += header_height + (rows * (slot_size + gap)) + 15

    # --- 3. Scrollbar Hooked to Engine ---
    max_scroll = max(0, total_height - view_h)
    modal['max_scroll_offset'] = max_scroll
    
    if 'scroll_offset_y' not in modal:
        modal['scroll_offset_y'] = 0

    mouse_pressed = pygame.mouse.get_pressed()[0]

    if max_scroll > 0:
        if not mouse_pressed:
            modal['is_dragging_scrollbar'] = False

        if modal.get('is_dragging_scrollbar'):
            # Process the math while mouse.py holds the drag flag active
            handle_h = max(20, int((view_h / total_height) * view_h))
            rel_y = mouse_pos[1] - content_y - (handle_h / 2)
            pct = max(0.0, min(1.0, rel_y / (view_h - handle_h)))
            modal['scroll_offset_y'] = pct * max_scroll
            
    modal['scroll_offset_y'] = max(0, min(modal['scroll_offset_y'], max_scroll))

    # --- 4. Render Content with Hardware Clipping ---
    old_clip = surface.get_clip()
    clip_rect = pygame.Rect(base_modal.modal_x, content_y, base_modal.modal_w - (20 if max_scroll > 0 else 0), view_h)
    final_clip = old_clip.clip(clip_rect)
    surface.set_clip(final_clip)

    current_y = content_y - modal['scroll_offset_y']
    
    # --- 5. Cache Slots for Drag & Drop ---
    modal['slot_rects'] = []
    modal['header_rects'] = []

    for c, breadcrumb in containers:
        cap = get_safe_capacity(c)
        rows = math.ceil(cap / 5.0)
        container_h = header_height + (rows * (slot_size + gap)) + 15
        
        if current_y > content_y + view_h: break
        if current_y + container_h < content_y:
            current_y += container_h
            continue
            
        icon_rect = pygame.Rect(start_x, current_y, 24, 24)
        if hasattr(c, 'image') and c.image:
            surface.blit(pygame.transform.scale(c.image, (24, 24)), icon_rect)
        else:
            pygame.draw.rect(surface, getattr(c, 'color', WHITE), icon_rect)
            
        name_text = tr('item', c.name) if hasattr(c, 'name') else "Unknown"
        text_surf = font_12.render(name_text, False, WHITE)
        surface.blit(text_surf, (start_x + 30, current_y + 4))
        
        # Cache the header rect for the breadcrumb tooltip
        header_w = 30 + text_surf.get_width()
        header_rect = pygame.Rect(start_x, current_y, header_w, 24)
        if clip_rect.colliderect(header_rect):
            modal['header_rects'].append({'rect': header_rect, 'breadcrumb': breadcrumb})
        
        _draw_slots(surface, game, c, start_x, current_y + header_height, 10000, 0, mouse_pos)
        
        # Calculate exactly where slots rendered and store them
        start_y_slots = current_y + header_height
        for i in range(cap):
            row = i // 5
            col = i % 5
            slot_rect = pygame.Rect(start_x + col * (slot_size + gap), start_y_slots + row * (slot_size + gap), slot_size, slot_size)
            if clip_rect.colliderect(slot_rect):
                modal['slot_rects'].append({'rect': slot_rect, 'container': c, 'index': i})
        
        current_y += container_h

    surface.set_clip(old_clip)

    # --- CHANGED: Use Standardized Scrollbar ---
    bar_rect = pygame.Rect(base_modal.modal_x + base_modal.modal_w - 10, content_y, 8, view_h)
    draw_scrollbar(surface, modal, bar_rect, view_h, total_height, modal['scroll_offset_y'])

    # --- 6. Draw Tooltips and Breadcrumbs ---
    hovered_header = None
    for header_data in modal.get('header_rects', []):
        if header_data['rect'].collidepoint(mouse_pos):
            hovered_header = header_data
            break

    if hovered_header and not getattr(game, 'is_dragging', False) and not modal.get('is_dragging_scrollbar') and not modal.get('is_dragging', False):
        # Draw Breadcrumb Tooltip on Container Header
        bc_text = hovered_header['breadcrumb']
        bc_surf = font_12.render(bc_text, False, YELLOW)
        bc_rect = bc_surf.get_rect(midbottom=(mouse_pos[0], mouse_pos[1] - 15))
        
        if bc_rect.left < 0: bc_rect.left = 5
        if bc_rect.right > GAME_WIDTH: bc_rect.right = GAME_WIDTH - 5
        
        bg_rect = bc_rect.inflate(10, 6)
        s = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        surface.blit(s, bg_rect.topleft)
        pygame.draw.rect(surface, WHITE, bg_rect, 1)
        surface.blit(bc_surf, bc_rect)

    hovered_slot = None
    for slot_data in modal.get('slot_rects', []):
        if slot_data['rect'].collidepoint(mouse_pos):
            hovered_slot = slot_data
            break

    if hovered_slot and not getattr(game, 'is_dragging', False) and not modal.get('is_dragging_scrollbar') and not modal.get('is_dragging', False):
        # Draw Item Tooltip for contents
        c = hovered_slot['container']
        idx = hovered_slot['index']
        if idx < len(c.inventory):
            item = c.inventory[idx]
            draw_tooltip(surface, item, (mouse_pos[0] + 15, mouse_pos[1] + 15))

    buttons = [close_button]
    return buttons