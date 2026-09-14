# core/ui/crafting_dismantle_tab.py
import pygame
import random
from core.data.config import *
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
from core.ui.notifications import check_milestone_progress
from core.ui.crafting_common import draw_common_ingredients_grid, draw_craft_action_footer

class CraftingDismantleTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            craft_type = getattr(r, 'craft_type', 'create')
            if craft_type != 'dismantle':
                continue
            if search_text:
                st = search_text.lower()
                if (st not in r.output_name.lower()) and (st not in tr('item', r.output_name).lower()):
                    continue
            filtered.append(r)
        return filtered

    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        r = self.modal.selected_recipe
        surface = self.modal.surface

        surface.blit(font_12.render(tr('item', r.output_name), False, WHITE), (details_x, details_y))

        sel_id = self.modal.selected_ingredients.get(0)
        if sel_id:
            locs = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
            for _, _, item, _, _ in locs:
                if item.id == sel_id:
                    self.modal.result_image = item.image
                    break

        if self.modal.result_image:
            scaled_result = pygame.transform.scale(self.modal.result_image, (32, 32))
            surface.blit(scaled_result, (details_x + details_w - 40, details_y))

        pygame.draw.line(surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)

        can_craft, tooltips, _ = draw_common_ingredients_grid(
            self.modal, r, details_x, details_y + 50, details_w,
            mouse_pos, click, nearby_containers, player_items, nearby_items
        )

        draw_craft_action_footer(
            self.modal, r, details_x, details_y, details_w, list_h, can_craft,
            action_label="DISMANTLE", locked_label="LOCKED (MAG/SKILL)",
            on_execute=self.execute_craft, click=click, mouse_pos=mouse_pos
        )
        return tooltips

    def execute_craft(self, recipe):
        if self.modal.player.action_timer > 0:
            return

        error = self.modal._validate_ingredients(recipe)
        if error:
            self.modal.warning_message = error
            return

        def craft_complete():
            nearby = self.modal.game.find_nearby_containers()
            check_milestone_progress(self.modal.game, 'craft_dismantle', 'item')

            if recipe.gain_xp:
                for attr, amount in recipe.gain_xp.items():
                    if hasattr(self.modal.player.progression, 'add_xp'):
                        self.modal.player.progression.add_xp(self.modal.player, attr, amount)

            for r_idx, req in enumerate(recipe.ingredients):
                if not req['destroy']:
                    continue
                to_remove = req['amount']
                valid_names = req['names']
                removed = 0

                locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
                pref_id = self.modal.selected_ingredients.get(r_idx)
                locations = self.modal.prioritize_locations(locations, pref_id)

                for container, key, item, ctype, _ in locations:
                    if removed >= to_remove:
                        break
                    if item.name in valid_names:
                        item_qty = item.load if (item.load is not None and item.is_stackable()) else 1
                        take = min(to_remove - removed, item_qty)
                        if item.is_stackable() and item.load is not None:
                            item.load -= take
                        removed += take
                        if (item.is_stackable() and item.load is not None and item.load <= 0) or (not item.is_stackable() and take > 0):
                            if ctype == 'list':
                                container.pop(key)
                            elif ctype == 'fixed_list':
                                container[key] = None
                            elif ctype == 'dict':
                                container[key] = None
                            elif ctype == 'attr':
                                setattr(container, key, None)
                        if removed >= to_remove:
                            break

            created_items_log = []
            maint_level = self.modal.player.progression.get_maintenance(self.modal.player)
            maint_scale = min(10, maint_level) / 10.0

            for res in recipe.results:
                base_chance = res.get('chance', 1.0)
                effective_chance = base_chance + (1.0 - base_chance) * maint_scale
                if effective_chance < 1.0 and random.random() > effective_chance:
                    continue

                final_name = random.choice(res['names'])
                result_item = Item.create_from_name(final_name)
                if result_item:
                    result_item.load = res['amount']
                    if len(self.modal.player.inventory) < self.modal.player.get_total_inventory_slots():
                        self.modal.player.inventory.append(result_item)
                    else:
                        self.modal.game.items_on_ground.append(result_item)
                        result_item.x, result_item.y = self.modal.player.x, self.modal.player.y
                        result_item.rect.topleft = (result_item.x, result_item.y)
                    created_items_log.append(f"{res['amount']}x {final_name}")

            if created_items_log:
                display_message(f"{tr('msg', 'Dismantled into:')} {', '.join(created_items_log)}")
            else:
                display_message(tr('msg', "Dismantling yielded nothing."))

        self.modal.player.start_action(f"Dismantling {recipe.output_name}", recipe.time_required, craft_complete)