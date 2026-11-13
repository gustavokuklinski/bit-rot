# core/ui/crafting_cooking_tab.py

import pygame
import random
from core.data.config import WHITE, GRAY, GREEN, RED, YELLOW, DARK_GRAY, font_12
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
from core.ui.notifications import check_milestone_progress
from core.entities.item.item_factory import build_seasoned_food_name
from core.ui.crafting_common import (
    draw_common_ingredients_grid,
    draw_craft_action_footer,
    player_has_at_least_one_ingredient,
    add_craft_results_to_player,
    is_craft_name_match
)

class CraftingCookingTab:
    def __init__(self, modal):
        self.modal = modal
        self.selected_extras = set()
        self.seasoning_search_text = ""
        self.seasoning_search_active = False
        self.seasoning_scroll_y = 0
        self.seasoning_max_scroll = 0
        self.is_dragging_scrollbar = False
        self.seasoning_box_rect = None
        self.search_rect = None

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            is_food_drink = (
                getattr(r, 'craft_type', 'create') == 'cook' or
                getattr(r, 'recipe_type', '') in ('consumable_food', 'consumable_drink') or
                (hasattr(r, 'extra_ingredients') and len(r.extra_ingredients) > 0)
            )
            if not is_food_drink:
                continue

            if search_text:
                st = search_text.lower()
                matches_out = (st in r.output_name.lower()) or (st in tr('item', r.output_name).lower())
                matches_ing = any(any((st in n.lower()) or (st in tr('item', n).lower()) for n in ing['names']) for ing in r.ingredients)
                if not (matches_out or matches_ing):
                    continue

            filtered.append(r)
        return filtered

    def handle_event(self, event, mouse_pos):
        """Processes keyboard typing and mouse interactions for the seasonings search box and scrollbar."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
            if self.search_rect and self.search_rect.collidepoint(mouse_pos):
                self.seasoning_search_active = True
                self.modal.search_active = False
                self.modal.modal['search_active'] = False
                pygame.key.set_repeat(500, 50)
                return True
            else:
                if self.seasoning_search_active:
                    self.seasoning_search_active = False
                    pygame.key.set_repeat()

        elif event.type == pygame.KEYDOWN and self.seasoning_search_active:
            if event.key == pygame.K_BACKSPACE:
                self.seasoning_search_text = self.seasoning_search_text[:-1]
                self.seasoning_scroll_y = 0
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.seasoning_search_active = False
                pygame.key.set_repeat()
            else:
                if len(self.seasoning_search_text) < 20 and event.unicode and event.unicode.isprintable():
                    self.seasoning_search_text += event.unicode
                    self.seasoning_scroll_y = 0
            return True

        elif event.type == pygame.MOUSEWHEEL:
            if self.seasoning_box_rect and self.seasoning_box_rect.collidepoint(mouse_pos):
                scroll_amt = event.y * 28
                self.seasoning_scroll_y = max(0, min(self.seasoning_scroll_y - scroll_amt, self.seasoning_max_scroll))
                return True

        return False

    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        r = self.modal.selected_recipe
        surface = self.modal.surface
        count = getattr(self.modal, 'craft_count', self.modal.modal.get('craft_count', 1))

        # Reset selection if active recipe changes
        if getattr(self.modal, '_last_cooking_recipe', None) != r:
            self.modal._last_cooking_recipe = r
            self.selected_extras = set()
            self.seasoning_search_text = ""
            self.seasoning_search_active = False
            self.seasoning_scroll_y = 0

        # 1. Output Name Preview
        chosen_seasoning_names = []
        extra_ingredients = getattr(r, 'extra_ingredients', []) or []
        for idx in sorted(list(self.selected_extras)):
            if idx < len(extra_ingredients):
                if extra_ingredients[idx].get('names'):
                    chosen_seasoning_names.append(extra_ingredients[idx]['names'][0])

        preview_output_name = build_seasoned_food_name(r.output_name, chosen_seasoning_names)

        title_surf = font_12.render(preview_output_name, False, YELLOW if chosen_seasoning_names else WHITE)
        surface.blit(title_surf, (details_x, details_y))

        if self.modal.result_image:
            scaled = pygame.transform.scale(self.modal.result_image, (32, 32))
            surface.blit(scaled, (details_x + details_w - 40, details_y))

        pygame.draw.line(surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)

        # 2. Required Ingredients Grid
        can_craft, tooltips, after_ing_y = draw_common_ingredients_grid(
            self.modal, r, details_x, details_y + 45, details_w,
            mouse_pos, click, nearby_containers, player_items, nearby_items,
            count=count
        )

        # 3. Calculate Accurate Footer Height to Prevent Bottom Overlaps
        # Button (40) + Gap (8) + Quantity Bar (28) + Gap (8) + Time (20) + Margins/Warnings (30+)
        footer_h = 135
        if getattr(r, 'req_level', None):
            footer_h += 25
        if getattr(r, 'magazine', None):
            footer_h += 22
        if getattr(self.modal, 'warning_message', None):
            footer_h += 20
        if getattr(self.modal.player, 'action_timer', 0) > 0:
            footer_h += 20
        footer_top = details_y + list_h - footer_h

        # 4. Header & Search Bar Placed Cleanly Below Ingredients
        header_y = after_ing_y + 6
        header_h = 22

        lbl_extra = font_12.render(tr('ui', "Optional Seasonings & Add-ins:"), False, (255, 215, 0))
        surface.blit(lbl_extra, (details_x, header_y + 4))

        # Compact Seasoning Search Box
        search_w = 160
        search_h = 22
        search_x = details_x + details_w - search_w - 5
        self.search_rect = pygame.Rect(search_x, header_y + 1, search_w, search_h)
        self.modal.modal['seasoning_search_rect'] = self.search_rect

        if click and self.search_rect.collidepoint(mouse_pos) and not self.modal.dropdown_state['active']:
            self.seasoning_search_active = True
            self.modal.search_active = False
            self.modal.modal['search_active'] = False
            pygame.key.set_repeat(500, 50)
        elif click and not self.search_rect.collidepoint(mouse_pos) and not self.modal.dropdown_state['active']:
            if self.seasoning_search_active:
                self.seasoning_search_active = False
                pygame.key.set_repeat()

        s_bg = (20, 20, 20) if self.seasoning_search_active else (30, 30, 30)
        pygame.draw.rect(surface, s_bg, self.search_rect, border_radius=3)
        s_border = (200, 200, 200) if self.seasoning_search_active else ((100, 100, 100) if self.search_rect.collidepoint(mouse_pos) else (60, 60, 60))
        pygame.draw.rect(surface, s_border, self.search_rect, 1, border_radius=3)

        disp_search = self.seasoning_search_text
        if self.seasoning_search_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            disp_search += "_"

        if not self.seasoning_search_text and not self.seasoning_search_active:
            s_txt_surf = font_12.render(tr('ui', "Search..."), False, (100, 100, 100))
        else:
            s_txt_surf = font_12.render(disp_search, False, WHITE)

        old_clip = surface.get_clip()
        surface.set_clip(self.search_rect.inflate(-4, -4))
        surface.blit(s_txt_surf, (self.search_rect.x + 5, self.search_rect.y + 4))
        surface.set_clip(old_clip)

        # 5. Dedicated Bounded Seasonings Viewport with Safe Margin
        box_x = details_x
        box_y = header_y + header_h + 4
        box_w = details_w
        box_h = max(50, footer_top - box_y - 8)
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        self.seasoning_box_rect = box_rect
        self.modal.modal['seasoning_box_rect'] = box_rect

        # Filter seasonings by search input
        filtered_extras = []
        for e_idx, extra in enumerate(extra_ingredients):
            ing_name = extra['names'][0]
            if self.seasoning_search_text:
                st = self.seasoning_search_text.lower().strip()
                if st not in ing_name.lower() and st not in tr('item', ing_name).lower():
                    continue
            filtered_extras.append((e_idx, extra))

        card_h = 22
        card_gap = 3
        total_items_h = len(filtered_extras) * (card_h + card_gap)
        max_scroll = max(0, total_items_h - box_h)
        self.seasoning_max_scroll = max_scroll

        needs_scrollbar = total_items_h > box_h
        bar_w = 8 if needs_scrollbar else 0
        card_w = box_w - (bar_w + 14 if needs_scrollbar else 10)

        bar_rect = pygame.Rect(box_rect.right - bar_w - 2, box_rect.y + 2, bar_w, box_h - 4) if needs_scrollbar else None
        self.modal.modal['seasoning_bar_rect'] = bar_rect

        mouse_pressed = pygame.mouse.get_pressed()[0]
        if not mouse_pressed:
            self.is_dragging_scrollbar = False

        if needs_scrollbar and bar_rect:
            handle_h = max(18, int((box_h / float(total_items_h)) * bar_rect.height))
            track_avail = max(1, bar_rect.height - handle_h)

            # Click on scrollbar track or thumb initiates isolated seasoning drag
            if click and bar_rect.collidepoint(mouse_pos) and not self.modal.dropdown_state['active']:
                self.is_dragging_scrollbar = True
                rel_y = mouse_pos[1] - bar_rect.y - (handle_h // 2)
                pct = max(0.0, min(1.0, rel_y / track_avail))
                self.seasoning_scroll_y = int(pct * max_scroll)

            # Continuous drag while holding mouse button
            if mouse_pressed and self.is_dragging_scrollbar:
                rel_y = mouse_pos[1] - bar_rect.y - (handle_h // 2)
                pct = max(0.0, min(1.0, rel_y / track_avail))
                self.seasoning_scroll_y = int(pct * max_scroll)

        self.seasoning_scroll_y = max(0, min(self.seasoning_scroll_y, max_scroll))

        # Background frame for seasonings box
        pygame.draw.rect(surface, (25, 25, 25), box_rect, border_radius=4)
        pygame.draw.rect(surface, (50, 50, 50), box_rect, 1, border_radius=4)

        # Render clipped cards
        old_clip = surface.get_clip()
        surface.set_clip(box_rect.inflate(-4, -4))

        cb_size = 16
        all_items = player_items + (nearby_items or [])

        if not extra_ingredients:
            no_extra = font_12.render(tr('ui', "None (Simple recipe)"), False, GRAY)
            surface.blit(no_extra, (box_rect.x + 10, box_rect.y + 10))
        elif not filtered_extras:
            no_match = font_12.render(tr('ui', "No seasonings found."), False, GRAY)
            surface.blit(no_match, (box_rect.x + 10, box_rect.y + 10))
        else:
            for item_i, (e_idx, extra) in enumerate(filtered_extras):
                card_y = box_rect.y + 4 + (item_i * (card_h + card_gap)) - self.seasoning_scroll_y

                if card_y + card_h < box_rect.y or card_y > box_rect.bottom:
                    continue

                ing_name = extra['names'][0]
                needed_qty = extra['amount'] * count

                skills_met = True
                missing_skill_str = ""
                if extra['req_level']:
                    for attr, lvl in extra['req_level'].items():
                        p_lvl = self.modal.player.progression.get_level(attr)
                        if p_lvl < lvl:
                            skills_met = False
                            missing_skill_str = f"Req {tr('ui', attr.capitalize())} Lv {int(lvl)}"
                            break

                knows_mag = True
                if extra['magazine']:
                    knows_mag = extra['magazine'] in self.modal.player.known_recipes
                    if not knows_mag and not missing_skill_str:
                        missing_skill_str = f"Req {extra['magazine']}"

                is_unlocked = skills_met and knows_mag

                have_qty = sum(
                    (it.load if it.load is not None else 1)
                    for it in all_items if is_craft_name_match(ing_name, it)
                )
                has_enough = (have_qty >= needed_qty)

                card_rect = pygame.Rect(box_rect.x + 6, card_y, card_w, card_h)
                cb_rect = pygame.Rect(card_rect.x + 4, card_rect.centery - (cb_size // 2), cb_size, cb_size)

                is_selected = e_idx in self.selected_extras
                is_usable = is_unlocked and has_enough
                is_hover = card_rect.collidepoint(mouse_pos) and box_rect.collidepoint(mouse_pos)

                if click and is_usable and is_hover and not self.modal.dropdown_state['active'] and not self.is_dragging_scrollbar:
                    if is_selected:
                        self.selected_extras.remove(e_idx)
                    else:
                        self.selected_extras.add(e_idx)
                    if hasattr(self.modal.game, 'sound_manager'):
                        self.modal.game.sound_manager.play_ui_hover()

                bg_col = (45, 45, 45) if is_hover and is_usable else (32, 32, 32)
                pygame.draw.rect(surface, bg_col, card_rect, border_radius=3)
                pygame.draw.rect(surface, WHITE if is_selected else (60, 60, 60), card_rect, 1, border_radius=3)

                pygame.draw.rect(surface, (20, 20, 20), cb_rect, border_radius=2)
                pygame.draw.rect(surface, GREEN if is_selected else (80, 80, 80), cb_rect, 1, border_radius=2)
                if is_selected:
                    pygame.draw.rect(surface, GREEN, cb_rect.inflate(-4, -4), border_radius=1)

                if not is_unlocked:
                    txt_col = (140, 60, 60)
                    info_str = f"{tr('item', ing_name)} ({missing_skill_str})"
                elif not has_enough:
                    txt_col = (180, 100, 100)
                    info_str = f"{tr('item', ing_name)} ({have_qty}/{needed_qty})"
                else:
                    txt_col = YELLOW if is_selected else WHITE
                    info_str = f"{tr('item', ing_name)} ({have_qty}/{needed_qty})"

                t_surf = font_12.render(info_str, False, txt_col)
                surface.blit(t_surf, (cb_rect.right + 8, card_rect.centery - (t_surf.get_height() // 2)))

        surface.set_clip(old_clip)

        # Draw Scrollbar Handle
        if needs_scrollbar and bar_rect:
            pygame.draw.rect(surface, (35, 35, 35), bar_rect, border_radius=3)
            handle_h = max(18, int((box_h / float(total_items_h)) * bar_rect.height))
            track_avail = max(1, bar_rect.height - handle_h)
            scroll_pct = self.seasoning_scroll_y / max(1, max_scroll)
            handle_y = bar_rect.y + int(scroll_pct * track_avail)
            handle_rect = pygame.Rect(bar_rect.x, handle_y, bar_rect.width, handle_h)
            
            is_hover = handle_rect.collidepoint(mouse_pos)
            h_col = (150, 150, 150) if (self.is_dragging_scrollbar or is_hover) else (90, 90, 90)
            pygame.draw.rect(surface, h_col, handle_rect, border_radius=3)

        # 6. Action Footer Rendered in its Reserved Space
        draw_craft_action_footer(
            self.modal, r, details_x, details_y, details_w, list_h, can_craft,
            action_label="COOK DISH", locked_label="LOCKED (COOKING)",
            on_execute=self.execute_cook, click=click, mouse_pos=mouse_pos
        )
        return tooltips

    def execute_cook(self, recipe, count=1):
        if self.modal.player.action_timer > 0:
            return

        count = max(1, int(count))

        if not player_has_at_least_one_ingredient(self.modal.player, self.modal.game, recipe):
            display_message(tr('msg', "At least one required item must be in your inventory."))
            return

        error = self.modal._validate_ingredients(recipe, count=count)
        if error:
            self.modal.warning_message = error
            return

        total_time = round(recipe.time_required * count, 1)

        extra_ingredients = getattr(recipe, 'extra_ingredients', []) or []
        selected_extras_data = []
        chosen_seasoning_names = []

        for idx in sorted(list(self.selected_extras)):
            if idx < len(extra_ingredients):
                extra = extra_ingredients[idx]
                selected_extras_data.append(extra)
                if extra.get('names'):
                    chosen_seasoning_names.append(extra['names'][0])

        preview_output_name = build_seasoned_food_name(recipe.output_name, chosen_seasoning_names)

        def cook_complete():
            nearby = self.modal.game.find_nearby_containers()
            check_milestone_progress(self.modal.game, 'craft_cooking', 'item')

            if recipe.gain_xp:
                for attr, amount in recipe.gain_xp.items():
                    if hasattr(self.modal.player.progression, 'add_xp'):
                        self.modal.player.progression.add_xp(self.modal.player, attr, amount * count)
            else:
                self.modal.player.progression.award_action_xp(self.modal.player, 'cooking', 'success', fallback=2.0 * count)

            locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
            inherited_seasonings = []

            for r_idx, req in enumerate(recipe.ingredients):
                if not req['destroy']:
                    continue
                to_remove = req['amount'] * count
                valid_names = req['names']
                removed = 0

                locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
                pref_id = self.modal.selected_ingredients.get(r_idx)
                locations = self.modal.prioritize_locations(locations, pref_id)

                for container, key, item, ctype, _ in locations:
                    if removed >= to_remove:
                        break
                    if ctype == 'maptile':
                        continue
                    if any(is_craft_name_match(vn, item) for vn in valid_names):
                        if getattr(item, 'seasonings', None):
                            inherited_seasonings.extend(item.seasonings)

                        has_item_load = (item.load is not None)
                        item_qty = item.load if has_item_load else 1
                        take = min(to_remove - removed, item_qty)
                        if has_item_load:
                            item.load -= take
                        removed += take
                        if (has_item_load and item.load <= 0) or (not has_item_load and take > 0):
                            if hasattr(item, 'inventory') and item.inventory:
                                item.inventory.clear()

                            if ctype == 'list':
                                if item in container: container.remove(item)
                                elif key < len(container): container.pop(key)
                            elif ctype == 'fixed_list': container[key] = None
                            elif ctype == 'dict': container[key] = None
                            elif ctype == 'attr': setattr(container, key, None)
                        if removed >= to_remove:
                            break

            active_seasoning_names = list(inherited_seasonings)
            for extra in selected_extras_data:
                extra_name = extra['names'][0]
                active_seasoning_names.append(extra_name)
                if not extra.get('destroy', True):
                    continue

                to_remove = extra['amount'] * count
                removed = 0

                locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
                for container, key, item, ctype, _ in locations:
                    if removed >= to_remove:
                        break
                    if ctype == 'maptile':
                        continue
                    if is_craft_name_match(extra_name, item):
                        has_item_load = (item.load is not None)
                        item_qty = item.load if has_item_load else 1
                        take = min(to_remove - removed, item_qty)
                        if has_item_load:
                            item.load -= take
                        removed += take
                        if (has_item_load and item.load <= 0) or (not has_item_load and take > 0):
                            if ctype == 'list':
                                if item in container: container.remove(item)
                                elif key < len(container): container.pop(key)
                            elif ctype == 'fixed_list': container[key] = None
                            elif ctype == 'dict': container[key] = None
                            elif ctype == 'attr': setattr(container, key, None)

            add_craft_results_to_player(
                self.modal.player, self.modal.game, recipe, 
                count=count, inherited_seasonings=active_seasoning_names
            )

        action_name = f"Cooking {preview_output_name}"
        if count > 1:
            action_name += f" x{count}"

        self.modal.player.start_action(
            action_name,
            total_time,
            cook_complete,
            cancel_on_move=True,
            action_sound='cooking.ogg',
            action_sound_subdir='craft'
        )