import pygame
import random
from core.data.config import *
from core.data.localization import tr
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.modals import draw_scrollbar
from core.ui.tooltip import draw_tooltip # Import the tooltip renderer

# Visual Design Constants
DARK_GREEN = (0, 120, 0)
GREEN_HOVER = (50, 205, 50)
GOLD = (255, 215, 0)
BLUE_BTN = (0, 70, 140)
BLUE_HOVER = (30, 120, 200)
SLOT_BG = (60, 60, 60)    
SLOT_BORDER = (120, 120, 120) 
SLOT_HOVER = (80, 80, 80) 

NO_DURABILITY_TYPES = [
    'container', 'consumable_drugs', 'consumable_food', 'consumable_ammo', 
    'consumable_drink', 'consumable_medication', 'car_key', 'car_battery', 
    'camp', 'car_motor', 'car_tire', 'charm', 'map', 'recipe', 
    'resource', 'sd_card', 'text', 'quest', 'weapon_throw'
]
HAS_DURABILITY_TYPES = ['weapon_melee', 'weapon_ranged', 'cloth']
UTIL_TYPES = ['util1', 'util2', 'util3']

def generate_npc_trade_stock(npc):
    if getattr(npc, 'trade_stock_generated', False):
        return
    valid_templates = []
    for name, tmpl in ITEM_TEMPLATES.items():
        if name.startswith("Empty "): continue
        itype = tmpl.get('type', '')
        slot = tmpl.get('slot', '')
        if itype in NO_DURABILITY_TYPES or itype in HAS_DURABILITY_TYPES or itype in UTIL_TYPES:
            valid_templates.append(name)
        elif slot in ['head', 'body', 'legs', 'feet', 'arms', 'hands']: # Removed facial/hair as requested previously
            valid_templates.append(name)
            
    if valid_templates:
        if not hasattr(npc, 'inventory'): npc.inventory = []
        for _ in range(5):
            choice = random.choice(valid_templates)
            new_item = Item.create_from_name(choice)
            if new_item:
                itype = getattr(new_item, 'item_type', '')
                
                # 1. Handle items that strictly have NO Durability
                if itype in NO_DURABILITY_TYPES or itype == 'currency':
                    if hasattr(new_item, 'durability'): 
                        new_item.durability = None
                    
                    # FIX: Only assign 'load' if the item is a stackable type.
                    # Items like sd_card, map, recipe, car_key will skip this block.
                    stackable_types = ['consumable_ammo', 'consumable_food', 'consumable_medication', 
                                       'consumable_drink', 'consumable_drugs', 'resource', 'currency']
                    if itype in stackable_types:
                        cap = getattr(new_item, 'capacity', 30) or 30
                        new_item.load = random.randint(1, max(1, int(cap)))
                
                # 2. Handle Gear that DOES have Durability
                elif itype in HAS_DURABILITY_TYPES or itype in UTIL_TYPES:
                    max_dur = getattr(new_item, 'max_durability', None)
                    if max_dur and max_dur > 0:
                        new_item.durability = random.randint(1, max(1, int(max_dur)))
                
                npc.inventory.append(new_item)
    npc.trade_stock_generated = True

def is_currency(item):
    return getattr(item, 'name', '') == "Money WBRL" or getattr(item, 'item_type', '') == 'currency'

def get_trade_category(item):
    if is_currency(item): return 'currency'
    itype = getattr(item, 'item_type', '')
    if itype in NO_DURABILITY_TYPES: return itype
    slot = getattr(item, 'slot', None)
    if slot in ['head', 'body', 'legs', 'feet', 'arms', 'hands'] or itype == 'cloth':
        return 'clothing'
    return itype

def is_empty_container(item):
    if hasattr(item, 'inventory') and item.inventory is not None:
        if len(item.inventory) > 0: return False
    return True

def get_total_price(item):
    itype = getattr(item, 'item_type', '')
    if itype == 'consumable_ammo': return max(1, int(getattr(item, 'load', 1) or 1))
    if itype in ['consumable_food', 'consumable_medication', 'consumable_drink', 'resource', 'consumable']:
        weight = getattr(item, 'weight', 0.01) or 0.01
        unit_price = max(1, int(weight * 100))
        if hasattr(item, 'is_stackable') and item.is_stackable():
            return max(1, int(unit_price * (getattr(item, 'load', 1) or 1)))
        return unit_price
    if itype == 'weapon_ranged': base_price = 50
    elif itype == 'weapon_melee': base_price = 25
    else: base_price = 30
    rng = random.Random(hash(getattr(item, 'name', 'Item')))
    price = max(1, base_price + rng.randint(-5, 10))
    dur, max_dur = getattr(item, 'durability', None), getattr(item, 'max_durability', None)
    if dur is not None and max_dur and max_dur > 0:
        price = max(1, int(price * (dur / max_dur)))
    return price

