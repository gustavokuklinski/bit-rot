# core/ui/crafting_craft_tab.py
import pygame
import random
from core.data.config import *
from core.entities.item.item import Item
from core.messages import display_message
from core.data.localization import tr
class CraftingCraftTab:
    def __init__(self, modal):
        self.modal = modal

    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            craft_type = getattr(r, 'craft_type', 'create')
            if craft_type in ('repair', 'dismantle'): continue
            
            if search_text and search_text.lower() not in r.output_name.lower(): continue
            filtered.append(r)
        return filtered

    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        r = self.modal.selected_recipe
        surface = self.modal.surface
        
        # Target Title
        title_surf = font.render(r.output_name, False, WHITE)
        surface.blit(title_surf, (details_x, details_y))
        
        if self.modal.result_image:
            scaled_result = pygame.transform.scale(self.modal.result_image, (32, 32))
            surface.blit(scaled_result, (details_x + details_w - 40, details_y))

        pygame.draw.line(surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)
        
        # Ingredients list
       # Ingredients list
        # Ingredients list
        ing_y = details_y + 50
        lbl = font_14.render(tr('ui', "Required Ingredients:"), False, GRAY)
        surface.blit(lbl, (details_x, ing_y))
        
        curr_y = ing_y + 30
        col_width = details_w // 2  # Split the details area perfectly in half
        
        can_craft = True
        active_tooltip_ingredients = None
        
        for r_idx, req in enumerate(r.ingredients):
            needed = req['amount']
            valid_names = req['names'] 
            
            have = sum((item.load if (item.load is not None and item.is_stackable()) else 1) 
                       for item in player_items 
                       if tr('item', item.name) in valid_names)
            
            if nearby_items:
                have += sum((item.load if (item.load is not None and item.is_stackable()) else 1) 
                       for item in nearby_items 
                       if tr('item', item.name) in valid_names)
            
            color = GREEN if have >= needed else RED
            if have < needed: can_craft = False
            
            primary_name = valid_names[0]
            img = self.modal.ingredient_images.get(primary_name)
            name_display = primary_name if len(valid_names) == 1 else f"{primary_name}"

            sel_id = self.modal.selected_ingredients.get(r_idx)
            if sel_id:
                locs = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
                for container, key, item, ctype, path in locs:
                    if item.id == sel_id:
                        name_display = f"[*] {tr('item', item.name)}"
                        img = item.image
                        break

            # 1. Determine which column we are drawing in (Left = Even, Right = Odd)
            is_right_col = (r_idx % 2 == 1)
            
            # 2. Set X coordinate based on column
            current_x = (details_x + 10 + col_width) if is_right_col else (details_x + 10)

            txt_str = f" {name_display}: {int(have)}/{needed}"
            text_width = font_14.render(txt_str, False, color).get_width()
            
            # Calculate item width, but cap it so hover bounds don't leak into the next column
            item_width = min((35 if img else 0) + text_width + 10, col_width - 15)
            
            row_rect = pygame.Rect(current_x, curr_y, item_width, 32)
            
            if row_rect.collidepoint(mouse_pos):
                active_tooltip_ingredients = valid_names
                color = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))
                pygame.draw.rect(surface, (50,50,50), row_rect, border_radius=3)
                
                if click and not self.modal.dropdown_state['active']:
                    opts = []
                    itms = []
                    locs = self.modal._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
                    for container, key, item, ctype, path in locs:
                        if tr('item', item.name) in valid_names:
                            qty = item.load if item.is_stackable() else f"Dur: {int(item.durability or 0)}"
                            opts.append(f"{tr('item', item.name)} ({qty}) - {' > '.join(path)}")
                            itms.append(item.id)
                    if opts:
                        self.modal.dropdown_state.update({
                            'active': True, 'options': opts, 'items': itms, 
                            'req_idx': r_idx, 'position': mouse_pos
                        })

            # Draw the Icon and Text
            draw_x = current_x
            if img:
                scaled_icon = pygame.transform.scale(img, (32, 32))
                surface.blit(scaled_icon, (draw_x, curr_y))
                draw_x += 35

            ing_surf = font_14.render(txt_str, False, color)
            surface.blit(ing_surf, (draw_x, curr_y + 8))
            
            # 3. ONLY drop down to the next line if we just finished the Right Column
            if is_right_col:
                curr_y += 35
                
        # (The rest of your code remains exactly the same starting from btn_h = 40)
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
            # 1. Move Y up ONCE for the entire single line
            element_cursor_y -= 25 
            
            # 2. Draw the Header on the left
            head_txt = tr('ui', "OR Skills:") if r.magazine else tr('ui', "Requires Skills:")
            head_surf = font_14.render(head_txt, False, WHITE)
            surface.blit(head_surf, (details_x, element_cursor_y))
            
            # 3. Start drawing the skills exactly to the right of the Header
            current_skill_x = details_x + head_surf.get_width() + 10
            
            items = list(r.req_level.items())
            for idx, (attr, lvl) in enumerate(items):
                attr_name = attr.replace('_', ' ').capitalize()
                attr_name_tr = tr('ui', attr_name) 
                p_lvl = self.modal.player.progression.get_level(attr)
                s_color = GREEN if p_lvl >= lvl else RED
                
                # Render Skill Text
                txt = f"{attr_name_tr}: {p_lvl}/{int(lvl)}"
                s_surf = font_14.render(txt, False, s_color)
                
                # Notice how Y never changes here, only X!
                surface.blit(s_surf, (current_skill_x, element_cursor_y))
                current_skill_x += s_surf.get_width()
                
                # Draw the " - " separator if there are more skills
                if idx < len(items) - 1:
                    sep_surf = font_14.render(" - ", False, GRAY)
                    surface.blit(sep_surf, (current_skill_x, element_cursor_y))
                    current_skill_x += sep_surf.get_width()

        if r.magazine:
            mag_color = GREEN if knows_magazine else RED
            mag_text = f"{tr('ui', 'Requires Magazine:')} {r.magazine}"
            mag_surf = font_14.render(mag_text, False, mag_color)
            element_cursor_y -= 20
            surface.blit(mag_surf, (details_x, element_cursor_y))
            element_cursor_y -= 5 

        time_text = f"{tr('ui', 'Time:')} {r.time_required}s"
        time_surf = font_14.render(time_text, False, GRAY)
        element_cursor_y -= 20
        surface.blit(time_surf, (details_x, element_cursor_y))

        if self.modal.warning_message:
            warn_surf = font_14.render(self.modal.warning_message, False, RED)
            element_cursor_y -= 20
            surface.blit(warn_surf, (details_x, element_cursor_y))

        btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
        border_color = WHITE if can_craft else GRAY
        
        pygame.draw.rect(surface, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(surface, border_color, btn_rect, 1, border_radius=5)
        
        if not is_unlocked:
            if r.magazine and not knows_magazine and r.req_level: btn_text = tr('ui', "LOCKED (MAG/SKILL)")
            elif r.magazine: btn_text = tr('ui', "NEED MAGAZINE")
            else: btn_text = tr('ui', "NEED SKILLS")
        elif can_craft:
            btn_text = tr('ui', "CRAFT ITEM") # Use "REPAIR ITEM" and "DISMANTLE" for the other tabs
        else:
            btn_text = tr('ui', "MISSING RESOURCES")

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

                    if tr('item', item.name) in valid_names:
                        item_qty = item.load if (item.load is not None and item.is_stackable()) else 1
                        take = min(to_remove - removed, item_qty)
                        
                        if item.is_stackable() and item.load is not None:
                            item.load -= take
                        
                        removed += take
                        
                        if (item.is_stackable() and item.load is not None and item.load <= 0) or (not item.is_stackable() and take > 0):
                            if ctype == 'list': container.pop(key)
                            elif ctype == 'fixed_list': container[key] = None
                            elif ctype == 'dict': container[key] = None
                            elif ctype == 'attr': setattr(container, key, None)
                                
                        if removed >= to_remove: break
            
            created_items_log = []
            
            for res in recipe.results:
                if res['chance'] < 1.0 and random.random() > res['chance']: continue
                    
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
                msg = ", ".join(created_items_log)
                display_message(f"{tr('msg', 'Crafted:')} {msg}")
            else:
                display_message(tr('msg', "Crafting yielded nothing."))

        self.modal.player.start_action(f"Crafting {recipe.output_name}", recipe.time_required, craft_complete)