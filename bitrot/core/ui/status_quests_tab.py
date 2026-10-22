# core/ui/status_quests_tab.py

import pygame
import os
import xml.etree.ElementTree as ET
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item import Item
from core.data.localization import tr
from core.entities.npc.npc_dialog import NPCDialog 
from core.ui.modals import draw_scrollbar
from core.data.recipe_manager import RecipeManager
from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data

_QUESTS_CACHE = None
_RECIPE_BOOKS_CACHE = None

def load_quests():
    global _QUESTS_CACHE
    if _QUESTS_CACHE is not None:
        return _QUESTS_CACHE
        
    _QUESTS_CACHE = []

    # Load Standard Handcrafted Quests from XML
    dialogs_dir = os.path.join(DATA_PATH, 'npc_dialogs')
    if os.path.exists(dialogs_dir):
        for filename in os.listdir(dialogs_dir):
            if filename.endswith('.xml'):
                filepath = os.path.join(dialogs_dir, filename)
                try:
                    tree = ET.parse(filepath)
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
                                'complete_flag': complete_flag
                            })
                except Exception as e:
                    print(f"Error loading quests from {filename}: {e}")

    return _QUESTS_CACHE


def load_recipe_books():
    """Discovers and caches all recipe book items and the crafts they teach."""
    global _RECIPE_BOOKS_CACHE
    if _RECIPE_BOOKS_CACHE is not None:
        return _RECIPE_BOOKS_CACHE

    if not ITEM_TEMPLATES:
        load_item_templates_data()
    if not RecipeManager.RECIPES:
        RecipeManager.load_recipes()

    books_dict = {}

    # 1. Gather all recipe items defined with type="recipe" from ITEM_TEMPLATES
    for name, tmpl in ITEM_TEMPLATES.items():
        if tmpl.get('type') == 'recipe' or name.lower().startswith('recipe'):
            books_dict[name] = {
                'name': name,
                'item_obj': Item.create_from_name(name, spawn_loot=False),
                'recipes': []
            }

    # 2. Gather magazines referenced in RecipeManager.RECIPES
    for r in RecipeManager.RECIPES:
        mag = getattr(r, 'magazine', None)
        if mag:
            if mag not in books_dict:
                books_dict[mag] = {
                    'name': mag,
                    'item_obj': Item.create_from_name(mag, spawn_loot=False),
                    'recipes': []
                }
            if r not in books_dict[mag]['recipes']:
                books_dict[mag]['recipes'].append(r)

    # 3. Associate recipes for any items found from step 1
    for mag, b_data in books_dict.items():
        if not b_data['recipes']:
            b_data['recipes'] = [
                r for r in RecipeManager.RECIPES
                if r.magazine and (r.magazine == mag or r.magazine.lower() == mag.lower())
            ]

    _RECIPE_BOOKS_CACHE = sorted(list(books_dict.values()), key=lambda b: b['name'])
    return _RECIPE_BOOKS_CACHE


class RecipeBookTooltipDummy:
    """Tooltip proxy showing book name, read status, and what crafting recipes it teaches."""
    def __init__(self, book_data):
        self.name = tr('item', book_data['name'])
        is_read = book_data.get('is_read', False)
        status_text = tr('ui', 'Read') if is_read else tr('ui', 'Unread')
        status_color = GREEN if is_read else (180, 180, 180)

        self.tooltip_lines = [
            [(f"{tr('ui', 'Status')}: ", WHITE), (status_text, status_color)],
            ""
        ]

        recipes = book_data.get('recipes', [])
        if recipes:
            self.tooltip_lines.append([(f"{tr('tooltip', 'Teaches')}:", YELLOW)])
            for r in recipes:
                c_type = getattr(r, 'craft_type', 'create').lower()
                out_name = tr('item', r.output_name)
                amt = getattr(r, 'output_amount', 1)
                if amt > 1:
                    out_name = f"{out_name} x{amt}"

                if c_type == 'repair':
                    self.tooltip_lines.append(f" - [{tr('tab', 'Repair')}] {out_name}")
                elif c_type == 'dismantle':
                    self.tooltip_lines.append(f" - [{tr('tab', 'Dismantle')}] {out_name}")
                else:
                    self.tooltip_lines.append(f" - {out_name}")
        else:
            self.tooltip_lines.append(tr('ui', "No recipes recorded."))

        self.tooltip_text = None
        self.item_type = None
        self.durability = None
        self.max_durability = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None
        self.defence = None


