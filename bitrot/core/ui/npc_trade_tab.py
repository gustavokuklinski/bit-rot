# core/ui/npc_trade_tab.py

import pygame
import random
from core.data.config import *
from core.data.localization import tr
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.modals import draw_scrollbar
from core.events.mouse_context_helpers import get_player_fuel_units, consume_player_fuel_units

DARK_GREEN = (0, 120, 0)
GREEN_HOVER = (50, 205, 50)
GOLD = (255, 215, 0)
DISABLED_GRAY = (60, 60, 60)

GAMBLE_CURRENCY_COST = 20
GAMBLE_FUEL_COST = 10

HAS_DURABILITY_TYPES = ['weapon_melee', 'weapon_ranged', 'cloth', 'tool']
UTIL_TYPES = ['util1', 'util2', 'util3']

def is_currency(item):
    return getattr(item, 'name', '') == "Money WBRL" or getattr(item, 'item_type', '') == 'currency'

def get_player_total_currency(player):
    """Calculates total Money WBRL held recursively across inventory, belt, gear, and nested containers."""
    if not player:
        return 0
    total = 0
    visited_containers = set()

    def scan(container):
        nonlocal total
        if not container:
            return
        c_id = id(container)
        if c_id in visited_containers:
            return
        visited_containers.add(c_id)

        items_iterable = container.values() if isinstance(container, dict) else container
        for it in items_iterable:
            if not it:
                continue
            if is_currency(it):
                total += int(getattr(it, 'load', 1) or 1)
            if hasattr(it, 'inventory') and it.inventory:
                scan(it.inventory)

    scan(getattr(player, 'inventory', []))
    scan(getattr(player, 'belt', []))
    if hasattr(player, 'clothes'):
        scan(player.clothes)

    return total

