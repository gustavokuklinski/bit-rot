import pygame
import os
import xml.etree.ElementTree as ET
from core.data.config import *
from core.ui.tooltip import draw_tooltip
from core.entities.item.item import Item
from core.data.localization import tr

# Module-level cache to parse the XML only once
_QUESTS_CACHE = None

def load_quests():
    global _QUESTS_CACHE
    if _QUESTS_CACHE is not None:
        return _QUESTS_CACHE
        
    _QUESTS_CACHE = []
    
    # Check for dialogs.xml, fallback to dialog.xml just in case
    dialogs_path = os.path.join(DATA_PATH, 'npc/dialogs.xml')
    if not os.path.exists(dialogs_path):
        if not os.path.exists(dialogs_path):
            print(f"Warning: Could not find dialogs.xml at {DATA_PATH}")
            return _QUESTS_CACHE
        
    try:
        tree = ET.parse(dialogs_path)
        root = tree.getroot()
        
        # Use .iter('node') to safely find all <node> elements regardless of XML nesting depth
        for node in root.iter('node'):
            node_id = node.get('id', '')
            
            # Case-insensitive check just in case it's written as "quest:" or "Quest:"
            if node_id.lower().startswith('quest:'):
                # Safely slice off the prefix (6 characters) and strip whitespace
                quest_name = node_id[6:].strip() 
                
                raw_item_str = None
                tip = "No tip provided"
                complete_flag = quest_name
                
                # Iterate over ALL option tags in the node.
                for options in node.findall('options') + node.findall('option'):
                    if options.get('rqst_item'):
                        raw_item_str = options.get('rqst_item')
                    elif not raw_item_str and options.get('award_item'):
                        raw_item_str = options.get('award_item')
                        
                    if options.get('tip'):
                        tip = options.get('tip')
                        
                    if options.get('complete_flag'):
                        complete_flag = options.get('complete_flag').strip()
                    
                rqst_item = None
                if raw_item_str:
                    # Strip the '[' and ']' brackets, and just take the first item if there are multiple
                    cleaned_str = raw_item_str.replace('[', '').replace(']', '')
                    rqst_item = cleaned_str.split(',')[0].strip()
                    
                # Create a dummy item just to cache the sprite inside the Item class
                item = None
                if rqst_item:
                    item = Item.create_from_name(rqst_item)
                    
                _QUESTS_CACHE.append({
                    'node_id': node_id,  
                    'name': quest_name,
                    'rqst_item_name': rqst_item,
                    'item_obj': item,
                    'tip': tip,
                    'complete_flag': complete_flag
                })
    except Exception as e:
        print(f"Error loading quests from dialogs.xml: {e}")
        
    return _QUESTS_CACHE


def draw_quests_tab(surface, player, modal, assets, mouse_pos):
    modal_rect = modal['rect']
    quests = load_quests()
    
    # Starting layout positions
    start_x = modal_rect.left + 15
    start_y = modal_rect.top + 80 
    slot_size = 40
    gap = 10
    cols = 4 # How many slots fit in the UI width horizontally
    
    pending_tooltip = None
    
    for i, quest in enumerate(quests):
        row = i // cols
        col = i % cols
        
        x = start_x + col * (slot_size + gap)
        y = start_y + row * (slot_size + gap)
        
        slot_rect = pygame.Rect(x, y, slot_size, slot_size)
        
        completed_list = getattr(player, 'completed_quests', [])
        active_list = getattr(player, 'quests', [])
        
        # [FIX] Check if completed by complete_flag OR node_id
        is_completed = (quest['complete_flag'] in completed_list) or (quest['node_id'] in completed_list)
        
        # [FIX] Check if open by checking if node_id (e.g. "Quest: Mobile phone") OR the name is in active_list
        is_open = ((quest['node_id'] in active_list) or (quest['name'] in active_list)) and not is_completed
        
        # 1. Draw Slot Background
        pygame.draw.rect(surface, GRAY_40, slot_rect)
        
        # 2. Draw Sprite or Fallback Text
        item = quest['item_obj']
        if item and getattr(item, 'image', None):
            img = item.image.copy()
            
            # Make image opaque if quest is not started
            if not is_open and not is_completed:
                img.set_alpha(100)
                
            # Keep it contained in the slot padding
            scaled_img = pygame.transform.scale(img, (32, 32))
            img_rect = scaled_img.get_rect(center=slot_rect.center)
            surface.blit(scaled_img, img_rect)
        else:
            # Fallback if the item has no image or item is missing
            fallback_text = font_14.render("?", True, WHITE)
            if not is_open and not is_completed:
                fallback_text.set_alpha(100)
            text_rect = fallback_text.get_rect(center=slot_rect.center)
            surface.blit(fallback_text, text_rect)
            
        # 3. Draw Border depending on state
        border_color = GRAY_60 # Default / Not Open
        border_width = 1
        
        if is_completed:
            border_color = GREEN
            border_width = 2
        elif is_open:
            border_color = YELLOW
            border_width = 2
            
        pygame.draw.rect(surface, border_color, slot_rect, border_width)
        
        # 4. Handle Tooltip Intersection Logic
        if slot_rect.collidepoint(mouse_pos):
            class QuestTooltipDummy:
                """Mock class bridging attributes safely to your generic `draw_tooltip`"""
                def __init__(self, q):
                    self.name = tr('ui', q['name'])
                    status = tr('ui', 'Completed') if is_completed else (tr('ui', 'In Progress') if is_open else tr('ui', 'Locked'))
                    self.tooltip_text = f"{tr('ui', 'Status:')} {status}\n{tr('ui', q['tip'])}"
                    
                    # Dummy params to avoid traceback from the tooltips item-based renderer
                    self.item_type = self.durability = self.max_durability = None
                    self.load = self.capacity = self.min_damage = self.max_damage = None
                    self.ammo_type = self.defence = None
                    
            pending_tooltip = QuestTooltipDummy(quest)
            
    # Draw tooltip absolutely last so it sits on top of all UI elements
    if pending_tooltip:
        draw_tooltip(surface, pending_tooltip, (mouse_pos[0] + 10, mouse_pos[1] + 10))