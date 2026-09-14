# core/ui/crafting_repair_tab.py
import pygame
import random
from core.data.config import *
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
from core.ui.notifications import check_milestone_progress
from core.ui.crafting_common import draw_common_ingredients_grid, draw_craft_action_footer

class CraftingRepairTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            craft_type = getattr(r, 'craft_type', 'create')
            if craft_type != 'repair':
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

        target_opts, target_ids = [], []
        locs = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers, exclude_equipped=True)
        for _, _, item, _, path in locs:
            if item.name == r.output_name and item.durability is not None and item.durability < item.max_durability:
                target_opts.append(f"{tr('item', item.name)} (Dur: {int(item.durability)}) - {' > '.join(path)}")
                target_ids.append(item.id)

        target_text = tr('item', r.output_name)
        if self.modal.selected_target in target_ids:
            idx = target_ids.index(self.modal.selected_target)
            target_text = f"{tr('tab', 'Repair')}: {target_opts[idx]}"
            for _, _, item, _, _ in locs:
                if item.id == self.modal.selected_target:
                    self.modal.result_image = item.image
                    break
        elif target_opts:
            target_text = f"{tr('tab', 'Repair')}: {target_opts[0]}"
        else:
            target_text = f"{tr('tab', 'Repair')}: {r.output_name} {tr('ui', '(None available)')}"

        title_surf = font_12.render(target_text, False, YELLOW if target_opts else WHITE)
        title_rect = title_surf.get_rect(topleft=(details_x, details_y))
        surface.blit(title_surf, title_rect)

        if click and title_rect.collidepoint(mouse_pos) and target_opts and not self.modal.dropdown_state['active']:
            self.modal.dropdown_state.update({
                'active': True, 'options': target_opts, 'items': target_ids,
                'req_idx': 'target', 'position': mouse_pos
            })

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
            action_label="REPAIR ITEM", locked_label="LOCKED (MAG/SKILL)",
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
            check_milestone_progress(self.modal.game, 'craft_repair', 'item')

            if recipe.gain_xp:
                for attr, amount in recipe.gain_xp.items():
                    if hasattr(self.modal.player.progression, 'add_xp'):
                        self.modal.player.progression.add_xp(self.modal.player, attr, amount)

            target_item, target_container, target_key, target_ctype = None, None, None, None
            locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
            locations = self.modal.prioritize_locations(locations, self.modal.selected_target)

            for container, key, item, ctype, _ in locations:
                if item.name == recipe.output_name and item.durability is not None and item.durability < item.max_durability:
                    target_item, target_container, target_key, target_ctype = item, container, key, ctype
                    break

            if not target_item:
                display_message(f"{tr('msg', 'No damaged')} {recipe.output_name} {tr('msg', 'found.')}")
                return

            total_repair_amount = 0
            maint_level = self.modal.player.progression.get_maintenance(self.modal.player)
            maint_scale = min(10, maint_level) / 10.0

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
                    if item.name in valid_names and item != target_item:
                        item_qty = item.load if (item.load is not None and item.is_stackable()) else 1
                        take = min(to_remove - removed, item_qty)
                        if item.min_restore is not None and item.max_restore is not None:
                            effective_min = item.min_restore + (item.max_restore - item.min_restore) * maint_scale
                            restore_per_unit = random.randint(int(effective_min), int(item.max_restore))
                            total_repair_amount += (restore_per_unit * take)
                        if item.is_stackable() and item.load is not None:
                            item.load -= take
                        removed += take
                        if (item.is_stackable() and item.load is not None and item.load <= 0) or (not item.is_stackable() and take > 0):
                            if ctype == 'list' and item in container:
                                container.remove(item)
                            elif ctype == 'fixed_list':
                                container[key] = None
                            elif ctype == 'dict':
                                container[key] = None
                            elif ctype == 'attr':
                                setattr(container, key, None)
                        if removed >= to_remove:
                            break

            if total_repair_amount <= 0:
                total_repair_amount = target_item.max_durability - target_item.durability

            if target_ctype == 'list' and target_item in target_container:
                target_container.remove(target_item)
            elif target_ctype == 'fixed_list':
                target_container[target_key] = None
            elif target_ctype == 'dict':
                target_container[target_key] = None
            elif target_ctype == 'attr':
                setattr(target_container, target_key, None)

            old_durability = target_item.durability
            target_item.durability = min(target_item.max_durability, target_item.durability + total_repair_amount)
            restored = target_item.durability - old_durability

            if len(self.modal.player.inventory) < self.modal.player.get_total_inventory_slots():
                self.modal.player.inventory.append(target_item)
            else:
                self.modal.game.items_on_ground.append(target_item)
                target_item.x, target_item.y = self.modal.player.x, self.modal.player.y
                target_item.rect.topleft = (target_item.x, target_item.y)

            if hasattr(self.modal.player, 'progression'):
                self.modal.player.progression.add_xp(self.modal.player, 'maintenance', 15)

            display_message(f"{tr('msg', 'Repaired')} {target_item.name} {tr('msg', 'by')} {int(restored)} {tr('msg', 'points.')}")

        self.modal.player.start_action(f"Repairing {recipe.output_name}", recipe.time_required, craft_complete)