def get_tradable_items(npc):
    tradable = []
    def is_tradable(item):
        if not item or getattr(item, 'name', '').startswith("Empty "): return False
        
        # ADD THIS CHECK: Strictly hide Facial and Hair slots
        if getattr(item, 'slot', None) in ['facial', 'hair']: return False
        
        if getattr(item, 'item_type', '') == 'mobile': return False
        cat = get_trade_category(item)
        if cat == 'clothing' or getattr(item, 'item_type', '') == 'container':
            return is_empty_container(item)
        return True
    if hasattr(npc, 'inventory'):
        for item in npc.inventory:
            if is_tradable(item): tradable.append(('inventory', item, None))
    if getattr(npc, 'equipped_weapon', None) and is_tradable(npc.equipped_weapon):
        tradable.append(('equipped_weapon', npc.equipped_weapon, None))
    if getattr(npc, 'clothes', None):
        for slot, item in npc.clothes.items():
            if is_tradable(item): tradable.append(('clothes', item, slot))
    return tradable

def remove_player_item(game, player_item):
    if hasattr(game.player, 'inventory') and player_item in game.player.inventory:
        game.player.inventory.remove(player_item)
        return True
    if hasattr(game.player, 'belt') and player_item in game.player.belt:
        idx = game.player.belt.index(player_item)
        game.player.belt[idx] = None
        return True
    if hasattr(game.player, 'clothes'):
        for slot, item in list(game.player.clothes.items()):
            if item == player_item:
                game.player.clothes[slot] = None
                return True
    return False

def return_offered_item(game, modal):
    item = modal.get('trade_offered_item')
    if item:
        if not hasattr(game.player, 'inventory'): game.player.inventory = []
        game.player.inventory.append(item)
        modal['trade_offered_item'] = None

def remove_npc_item(npc, npc_item_data):
    location, item, slot = npc_item_data
    if location == 'inventory' and item in npc.inventory: npc.inventory.remove(item)
    elif location == 'equipped_weapon':
        npc.equipped_weapon = None
        if item in npc.inventory: npc.inventory.remove(item)
    elif location == 'clothes': npc.clothes[slot] = None

def perform_buy(game, npc, npc_item_data, player_money, price):
    if player_money.load > price: player_money.load -= price
    else: remove_player_item(game, player_money)
    found_money = next((i for i in npc.inventory if is_currency(i)), None)
    if found_money: found_money.load += price
    else:
        new_money = Item.create_from_name("Money WBRL")
        if new_money:
            new_money.load = price
            npc.inventory.append(new_money)
    remove_npc_item(npc, npc_item_data)
    if not hasattr(game.player, 'inventory'): game.player.inventory = []
    game.player.inventory.append(npc_item_data[1])
    return True

def perform_sell(game, npc, player_item, price, npc_money_data=None):
    if npc_money_data:
        npc_money = npc_money_data[1]
        if npc_money.load > price: npc_money.load -= price
        else: remove_npc_item(npc, npc_money_data)
    remove_player_item(game, player_item)
    if not hasattr(npc, 'inventory'): npc.inventory = []
    npc.inventory.append(player_item)
    if not hasattr(game.player, 'inventory'): game.player.inventory = []
    found_money = next((i for i in game.player.inventory if is_currency(i)), None)
    if found_money: found_money.load += price
    else:
        new_money = Item.create_from_name("Money WBRL")
        if new_money:
            new_money.load = price
            game.player.inventory.append(new_money)
    return True

def perform_barter(game, npc, npc_item_data, player_item):
    if not remove_player_item(game, player_item): return False
    if not hasattr(game.player, 'inventory'): game.player.inventory = []
    game.player.inventory.append(npc_item_data[1])
    if npc_item_data[0] == 'inventory':
        if npc_item_data[1] in npc.inventory: npc.inventory.remove(npc_item_data[1])
        npc.inventory.append(player_item)
    elif npc_item_data[0] == 'equipped_weapon':
        npc.equipped_weapon = player_item
        if npc_item_data[1] in npc.inventory: npc.inventory.remove(npc_item_data[1])
        npc.inventory.append(player_item)
    elif npc_item_data[0] == 'clothes': npc.clothes[npc_item_data[2]] = player_item
    return True

