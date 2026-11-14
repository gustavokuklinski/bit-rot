# core/ui/crafting_build_tab.py
import pygame
from core.data.config import WHITE, GRAY, font_12
from core.messages import display_message
from core.data.localization import tr
from core.ui.crafting_common import (
    draw_common_ingredients_grid,
    draw_craft_action_footer,
    player_has_at_least_one_ingredient,
    execute_recipe_craft
)

class CraftingBuildTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            is_building = (
                getattr(r, 'is_building', False) or
                getattr(r, 'recipe_type', '') in ('maptile', 'maptile_container') or
                str(getattr(r, 'recipe_type', '')).startswith('maptile') or
                getattr(r, 'map_location', None) is not None
            )
            if not is_building:
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
            action_label="BUILD", locked_label="LOCKED (SKILL/MAG)",
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

        execute_recipe_craft(self.modal.game, recipe, player=self.modal.player, count=count)