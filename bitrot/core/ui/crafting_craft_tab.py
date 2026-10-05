# core/ui/crafting_craft_tab.py
import pygame
import random
from core.data.config import WHITE, GRAY, font_12
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
from core.ui.notifications import check_milestone_progress
from core.ui.crafting_common import (
    draw_common_ingredients_grid, 
    draw_craft_action_footer, 
    player_has_at_least_one_ingredient, 
    add_craft_results_to_player
)
class CraftingCraftTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            if getattr(r, 'craft_type', 'create') in ('repair', 'dismantle'):
                continue
            if search_text:
                st = search_text.lower()
                matches_out = (st in r.output_name.lower()) or (st in tr('item', r.output_name).lower())
                matches_ing = any(any((st in n.lower()) or (st in tr('item', n).lower()) for n in ing['names']) for ing in r.ingredients)
                if not (matches_out or matches_ing):
                    continue
            filtered.append(r)
        return filtered

    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        r = self.modal.selected_recipe
        surface = self.modal.surface
        count = getattr(self.modal, 'craft_count', self.modal.modal.get('craft_count', 1))

        surface.blit(font_12.render(tr('item', r.output_name), False, WHITE), (details_x, details_y))
        if self.modal.result_image:
            scaled = pygame.transform.scale(self.modal.result_image, (32, 32))
            surface.blit(scaled, (details_x + details_w - 40, details_y))

        pygame.draw.line(surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)

        can_craft, tooltips, _ = draw_common_ingredients_grid(
            self.modal, r, details_x, details_y + 50, details_w, 
            mouse_pos, click, nearby_containers, player_items, nearby_items,
            count=count
        )

        draw_craft_action_footer(
            self.modal, r, details_x, details_y, details_w, list_h, can_craft,
            action_label="CRAFT ITEM", locked_label="LOCKED (MAG/SKILL)",
            on_execute=self.execute_craft, click=click, mouse_pos=mouse_pos
        )
        return tooltips

    def execute_craft(self, recipe, count=1):
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

        def craft_complete():
            nearby = self.modal.game.find_nearby_containers()
            check_milestone_progress(self.modal.game, 'craft_craft', 'item')

            if recipe.gain_xp:
                for attr, amount in recipe.gain_xp.items():
                    if hasattr(self.modal.player.progression, 'add_xp'):
                        self.modal.player.progression.add_xp(self.modal.player, attr, amount * count)

            # Deduct ingredients prioritizing nearby/ground items first
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
                    if item.name in valid_names:
                        has_item_load = (item.load is not None)
                        item_qty = item.load if has_item_load else 1
                        take = min(to_remove - removed, item_qty)
                        if has_item_load:
                            item.load -= take
                        removed += take
                        if (has_item_load and item.load <= 0) or (not has_item_load and take > 0):
                            if ctype == 'list':
                                if item in container:
                                    container.remove(item)
                                elif key < len(container):
                                    container.pop(key)
                            elif ctype == 'fixed_list': container[key] = None
                            elif ctype == 'dict': container[key] = None
                            elif ctype == 'attr': setattr(container, key, None)
                        if removed >= to_remove:
                            break

            # Auto-stack results into player inventory
            add_craft_results_to_player(self.modal.player, self.modal.game, recipe, count=count)

        self.modal.player.start_action(
            f"Crafting {recipe.output_name} x{count}",
            total_time,
            craft_complete,
            cancel_on_move=True,
            action_sound='craft.ogg',
            action_sound_subdir='craft'
        )