def get_dragged_item(game):
    for obj in [game, getattr(game, 'player', None), getattr(game, 'ui_manager', None)]:
        if hasattr(obj, 'dragged_item') and obj.dragged_item: return obj.dragged_item, obj, 'dragged_item'
        if hasattr(obj, 'drag_item') and obj.drag_item: return obj.drag_item, obj, 'drag_item'
        if hasattr(obj, 'mouse_item') and obj.mouse_item: return obj.mouse_item, obj, 'mouse_item'
    return None, None, None

def draw_trade_tab(surface, modal, game, start_x, start_y, width, height):
    generate_npc_trade_stock(modal['npc'])
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    prev_pressed = modal.get('trade_last_mouse_pressed', False)
    mouse_just_pressed = mouse_pressed and not prev_pressed
    modal['trade_last_mouse_pressed'] = mouse_pressed
    
    npc = modal['npc']
    tradable_items = get_tradable_items(npc)
    
    slot_size, padding = 52, 8
    header_h = 30
    bottom_bar_h = 80
    content_h = height - header_h - bottom_bar_h - 20
    
    scroll_y = modal.get('scroll_offset_y', 0)
    title_surf = font_12.render(tr('dialog', 'NPC Trade Shop:'), True, WHITE)
    surface.blit(title_surf, (start_x + (width - title_surf.get_width()) // 2, start_y))
    
    item_area_rect = pygame.Rect(start_x + 10, start_y + header_h, width - 20, content_h)
    cols = 5
    rows = (len(tradable_items) + cols - 1) // cols
    total_grid_h = rows * (slot_size + padding)
    grid_w = (cols * slot_size) + ((cols - 1) * padding)
    grid_start_x_absolute = start_x + (width - grid_w) // 2
    grid_start_x_relative = grid_start_x_absolute - item_area_rect.x

    max_scroll = max(0, total_grid_h - content_h)
    if scroll_y > max_scroll: scroll_y = max_scroll
    if scroll_y < 0: scroll_y = 0
    modal['scroll_offset_y'] = scroll_y
    modal['content_rect'] = item_area_rect

    clip_surf = pygame.Surface((item_area_rect.width, item_area_rect.height), pygame.SRCALPHA)
    selected_index = modal.get('trade_selected_index', -1)
    
    # Track the item currently hovered for the final tooltip render
    current_hover_item = None
    current_hover_rect = None
    
    if not tradable_items:
        empty_surf = font_12.render(tr('dialog', 'This NPC has nothing to trade.'), True, GRAY)
        clip_surf.blit(empty_surf, ((item_area_rect.width - empty_surf.get_width()) // 2, 20))
    else:
        for i, item_data in enumerate(tradable_items):
            item = item_data[1]
            row, col = i // cols, i % cols
            
            lx = grid_start_x_relative + col * (slot_size + padding)
            ly = row * (slot_size + padding) - scroll_y
            
            slot_rect_abs = pygame.Rect(grid_start_x_absolute + col * (slot_size + padding), 
                                        start_y + header_h + row * (slot_size + padding) - scroll_y, 
                                        slot_size, slot_size)
            
            is_hovered = slot_rect_abs.collidepoint(mouse_pos)
            
            if is_hovered:
                current_hover_item = item
                current_hover_rect = slot_rect_abs
                if mouse_just_pressed:
                    modal['trade_selected_index'] = i
                    modal['trade_message'] = "" 

            if -slot_size < ly < content_h:
                slot_rect_rel = pygame.Rect(lx, ly, slot_size, slot_size)
                if i == selected_index:
                    bg_color, border_color, border_w = SLOT_BG, GREEN, 3
                elif is_hovered:
                    bg_color, border_color, border_w = SLOT_HOVER, WHITE, 1
                else:
                    bg_color, border_color, border_w = SLOT_BG, SLOT_BORDER, 1
                
                pygame.draw.rect(clip_surf, bg_color, slot_rect_rel, 0, 3)
                pygame.draw.rect(clip_surf, border_color, slot_rect_rel, border_w, 3)

                if item and getattr(item, 'image', None):
                    scaled_img = pygame.transform.scale(item.image, (slot_size - 4, slot_size - 4))
                    clip_surf.blit(scaled_img, (lx + 2, ly + 2))
                
                if hasattr(item, 'is_stackable') and item.is_stackable() and getattr(item, 'load', 0) > 0:
                    qty_text = font_12.render(str(int(item.load)), True, WHITE)
                    clip_surf.blit(qty_text, (slot_rect_rel.right - qty_text.get_width() - 2, slot_rect_rel.bottom - qty_text.get_height() - 2))
                
                if not is_currency(item):
                    price = get_total_price(item)
                    p_shadow = font_12.render(f"${price}", True, BLACK)
                    p_text = font_12.render(f"${price}", True, GOLD)
                    clip_surf.blit(p_shadow, (lx + 3, ly + 3))
                    clip_surf.blit(p_text, (lx + 2, ly + 2))

                itype = getattr(item, 'item_type', '')
                if itype in HAS_DURABILITY_TYPES or itype in UTIL_TYPES:
                    item_dur, item_max_dur = getattr(item, 'durability', None), getattr(item, 'max_durability', None)
                    if item_dur is not None and item_max_dur and item_max_dur > 0:
                        dur_pct = max(0, min(1, item_dur / float(item_max_dur)))
                        bar_color = GREEN if dur_pct > 0.5 else (YELLOW if dur_pct > 0.25 else RED)
                        pygame.draw.rect(clip_surf, bar_color, (lx + 2, ly + slot_size - 6, (slot_size - 4) * dur_pct, 4))

    surface.blit(clip_surf, item_area_rect.topleft)
    
    bar_rect = pygame.Rect(item_area_rect.right - 10, item_area_rect.y, 8, item_area_rect.height)
    draw_scrollbar(surface, modal, bar_rect, item_area_rect.height, total_grid_h, scroll_y)

    bottom_y_absolute = start_y + height - bottom_bar_h - 10
    bar_center_x = start_x + width // 2
    
    drop_zone_rect = pygame.Rect(bar_center_x - 130, bottom_y_absolute + 10, slot_size, slot_size)
    modal['trade_drop_zone_rect'] = drop_zone_rect
    pygame.draw.rect(surface, SLOT_BG, drop_zone_rect, 0, 3)
    pygame.draw.rect(surface, YELLOW if drop_zone_rect.collidepoint(mouse_pos) else WHITE, drop_zone_rect, 2, 3)
    
    drop_label = font_12.render(tr('dialog', 'Offer:'), True, WHITE)
    surface.blit(drop_label, (drop_zone_rect.x - 45, drop_zone_rect.centery - 6))

    sell_btn_rect = pygame.Rect(bar_center_x - 40, bottom_y_absolute + 10, 70, 35)
    pygame.draw.rect(surface, BLUE_HOVER if sell_btn_rect.collidepoint(mouse_pos) else BLUE_BTN, sell_btn_rect, 0, 5)
    pygame.draw.rect(surface, WHITE, sell_btn_rect, 1, 5)
    sell_text = font_12.render(tr('dialog', 'SELL'), True, WHITE)
    surface.blit(sell_text, (sell_btn_rect.centerx - sell_text.get_width() // 2, sell_btn_rect.centery - sell_text.get_height() // 2))

    trade_btn_rect = pygame.Rect(bar_center_x + 40, bottom_y_absolute + 10, 70, 35)
    pygame.draw.rect(surface, GREEN_HOVER if trade_btn_rect.collidepoint(mouse_pos) else DARK_GREEN, trade_btn_rect, 0, 5)
    pygame.draw.rect(surface, WHITE, trade_btn_rect, 1, 5)
    trade_text = font_12.render(tr('dialog', 'TRADE'), True, WHITE)
    surface.blit(trade_text, (trade_btn_rect.centerx - trade_text.get_width() // 2, trade_btn_rect.centery - trade_text.get_height() // 2))

    dragged_item, _, _ = get_dragged_item(game)
    if dragged_item and drop_zone_rect.collidepoint(mouse_pos):
        if getattr(dragged_item, 'image', None):
            ghost_img = pygame.transform.scale(dragged_item.image, (slot_size - 4, slot_size - 4))
            ghost_img.set_alpha(150)
            surface.blit(ghost_img, (drop_zone_rect.x + 2, drop_zone_rect.y + 2))

    offered_item = modal.get('trade_offered_item')
    if offered_item:
        if offered_item and drop_zone_rect.collidepoint(mouse_pos):
            current_hover_item = offered_item
            current_hover_rect = drop_zone_rect
            
        if getattr(offered_item, 'image', None):
            scaled_img = pygame.transform.scale(offered_item.image, (slot_size - 4, slot_size - 4))
            surface.blit(scaled_img, (drop_zone_rect.x + 2, drop_zone_rect.y + 2))
        if hasattr(offered_item, 'is_stackable') and offered_item.is_stackable() and getattr(offered_item, 'load', 0) > 0:
            qty_text = font_12.render(str(int(offered_item.load)), True, WHITE)
            surface.blit(qty_text, (drop_zone_rect.right - qty_text.get_width() - 2, drop_zone_rect.bottom - qty_text.get_height() - 2))
        if not is_currency(offered_item):
            p_shadow = font_12.render(f"${get_total_price(offered_item)}", True, BLACK)
            p_text = font_12.render(f"${get_total_price(offered_item)}", True, GOLD)
            surface.blit(p_shadow, (drop_zone_rect.x + 3, drop_zone_rect.y + 3))
            surface.blit(p_text, (drop_zone_rect.x + 2, drop_zone_rect.y + 2))
        if drop_zone_rect.collidepoint(mouse_pos) and mouse_just_pressed:
            modal['trade_offered_item'] = None
            modal['trade_message'] = tr('dialog', 'Offer removed.')

    # FINAL STEP: Render Tooltip on top of everything else
    if current_hover_item:
        draw_tooltip(surface, current_hover_item, mouse_pos, current_hover_rect)

    if mouse_just_pressed and sell_btn_rect.collidepoint(mouse_pos):
        error = None
        if not offered_item: error = tr('dialog', 'Drop an item to sell!')
        elif is_currency(offered_item): error = tr('dialog', 'Cannot sell currency!')
        elif (get_trade_category(offered_item) == 'clothing' or getattr(offered_item, 'item_type', '') == 'container') and not is_empty_container(offered_item):
            error = tr('dialog', 'Your item must be empty to sell!')
        if error: modal['trade_message'] = error
        else:
            price = get_total_price(offered_item)
            perform_sell(game, npc, offered_item, price)
            modal['trade_offered_item'], modal['trade_selected_index'] = None, -1
            modal['trade_message'] = f"{tr('dialog', 'Sold for')} ${price}!"

    elif mouse_just_pressed and trade_btn_rect.collidepoint(mouse_pos):
        error = None
        if selected_index == -1: error = tr('dialog', 'Select an NPC item first!')
        elif not offered_item: error = tr('dialog', 'Drop an item to offer!')
        elif (get_trade_category(offered_item) == 'clothing' or getattr(offered_item, 'item_type', '') == 'container') and not is_empty_container(offered_item):
            error = tr('dialog', 'Your item must be empty to trade!')
        if error: modal['trade_message'] = error
        else:
            npc_item_data = tradable_items[selected_index]
            npc_item = npc_item_data[1]
            if is_currency(offered_item) and not is_currency(npc_item):
                price = get_total_price(npc_item)
                if offered_item.load >= price:
                    if (offered_item.load > price) and len(getattr(game.player, 'inventory', [])) >= game.player.get_total_inventory_slots():
                        modal['trade_message'] = tr('dialog', 'Your inventory is full!')
                    else:
                        perform_buy(game, npc, npc_item_data, offered_item, price)
                        if offered_item.load <= 0: modal['trade_offered_item'] = None
                        modal['trade_selected_index'] = -1
                        modal['trade_message'] = tr('dialog', 'Purchase successful!')
                else: modal['trade_message'] = f"{tr('dialog', 'Not enough money! Need')} ${price}."
            elif not is_currency(offered_item) and not is_currency(npc_item):
                if get_total_price(offered_item) >= get_total_price(npc_item):
                    if perform_barter(game, npc, npc_item_data, offered_item):
                        modal['trade_offered_item'], modal['trade_selected_index'] = None, -1
                        modal['trade_message'] = tr('dialog', 'Trade successful!')
                else: modal['trade_message'] = tr('dialog', 'Offer too low!')
            else: modal['trade_message'] = tr('dialog', 'Invalid trade combination!')

    msg = modal.get('trade_message', '')
    if msg:
        msg_color = GREEN if 'successful' in msg or 'Sold' in msg else (YELLOW if 'removed' in msg else RED)
        msg_surf = font_12.render(msg, True, msg_color)
        surface.blit(msg_surf, (start_x + 60 + (width - msg_surf.get_width()) // 2, trade_btn_rect.bottom + 10))