# core/ui/crafting_repair_tab.py
import pygame
import random
from core.data.config import *
from core.entities.item.item import Item
from core.messages import display_message

class CraftingRepairTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            craft_type = getattr(r, 'craft_type', 'create')
            if craft_type != 'repair': continue
            
            if search_text and search_text.lower() not in r.output_name.lower(): continue
            filtered.append(r)
        return filtered

    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        r = self.modal.selected_recipe
        surface = self.modal.surface

        # Target selection for repair
        target_opts = []
        target_ids = []
        locs = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
        for container, key, item, ctype, path in locs:
            if item.name == r.output_name and item.durability is not None and item.durability < item.max_durability:
                target_opts.append(f"{item.name} (Dur: {int(item.durability)}) - {' > '.join(path)}")
                target_ids.append(item.id)
        
        target_text = r.output_name
        if self.modal.selected_target in target_ids:
            idx = target_ids.index(self.modal.selected_target)
            target_text = f"Repair: {target_opts[idx]}"
            
            for container, key, item, ctype, path in locs:
                if item.id == self.modal.selected_target:
                    self.modal.result_image = item.image
                    break
        elif target_opts:
            target_text = f"Repair: {target_opts[0]}"
        else:
            target_text = f"Repair: {r.output_name} (None damaged)"
            
        title_surf = font.render(target_text, True, YELLOW if target_opts else WHITE)
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
        
        # Ingredients
        ing_y = details_y + 50
        lbl = font_small.render("Required Ingredients:", True, GRAY)
        surface.blit(lbl, (details_x, ing_y))
        
        curr_y = ing_y + 30
        can_craft = True
        active_tooltip_ingredients = None
        
        for r_idx, req in enumerate(r.ingredients):
            needed = req['amount']
            valid_names = req['names'] 
            
            have = sum((item.load if (item.load is not None and item.is_stackable()) else 1) 
                       for item in player_items 
                       if item.name in valid_names)
            
            if nearby_items:
                have += sum((item.load if (item.load is not None and item.is_stackable()) else 1) 
                       for item in nearby_items 
                       if item.name in valid_names)
            
            color = GREEN if have >= needed else RED
            if have < needed: can_craft = False
            
            primary_name = valid_names[0]
            img = self.modal.ingredient_images.get(primary_name)
            name_display = primary_name if len(valid_names) == 1 else f"{primary_name} (Any)"

            sel_id = self.modal.selected_ingredients.get(r_idx)
            if sel_id:
                for container, key, item, ctype, path in locs:
                    if item.id == sel_id:
                        name_display = f"[*] {item.name}"
                        img = item.image
                        break

            text_x = details_x + 10
            if img:
                scaled_icon = pygame.transform.scale(img, (32, 32))
                surface.blit(scaled_icon, (text_x, curr_y))
                text_x += 35

            row_rect = pygame.Rect(details_x, curr_y, details_w, 32)
            if row_rect.collidepoint(mouse_pos):
                active_tooltip_ingredients = valid_names
                color = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))
                pygame.draw.rect(surface, (50,50,50), row_rect, border_radius=3)
                
                if click and not self.modal.dropdown_state['active']:
                    opts = []
                    itms = []
                    for container, key, item, ctype, path in locs:
                        if item.name in valid_names:
                            qty = item.load if item.is_stackable() else f"Dur: {int(item.durability or 0)}"
                            opts.append(f"{item.name} ({qty}) - {' > '.join(path)}")
                            itms.append(item.id)
                    if opts:
                        self.modal.dropdown_state.update({
                            'active': True, 'options': opts, 'items': itms, 
                            'req_idx': r_idx, 'position': mouse_pos
                        })

            txt_str = f" {name_display}: {int(have)} / Need: {needed}"
            ing_surf = font_small.render(txt_str, True, color)
            surface.blit(ing_surf, (text_x, curr_y + 8))
            curr_y += 35

        btn_h = 40
        bottom_y = details_y + list_h
        btn_rect = pygame.Rect(details_x, bottom_y - btn_h, details_w, btn_h)
        
        element_cursor_y = btn_rect.top - 5

        if self.modal.player.action_timer > 0 and self.modal.player.action_total_time > 0:
            bar_h = 10
            pygame.draw.rect(surface, (30, 30, 30), (details_x, element_cursor_y - bar_h, details_w, bar_h))
            progress = 1.0 - (self.modal.player.action_timer / self.modal.player.action_total_time)
            fill_w = int(details_w * progress)
            pygame.draw.rect(surface, GREEN, (details_x, element_cursor_y - bar_h, fill_w, bar_h))
            element_cursor_y -= (bar_h + 10) 

        is_unlocked = True
        knows_magazine = True
        if r.magazine:
            knows_magazine = r.magazine in self.modal.player.known_recipes
        
        skills_met = self.modal._check_skill_reqs(r)

        if r.magazine:
            if r.req_level:
                if not knows_magazine and not skills_met: is_unlocked = False
            else:
                if not knows_magazine: is_unlocked = False
        elif r.req_level:
            if not skills_met: is_unlocked = False

        if not is_unlocked:
            can_craft = False

        if r.req_level:
            for attr, lvl in reversed(list(r.req_level.items())):
                attr_name = attr.replace('_', ' ').capitalize()
                p_lvl = self.modal.player.progression.get_level(attr)
                s_color = GREEN if p_lvl >= lvl else RED
                txt = f"- {attr_name}: {p_lvl}/{int(lvl)}"
                s_surf = font_small.render(txt, True, s_color)
                element_cursor_y -= 20
                surface.blit(s_surf, (details_x + 10, element_cursor_y))
            
            head_txt = "OR Skills:" if r.magazine else "Requires Skills:"
            head_surf = font_small.render(head_txt, True, WHITE)
            element_cursor_y -= 20
            surface.blit(head_surf, (details_x, element_cursor_y))
            element_cursor_y -= 5

        if r.magazine:
            mag_color = GREEN if knows_magazine else RED
            mag_text = f"Requires Magazine: {r.magazine}"
            mag_surf = font_small.render(mag_text, True, mag_color)
            element_cursor_y -= 20
            surface.blit(mag_surf, (details_x, element_cursor_y))
            element_cursor_y -= 5 

        time_text = f"Time: {r.time_required}s"
        time_surf = font_small.render(time_text, True, GRAY)
        element_cursor_y -= 20
        surface.blit(time_surf, (details_x, element_cursor_y))

        if self.modal.warning_message:
            warn_surf = font_small.render(self.modal.warning_message, True, RED)
            element_cursor_y -= 20
            surface.blit(warn_surf, (details_x, element_cursor_y))

        btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
        border_color = WHITE if can_craft else GRAY
        
        pygame.draw.rect(surface, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(surface, border_color, btn_rect, 1, border_radius=5)
        
        if not is_unlocked:
            if r.magazine and not knows_magazine and r.req_level: btn_text = "LOCKED (MAG/SKILL)"
            elif r.magazine: btn_text = "NEED MAGAZINE"
            else: btn_text = "NEED SKILLS"
        elif can_craft:
            btn_text = "REPAIR ITEM"
        else:
            btn_text = "MISSING RESOURCES"

        lbl = font.render(btn_text, True, WHITE if can_craft else GRAY)
        text_rect = lbl.get_rect(center=btn_rect.center)
        surface.blit(lbl, text_rect)
        
        if can_craft and click and not self.modal.dropdown_state['active']:
            mouse_rect = pygame.Rect(mouse_pos[0], mouse_pos[1], 1, 1)
            if mouse_rect.colliderect(btn_rect):
                self.execute_craft(r)
                
        return active_tooltip_ingredients

    def execute_craft(self, recipe):
        if self.modal.player.action_timer > 0: return

        error = self.modal._validate_ingredients(recipe)
        if error:
            self.modal.warning_message = error
            return

        def craft_complete():
            nearby = self.modal.game.find_nearby_containers()
            if recipe.gain_xp:
                for attr, amount in recipe.gain_xp.items():
                    if hasattr(self.modal.player.progression, 'add_xp'):
                        self.modal.player.progression.add_xp(self.modal.player, attr, amount)

            target_item = None
            target_container = None
            target_key = None
            target_ctype = None
            
            locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
            locations = self.modal.prioritize_locations(locations, self.modal.selected_target)

            for container, key, item, ctype, path in locations:
                if item.name == recipe.output_name and item.durability is not None and item.durability < item.max_durability:
                    target_item = item
                    target_container = container
                    target_key = key
                    target_ctype = ctype
                    break
            
            if not target_item:
                display_message(f"No damaged {recipe.output_name} found.")
                return

            total_repair_amount = 0

            for r_idx, req in enumerate(recipe.ingredients):
                if not req['destroy']: continue 

                to_remove = req['amount']
                valid_names = req['names']
                removed = 0
                
                locations = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby)
                pref_id = self.modal.selected_ingredients.get(r_idx)
                locations = self.modal.prioritize_locations(locations, pref_id)
                
                for container, key, item, ctype, path in locations:
                    if removed >= to_remove: break

                    if item.name in valid_names and item != target_item:
                        item_qty = item.load if (item.load is not None and item.is_stackable()) else 1
                        take = min(to_remove - removed, item_qty)
                        
                        if item.min_restore is not None and item.max_restore is not None:
                            restore_per_unit = random.randint(item.min_restore, item.max_restore)
                            total_repair_amount += (restore_per_unit * take)
                        
                        if item.is_stackable() and item.load is not None:
                            item.load -= take
                        
                        removed += take
                        
                        if (item.is_stackable() and item.load is not None and item.load <= 0) or (not item.is_stackable() and take > 0):
                            if ctype == 'list': container.pop(key)
                            elif ctype == 'fixed_list': container[key] = None
                            elif ctype == 'dict': container[key] = None
                            elif ctype == 'attr': setattr(container, key, None)
                                
                        if removed >= to_remove: break
            
            if target_ctype == 'list': target_container.pop(target_key)
            elif target_ctype == 'fixed_list': target_container[target_key] = None
            elif target_ctype == 'dict': target_container[target_key] = None
            elif target_ctype == 'attr': setattr(target_container, target_key, None)

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

            display_message(f"Repaired {target_item.name} by {int(restored)} points.")

        self.modal.player.start_action(f"Repairing {recipe.output_name}", recipe.time_required, craft_complete)