def deduct_player_currency(player, amount_needed):
    """Deducts currency units recursively from player inventory, belt, gear, and nested containers."""
    if not player or amount_needed <= 0:
        return True

    remaining = amount_needed
    currency_entries = []
    visited_containers = set()

    def scan(container, ctype):
        if not container:
            return
        c_id = id(container)
        if c_id in visited_containers:
            return
        visited_containers.add(c_id)

        if ctype == 'dict':
            for k in list(container.keys()):
                it = container[k]
                if not it:
                    continue
                if is_currency(it):
                    currency_entries.append((container, k, it, 'dict'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')
        elif ctype == 'fixed_list':
            for idx in range(len(container)):
                it = container[idx]
                if not it:
                    continue
                if is_currency(it):
                    currency_entries.append((container, idx, it, 'fixed_list'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')
        else:
            for idx in range(len(container) - 1, -1, -1):
                it = container[idx]
                if not it:
                    continue
                if is_currency(it):
                    currency_entries.append((container, idx, it, 'list'))
                if hasattr(it, 'inventory') and it.inventory:
                    scan(it.inventory, 'list')

    scan(getattr(player, 'inventory', []), 'list')
    scan(getattr(player, 'belt', []), 'fixed_list')
    if hasattr(player, 'clothes'):
        scan(player.clothes, 'dict')

    for container, key, it, ctype in currency_entries:
        if remaining <= 0:
            break
        cur_load = int(getattr(it, 'load', 1) or 1)
        take = min(remaining, cur_load)
        remaining -= take
        it.load = cur_load - take

        if it.load <= 0:
            if ctype == 'fixed_list':
                container[key] = None
                it.in_belt = False
            elif ctype == 'list':
                if it in container:
                    container.remove(it)
                elif isinstance(key, int) and 0 <= key < len(container):
                    container.pop(key)
            elif ctype == 'dict':
                container[key] = None

    return remaining <= 0

def get_unit_price(item):
    """Calculates price for a single unit of an item."""
    itype = getattr(item, 'item_type', '')
    if itype == 'consumable_ammo':
        return 1

    if itype in ['consumable']:
        base_price = 15
    elif itype == 'weapon_ranged':
        base_price = 50
    elif itype == 'weapon_melee':
        base_price = 35
    elif itype == 'weapon_throw':
        base_price = 35
    elif itype == 'map':
        base_price = 10
    elif itype == 'consumable_drugs':
        base_price = 20
    elif itype == 'consumable_medication':
        base_price = 10
    elif itype == 'consumable_food':
        base_price = 15
    elif itype == 'consumable_drink':
        base_price = 10
    else:
        base_price = 20

    rng = random.Random(hash(getattr(item, 'name', 'Item')))
    price = max(1, base_price + rng.randint(-3, 8))

    dur, max_dur = getattr(item, 'durability', None), getattr(item, 'max_durability', None)
    if dur is not None and max_dur and max_dur > 0:
        price = max(1, int(price * (dur / max_dur)))

    return price

def get_trade_type_options():
    """Returns 'Default' followed by sorted available item types for the dropdown."""
    available_types = set()
    for name, tmpl in ITEM_TEMPLATES.items():
        if name.startswith("Empty ") or name.endswith(" on"):
            continue
        itype = tmpl.get('type')
        if itype and itype not in ('quest', 'maptile', 'maptile_container', 'currency', 'vehicle'):
            available_types.add(itype)

    preferred_order = [
        'weapon_melee', 'weapon_ranged', 'weapon_throw',
        'consumable_ammo', 'consumable_food', 'consumable_drink',
        'consumable_medication', 'consumable_drugs',
        'cloth', 'tool', 'resource', 'container', 'map', 'recipe'
    ]

    ordered = [t for t in preferred_order if t in available_types]
    for t in sorted(available_types):
        if t not in ordered:
            ordered.append(t)

    return ['Default'] + ordered

def generate_npc_trade_stock(npc, game=None, trade_type='Default', force=False):
    if not force and getattr(npc, 'trade_stock_generated', False) and hasattr(npc, 'trade_stock') and npc.trade_stock:
        return

    trade_cfg = getattr(npc, 'trade_config', None)
    limit = 15
    allowed_types = []
    allowed_items = []

    if trade_cfg:
        limit = trade_cfg.get('limit', 15)
        allowed_types = trade_cfg.get('types', [])
        allowed_items = trade_cfg.get('items', [])

    if force:
        rng = random.Random()
    else:
        seed_val = hash(getattr(npc, 'id', npc.name))
        rng = random.Random(seed_val)

    lucky_level = 0.0
    if game and hasattr(game, 'player') and game.player and hasattr(game.player, 'progression'):
        lucky_level = float(game.player.progression.get_lucky(game.player))

    candidates = []
    weights = []

    for name, tmpl in ITEM_TEMPLATES.items():
        if name.startswith("Empty ") or name.endswith(" on"):
            continue
        itype = tmpl.get('type', '')

        if trade_type != 'Default':
            if itype != trade_type:
                continue
        else:
            if trade_cfg:
                match_type = bool(allowed_types and itype in allowed_types)
                match_name = bool(allowed_items and (name in allowed_items or tmpl.get('name') in allowed_items))
                if not (match_type or match_name):
                    continue
            else:
                if itype not in ['consumable_food', 'consumable_medication', 'consumable_ammo', 'weapon_ranged', 'weapon_melee', 'resource']:
                    continue

        base_chance = float(tmpl.get('spawn_chance', 1.0))
        if base_chance <= 0:
            base_chance = 0.2

        is_valuable = itype in ['weapon_ranged', 'weapon_melee', 'weapon_throw', 'consumable_drugs', 'consumable_medication', 'map']
        luck_boost = 1.0 + (lucky_level * 0.10)

        if base_chance < 0.3 or is_valuable:
            weight = (base_chance + (lucky_level * 0.05)) * luck_boost
        else:
            weight = base_chance

        candidates.append(name)
        weights.append(max(0.01, weight))

    npc.trade_stock = []

    if candidates and limit > 0:
        k_count = min(limit, len(candidates))
        selected_names = []
        c_copy = list(candidates)
        w_copy = list(weights)

        for _ in range(k_count):
            if not c_copy:
                break
            choice = rng.choices(c_copy, weights=w_copy, k=1)[0]
            selected_names.append(choice)
            idx = c_copy.index(choice)
            c_copy.pop(idx)
            w_copy.pop(idx)

        while len(selected_names) < limit:
            selected_names.append(rng.choices(candidates, weights=weights, k=1)[0])

        for choice_name in selected_names:
            new_item = Item.create_from_name(choice_name, spawn_loot=False)
            if not new_item:
                continue

            itype = getattr(new_item, 'item_type', '')
            is_weapon = (
                itype in ['weapon_ranged', 'weapon_melee', 'weapon_throw', 'tool']
                or itype.startswith('weapon')
            )

            if is_weapon:
                if hasattr(new_item, 'load'):
                    new_item.load = 0
                max_dur = getattr(new_item, 'max_durability', 100) or 100
                new_item.durability = max_dur
            else:
                if hasattr(new_item, 'is_stackable') and new_item.is_stackable():
                    cap = getattr(new_item, 'capacity', 30) or 30
                    min_ratio = min(0.8, 0.2 + (lucky_level * 0.03))
                    new_item.load = rng.randint(max(1, int(cap * min_ratio)), max(1, int(cap)))
                elif itype in HAS_DURABILITY_TYPES or itype in UTIL_TYPES:
                    max_dur = getattr(new_item, 'max_durability', 100) or 100
                    new_item.durability = max_dur

            npc.trade_stock.append(new_item)

    npc.trade_stock_generated = True


def draw_trade_tab(surface, modal, game, start_x, start_y, width, height):
    npc = modal['npc']

    # Initial conversation generation as Default
    if not modal.get('_trade_initialized', False):
        modal['_trade_initialized'] = True
        modal['trade_selected_type'] = 'Default'
        modal['trade_selected_index'] = -1
        modal['trade_type_dd_open'] = False
        modal['trade_message'] = ""
        generate_npc_trade_stock(npc, game=game, trade_type='Default', force=True)

    selected_type = modal.get('trade_selected_type', 'Default')
    generate_npc_trade_stock(npc, game, trade_type=selected_type, force=False)

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    prev_pressed = modal.get('trade_last_mouse_pressed', False)
    mouse_just_pressed = mouse_pressed and not prev_pressed
    modal['trade_last_mouse_pressed'] = mouse_pressed

    tradable_items = getattr(npc, 'trade_stock', [])

    # Proportional dimensions
    slot_size, padding = 48, 6
    header_h = 24
    gamble_panel_h = 56
    buy_panel_h = 56

    content_h = (3 * slot_size) + (2 * padding) + 15
    scroll_y = modal.get('scroll_offset_y', 0)

    # 1. Title Header
    title_str = tr('dialog', 'NPC Trade Shop')
    title_surf = font_12.render(title_str, True, WHITE)
    surface.blit(title_surf, (start_x + (width - title_surf.get_width()) // 2, start_y + 2))

    # Pre-calculate Dropdown Rect to prevent mouse pass-through into underlying slots
    type_options = get_trade_type_options()
    dd_open = modal.get('trade_type_dd_open', False)
    opt_h = 22
    max_vis = 6
    vis_count = min(len(type_options), max_vis)
    popup_h = vis_count * opt_h

    gamble_panel_y = start_y + header_h + content_h + 6
    gamble_panel_rect = pygame.Rect(start_x + 10, gamble_panel_y, width - 20, gamble_panel_h)
    
    gamble_icon_txt = font_12.render(f"{tr('ui', 'Gamble')}:", False, GOLD)
    dd_btn_w = 150
    dd_btn_h = 26
    dd_btn_x = gamble_panel_rect.x + gamble_icon_txt.get_width() + 20
    dd_btn_y = gamble_panel_rect.centery - (dd_btn_h // 2)
    dd_btn_rect = pygame.Rect(dd_btn_x, dd_btn_y, dd_btn_w, dd_btn_h)
    modal['trade_type_dd_btn_rect'] = dd_btn_rect

    popup_y = dd_btn_rect.top - popup_h - 2
    popup_rect = pygame.Rect(dd_btn_rect.x, popup_y, dd_btn_rect.width + 20, popup_h)
    
    # Store popup hitbox for mouse.py & input.py
    if dd_open:
        modal['trade_type_dd_popup_rect'] = popup_rect
    else:
        modal['trade_type_dd_popup_rect'] = None

    # Mouse is over popup check
    is_over_dd_popup = dd_open and popup_rect.collidepoint(mouse_pos)

    # ==============================================================
    # 2. ITEMS GRID (LIST)
    # ==============================================================
    item_area_rect = pygame.Rect(start_x + 10, start_y + header_h, width - 20, content_h)
    cols = 5
    rows = (len(tradable_items) + cols - 1) // cols
    total_grid_h = rows * (slot_size + padding)
    grid_w = (cols * slot_size) + ((cols - 1) * padding)
    grid_start_x_absolute = start_x + (width - grid_w) // 2
    grid_start_x_relative = grid_start_x_absolute - item_area_rect.x

    max_scroll = max(0, total_grid_h - content_h)
    scroll_y = max(0, min(scroll_y, max_scroll))
    modal['scroll_offset_y'] = scroll_y
    modal['content_rect'] = item_area_rect

    clip_surf = pygame.Surface((item_area_rect.width, item_area_rect.height))
    clip_surf.fill((20, 20, 20))
    selected_index = modal.get('trade_selected_index', -1)

    modal['trade_slot_rects'] = []

    if not tradable_items:
        empty_surf = font_12.render(tr('dialog', 'No items available in this category.'), True, GRAY)
        clip_surf.blit(empty_surf, ((item_area_rect.width - empty_surf.get_width()) // 2, 30))
    else:
        for i, item in enumerate(tradable_items):
            row, col = i // cols, i % cols
            lx = grid_start_x_relative + col * (slot_size + padding)
            ly = row * (slot_size + padding) - scroll_y

            slot_rect_abs = pygame.Rect(
                grid_start_x_absolute + col * (slot_size + padding),
                item_area_rect.y + row * (slot_size + padding) - scroll_y,
                slot_size, slot_size
            )

            # Block hover/clicks if the dropdown popup is currently covering this spot
            is_hovered = slot_rect_abs.collidepoint(mouse_pos) and not is_over_dd_popup and not dd_open

            if is_hovered and mouse_just_pressed:
                modal['trade_selected_index'] = i
                modal['trade_message'] = ""

            if -slot_size < ly < content_h:
                slot_rect_rel = pygame.Rect(lx, ly, slot_size, slot_size)

                # Do NOT register slot for drag if covered by the dropdown
                if item_area_rect.collidepoint(slot_rect_abs.center) and not is_over_dd_popup:
                    modal['trade_slot_rects'].append({'rect': slot_rect_abs, 'index': i, 'item': item})

                # Slot Frame
                pygame.draw.rect(clip_surf, GRAY_40, slot_rect_rel, 0, 3)
                if i == selected_index:
                    pygame.draw.rect(clip_surf, GREEN, slot_rect_rel, 2, 3)
                elif is_hovered:
                    pygame.draw.rect(clip_surf, WHITE, slot_rect_rel, 1, 3)
                else:
                    pygame.draw.rect(clip_surf, GRAY_60, slot_rect_rel, 1, 3)

                # Item Sprite
                if item and getattr(item, 'image', None):
                    scaled_img = pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8))
                    clip_surf.blit(scaled_img, (lx + 4, ly + 4))
                elif item and hasattr(item, 'color'):
                    pygame.draw.rect(clip_surf, item.color, slot_rect_rel.inflate(-8, -8))

                # Stack Count
                if hasattr(item, 'is_stackable') and item.is_stackable() and getattr(item, 'load', 0) > 1:
                    qty_text = font_12.render(str(int(item.load)), True, WHITE)
                    clip_surf.blit(qty_text, (slot_rect_rel.right - qty_text.get_width() - 3, slot_rect_rel.bottom - qty_text.get_height() - 2))

                # Price Tag
                price = get_unit_price(item)
                p_shadow = font_12.render(f"${price}", True, BLACK)
                p_text = font_12.render(f"${price}", True, GOLD)
                clip_surf.blit(p_shadow, (lx + 3, ly + 3))
                clip_surf.blit(p_text, (lx + 2, ly + 2))

                # Durability Bar
                itype = getattr(item, 'item_type', '')
                if itype in HAS_DURABILITY_TYPES or itype in UTIL_TYPES:
                    item_dur = getattr(item, 'durability', None)
                    item_max_dur = getattr(item, 'max_durability', None)
                    if item_dur is not None and item_max_dur and item_max_dur > 0:
                        dur_pct = max(0.0, min(1.0, float(item_dur) / float(item_max_dur)))
                        bar_w = slot_size - 10
                        bar_h = 3
                        bar_x = lx + 5
                        bar_y = ly + slot_size - 6
                        bar_color = GREEN if dur_pct > 0.5 else (YELLOW if dur_pct > 0.25 else RED)
                        pygame.draw.rect(clip_surf, BLACK, (bar_x, bar_y, bar_w, bar_h))
                        if dur_pct > 0:
                            pygame.draw.rect(clip_surf, bar_color, (bar_x, bar_y, int(bar_w * dur_pct), bar_h))

    surface.blit(clip_surf, item_area_rect.topleft)

    if max_scroll > 0 and not is_over_dd_popup and not dd_open:
        bar_rect = pygame.Rect(item_area_rect.right - 8, item_area_rect.y, 6, item_area_rect.height)
        draw_scrollbar(surface, modal, bar_rect, item_area_rect.height, total_grid_h, scroll_y)

    # ==============================================================
    # 3. GAMBLE SQUARE PANEL (BELOW THE LIST, ON TOP OF BUY)
    # ==============================================================
    pygame.draw.rect(surface, (28, 28, 28), gamble_panel_rect, border_radius=4)
    pygame.draw.rect(surface, (70, 70, 80), gamble_panel_rect, 1, border_radius=4)

    # A. Gamble Label
    surface.blit(gamble_icon_txt, (gamble_panel_rect.x + 12, gamble_panel_rect.centery - gamble_icon_txt.get_height() // 2))

    # B. Type Dropdown Button
    disp_type_name = tr('item_type', selected_type) if selected_type != 'Default' else tr('ui', 'Default')
    if len(disp_type_name) > 13:
        disp_type_name = disp_type_name[:11] + ".."

    is_dd_hover = dd_btn_rect.collidepoint(mouse_pos) and not is_over_dd_popup
    pygame.draw.rect(surface, (45, 45, 45) if is_dd_hover else (35, 35, 35), dd_btn_rect, border_radius=3)
    pygame.draw.rect(surface, YELLOW if is_dd_hover else GRAY_60, dd_btn_rect, 1, border_radius=3)

    cur_type_surf = font_12.render(disp_type_name, False, YELLOW if selected_type != 'Default' else WHITE)
    surface.blit(cur_type_surf, (dd_btn_rect.x + 8, dd_btn_rect.centery - cur_type_surf.get_height() // 2))

    arrow_char = "^" if dd_open else "v"
    arrow_surf = font_12.render(arrow_char, False, WHITE)
    surface.blit(arrow_surf, (dd_btn_rect.right - 14, dd_btn_rect.centery - arrow_surf.get_height() // 2))

    # C. Gamble Button
    gamble_btn_w = 175
    gamble_btn_h = 26
    gamble_btn_x = gamble_panel_rect.right - gamble_btn_w - 12
    gamble_btn_y = gamble_panel_rect.centery - (gamble_btn_h // 2)
    gamble_btn_rect = pygame.Rect(gamble_btn_x, gamble_btn_y, gamble_btn_w, gamble_btn_h)

    player_money = get_player_total_currency(game.player)
    player_fuel = get_player_fuel_units(game.player)
    can_gamble = (player_money >= GAMBLE_CURRENCY_COST and player_fuel >= GAMBLE_FUEL_COST and not dd_open)

    is_gamble_hover = gamble_btn_rect.collidepoint(mouse_pos) and not dd_open
    if can_gamble:
        gamble_bg = (60, 60, 95) if is_gamble_hover else (40, 40, 70)
        gamble_border = YELLOW if is_gamble_hover else (130, 130, 200)
        gamble_txt_col = YELLOW if is_gamble_hover else WHITE
    else:
        gamble_bg = (35, 35, 35)
        gamble_border = (60, 60, 60)
        gamble_txt_col = (110, 110, 110)

    pygame.draw.rect(surface, gamble_bg, gamble_btn_rect, border_radius=4)
    pygame.draw.rect(surface, gamble_border, gamble_btn_rect, 1, border_radius=4)

    gamble_label = font_12.render(f"{tr('ui', 'Gamble')} (${GAMBLE_CURRENCY_COST} + {GAMBLE_FUEL_COST}F)", False, gamble_txt_col)
    surface.blit(gamble_label, gamble_label.get_rect(center=gamble_btn_rect.center))

    # Dropdown Button Click
    if mouse_just_pressed and is_dd_hover:
        modal['trade_type_dd_open'] = not modal.get('trade_type_dd_open', False)

    # Gamble Click
    if mouse_just_pressed and is_gamble_hover:
        modal['trade_type_dd_open'] = False
        if not can_gamble:
            missing = []
            if player_money < GAMBLE_CURRENCY_COST:
                missing.append(f"${GAMBLE_CURRENCY_COST}")
            if player_fuel < GAMBLE_FUEL_COST:
                missing.append(f"{GAMBLE_FUEL_COST} Fuel")
            modal['trade_message'] = f"{tr('dialog', 'Need')} {', '.join(missing)} {tr('dialog', 'to Gamble!')}"
        else:
            deduct_player_currency(game.player, GAMBLE_CURRENCY_COST)
            consume_player_fuel_units(game.player, GAMBLE_FUEL_COST)

            generate_npc_trade_stock(npc, game=game, trade_type=selected_type, force=True)
            modal['trade_selected_index'] = -1
            type_lbl = tr('item_type', selected_type) if selected_type != 'Default' else tr('ui', 'Default')
            modal['trade_message'] = f"{tr('dialog', 'Gambled')} ({type_lbl})!"

            if hasattr(game, 'sound_manager'):
                game.sound_manager.play_sound('buy.ogg', subdir='ui', game=game, base_volume=0.6, is_critical=True)

    # ==============================================================
    # 4. BUY SQUARE PANEL (AT THE BOTTOM, BELOW GAMBLE)
    # ==============================================================
    buy_panel_y = gamble_panel_rect.bottom + 6
    bottom_panel_rect = pygame.Rect(start_x + 10, buy_panel_y, width - 20, buy_panel_h)
    
    pygame.draw.rect(surface, (25, 25, 25), bottom_panel_rect, border_radius=4)
    pygame.draw.rect(surface, GRAY_60, bottom_panel_rect, 1, border_radius=4)

    # A. Player Funds & Fuel
    funds_title = font_12.render(f"{tr('ui', 'Resources')}:", False, (170, 170, 170))
    funds_val = font_12.render(f"${player_money} | {player_fuel}F", False, GOLD)
    surface.blit(funds_title, (bottom_panel_rect.x + 12, bottom_panel_rect.y + 10))
    surface.blit(funds_val, (bottom_panel_rect.x + 12, bottom_panel_rect.y + 28))

    # B. Selected Item Info
    selected_item = None
    item_price = 0
    if 0 <= selected_index < len(tradable_items):
        selected_item = tradable_items[selected_index]
        item_price = get_unit_price(selected_item)

    if selected_item:
        item_name_str = tr('item', selected_item.name)
        if len(item_name_str) > 20:
            item_name_str = item_name_str[:18] + ".."
        sel_title = font_12.render(item_name_str, False, WHITE)

        is_stack = (
            hasattr(selected_item, 'is_stackable')
            and selected_item.is_stackable()
            and (getattr(selected_item, 'load', 1) or 1) > 1
        )
        suffix = " (ea)" if is_stack else ""
        price_str = f"{tr('ui', 'Price')}: ${item_price}{suffix}"
        price_color = GOLD if player_money >= item_price else RED
        sel_price = font_12.render(price_str, False, price_color)

        surface.blit(sel_title, (bottom_panel_rect.x + 155, bottom_panel_rect.y + 10))
        surface.blit(sel_price, (bottom_panel_rect.x + 155, bottom_panel_rect.y + 28))
    else:
        hint_surf = font_12.render(tr('dialog', "Select an item to buy"), False, GRAY)
        surface.blit(hint_surf, (bottom_panel_rect.x + 155, bottom_panel_rect.y + 20))

    # C. BUY Button
    buy_btn_w, buy_btn_h = 95, 34
    buy_btn_rect = pygame.Rect(
        bottom_panel_rect.right - buy_btn_w - 12,
        bottom_panel_rect.centery - (buy_btn_h // 2),
        buy_btn_w,
        buy_btn_h
    )

    can_buy = selected_item is not None and player_money >= item_price and not dd_open
    btn_hovered = buy_btn_rect.collidepoint(mouse_pos) and not dd_open

    if can_buy:
        btn_color = GREEN_HOVER if btn_hovered else DARK_GREEN
        text_color = WHITE
    else:
        btn_color = DISABLED_GRAY
        text_color = (130, 130, 130)

    pygame.draw.rect(surface, btn_color, buy_btn_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if can_buy and btn_hovered else GRAY_60, buy_btn_rect, 1, border_radius=4)

    buy_label = font_12.render(tr('dialog', "BUY"), True, text_color)
    surface.blit(buy_label, buy_label.get_rect(center=buy_btn_rect.center))

    # Handle Buy Click
    if mouse_just_pressed and buy_btn_rect.collidepoint(mouse_pos) and not dd_open:
        if not selected_item:
            modal['trade_message'] = tr('dialog', "Select an item first!")
        elif player_money < item_price:
            modal['trade_message'] = f"{tr('dialog', 'Not enough money! Need')} ${item_price}."
        else:
            can_fit = len(getattr(game.player, 'inventory', [])) < game.player.get_total_inventory_slots()
            if not can_fit:
                for inv_it in game.player.inventory:
                    if inv_it and hasattr(inv_it, 'can_stack_with') and inv_it.can_stack_with(selected_item):
                        avail = (inv_it.capacity or 100) - (inv_it.load or 1)
                        if avail >= 1:
                            can_fit = True
                            break

            if not can_fit:
                modal['trade_message'] = tr('dialog', "Your inventory is full!")
            else:
                if deduct_player_currency(game.player, item_price):
                    is_stackable = (
                        hasattr(selected_item, 'is_stackable')
                        and selected_item.is_stackable()
                        and (getattr(selected_item, 'load', 1) or 1) > 1
                    )
                    if is_stackable:
                        bought_unit = Item.create_from_name(selected_item.name, spawn_loot=False)
                        if bought_unit:
                            if hasattr(bought_unit, 'load'):
                                bought_unit.load = 1
                            if hasattr(selected_item, 'durability'):
                                bought_unit.durability = selected_item.durability
                            game.player.inventory.append(bought_unit)
                            if hasattr(game.player, 'stack_item_in_inventory'):
                                game.player.stack_item_in_inventory(bought_unit)

                        selected_item.load -= 1
                        if selected_item.load <= 0:
                            tradable_items.pop(selected_index)
                            modal['trade_selected_index'] = -1
                    else:
                        game.player.inventory.append(selected_item)
                        if hasattr(game.player, 'stack_item_in_inventory'):
                            game.player.stack_item_in_inventory(selected_item)
                        tradable_items.pop(selected_index)
                        modal['trade_selected_index'] = -1

                    modal['trade_message'] = f"{tr('dialog', 'Bought')} 1x {tr('item', selected_item.name)}!"
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_sound('buy.ogg', subdir='ui', game=game, base_volume=0.6, is_critical=True)

    # Status Message
    msg = modal.get('trade_message', '')
    if msg:
        msg_color = GREEN if 'Bought' in msg or 'Gambled' in msg else RED
        msg_surf = font_12.render(msg, True, msg_color)
        surface.blit(msg_surf, (start_x + 15, bottom_panel_rect.bottom + 2))

    # ==============================================================
    # 5. DROPDOWN POPUP OVERLAY (PROPER Z-INDEX & FIXED SCROLLBAR)
    # ==============================================================
    if dd_open:
        # Calculate popup boundaries
        popup_y = dd_btn_rect.top - popup_h - 2
        popup_rect = pygame.Rect(dd_btn_rect.x, popup_y, dd_btn_rect.width + 20, popup_h)
        modal['trade_type_dd_popup_rect'] = popup_rect

        # Draw popup background and outline
        pygame.draw.rect(surface, (20, 20, 20), popup_rect, border_radius=4)
        pygame.draw.rect(surface, WHITE, popup_rect, 1, border_radius=4)

        if 'trade_dd_scroll' not in modal:
            modal['trade_dd_scroll'] = 0

        max_dd_scroll = max(0, len(type_options) - max_vis)
        modal['trade_dd_max_scroll'] = max_dd_scroll

        needs_bar = len(type_options) > max_vis
        bar_w = 6 if needs_bar else 0
        opt_w = popup_rect.width - (bar_w + 4 if needs_bar else 0)

        # Isolated Scrollbar Track & Handle Rects with accurate proportional height
        dd_bar_rect = pygame.Rect(popup_rect.right - bar_w - 2, popup_rect.y + 2, bar_w, popup_h - 4) if needs_bar else None
        dd_handle_rect = None

        if needs_bar and dd_bar_rect:
            # FIXED: Correct ratio calculation (vis_count / total_options)
            visible_ratio = float(vis_count) / float(max(1, len(type_options)))
            handle_h = max(16, int(visible_ratio * dd_bar_rect.height))
            track_avail = max(1, dd_bar_rect.height - handle_h)

            # Handle Dragging & Clicking on the Scrollbar
            if mouse_just_pressed:
                if dd_bar_rect.collidepoint(mouse_pos):
                    modal['trade_dd_dragging'] = True
                    rel_y = mouse_pos[1] - dd_bar_rect.y - (handle_h // 2)
                    pct = max(0.0, min(1.0, rel_y / track_avail))
                    modal['trade_dd_scroll'] = int(round(pct * max_dd_scroll))

            if mouse_pressed and modal.get('trade_dd_dragging', False):
                rel_y = mouse_pos[1] - dd_bar_rect.y - (handle_h // 2)
                pct = max(0.0, min(1.0, rel_y / track_avail))
                modal['trade_dd_scroll'] = int(round(pct * max_dd_scroll))

            # Recalculate handle position based on active scroll
            dd_scroll = max(0, min(modal.get('trade_dd_scroll', 0), max_dd_scroll))
            modal['trade_dd_scroll'] = dd_scroll
            scroll_pct = dd_scroll / max(1, max_dd_scroll)
            handle_y = dd_bar_rect.y + int(scroll_pct * track_avail)
            dd_handle_rect = pygame.Rect(dd_bar_rect.x, handle_y, dd_bar_rect.width, handle_h)
        else:
            modal['trade_dd_scroll'] = 0
            dd_scroll = 0

        if not mouse_pressed:
            modal['trade_dd_dragging'] = False

        # Render Dropdown Options
        old_clip = surface.get_clip()
        clip_rect = pygame.Rect(popup_rect.x, popup_rect.y, opt_w, popup_h)
        surface.set_clip(clip_rect)

        clicked_new_type = None
        modal['trade_type_dd_opt_rects'] = []
        is_over_bar = dd_bar_rect.collidepoint(mouse_pos) if (needs_bar and dd_bar_rect) else False

        for idx in range(vis_count):
            opt_idx = idx + modal.get('trade_dd_scroll', 0)
            if opt_idx >= len(type_options):
                break
            t_opt = type_options[opt_idx]
            r_rect = pygame.Rect(popup_rect.x, popup_rect.y + (idx * opt_h), opt_w, opt_h)
            modal['trade_type_dd_opt_rects'].append((r_rect, t_opt))

            is_opt_hover = r_rect.collidepoint(mouse_pos) and not is_over_bar and not modal.get('trade_dd_dragging', False)
            if is_opt_hover:
                pygame.draw.rect(surface, (50, 50, 50), r_rect)
                if mouse_just_pressed:
                    clicked_new_type = t_opt

            t_disp = tr('item_type', t_opt) if t_opt != 'Default' else tr('ui', 'Default')
            if len(t_disp) > 16:
                t_disp = t_disp[:14] + ".."

            opt_color = YELLOW if t_opt == selected_type else WHITE
            t_surf = font_12.render(t_disp, False, opt_color)
            surface.blit(t_surf, (r_rect.x + 6, r_rect.centery - t_surf.get_height() // 2))

        surface.set_clip(old_clip)

        # Draw Scrollbar Track and Thumb cleanly bounded inside the popup
        if needs_bar and dd_bar_rect and dd_handle_rect:
            pygame.draw.rect(surface, (35, 35, 35), dd_bar_rect, border_radius=2)
            pygame.draw.rect(surface, (130, 130, 130), dd_handle_rect, border_radius=2)

        # Handle Selection and Closing
        if mouse_just_pressed and not is_dd_hover and not modal.get('trade_dd_dragging', False):
            if clicked_new_type:
                modal['trade_selected_type'] = clicked_new_type
                modal['trade_type_dd_open'] = False
                if hasattr(game, 'sound_manager'):
                    game.sound_manager.play_ui_hover()
            elif not popup_rect.collidepoint(mouse_pos):
                modal['trade_type_dd_open'] = False
    else:
        modal['trade_type_dd_popup_rect'] = None
        modal['trade_type_dd_opt_rects'] = []