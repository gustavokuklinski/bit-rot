# core/ui/crafting_common.py
import random
import pygame
from core.data.config import WHITE, GRAY, GREEN, RED, YELLOW, DARK_GRAY, TILE_SIZE, font_12
from core.data.localization import tr
from core.entities.item.item import Item
from core.messages import display_message
from core.ui.notifications import check_milestone_progress

def player_has_at_least_one_ingredient(player, game, recipe):
    """Checks if the player carries at least one required ingredient/target item in their own inventory/belt/gear."""
    locs = get_crafting_item_locations(player, game, include_nearby=False)
    player_items = [loc[2] for loc in locs if loc[2]]

    c_type = getattr(recipe, 'craft_type', 'create').lower()
    if c_type == 'repair':
        if any(it.name.lower() == recipe.output_name.lower() for it in player_items):
            return True

    for req in recipe.ingredients:
        valid_names = [n.lower() for n in req['names']]
        for it in player_items:
            if it.name.lower() in valid_names:
                qty = it.load if it.load is not None else 1
                if qty > 0:
                    return True
    return False

def calculate_max_crafts(player, game, recipe, nearby_containers=None):
    """Calculates maximum possible crafts based on player inventory, gear, belt, and nearby items."""
    if not player:
        return 0

    if not is_recipe_unlocked(recipe, player):
        return 0

    if not player_has_at_least_one_ingredient(player, game, recipe):
        return 0

    locs = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby_containers)
    search_items = [loc[2] for loc in locs if loc[2]]

    c_type = getattr(recipe, 'craft_type', 'create').lower()
    if c_type == 'repair':
        damaged = sum(1 for it in search_items if it.name == recipe.output_name and it.durability is not None and it.durability < it.max_durability)
        if damaged <= 0:
            return 0
        mat_limits = []
        for req in recipe.ingredients:
            if not req.get('destroy', True): continue
            needed = req['amount']
            valid_names = [n.lower() for n in req['names']]
            have = sum((it.load if it.load is not None else 1) for it in search_items if it.name.lower() in valid_names and it.name != recipe.output_name)
            mat_limits.append(have // needed if needed > 0 else 0)
        return min(damaged, min(mat_limits)) if mat_limits else min(damaged, 1)

    craft_limits = []
    for req in recipe.ingredients:
        needed = req['amount']
        if needed <= 0: continue
        valid_names = [n.lower() for n in req['names']]
        have = sum((it.load if it.load is not None else 1) for it in search_items if it.name.lower() in valid_names)

        # Tools/catalysts that are NOT destroyed (destroy="false") do not limit batch size
        if not req.get('destroy', True):
            if have < needed:
                return 0
            continue

        craft_limits.append(have // needed)

    return max(0, min(craft_limits)) if craft_limits else 1

def add_craft_results_to_player(player, game, recipe, count=1):
    """Adds crafted results to player, automatically stacking items of the same type."""
    created_items_log = []

    for res in recipe.results:
        base_chance = res.get('chance', 1.0)
        c_type = getattr(recipe, 'craft_type', 'create').lower()
        maint_level = player.progression.get_maintenance(player)
        maint_scale = min(10, maint_level) / 10.0
        effective_chance = (base_chance + (1.0 - base_chance) * maint_scale) if c_type == 'dismantle' else base_chance

        total_units = 0
        for _ in range(count):
            if effective_chance >= 1.0 or random.random() <= effective_chance:
                total_units += res['amount']

        if total_units <= 0:
            continue

        sample_name = random.choice(res['names'])
        dummy_item = Item.create_from_name(sample_name)
        if not dummy_item:
            continue

        is_stackable = dummy_item.is_stackable()
        unit_capacity = getattr(dummy_item, 'capacity', 100) or 100

        if is_stackable:
            remaining_to_give = total_units
            # 1. Fill existing matching stacks in inventory and belt
            for inv_item in list(player.inventory) + list(player.belt):
                if not inv_item or not inv_item.can_stack_with(dummy_item):
                    continue
                cap = getattr(inv_item, 'capacity', unit_capacity) or unit_capacity
                cur_load = getattr(inv_item, 'load', 1) or 1
                avail = max(0, cap - cur_load)
                if avail > 0:
                    transfer = min(avail, remaining_to_give)
                    inv_item.load = cur_load + transfer
                    remaining_to_give -= transfer
                    if remaining_to_give <= 0:
                        break

            # 2. Place remaining units into new inventory slots
            while remaining_to_give > 0:
                pack_load = min(remaining_to_give, unit_capacity)
                new_item = Item.create_from_name(sample_name)
                if not new_item:
                    break
                new_item.load = pack_load
                if len(player.inventory) < player.get_total_inventory_slots():
                    player.inventory.append(new_item)
                else:
                    new_item.x, new_item.y = player.x, player.y
                    new_item.rect.topleft = (new_item.x, new_item.y)
                    game.items_on_ground.append(new_item)
                remaining_to_give -= pack_load

        else:
            # Non-stackables: create unit by unit
            for _ in range(total_units):
                unit_item = Item.create_from_name(sample_name)
                if not unit_item:
                    continue
                if len(player.inventory) < player.get_total_inventory_slots():
                    player.inventory.append(unit_item)
                else:
                    unit_item.x, unit_item.y = player.x, player.y
                    unit_item.rect.topleft = (unit_item.x, unit_item.y)
                    game.items_on_ground.append(unit_item)

        log_name = getattr(recipe, 'output_name', None) or dummy_item.name
        created_items_log.append(f"{total_units}x {tr('item', log_name)}")

    if created_items_log:
        label = tr('msg', 'Dismantled into:') if getattr(recipe, 'craft_type', 'create') == 'dismantle' else tr('msg', 'Crafted:')
        display_message(f"{label} {', '.join(created_items_log)}")
    else:
        display_message(tr('msg', "Crafting yielded nothing."))

def prioritize_locations_for_craft(locs, preferred_id=None):
    """Prioritizes preferred items first, then nearby/ground items, then player inventory."""
    def sort_key(loc):
        if preferred_id and loc[2].id == preferred_id:
            return 0
        path = loc[4]
        is_nearby = bool(path and (path[0] == "Nearby" or path[0] == tr('ui', "Ground")))
        if is_nearby:
            return 1
        return 2
    return sorted(locs, key=sort_key)

def has_recipe_ingredients(player, game, recipe, include_nearby=True, count=1):
    if not player_has_at_least_one_ingredient(player, game, recipe):
        return False

    locs = get_crafting_item_locations(player, game, include_nearby=include_nearby)
    search_items = [loc[2] for loc in locs]
    
    for req in recipe.ingredients:
        is_destroyed = req.get('destroy', True)
        needed = req['amount'] * count if is_destroyed else req['amount']
        valid_names = req['names']
        have = sum((it.load if it.load is not None else 1)
                   for it in search_items
                   if it.name in valid_names)
        if have < needed:
            return False
    return True

def get_recipe_status_details(player, game, recipe, count=1):
    knows_magazine = bool(not recipe.magazine or recipe.magazine in player.known_recipes)
    missing_skills = []
    if recipe.req_level:
        for attr, lvl in recipe.req_level.items():
            p_lvl = player.progression.get_level(attr)
            if p_lvl < lvl:
                missing_skills.append((attr, p_lvl, lvl))

    if recipe.magazine:
        if recipe.req_level:
            is_unlocked = knows_magazine or (len(missing_skills) == 0)
        else:
            is_unlocked = knows_magazine
    elif recipe.req_level:
        is_unlocked = (len(missing_skills) == 0)
    else:
        is_unlocked = True

    missing_magazine = recipe.magazine if (recipe.magazine and not knows_magazine) else None

    has_on_player = player_has_at_least_one_ingredient(player, game, recipe)

    locs = get_crafting_item_locations(player, game, include_nearby=True)
    search_items = [loc[2] for loc in locs]
    missing_ingredients = []

    for req in recipe.ingredients:
        is_destroyed = req.get('destroy', True)
        needed = req['amount'] * count if is_destroyed else req['amount']
        valid_names = req['names']
        have = sum((it.load if it.load is not None else 1)
                   for it in search_items if it.name in valid_names)
        if have < needed:
            missing_ingredients.append({
                'name': valid_names[0],
                'have': int(have),
                'needed': int(needed)
            })

    can_craft = is_unlocked and (len(missing_ingredients) == 0) and has_on_player
    return can_craft, is_unlocked, missing_ingredients, missing_magazine, missing_skills

def draw_common_ingredients_grid(modal, recipe, details_x, ing_y, details_w, mouse_pos, click, nearby_containers, player_items, nearby_items, count=1):
    """Renders ingredients grid scaled by current craft count for consumed items only. Returns (can_craft, active_tooltip_ingredients, curr_y)."""
    surface = modal.surface
    lbl = font_12.render(tr('ui', "Required Ingredients:"), False, GRAY)
    surface.blit(lbl, (details_x, ing_y))

    curr_y = ing_y + 30
    col_width = details_w // 2
    can_craft = True
    active_tooltip_ingredients = None

    if not player_has_at_least_one_ingredient(modal.player, modal.game, recipe):
        can_craft = False

    for r_idx, req in enumerate(recipe.ingredients):
        # Tools with destroy="false" do NOT scale with craft count!
        is_destroyed = req.get('destroy', True)
        needed = req['amount'] * count if is_destroyed else req['amount']
        valid_names = req['names']

        have = sum((item.load if item.load is not None else 1)
                   for item in player_items if item.name in valid_names)
        if nearby_items:
            have += sum((item.load if item.load is not None else 1)
                        for item in nearby_items if item.name in valid_names)

        color = GREEN if have >= needed else RED
        if have < needed:
            can_craft = False

        primary_name = valid_names[0]
        img = modal.ingredient_images.get(primary_name)
        translated_name = tr('item', primary_name)
        name_display = translated_name

        is_right_col = (r_idx % 2 == 1)
        current_x = (details_x + 10 + col_width) if is_right_col else (details_x + 10)

        txt_str = f" {name_display}: {int(have)}/{needed}"
        text_width = font_12.render(txt_str, False, color).get_width()
        item_width = min((35 if img else 0) + text_width + 10, col_width - 15)

        row_rect = pygame.Rect(current_x, curr_y, item_width, 32)
        if row_rect.collidepoint(mouse_pos):
            active_tooltip_ingredients = valid_names
            pygame.draw.rect(surface, (50, 50, 50), row_rect, border_radius=3)

        draw_x = current_x
        if img:
            scaled_icon = pygame.transform.scale(img, (32, 32))
            surface.blit(scaled_icon, (draw_x, curr_y))
            draw_x += 35

        ing_surf = font_12.render(txt_str, False, color)
        surface.blit(ing_surf, (draw_x, curr_y + 8))

        if is_right_col:
            curr_y += 35

    return can_craft, active_tooltip_ingredients, curr_y

def draw_craft_action_footer(modal, recipe, details_x, details_y, details_w, list_h, can_craft, action_label, locked_label, on_execute, click, mouse_pos):
    """Draws quantity selector [ONE] [HALF] [ALL], time, skills, progress bar, and execution button."""
    surface = modal.surface
    btn_h = 40
    bottom_y = details_y + list_h
    btn_rect = pygame.Rect(details_x, bottom_y - btn_h, details_w, btn_h)

    # 1. Quantity Selector Bar directly above the execution button
    q_bar_h = 28
    q_bar_y = btn_rect.top - q_bar_h - 8
    element_cursor_y = q_bar_y - 8

    # Calculate max possible crafts (ignores destroy="false" tools)
    max_crafts = calculate_max_crafts(modal.player, modal.game, recipe)
    cur_count = getattr(modal, 'craft_count', modal.modal.get('craft_count', 1))
    cur_count = max(1, cur_count)

    # Controls coordinates
    lbl_qty = font_12.render(f"{tr('ui', 'Quantity')}:", False, WHITE)

    ctrl_x = details_x + lbl_qty.get_width() + 10
    btn_minus = pygame.Rect(ctrl_x, q_bar_y + 2, 26, 24)
    box_num = pygame.Rect(btn_minus.right + 4, q_bar_y + 2, 40, 24)
    btn_plus = pygame.Rect(box_num.right + 4, q_bar_y + 2, 26, 24)

    # Right buttons: [ ONE ] [ HALF ] [ ALL ]
    b_all_w = 46
    b_half_w = 54
    b_one_w = 46
    gap = 6

    btn_all = pygame.Rect(details_x + details_w - b_all_w, q_bar_y + 2, b_all_w, 24)
    btn_half = pygame.Rect(btn_all.left - b_half_w - gap, q_bar_y + 2, b_half_w, 24)
    btn_one = pygame.Rect(btn_half.left - b_one_w - gap, q_bar_y + 2, b_one_w, 24)

    # Process clicks immediately so the current frame renders the updated count
    if click and not modal.dropdown_state['active']:
        if btn_one.collidepoint(mouse_pos):
            cur_count = 1
            modal.craft_count = 1
            modal.modal['craft_count'] = 1
            if hasattr(modal.game, 'sound_manager'):
                modal.game.sound_manager.play_ui_hover()
        elif btn_half.collidepoint(mouse_pos):
            cur_count = max(1, max_crafts // 2) if max_crafts > 1 else 1
            modal.craft_count = cur_count
            modal.modal['craft_count'] = cur_count
            if hasattr(modal.game, 'sound_manager'):
                modal.game.sound_manager.play_ui_hover()
        elif btn_all.collidepoint(mouse_pos):
            cur_count = max(1, max_crafts) if max_crafts > 1 else 1
            modal.craft_count = cur_count
            modal.modal['craft_count'] = cur_count
            if hasattr(modal.game, 'sound_manager'):
                modal.game.sound_manager.play_ui_hover()
        elif btn_minus.collidepoint(mouse_pos):
            cur_count = max(1, cur_count - 1)
            modal.craft_count = cur_count
            modal.modal['craft_count'] = cur_count
            if hasattr(modal.game, 'sound_manager'):
                modal.game.sound_manager.play_ui_hover()
        elif btn_plus.collidepoint(mouse_pos):
            cur_count = min(max_crafts if max_crafts > 0 else 99, cur_count + 1)
            modal.craft_count = cur_count
            modal.modal['craft_count'] = cur_count
            if hasattr(modal.game, 'sound_manager'):
                modal.game.sound_manager.play_ui_hover()

    # Draw quantity controls
    surface.blit(lbl_qty, (details_x, q_bar_y + 7))

    def _draw_ctrl_btn(rect, text, is_active=False):
        hover = rect.collidepoint(mouse_pos)
        bg = (70, 70, 70) if hover else ((55, 55, 55) if is_active else (35, 35, 35))
        pygame.draw.rect(surface, bg, rect, border_radius=3)
        pygame.draw.rect(surface, YELLOW if hover or is_active else (100, 100, 100), rect, 1, border_radius=3)
        ts = font_12.render(text, False, YELLOW if hover or is_active else WHITE)
        surface.blit(ts, ts.get_rect(center=rect.center))

    _draw_ctrl_btn(btn_minus, "-")
    pygame.draw.rect(surface, (20, 20, 20), box_num, border_radius=3)
    pygame.draw.rect(surface, WHITE, box_num, 1, border_radius=3)
    cnt_surf = font_12.render(str(cur_count), False, YELLOW)
    surface.blit(cnt_surf, cnt_surf.get_rect(center=box_num.center))
    _draw_ctrl_btn(btn_plus, "+")

    _draw_ctrl_btn(btn_one, "ONE", is_active=(cur_count == 1))
    _draw_ctrl_btn(btn_half, "HALF", is_active=(max_crafts > 1 and cur_count == max(1, max_crafts // 2)))
    _draw_ctrl_btn(btn_all, "ALL", is_active=(max_crafts > 1 and cur_count == max_crafts))

    # Progress bar
    if modal.player.action_timer > 0 and modal.player.action_total_time > 0:
        bar_h = 10
        pygame.draw.rect(surface, (30, 30, 30), (details_x, element_cursor_y - bar_h, details_w, bar_h))
        progress = 1.0 - (modal.player.action_timer / modal.player.action_total_time)
        fill_w = int(details_w * progress)
        pygame.draw.rect(surface, GREEN, (details_x, element_cursor_y - bar_h, fill_w, bar_h))
        element_cursor_y -= (bar_h + 10)

    # Unlock condition verification
    is_unlocked = True
    knows_magazine = bool(not recipe.magazine or recipe.magazine in modal.player.known_recipes)
    skills_met = modal._check_skill_reqs(recipe)

    if recipe.magazine:
        if recipe.req_level and not knows_magazine and not skills_met:
            is_unlocked = False
        elif not recipe.req_level and not knows_magazine:
            is_unlocked = False
    elif recipe.req_level and not skills_met:
        is_unlocked = False

    if not is_unlocked:
        can_craft = False

    # Render Skills Requirements
    if recipe.req_level:
        element_cursor_y -= 25
        head_txt = tr('ui', "OR Skills:") if recipe.magazine else tr('ui', "Requires Skills:")
        head_surf = font_12.render(head_txt, False, WHITE)
        surface.blit(head_surf, (details_x, element_cursor_y))
        current_skill_x = details_x + head_surf.get_width() + 10
        items = list(recipe.req_level.items())
        for idx, (attr, lvl) in enumerate(items):
            attr_name_tr = tr('ui', attr.replace('_', ' ').capitalize())
            p_lvl = modal.player.progression.get_level(attr)
            s_color = GREEN if p_lvl >= lvl else RED
            s_surf = font_12.render(f"{attr_name_tr}: {p_lvl}/{int(lvl)}", False, s_color)
            surface.blit(s_surf, (current_skill_x, element_cursor_y))
            current_skill_x += s_surf.get_width()
            if idx < len(items) - 1:
                sep_surf = font_12.render(" - ", False, GRAY)
                surface.blit(sep_surf, (current_skill_x, element_cursor_y))
                current_skill_x += sep_surf.get_width()

    # Render Magazine Requirement
    if recipe.magazine:
        mag_color = GREEN if knows_magazine else RED
        mag_surf = font_12.render(f"{tr('ui', 'Requires Magazine:')} {tr('item', recipe.magazine)}", False, mag_color)
        element_cursor_y -= 20
        surface.blit(mag_surf, (details_x, element_cursor_y))
        element_cursor_y -= 5

    # Total Crafting Time (multiplied by count)
    total_time = round(recipe.time_required * cur_count, 1)
    if cur_count > 1:
        time_text = f"{tr('ui', 'Time:')} {total_time}s ({recipe.time_required}s ea)"
    else:
        time_text = f"{tr('ui', 'Time:')} {recipe.time_required}s"
    time_surf = font_12.render(time_text, False, GRAY)
    element_cursor_y -= 20
    surface.blit(time_surf, (details_x, element_cursor_y))

    # Warnings
    if modal.warning_message:
        warn_surf = font_12.render(modal.warning_message, False, RED)
        element_cursor_y -= 20
        surface.blit(warn_surf, (details_x, element_cursor_y))

    # Main Execution Button
    btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
    border_color = WHITE if can_craft else GRAY
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=5)
    pygame.draw.rect(surface, border_color, btn_rect, 1, border_radius=5)

    if not is_unlocked:
        btn_text = tr('ui', locked_label)
    elif not player_has_at_least_one_ingredient(modal.player, modal.game, recipe):
        btn_text = tr('ui', "NEED ITEM IN INVENTORY")
        can_craft = False
    elif can_craft:
        suffix = f" x{cur_count}" if cur_count > 1 else ""
        btn_text = f"{tr('ui', action_label)}{suffix}"
    else:
        btn_text = tr('ui', "MISSING RESOURCES")

    lbl = font_12.render(btn_text, True, WHITE if can_craft else GRAY)
    surface.blit(lbl, lbl.get_rect(center=btn_rect.center))

    if can_craft and click and not modal.dropdown_state['active']:
        if btn_rect.collidepoint(mouse_pos):
            on_execute(recipe, cur_count)

def execute_recipe_craft(game, recipe, player=None, count=1, preferred_item_id=None):
    """Executes a craft action for `count` batches, using Nearby items first and auto-stacking output."""
    if player is None:
        player = game.player
    if not player or player.action_timer > 0:
        return

    count = max(1, int(count))

    if not is_recipe_unlocked(recipe, player):
        display_message(tr('msg', "You haven't unlocked this recipe yet."))
        return

    if not player_has_at_least_one_ingredient(player, game, recipe):
        display_message(tr('msg', "At least one required item must be in your inventory."))
        return

    nearby = game.find_nearby_containers()
    if not has_recipe_ingredients(player, game, recipe, include_nearby=True, count=count):
        display_message(tr('msg', "Missing required ingredients."))
        return

    locations = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby)
    locations = prioritize_locations_for_craft(locations, preferred_id=preferred_item_id)

    for req in recipe.ingredients:
        if not req.get('destroy', True):
            continue
        for _, _, it, _, _ in locations:
            if it.name in req['names'] and hasattr(it, 'inventory') and it.inventory:
                display_message(f"{tr('msg', 'Cannot use')} {tr('item', it.name)}: {tr('msg', 'It contains items!')}")
                return

    craft_type = getattr(recipe, 'craft_type', 'create').lower()
    if craft_type == 'dismantle':
        action_sound = 'dismantle.ogg'
    elif craft_type == 'repair':
        action_sound = 'repair.ogg'
    else:
        action_sound = 'craft.ogg'

    total_time = round(recipe.time_required * count, 1)

    def craft_complete():
        nearby_now = game.find_nearby_containers()

        if craft_type == 'dismantle':
            check_milestone_progress(game, 'craft_dismantle', 'item')
        elif craft_type == 'repair':
            check_milestone_progress(game, 'craft_repair', 'item')
        else:
            check_milestone_progress(game, 'craft_craft', 'item')

        if recipe.gain_xp:
            for attr, amount in recipe.gain_xp.items():
                if hasattr(player.progression, 'add_xp'):
                    player.progression.add_xp(player, attr, amount * count)

        total_repair_amount = 0
        target_repair_item = None
        if craft_type == 'repair':
            locs_now = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby_now)
            locs_now = prioritize_locations_for_craft(locs_now, preferred_id=preferred_item_id)
            for container, key, it, ctype, _ in locs_now:
                if it.name.lower() == recipe.output_name.lower() and it.durability is not None and it.durability < it.max_durability:
                    target_repair_item = it
                    break
            if not target_repair_item:
                display_message(f"{tr('msg', 'No damaged')} {tr('item', recipe.output_name)} {tr('msg', 'found.')}")
                return

        maint_level = player.progression.get_maintenance(player)
        maint_scale = min(10, maint_level) / 10.0

        # Deduct ingredients prioritizing Nearby / Ground items first
        for req in recipe.ingredients:
            if not req.get('destroy', True):
                continue
            to_remove = req['amount'] * count
            valid_names = req['names']
            removed = 0

            locs_now = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby_now)
            locs_now = prioritize_locations_for_craft(locs_now, preferred_id=preferred_item_id)

            for container, key, it, ctype, _ in locs_now:
                if removed >= to_remove:
                    break
                if any(it.name.lower() == vn.lower() for vn in valid_names) and it != target_repair_item:
                    has_item_load = (it.load is not None)
                    item_qty = it.load if has_item_load else 1
                    take = min(to_remove - removed, item_qty)

                    if craft_type == 'repair':
                        if getattr(it, 'min_restore', None) is not None and getattr(it, 'max_restore', None) is not None:
                            effective_min = it.min_restore + (it.max_restore - it.min_restore) * maint_scale
                            restore_per_unit = random.randint(int(effective_min), int(it.max_restore))
                            total_repair_amount += (restore_per_unit * take)

                    if has_item_load:
                        it.load -= take
                    removed += take

                    if (has_item_load and it.load <= 0) or (not has_item_load and take > 0):
                        if ctype == 'list':
                            if it in container:
                                container.remove(it)
                            elif key < len(container):
                                container.pop(key)
                        elif ctype == 'fixed_list':
                            container[key] = None
                        elif ctype == 'dict':
                            container[key] = None
                        elif ctype == 'attr':
                            setattr(container, key, None)

                    if removed >= to_remove:
                        break

        if craft_type == 'repair' and target_repair_item:
            if total_repair_amount <= 0:
                total_repair_amount = target_repair_item.max_durability - target_repair_item.durability

            old_durability = target_repair_item.durability
            target_repair_item.durability = min(target_repair_item.max_durability, target_repair_item.durability + total_repair_amount)
            restored = target_repair_item.durability - old_durability
            display_message(f"{tr('msg', 'Repaired')} {tr('item', target_repair_item.name)} {tr('msg', 'by')} {int(restored)} {tr('msg', 'points.')}")
        else:
            # Give results and auto-stack
            add_craft_results_to_player(player, game, recipe, count=count)

    if craft_type == 'dismantle':
        action_label = f"{tr('ui', 'Dismantling')} {tr('item', recipe.output_name)}"
    elif craft_type == 'repair':
        action_label = f"{tr('ui', 'Repairing')} {tr('item', recipe.output_name)}"
    else:
        action_label = f"{tr('ui', 'Crafting')} {tr('item', recipe.output_name)}"
    if count > 1:
        action_label += f" x{count}"

    player.start_action(
        action_label,
        total_time,
        craft_complete,
        cancel_on_move=True,
        action_sound=action_sound,
        action_sound_subdir='craft'
    )

def get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=None, exclude_equipped=False):
    """Gathers all item locations across player inventory, belt, clothes, nearby containers,
    and items dropped on the ground within 1 tile of the player.
    """
    locations = []
    seen_item_ids = set()
    
    def extract_list(container_list, path):
        for i in range(len(container_list) - 1, -1, -1):
            it = container_list[i]
            if it and id(it) not in seen_item_ids:
                seen_item_ids.add(id(it))
                locations.append((container_list, i, it, 'list', path))
                if hasattr(it, 'inventory') and it.inventory:
                    extract_list(it.inventory, path + [tr('item', it.name)])

    extract_list(player.inventory, ["Inventory"])

    if not exclude_equipped:
        for i in range(len(player.belt) - 1, -1, -1):
            it = player.belt[i]
            if it and id(it) not in seen_item_ids:
                seen_item_ids.add(id(it))
                locations.append((player.belt, i, it, 'fixed_list', ["Belt"]))
                if hasattr(it, 'inventory') and it.inventory:
                    extract_list(it.inventory, ["Belt", tr('item', it.name)])
                    
        protected_slots = ['arms', 'legs', 'body', 'feet', 'hands']
        for k in list(player.clothes.keys()):
            it = player.clothes[k]
            if it and id(it) not in seen_item_ids:
                if str(k).lower() not in protected_slots:
                    seen_item_ids.add(id(it))
                    locations.append((player.clothes, k, it, 'dict', ["Gear", str(k).capitalize()]))
                if hasattr(it, 'inventory') and it.inventory:
                    extract_list(it.inventory, ["Gear", str(k).capitalize(), tr('item', it.name)])
    
    if include_nearby and game:
        # 1. Nearby container contents
        if nearby_containers is None:
            nearby_containers = game.find_nearby_containers()
        if nearby_containers:
            for obj in nearby_containers:
                if hasattr(obj, 'inventory') and obj.inventory:
                    obj_name = getattr(obj, 'name', 'Ground')
                    extract_list(obj.inventory, ["Nearby", obj_name])
                    
        # 2. Loose ground dropped items within 1 tile (TILE_SIZE * 1.5) of the player
        if hasattr(game, 'items_on_ground') and player and hasattr(player, 'rect'):
            p_rect = player.rect
            for i in range(len(game.items_on_ground) - 1, -1, -1):
                it = game.items_on_ground[i]
                if not it or getattr(it, 'type', '') == 'animal' or getattr(it, 'item_type', '') == 'vehicle':
                    continue
                if id(it) in seen_item_ids:
                    continue
                if hasattr(it, 'rect'):
                    dx = p_rect.centerx - it.rect.centerx
                    dy = p_rect.centery - it.rect.centery
                    if (dx * dx + dy * dy) <= (TILE_SIZE * 1.5) ** 2:
                        seen_item_ids.add(id(it))
                        locations.append((game.items_on_ground, i, it, 'list', [tr('ui', "Ground")]))
                        if hasattr(it, 'inventory') and it.inventory:
                            extract_list(it.inventory, [tr('ui', "Ground"), tr('item', it.name)])
                    
    return locations

def is_recipe_unlocked(recipe, player):
    """Checks whether the player has the required skill levels and magazines for a recipe."""
    knows_magazine = bool(not recipe.magazine or recipe.magazine in player.known_recipes)
    skills_met = True
    if recipe.req_level:
        for attr, lvl in recipe.req_level.items():
            if player.progression.get_level(attr) < lvl:
                skills_met = False
                break
    if recipe.magazine:
        if recipe.req_level:
            return knows_magazine or skills_met
        return knows_magazine
    elif recipe.req_level:
        return skills_met
    return True

def is_recipe_relevant_to_item(recipe, item_name):
    """Filters recipes relevant to the clicked item based on craft type:
    - 'create' / 'craft': Item MUST be an ingredient (you craft something USING this item).
    - 'repair': Item is the target being repaired, OR a repair material/ingredient.
    - 'dismantle': Item is the object being dismantled (an ingredient).
    """
    if not item_name:
        return False
        
    item_low = item_name.lower().strip()
    c_type = getattr(recipe, 'craft_type', 'create').lower()

    is_ingredient = False
    for ing in recipe.ingredients:
        if any(item_low == n.lower().strip() for n in ing.get('names', [])):
            is_ingredient = True
            break

    if c_type == 'repair':
        return (recipe.output_name.lower().strip() == item_low) or is_ingredient
    elif c_type == 'dismantle':
        return is_ingredient or (item_low in recipe.output_name.lower())
    else:
        return is_ingredient