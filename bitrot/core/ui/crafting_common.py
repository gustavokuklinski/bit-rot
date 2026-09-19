# core/ui/crafting_common.py
import random
import pygame
from core.data.config import WHITE, GRAY, GREEN, RED, TILE_SIZE, font_12
from core.data.localization import tr
from core.entities.item.item import Item
from core.messages import display_message
from core.ui.notifications import check_milestone_progress

def draw_common_ingredients_grid(modal, recipe, details_x, ing_y, details_w, mouse_pos, click, nearby_containers, player_items, nearby_items):
    """Renders the standard 2-column ingredients grid and handles item dropdown activation.
    Returns (can_craft, active_tooltip_ingredients, curr_y).
    """
    surface = modal.surface
    lbl = font_12.render(tr('ui', "Required Ingredients:"), False, GRAY)
    surface.blit(lbl, (details_x, ing_y))

    curr_y = ing_y + 30
    col_width = details_w // 2
    can_craft = True
    active_tooltip_ingredients = None

    for r_idx, req in enumerate(recipe.ingredients):
        needed = req['amount']
        valid_names = req['names']

        have = sum((item.load if (item.load is not None and item.is_stackable()) else 1)
                   for item in player_items if item.name in valid_names)
        if nearby_items:
            have += sum((item.load if (item.load is not None and item.is_stackable()) else 1)
                        for item in nearby_items if item.name in valid_names)

        color = GREEN if have >= needed else RED
        if have < needed:
            can_craft = False

        primary_name = valid_names[0]
        img = modal.ingredient_images.get(primary_name)
        translated_name = tr('item', primary_name)
        name_display = translated_name if len(valid_names) == 1 else f"{translated_name}"

        sel_id = modal.selected_ingredients.get(r_idx)
        if sel_id:
            locs = modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
            for _, _, item, _, _ in locs:
                if item.id == sel_id:
                    name_display = f"[*] {tr('item', item.name)}"
                    img = item.image
                    break

        is_right_col = (r_idx % 2 == 1)
        current_x = (details_x + 10 + col_width) if is_right_col else (details_x + 10)

        txt_str = f" {name_display}: {int(have)}/{needed}"
        text_width = font_12.render(txt_str, False, color).get_width()
        item_width = min((35 if img else 0) + text_width + 10, col_width - 15)

        row_rect = pygame.Rect(current_x, curr_y, item_width, 32)
        if row_rect.collidepoint(mouse_pos):
            active_tooltip_ingredients = valid_names
            color = (min(255, color[0] + 50), min(255, color[1] + 50), min(255, color[2] + 50))
            pygame.draw.rect(surface, (50, 50, 50), row_rect, border_radius=3)

            if click and not modal.dropdown_state['active']:
                opts, itms = [], []
                locs = modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers, exclude_equipped=True)
                for _, _, item, _, path in locs:
                    if item.name in valid_names:
                        qty = item.load if item.is_stackable() else f"Dur: {int(item.durability or 0)}"
                        opts.append(f"{tr('item', item.name)} ({qty}) - {' > '.join(path)}")
                        itms.append(item.id)
                if opts:
                    modal.dropdown_state.update({
                        'active': True, 'options': opts, 'items': itms,
                        'req_idx': r_idx, 'position': mouse_pos
                    })

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
    """Draws skill/magazine requirements, timers, action progress, and main execution button."""
    surface = modal.surface
    btn_h = 40
    bottom_y = details_y + list_h
    btn_rect = pygame.Rect(details_x, bottom_y - btn_h, details_w, btn_h)
    element_cursor_y = btn_rect.top - 5

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

    # Render Skill Requirements
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

    # Crafting Time
    time_surf = font_12.render(f"{tr('ui', 'Time:')} {recipe.time_required}s", False, GRAY)
    element_cursor_y -= 20
    surface.blit(time_surf, (details_x, element_cursor_y))

    # Warnings
    if modal.warning_message:
        warn_surf = font_12.render(modal.warning_message, False, RED)
        element_cursor_y -= 20
        surface.blit(warn_surf, (details_x, element_cursor_y))

    # Execution Button
    btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
    border_color = WHITE if can_craft else GRAY
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=5)
    pygame.draw.rect(surface, border_color, btn_rect, 1, border_radius=5)

    if not is_unlocked:
        btn_text = tr('ui', locked_label)
    elif can_craft:
        btn_text = tr('ui', action_label)
    else:
        btn_text = tr('ui', "MISSING RESOURCES")

    lbl = font_12.render(btn_text, True, WHITE if can_craft else GRAY)
    surface.blit(lbl, lbl.get_rect(center=btn_rect.center))

    if can_craft and click and not modal.dropdown_state['active']:
        if btn_rect.collidepoint(mouse_pos):
            on_execute(recipe)

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

def has_recipe_ingredients(player, game, recipe, include_nearby=True):
    """Checks if the player (and nearby ground/containers) has all required ingredients."""
    locs = get_crafting_item_locations(player, game, include_nearby=include_nearby)
    search_items = [loc[2] for loc in locs]
    
    for req in recipe.ingredients:
        needed = req['amount']
        valid_names = req['names']
        have = sum((it.load if (it.load is not None and it.is_stackable()) else 1)
                   for it in search_items
                   if it.name in valid_names)
        if have < needed:
            return False
    return True