class QuestTooltipDummy:
    """Tooltip proxy showing quest name, current state, and mission objective."""
    def __init__(self, q_data):
        self.name = tr('ui', q_data['name'])
        is_completed = q_data.get('is_completed', False)
        is_open = q_data.get('is_open', False)

        if is_completed:
            status = 'Completed'
            status_color = GREEN
        elif is_open:
            status = 'In Progress'
            status_color = YELLOW
        else:
            status = 'Locked'
            status_color = (180, 180, 180)

        self.tooltip_lines = [
            [(f"{tr('ui', 'Status')}: ", WHITE), (tr('ui', status), status_color)],
            ""
        ]

        tip_text = q_data.get('tip', '')
        if tip_text and tip_text != "No tip provided":
            header_label = tr('ui', 'In Progress') if is_open else (tr('ui', 'Task') if is_completed else tr('ui', 'Objective'))
            header_col = YELLOW if is_open else (GREEN if is_completed else WHITE)
            self.tooltip_lines.append([(f"{header_label}:", header_col)])
            for line in str(tip_text).split('\n'):
                self.tooltip_lines.append(f" {tr('ui', line)}")

        self.tooltip_text = None
        self.item_type = None
        self.durability = None
        self.max_durability = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None
        self.defence = None


class MilestoneTooltipDummy:
    """Tooltip proxy showing milestone title, status, and completion requirements."""
    def __init__(self, ms_data):
        self.name = tr('ui', ms_data.get('name', 'Milestone'))
        is_completed = ms_data.get('is_completed', False)
        status = 'Completed' if is_completed else 'Locked'
        status_color = GREEN if is_completed else (180, 180, 180)

        self.tooltip_lines = [
            [(f"{tr('ui', 'Status')}: ", WHITE), (tr('ui', status), status_color)],
            ""
        ]

        msg = ms_data.get('message', '')
        if msg:
            self.tooltip_lines.append(tr('ui', msg))

        target_num = ms_data.get('number', 1)
        cur_val = ms_data.get('current_val', 0)
        self.tooltip_lines.append(f"{tr('ui', 'Progress')}: {min(cur_val, target_num)}/{target_num}")

        self.tooltip_text = None
        self.item_type = None
        self.durability = None
        self.max_durability = None
        self.load = None
        self.capacity = None
        self.min_damage = None
        self.max_damage = None
        self.ammo_type = None
        self.defence = None


