# core/ui/crafting_common.py
import pygame
from core.data.config import WHITE, GRAY, GREEN, RED, font_12
from core.data.localization import tr

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