import pygame
import os
import json
import xml.etree.ElementTree as ET
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item import Item
from core.data.localization import tr
from core.entities.npc.npc_dialog import NPCDialog 
from core.ui.modals import draw_scrollbar

_QUESTS_CACHE = None

def load_quests():
    global _QUESTS_CACHE
    if _QUESTS_CACHE is not None:
        return _QUESTS_CACHE
        
    _QUESTS_CACHE = []
   

    # 1. Load Standard Handcrafted Quests from XML
    dialogs_path = os.path.join(DATA_PATH, 'npc/dialogs.xml')
    if os.path.exists(dialogs_path):
        try:
            tree = ET.parse(dialogs_path)
            root = tree.getroot()
            for node in root.iter('node'):
                node_id = node.get('id', '')
                if node_id.lower().startswith('quest:'):
                    quest_name = node_id[6:].strip() 
                    raw_item_str = None
                    tip = "No tip provided"
                    complete_flag = quest_name
                    
                    for options in node.findall('options') + node.findall('option'):
                        if options.get('rqst_item'): raw_item_str = options.get('rqst_item')
                        elif not raw_item_str and options.get('award_item'): raw_item_str = options.get('award_item')
                        if options.get('tip'): tip = options.get('tip')
                        if options.get('complete_flag'): complete_flag = options.get('complete_flag').strip()
                        
                    rqst_item = None
                    if raw_item_str:
                        cleaned_str = raw_item_str.replace('[', '').replace(']', '')
                        rqst_item = cleaned_str.split(',')[0].strip()
                        
                    item = Item.create_from_name(rqst_item) if rqst_item else None
                        
                    _QUESTS_CACHE.append({
                        'node_id': node_id,  
                        'name': quest_name,
                        'rqst_item_name': rqst_item,
                        'item_obj': item,
                        'tip': tip,
                        'complete_flag': complete_flag,
                        'is_procedural': False 
                    })
        except Exception as e:
            print(f"Error loading quests from dialogs.xml: {e}")

    # 2. Load Procedural Quests directly from the dynamic quests.rot
    quests_rot_path = NPCDialog.QUESTS_FILE_PATH
    
    if quests_rot_path and os.path.exists(quests_rot_path):
        try:
            with open(quests_rot_path, 'r') as f:
                proc_data = json.load(f)
                
            for node_id, options in proc_data.get("nodes", {}).items():
                if not any(q['node_id'] == node_id for q in _QUESTS_CACHE):
                    quest_name = node_id[6:].strip().replace("_", " ") 
                    
                    raw_item_str = None
                    tip = "Bring the requested supplies to a survivor."
                    complete_flag = node_id
                    
                    for opt in options:
                        if opt.get('rqst_item'): raw_item_str = opt.get('rqst_item')
                        elif not raw_item_str and opt.get('award_item'): raw_item_str = opt.get('award_item')
                    
                    rqst_item = None
                    if raw_item_str:
                        cleaned_str = raw_item_str.replace('[', '').replace(']', '')
                        rqst_item = cleaned_str.split(',')[0].strip()
                    
                    item = Item.create_from_name(rqst_item) if rqst_item else None
                    
                    _QUESTS_CACHE.append({
                        'node_id': node_id,
                        'name': quest_name,
                        'rqst_item_name': rqst_item,
                        'item_obj': item,
                        'tip': tip,
                        'complete_flag': complete_flag,
                        'is_procedural': True 
                    })
        except Exception as e:
            print(f"Error loading quests from {quests_rot_path}: {e}")

    return _QUESTS_CACHE


