# core/ui/npc_trade_tab.py

import pygame
import random
from core.data.config import *
from core.data.localization import tr
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.ui.modals import draw_scrollbar

# Visual Design Constants
DARK_GREEN = (0, 120, 0)
GREEN_HOVER = (50, 205, 50)
GOLD = (255, 215, 0)
DISABLED_GRAY = (60, 60, 60)

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

    # Scan order: Top-level inventory -> Belt -> Clothes/Gear & nested containers
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
        weight = getattr(item, 'weight', 0.01) or 0.01
        return max(1, int(weight * 80))

    if itype == 'weapon_ranged':
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

get_total_price = get_unit_price

def generate_npc_trade_stock(npc, game=None):
    if getattr(npc, 'trade_stock_generated', False) and hasattr(npc, 'trade_stock') and npc.trade_stock:
        return

    trade_cfg = getattr(npc, 'trade_config', None)
    limit = 15
    allowed_types = []
    allowed_items = []

    if trade_cfg:
        limit = trade_cfg.get('limit', 15)
        allowed_types = trade_cfg.get('types', [])
        allowed_items = trade_cfg.get('items', [])

    # Seed RNG deterministically per NPC so re-entering the tab preserves stock
    seed_val = hash(getattr(npc, 'id', npc.name))
    rng = random.Random(seed_val)

    # Calculate Player Luck Level for probability weighting
    lucky_level = 0.0
    if game and hasattr(game, 'player') and game.player and hasattr(game.player, 'progression'):
        lucky_level = float(game.player.progression.get_lucky(game.player))

    candidates = []
    weights = []

    for name, tmpl in ITEM_TEMPLATES.items():
        if name.startswith("Empty ") or name.endswith(" on"):
            continue
        itype = tmpl.get('type', '')

        # Filter by trade_config if present
        if trade_cfg:
            match_type = bool(allowed_types and itype in allowed_types)
            match_name = bool(allowed_items and (name in allowed_items or tmpl.get('name') in allowed_items))
            if not (match_type or match_name):
                continue
        else:
            # Fallback for NPCs without a <trade> node
            if itype not in ['consumable_food', 'consumable_medication', 'consumable_ammo', 'weapon_ranged', 'weapon_melee', 'resource']:
                continue

        base_chance = float(tmpl.get('spawn_chance', 1.0))
        if base_chance <= 0:
            base_chance = 0.2

        # --- LUCK-BASED PROBABILITY MODIFIER ---
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
        # Pick without replacement if pool is large enough to ensure unique stock
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

        # If pool was smaller than limit, fill remaining slots with replacement
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
                # Weapons bought ALWAYS without ammo and with FULL durability
                if hasattr(new_item, 'load'):
                    new_item.load = 0
                max_dur = getattr(new_item, 'max_durability', 100) or 100
                new_item.durability = max_dur
            else:
                # Stackables (ammo, food, meds, drugs)
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
    generate_npc_trade_stock(npc, game)

    mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]
    prev_pressed = modal.get('trade_last_mouse_pressed', False)
    mouse_just_pressed = mouse_pressed and not prev_pressed
    modal['trade_last_mouse_pressed'] = mouse_pressed

    tradable_items = getattr(npc, 'trade_stock', [])

    slot_size, padding = 52, 8
    header_h = 30
    bottom_bar_h = 75
    content_h = height - header_h - bottom_bar_h - 10

    scroll_y = modal.get('scroll_offset_y', 0)

    # Section Title
    title_str = f"{tr('dialog', 'NPC Trade Shop')}"
    title_surf = font_12.render(title_str, True, WHITE)
    surface.blit(title_surf, (start_x + (width - title_surf.get_width()) // 2, start_y))

    # Grid calculations (5 columns x 3 rows for 15 items)
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
        empty_surf = font_12.render(tr('dialog', 'This NPC is sold out.'), True, GRAY)
        clip_surf.blit(empty_surf, ((item_area_rect.width - empty_surf.get_width()) // 2, 30))
    else:
        for i, item in enumerate(tradable_items):
            row, col = i // cols, i % cols
            lx = grid_start_x_relative + col * (slot_size + padding)
            ly = row * (slot_size + padding) - scroll_y

            slot_rect_abs = pygame.Rect(
                grid_start_x_absolute + col * (slot_size + padding),
                start_y + header_h + row * (slot_size + padding) - scroll_y,
                slot_size, slot_size
            )

            is_hovered = slot_rect_abs.collidepoint(mouse_pos)

            if is_hovered and mouse_just_pressed:
                modal['trade_selected_index'] = i
                modal['trade_message'] = ""

            if -slot_size < ly < content_h:
                slot_rect_rel = pygame.Rect(lx, ly, slot_size, slot_size)

                if item_area_rect.collidepoint(slot_rect_abs.center):
                    modal['trade_slot_rects'].append({'rect': slot_rect_abs, 'index': i, 'item': item})

                # Background & Border
                pygame.draw.rect(clip_surf, GRAY_40, slot_rect_rel, 0, 3)
                if i == selected_index:
                    pygame.draw.rect(clip_surf, GREEN, slot_rect_rel, 2, 3)
                elif is_hovered:
                    pygame.draw.rect(clip_surf, WHITE, slot_rect_rel, 1, 3)
                else:
                    pygame.draw.rect(clip_surf, GRAY_60, slot_rect_rel, 1, 3)

                # 1. Item Sprite
                if item and getattr(item, 'image', None):
                    scaled_img = pygame.transform.scale(item.image, (slot_size - 8, slot_size - 8))
                    clip_surf.blit(scaled_img, (lx + 4, ly + 4))
                elif item and hasattr(item, 'color'):
                    pygame.draw.rect(clip_surf, item.color, slot_rect_rel.inflate(-8, -8))

                # 2. Stack Count / Ammo Load
                if hasattr(item, 'is_stackable') and item.is_stackable() and getattr(item, 'load', 0) > 1:
                    qty_text = font_12.render(str(int(item.load)), True, WHITE)
                    clip_surf.blit(qty_text, (slot_rect_rel.right - qty_text.get_width() - 3, slot_rect_rel.bottom - qty_text.get_height() - 2))

                # 3. Price Tag (Single unit cost in gold with dark drop shadow)
                price = get_unit_price(item)
                p_shadow = font_12.render(f"${price}", True, BLACK)
                p_text = font_12.render(f"${price}", True, GOLD)
                clip_surf.blit(p_shadow, (lx + 3, ly + 3))
                clip_surf.blit(p_text, (lx + 2, ly + 2))

                # 4. Durability Bar (Full for weapons)
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

    bar_rect = pygame.Rect(item_area_rect.right - 10, item_area_rect.y, 8, item_area_rect.height)
    draw_scrollbar(surface, modal, bar_rect, item_area_rect.height, total_grid_h, scroll_y)

    # ==========================================
    # --- CURRENCY-ONLY BOTTOM BAR ---
    # ==========================================
    bottom_y_absolute = start_y + height - bottom_bar_h - 5
    bottom_panel_rect = pygame.Rect(start_x + 10, bottom_y_absolute, width - 20, bottom_bar_h)
    pygame.draw.rect(surface, (25, 25, 25), bottom_panel_rect, border_radius=5)
    pygame.draw.rect(surface, GRAY_60, bottom_panel_rect, 1, border_radius=5)

    player_money = get_player_total_currency(game.player)

    # 1. Player Funds (Left side)
    funds_title = font_12.render(f"{tr('ui', 'Your Funds')}:", False, (180, 180, 180))
    funds_val = font_12.render(f"${player_money}", False, GOLD)
    surface.blit(funds_title, (bottom_panel_rect.x + 15, bottom_panel_rect.y + 12))
    surface.blit(funds_val, (bottom_panel_rect.x + 15, bottom_panel_rect.y + 32))

    # 2. Selected Item & Unit Price (Center)
    selected_item = None
    item_price = 0
    if 0 <= selected_index < len(tradable_items):
        selected_item = tradable_items[selected_index]
        item_price = get_unit_price(selected_item)

    if selected_item:
        item_name_str = tr('item', selected_item.name)
        if len(item_name_str) > 22:
            item_name_str = item_name_str[:20] + "..."
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

        surface.blit(sel_title, (bottom_panel_rect.x + 150, bottom_panel_rect.y + 12))
        surface.blit(sel_price, (bottom_panel_rect.x + 150, bottom_panel_rect.y + 32))
    else:
        hint_surf = font_12.render(tr('dialog', "Select an item to buy"), False, GRAY)
        surface.blit(hint_surf, (bottom_panel_rect.x + 150, bottom_panel_rect.y + 24))

    # 3. BUY Button (Right side)
    buy_btn_w, buy_btn_h = 100, 36
    buy_btn_rect = pygame.Rect(
        bottom_panel_rect.right - buy_btn_w - 15,
        bottom_panel_rect.centery - (buy_btn_h // 2),
        buy_btn_w,
        buy_btn_h
    )

    can_buy = selected_item is not None and player_money >= item_price
    btn_hovered = buy_btn_rect.collidepoint(mouse_pos)

    if can_buy:
        btn_color = GREEN_HOVER if btn_hovered else DARK_GREEN
        text_color = WHITE
    else:
        btn_color = DISABLED_GRAY
        text_color = (130, 130, 130)

    pygame.draw.rect(surface, btn_color, buy_btn_rect, border_radius=5)
    pygame.draw.rect(surface, WHITE if can_buy and btn_hovered else GRAY_60, buy_btn_rect, 1, border_radius=5)

    buy_label = font_12.render(tr('dialog', "BUY"), True, text_color)
    surface.blit(buy_label, buy_label.get_rect(center=buy_btn_rect.center))

    # 4. Handle Purchase Click
    if mouse_just_pressed and buy_btn_rect.collidepoint(mouse_pos):
        if not selected_item:
            modal['trade_message'] = tr('dialog', "Select an item first!")
        elif player_money < item_price:
            modal['trade_message'] = f"{tr('dialog', 'Not enough money! Need')} ${item_price}."
        else:
            is_stackable = (
                hasattr(selected_item, 'is_stackable')
                and selected_item.is_stackable()
                and (getattr(selected_item, 'load', 1) or 1) > 1
            )

            # Check if player inventory can receive 1 unit
            can_fit = len(getattr(game.player, 'inventory', [])) < game.player.get_total_inventory_slots()
            if not can_fit:
                for inv_it in game.player.inventory:
                    if inv_it and hasattr(inv_it, 'can_stack_with') and inv_it.can_stack_with(selected_item):
                        avail = (inv_it.capacity or 100) - (inv_it.load or 1)
                        if avail >= 1:
                            can_fit = True
                            break
            if not can_fit:
                rem_check = item_price
                for inv_it in reversed(game.player.inventory):
                    if inv_it and is_currency(inv_it):
                        l = int(getattr(inv_it, 'load', 1) or 1)
                        if rem_check >= l:
                            can_fit = True
                            break
                        rem_check -= l

            if not can_fit:
                modal['trade_message'] = tr('dialog', "Your inventory is full!")
            else:
                if deduct_player_currency(game.player, item_price):
                    if is_stackable:
                        # Buy 1 unit from the stack
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

                        modal['trade_message'] = f"{tr('dialog', 'Bought')} 1x {tr('item', selected_item.name)}!"
                    else:
                        # Non-stackable item or last remaining unit
                        game.player.inventory.append(selected_item)
                        if hasattr(game.player, 'stack_item_in_inventory'):
                            game.player.stack_item_in_inventory(selected_item)

                        tradable_items.pop(selected_index)
                        modal['trade_selected_index'] = -1
                        modal['trade_message'] = f"{tr('dialog', 'Bought')} {tr('item', selected_item.name)}!"

                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_sound('buy.ogg', subdir='ui', game=game, base_volume=0.6, is_critical=True)

    # 5. Status Feedback Message
    msg = modal.get('trade_message', '')
    if msg:
        msg_color = GREEN if 'Bought' in msg or 'success' in msg.lower() else RED
        msg_surf = font_12.render(msg, True, msg_color)
        surface.blit(msg_surf, (start_x + 15, bottom_panel_rect.bottom + 2))