def draw_quests_tab(surface, player, modal, assets, mouse_pos):
    modal_rect = modal['rect']
    quests = load_quests()
    
    if NPCDialog.MILESTONES is None:
        NPCDialog.load_dialogs(getattr(player, 'game', None))
    milestones = NPCDialog.MILESTONES or []
    
    completed_list = getattr(player, 'completed_quests', [])
    active_list = getattr(player, 'quests', [])
    completed_milestones = getattr(player, 'completed_milestones', [])
    milestone_progress = getattr(player, 'milestone_progress', {})
    known_recipes = getattr(player, 'known_recipes', [])
    
    # 1. PROCESS QUESTS (All in one section; In-Progress=Yellow, Completed=Green, Locked=Gray)
    all_quests_display = []
    np_total = len(quests)
    np_comp = 0

    for q in quests:
        is_completed = (
            (q['complete_flag'] in completed_list) or 
            (q['node_id'] in completed_list) or 
            (q['name'] in completed_list) or 
            (f"Quest: {q['name']}" in completed_list)
        )
        is_open = (
            (q['node_id'] in active_list) or 
            (q['name'] in active_list) or 
            (q['complete_flag'] in active_list) or
            (f"Quest: {q['name']}" in active_list)
        ) and not is_completed
        
        if is_completed:
            np_comp += 1

        q_entry = dict(q)
        q_entry['is_completed'] = is_completed
        q_entry['is_open'] = is_open
        all_quests_display.append(q_entry)

    # Active (In Progress) and Completed quests display first, followed by locked quests
    all_quests_display.sort(key=lambda x: (not (x['is_open'] or x['is_completed']), not x['is_open'], x['name']))

    # 2. PROCESS MILESTONES (All in one section; Completed=Green, Locked=Gray)
    all_milestones_display = []
    ms_comp_count = 0

    for ms in milestones:
        ms_name = ms.get('name', '').strip()
        is_completed = ms_name in completed_milestones
        if is_completed:
            ms_comp_count += 1

        progress_key = f"{ms.get('type')}_{ms.get('entity')}"
        cur_val = milestone_progress.get(progress_key, 0)
        if ms.get('type') == 'days' and hasattr(player, 'game') and hasattr(player.game, 'world_time'):
            cur_val = max(cur_val, getattr(player.game.world_time, 'day_count', 0))

        ms_entry = dict(ms)
        ms_entry['is_milestone'] = True
        ms_entry['is_completed'] = is_completed
        ms_entry['current_val'] = cur_val
        all_milestones_display.append(ms_entry)

    # Completed milestones display first, followed by locked ones
    all_milestones_display.sort(key=lambda x: (not x['is_completed'], x.get('name', '')))

    # 3. PROCESS RECIPE BOOKS (All in one section; Read=Green, Unread=Gray)
    recipe_books = load_recipe_books()
    recipe_books_display = []
    for b in recipe_books:
        is_read = any(k == b['name'] or k.lower() == b['name'].lower() for k in known_recipes)
        recipe_books_display.append({
            'is_recipe_book': True,
            'name': b['name'],
            'item_obj': b['item_obj'],
            'recipes': b['recipes'],
            'is_read': is_read
        })

    recipe_books_display.sort(key=lambda b: (not b['is_read'], b['name']))
    read_books_count = sum(1 for b in recipe_books_display if b['is_read'])
    total_books_count = len(recipe_books_display)

    start_x = modal_rect.left + 15
    base_y = modal_rect.top + 70 
    slot_size = 40
    gap = 10
    cols = 4 
    
    def get_section_height(items):
        if not items: return 0
        rows = (len(items) + cols - 1) // cols
        return 30 + (rows * (slot_size + gap)) + 10

    # Total content height across the 3 unified sections
    total_content_height = (
        get_section_height(all_quests_display) +
        get_section_height(all_milestones_display) +
        get_section_height(recipe_books_display)
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

    def draw_quest_section(title, items, y_offset):
        if not items: return y_offset
        title_surf = font_12.render(title, False, WHITE)
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
            
            # --- 1. RECIPE BOOKS ---
            if q.get('is_recipe_book'):
                is_read = q.get('is_read', False)
                item_outline = GREEN if is_read else GRAY_60
                item = q.get('item_obj')
                if item and getattr(item, 'image', None):
                    img = item.image.copy()
                    if not is_read:
                        img.set_alpha(100)
                    scaled_img = pygame.transform.scale(img, (32, 32))
                    surface.blit(scaled_img, scaled_img.get_rect(center=slot_rect.center))
                else:
                    fallback_text = font_12.render("B", False, WHITE)
                    if not is_read:
                        fallback_text.set_alpha(100)
                    surface.blit(fallback_text, fallback_text.get_rect(center=slot_rect.center))
                pygame.draw.rect(surface, item_outline, slot_rect, 2 if is_read else 1)

            # --- 2. MILESTONES (Green if completed, Faded Gray if locked) ---
            elif q.get('is_milestone'):
                is_completed = q.get('is_completed', False)
                item_outline = GREEN if is_completed else GRAY_60
                fallback_text = font_12.render("M", False, WHITE)
                if not is_completed:
                    fallback_text.set_alpha(100)
                surface.blit(fallback_text, fallback_text.get_rect(center=slot_rect.center))
                pygame.draw.rect(surface, item_outline, slot_rect, 2 if is_completed else 1)

            # --- 3. QUESTS (Yellow=In Progress, Green=Completed, Faded Gray=Locked) ---
            else:
                is_completed = q.get('is_completed', False)
                is_open = q.get('is_open', False)

                if is_completed:
                    item_outline = GREEN
                    is_faded = False
                elif is_open:
                    item_outline = YELLOW
                    is_faded = False
                else:
                    item_outline = GRAY_60
                    is_faded = True

                item = q.get('item_obj')
                if item and getattr(item, 'image', None):
                    img = item.image.copy()
                    if is_faded:
                        img.set_alpha(100)
                    scaled_img = pygame.transform.scale(img, (32, 32))
                    surface.blit(scaled_img, scaled_img.get_rect(center=slot_rect.center))
                else:
                    fallback_text = font_12.render("?", False, WHITE)
                    if is_faded:
                        fallback_text.set_alpha(100)
                    surface.blit(fallback_text, fallback_text.get_rect(center=slot_rect.center))
                pygame.draw.rect(surface, item_outline, slot_rect, 2 if (is_completed or is_open) else 1)
            
            # --- HOVER TOOLTIPS ---
            if slot_rect.collidepoint(mouse_pos) and clip_rect.collidepoint(mouse_pos):
                if not modal.get('quest_is_scrolling_content') and not modal.get('quest_is_dragging'):
                    if q.get('is_recipe_book'):
                        pending_tooltip = RecipeBookTooltipDummy(q)
                    elif q.get('is_milestone'):
                        pending_tooltip = MilestoneTooltipDummy(q)
                    else:
                        pending_tooltip = QuestTooltipDummy(q)
                    
        rows = (len(items) + cols - 1) // cols
        return y_offset + (rows * (slot_size + gap)) + 15
        
    # Render the 3 unified sections
    current_y = draw_quest_section(f"{tr('ui', 'Next Petrol')} ({np_comp}/{np_total})", all_quests_display, current_y)
    current_y = draw_quest_section(f"{tr('ui', 'Recipe Books')} ({read_books_count}/{total_books_count})", recipe_books_display, current_y)
    current_y = draw_quest_section(f"{tr('ui', 'Milestones')} ({ms_comp_count}/{len(milestones)})", all_milestones_display, current_y)

    surface.set_clip(None)
    bar_rect = pygame.Rect(modal_rect.right - 10, base_y, 8, visible_height)
    draw_scrollbar(surface, modal, bar_rect, visible_height, total_content_height, current_scroll)

    if pending_tooltip:
        draw_tooltip(surface, pending_tooltip, (mouse_pos[0] + 15, mouse_pos[1] + 15))