def draw_quests_tab(surface, player, modal, assets, mouse_pos):
    modal_rect = modal['rect']
    quests = load_quests()
    
    completed_list = getattr(player, 'completed_quests', [])
    active_list = getattr(player, 'quests', [])
    
    in_progress, next_petrol_locked, island_locked, completed_quests = [], [], [], []
    np_total = np_comp = isl_total = isl_comp = 0

    for q in quests:
        is_completed = (q['complete_flag'] in completed_list) or (q['node_id'] in completed_list)
        is_open = ((q['node_id'] in active_list) or (q['name'] in active_list)) and not is_completed
        
        if q['is_procedural']:
            isl_total += 1
            if is_completed: isl_comp += 1
        else:
            np_total += 1
            if is_completed: np_comp += 1
            
        if is_completed: completed_quests.append(q)
        elif is_open: in_progress.append(q)
        elif q['is_procedural']: island_locked.append(q)
        else: next_petrol_locked.append(q)

    total_global, comp_global, in_prog_count = len(quests), len(completed_quests), len(in_progress)

    start_x = modal_rect.left + 15
    base_y = modal_rect.top + 70 
    slot_size = 40
    gap = 10
    cols = 4 # Changed from 7 to 4 to fit 244px width
    
    def get_section_height(items):
        if not items: return 0
        rows = (len(items) + cols - 1) // cols
        return 30 + (rows * (slot_size + gap)) + 10

    total_content_height = (
        get_section_height(in_progress) + get_section_height(next_petrol_locked) +
        get_section_height(island_locked) + get_section_height(completed_quests)
    )
    
    visible_height = modal_rect.height - 80 
    max_scroll = max(0, total_content_height - visible_height)
    
    if 'quest_scroll_y' not in modal: modal['quest_scroll_y'] = 0.0
    if 'quest_is_dragging' not in modal: modal['quest_is_dragging'] = False
    if 'quest_is_scrolling_content' not in modal: modal['quest_is_scrolling_content'] = False
    if 'quest_content_last_y' not in modal: modal['quest_content_last_y'] = 0

    scroll_dy = modal.get('scroll_dy', 0)
    if scroll_dy != 0 and modal_rect.collidepoint(mouse_pos):
        modal['quest_scroll_y'] -= scroll_dy * 35
        modal['scroll_dy'] = 0 

    mouse_pressed = pygame.mouse.get_pressed()[0]
    scrollbar_x = modal_rect.right - 15
    scrollbar_w = 8
    
    handle_h = max(30, int((visible_height / max(1, total_content_height)) * visible_height))
    if total_content_height <= visible_height: handle_h = visible_height
    
    scroll_ratio = modal['quest_scroll_y'] / max(1, max_scroll)
    handle_y = base_y + (scroll_ratio * (visible_height - handle_h))
    handle_rect = pygame.Rect(scrollbar_x, handle_y, scrollbar_w, handle_h)
    track_rect = pygame.Rect(scrollbar_x, base_y, scrollbar_w, visible_height)
    
    clip_rect = pygame.Rect(modal_rect.left + 5, base_y, modal_rect.width - 25, visible_height)
    
    if mouse_pressed:
        if not modal.get('quest_was_pressed', False):
            if handle_rect.inflate(20, 0).collidepoint(mouse_pos):
                modal['quest_is_dragging'] = True
                modal['quest_drag_offset'] = mouse_pos[1] - handle_y
            elif track_rect.collidepoint(mouse_pos):
                new_y = mouse_pos[1] - (handle_h / 2)
                percent = max(0, min(1, (new_y - base_y) / (visible_height - handle_h)))
                modal['quest_scroll_y'] = percent * max_scroll
            elif clip_rect.collidepoint(mouse_pos) and max_scroll > 0:
                modal['quest_is_scrolling_content'] = True
                modal['quest_content_last_y'] = mouse_pos[1]
                
        if modal['quest_is_dragging']:
            new_y = mouse_pos[1] - modal.get('quest_drag_offset', 0)
            percent = max(0, min(1, (new_y - base_y) / (visible_height - handle_h)))
            modal['quest_scroll_y'] = percent * max_scroll
        elif modal.get('quest_is_scrolling_content'):
            delta_y = mouse_pos[1] - modal['quest_content_last_y']
            modal['quest_scroll_y'] -= delta_y
            modal['quest_content_last_y'] = mouse_pos[1]
    else: 
        modal['quest_is_dragging'] = False
        modal['quest_is_scrolling_content'] = False
        
    modal['quest_was_pressed'] = mouse_pressed
    modal['quest_scroll_y'] = max(0, min(modal['quest_scroll_y'], max_scroll))
    current_scroll = modal['quest_scroll_y']

    surface.set_clip(clip_rect)
    
    current_y = base_y - current_scroll
    pending_tooltip = None

    def draw_quest_section(title, items, y_offset, outline_color):
        if not items: return y_offset
        title_surf = font_14.render(title, False, WHITE)
        surface.blit(title_surf, (start_x, y_offset))
        y_offset += 25
        nonlocal pending_tooltip
        for i, q in enumerate(items):
            row = i // cols
            col = i % cols
            x = start_x + col * (slot_size + gap)
            y = y_offset + row * (slot_size + gap)
            slot_rect = pygame.Rect(x, y, slot_size, slot_size)
            if y > base_y + visible_height or y + slot_size < base_y: continue
            pygame.draw.rect(surface, GRAY_40, slot_rect)
            item = q['item_obj']
            if item and getattr(item, 'image', None):
                img = item.image.copy()
                if outline_color == GRAY_60: img.set_alpha(100)
                scaled_img = pygame.transform.scale(img, (32, 32))
                surface.blit(scaled_img, scaled_img.get_rect(center=slot_rect.center))
            else:
                fallback_text = font_14.render("?", False, WHITE)
                if outline_color == GRAY_60: fallback_text.set_alpha(100)
                surface.blit(fallback_text, fallback_text.get_rect(center=slot_rect.center))
            pygame.draw.rect(surface, outline_color, slot_rect, 2 if outline_color != GRAY_60 else 1)
            if slot_rect.collidepoint(mouse_pos) and clip_rect.collidepoint(mouse_pos):
                if not modal.get('quest_is_scrolling_content') and not modal.get('quest_is_dragging'):
                    class QuestTooltipDummy:
                        def __init__(self, q_data):
                            self.name = tr('ui', q_data['name'])
                            status = 'Completed' if outline_color == GREEN else ('In Progress' if outline_color == YELLOW else 'Locked')
                            self.tooltip_text = f"{tr('ui', 'Status:')} {tr('ui', status)}\n{tr('ui', q_data['tip'])}"
                            self.item_type = self.durability = self.max_durability = None
                            self.load = self.capacity = self.min_damage = self.max_damage = self.ammo_type = self.defence = None
                    pending_tooltip = QuestTooltipDummy(q)
        rows = (len(items) + cols - 1) // cols
        return y_offset + (rows * (slot_size + gap)) + 15
        
    current_y = draw_quest_section(f"In Progress ({in_prog_count})", in_progress, current_y, YELLOW)
    current_y = draw_quest_section(f"Next Petrol ({np_comp}/{np_total})", next_petrol_locked, current_y, GRAY_60)
    current_y = draw_quest_section(f"Island Quest ({isl_comp}/{isl_total})", island_locked, current_y, GRAY_60)
    current_y = draw_quest_section(f"Completed ({comp_global}/{total_global})", completed_quests, current_y, GREEN)

    surface.set_clip(None)
    bar_rect = pygame.Rect(modal_rect.right - 10, base_y, 8, visible_height)
    draw_scrollbar(surface, modal, bar_rect, visible_height, total_content_height, current_scroll)

    if pending_tooltip:
        draw_tooltip(surface, pending_tooltip, (mouse_pos[0] + 15, mouse_pos[1] + 15))