def execute_recipe_craft(game, recipe, player=None):
    """Executes a craft action (timed progress bar, consumption, and result creation)."""
    if player is None:
        player = game.player
    if not player or player.action_timer > 0:
        return

    if not is_recipe_unlocked(recipe, player):
        display_message(tr('msg', "You haven't unlocked this recipe yet."))
        return

    nearby = game.find_nearby_containers()
    if not has_recipe_ingredients(player, game, recipe, include_nearby=True):
        display_message(tr('msg', "Missing required ingredients."))
        return

    # Ensure items to be destroyed do not have items inside them (e.g. bags)
    locations = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby)
    for req in recipe.ingredients:
        if not req['destroy']:
            continue
        for _, _, it, _, _ in locations:
            if it.name in req['names'] and hasattr(it, 'inventory') and it.inventory:
                display_message(f"{tr('msg', 'Cannot use')} {tr('item', it.name)}: {tr('msg', 'It contains items!')}")
                return

    def craft_complete():
        nearby_now = game.find_nearby_containers()
        craft_type = getattr(recipe, 'craft_type', 'create')

        if craft_type == 'dismantle':
            check_milestone_progress(game, 'craft_dismantle', 'item')
        elif craft_type == 'repair':
            check_milestone_progress(game, 'craft_repair', 'item')
        else:
            check_milestone_progress(game, 'craft_craft', 'item')

        if recipe.gain_xp:
            for attr, amount in recipe.gain_xp.items():
                if hasattr(player.progression, 'add_xp'):
                    player.progression.add_xp(player, attr, amount)

        target_repair_item = None
        if craft_type == 'repair':
            locs_now = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby_now)
            for container, key, it, ctype, _ in locs_now:
                if it.name == recipe.output_name and it.durability is not None and it.durability < it.max_durability:
                    target_repair_item = it
                    break
            if not target_repair_item:
                display_message(f"{tr('msg', 'No damaged')} {recipe.output_name} {tr('msg', 'found.')}")
                return

        total_repair_amount = 0
        maint_level = player.progression.get_maintenance(player)
        maint_scale = min(10, maint_level) / 10.0

        for req in recipe.ingredients:
            if not req['destroy']:
                continue
            to_remove = req['amount']
            valid_names = req['names']
            removed = 0

            locs_now = get_crafting_item_locations(player, game, include_nearby=True, nearby_containers=nearby_now)
            for container, key, it, ctype, _ in locs_now:
                if removed >= to_remove:
                    break
                if it.name in valid_names and it != target_repair_item:
                    item_qty = it.load if (it.load is not None and it.is_stackable()) else 1
                    take = min(to_remove - removed, item_qty)

                    if craft_type == 'repair' and it.min_restore is not None and it.max_restore is not None:
                        effective_min = it.min_restore + (it.max_restore - it.min_restore) * maint_scale
                        restore_per_unit = random.randint(int(effective_min), int(it.max_restore))
                        total_repair_amount += (restore_per_unit * take)

                    if it.is_stackable() and it.load is not None:
                        it.load -= take
                    removed += take

                    if (it.is_stackable() and it.load is not None and it.load <= 0) or (not it.is_stackable() and take > 0):
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
            old_dur = target_repair_item.durability
            target_repair_item.durability = min(target_repair_item.max_durability, target_repair_item.durability + total_repair_amount)
            restored = target_repair_item.durability - old_dur
            display_message(f"{tr('msg', 'Repaired')} {target_repair_item.name} {tr('msg', 'by')} {int(restored)} {tr('msg', 'points.')}")
            return

        created_items_log = []
        for res in recipe.results:
            base_chance = res.get('chance', 1.0)
            effective_chance = (base_chance + (1.0 - base_chance) * maint_scale) if craft_type == 'dismantle' else base_chance

            if effective_chance < 1.0 and random.random() > effective_chance:
                continue

            final_name = random.choice(res['names'])
            result_item = Item.create_from_name(final_name)
            if result_item:
                result_item.load = res['amount']
                if len(player.inventory) < player.get_total_inventory_slots():
                    player.inventory.append(result_item)
                else:
                    game.items_on_ground.append(result_item)
                    result_item.x, result_item.y = player.x, player.y
                    result_item.rect.topleft = (result_item.x, result_item.y)
                log_name = getattr(recipe, 'output_name', None) or result_item.name
                created_items_log.append(f"{res['amount']}x {log_name}")

        if created_items_log:
            label = tr('msg', 'Dismantled into:') if craft_type == 'dismantle' else tr('msg', 'Crafted:')
            display_message(f"{label} {', '.join(created_items_log)}")
        else:
            display_message(tr('msg', "Crafting yielded nothing."))

    player.start_action(f"Crafting {recipe.output_name}", recipe.time_required, craft_complete)

def get_recipe_status_details(player, game, recipe):
    """Analyzes recipe unlock and ingredient state.
    Returns:
        can_craft (bool): True if fully unlocked and all ingredients present.
        is_unlocked (bool): True if magazine and skill requirements are met.
        missing_ingredients (list): [{'name': ..., 'have': ..., 'needed': ...}]
        missing_magazine (str or None): Name of magazine if missing.
        missing_skills (list): [(attr_name, current_lvl, required_lvl)]
    """
    # 1. Check Magazine & Skills
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

    # 2. Check Ingredients (including 1-tile loose ground items)
    locs = get_crafting_item_locations(player, game, include_nearby=True)
    search_items = [loc[2] for loc in locs]
    missing_ingredients = []

    for req in recipe.ingredients:
        needed = req['amount']
        valid_names = req['names']
        have = sum((it.load if (it.load is not None and it.is_stackable()) else 1)
                   for it in search_items if it.name in valid_names)
        if have < needed:
            missing_ingredients.append({
                'name': valid_names[0],
                'have': int(have),
                'needed': int(needed)
            })

    can_craft = is_unlocked and (len(missing_ingredients) == 0)
    return can_craft, is_unlocked, missing_ingredients, missing_magazine, missing_skills

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