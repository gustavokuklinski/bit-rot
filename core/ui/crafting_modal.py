import pygame
import random 
from core.ui.modals import BaseModal
from core.data.config import *
from core.entities.item.item import Item
from core.data.recipe_manager import RecipeManager
from core.ui.tabs import Tabs 

class CraftingModal(BaseModal):
    def __init__(self, surface, modal_data, assets, game):
        super().__init__(surface, modal_data, assets, "Craft (C)")
        self.game = game
        self.player = game.player
        
        self.modal_w = CRAFTING_MODAL_WIDTH
        self.modal_h = CRAFTING_MODAL_HEIGHT
        self.modal_rect.size = (self.modal_w, self.modal_h)
        
        self.list_width = 250
        self.padding = 20
        
        self.selected_recipe = None
        self.warning_message = None

        if 'crafting_scroll_offset' not in self.modal:
            self.modal['crafting_scroll_offset'] = 0
            
        self.visible_items = 14 
        
        if not RecipeManager.RECIPES:
            RecipeManager.load_recipes()
            
        self.recipes = list(RecipeManager.RECIPES)

        self.cached_recipe = None
        self.result_image = None
        self.ingredient_images = {}

        # Tabs Configuration
        self.tabs_data = [
            {'label': "All"},
            {'label': "Craft"},
            {'label': "Repair"}
        ]
        self.tabs_manager = Tabs(surface, self.modal, self.tabs_data, assets)
        
        if 'active_tab' not in self.modal:
            self.modal['active_tab'] = "All"

        # Search State
        self.search_text = ""
        self.search_active = False
        self.search_rect = None

    def handle_event(self, event):
        # [FIXED] Use scaled mouse position for accurate UI collision detection
        mouse_pos = self.game._get_scaled_mouse_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            # 1. Check Tabs
            if self.tabs_manager.check_click(mouse_pos):
                self.modal['crafting_scroll_offset'] = 0 
                return True
            
            # 2. Check Search Bar Focus
            if self.search_rect:
                if self.search_rect.collidepoint(mouse_pos):
                    self.search_active = True
                    # Enable key repeat for smoother backspace/typing
                    pygame.key.set_repeat(500, 50) 
                    return True
                else:
                    self.search_active = False
                    pygame.key.set_repeat() 
        
        elif event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
            elif event.key == pygame.K_RETURN:
                self.search_active = False
                pygame.key.set_repeat()
            elif event.key == pygame.K_ESCAPE:
                self.search_active = False
                pygame.key.set_repeat()
                # Return True to consume the ESC key so it doesn't close the modal immediately
                return True 
            else:
                if len(self.search_text) < 20 and len(event.unicode) > 0 and event.unicode.isprintable():
                    self.search_text += event.unicode
            
            self.modal['crafting_scroll_offset'] = 0 
            return True
            
        return False

    def _has_ingredients(self, recipe, nearby_items=None):
        search_items = self.player.inventory
        if nearby_items:
            search_items = search_items + nearby_items

        for req in recipe.ingredients:
            needed = req['amount']
            valid_names = req['names']
            
            have = sum((item.load if item.load is not None else 1) 
                       for item in search_items 
                       if item.name in valid_names)
            
            if have < needed:
                return False
        return True

    def _get_scrollbar_rects(self, total_items, list_rect):
        if total_items <= self.visible_items:
            return None, None

        track_w = 12
        track_x = list_rect.right - track_w - 2
        track_y = list_rect.top + 2
        track_h = list_rect.height - 4
        
        track_rect = pygame.Rect(track_x, track_y, track_w, track_h)
        
        visible_ratio = self.visible_items / total_items
        handle_h = max(20, int(track_h * visible_ratio))
        
        current_offset = self.modal.get('crafting_scroll_offset', 0)
        
        max_scroll = max(0, total_items - self.visible_items)
        if current_offset > max_scroll:
            current_offset = max_scroll
            self.modal['crafting_scroll_offset'] = current_offset
            
        scroll_pct = current_offset / max_scroll if max_scroll > 0 else 0
        available_track = track_h - handle_h
        handle_y = track_y + int(available_track * scroll_pct)
        
        handle_rect = pygame.Rect(track_x, handle_y, track_w, handle_h)
        return track_rect, handle_rect

    def get_preview_image(self, name):
        try:
            item = Item.create_from_name(name)
            return item.image if item else None
        except Exception:
            return None

    def draw(self):
        # [FIX] Ensure Tabs Manager uses the correct surface (Virtual Screen)
        self.tabs_manager.surface = self.surface

        self.minimized = self.modal.get('minimized', False)
        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)
        
        if self.minimized:
            self.modal_rect.height = self.header_h
        else:
            self.modal_rect.height = self.modal_h

        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        self.minimize_button_rect.topright = (self.close_button_rect.left - 10, self.modal_y + 10)

        self.draw_base()
        
        if self.minimized: 
            close_btn, min_btn = self.get_buttons()
            return None, close_btn, min_btn

        mouse_pos = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]

        # 1. LEFT PANEL: TABS, SEARCH, LIST
        list_x = self.modal_x + self.padding
        
        # Draw Tabs
        self.tabs_manager.draw()
        
        tab_area_height = 35 
        search_y = self.modal_y + self.header_h + tab_area_height + 5 
        search_h = 24
        self.search_rect = pygame.Rect(list_x, search_y, self.list_width, search_h)
        
        s_bg = (20, 20, 20) if self.search_active else (30, 30, 30)
        pygame.draw.rect(self.surface, s_bg, self.search_rect, border_radius=4)
        border_col = (200, 200, 200) if self.search_active else ((100,100,100) if self.search_rect.collidepoint(mouse_pos) else (60,60,60))
        pygame.draw.rect(self.surface, border_col, self.search_rect, 1, border_radius=4)
        
        display_text = self.search_text
        if self.search_active and (pygame.time.get_ticks() // 500) % 2 == 0:
            display_text += "_"
            
        if not self.search_text and not self.search_active:
            display_text = "Search..."
            txt_col = (80, 80, 80)
        else:
            txt_col = WHITE
            
        s_surf = font_small.render(display_text, True, txt_col)
        
        old_clip = self.surface.get_clip()
        self.surface.set_clip(self.search_rect.inflate(-4, -4))
        self.surface.blit(s_surf, (self.search_rect.x + 5, self.search_rect.y + 4))
        self.surface.set_clip(old_clip)

        list_y = search_y + search_h + 10
        list_h = self.modal_h - (list_y - self.modal_y) - 20 
        
        pygame.draw.rect(self.surface, (30, 30, 30), (list_x, list_y, self.list_width, list_h))
        pygame.draw.rect(self.surface, GRAY, (list_x, list_y, self.list_width, list_h), 1)

        filtered_recipes = []
        active_tab = self.modal.get('active_tab', 'All')

        nearby_items = []
        nearby_containers = self.game.find_nearby_containers()
        if nearby_containers:
            for cont in nearby_containers:
                if hasattr(cont, 'inventory') and cont.inventory:
                    nearby_items.extend(cont.inventory)

        filtered_recipes = []
        active_tab = self.modal.get('active_tab', 'All')

        for r in self.recipes:
            craft_type = getattr(r, 'craft_type', 'create')
            if active_tab == "Craft" and craft_type == 'repair': continue
            if active_tab == "Repair" and craft_type != 'repair': continue
            
            if self.search_text:
                if self.search_text.lower() not in r.output_name.lower(): continue
            
            filtered_recipes.append(r)

        filtered_recipes.sort(key=lambda r: (
            not self._has_ingredients(r, None),          # 1. Inventory-only (Priority)
            not self._has_ingredients(r, nearby_items),  # 2. Nearby-only
            r.output_name
        ))

        row_h = 28
        # [FIXED] Cast result to integer to prevent TypeError in range()
        self.visible_items = int(list_h // row_h)

        list_rect = pygame.Rect(list_x, list_y, self.list_width, list_h)
        track_rect, handle_rect = self._get_scrollbar_rects(len(filtered_recipes), list_rect)
        
        self.modal['crafting_track_rect'] = track_rect
        self.modal['crafting_handle_rect'] = handle_rect
        self.modal['crafting_total_items'] = len(filtered_recipes)
        self.modal['crafting_visible_items'] = self.visible_items
        
        item_width_adj = 15 if track_rect else 0
        scroll_offset = self.modal.get('crafting_scroll_offset', 0)
        
        for i in range(self.visible_items):
            idx = i + scroll_offset
            if idx >= len(filtered_recipes): break
            
            recipe = filtered_recipes[idx]
            row_y = list_y + 2 + (i * row_h)
            row_rect = pygame.Rect(list_x + 2, row_y, self.list_width - 4 - item_width_adj, row_h - 2)
            
            is_selected = (self.selected_recipe == recipe)
            is_hovered = row_rect.collidepoint(mouse_pos)
            has_ingredients_local = self._has_ingredients(recipe, None)          # Player only
            has_ingredients_global = self._has_ingredients(recipe, nearby_items) # Player + Nearby
            
            bg_color = (60, 60, 80) if is_selected else ((50, 50, 50) if is_hovered else (30, 30, 30))
            
            # [CHANGED] Text Color Logic
            if is_selected:
                text_color = YELLOW
            elif has_ingredients_local:
                text_color = GREEN   # Can craft with just inventory
            elif has_ingredients_global:
                text_color = YELLOW  # Can craft BUT requires nearby items
            elif is_hovered:
                text_color = WHITE
            else:
                text_color = GRAY
            
            pygame.draw.rect(self.surface, bg_color, row_rect, border_radius=3)
            
            old_clip = self.surface.get_clip()
            self.surface.set_clip(row_rect)
            
            name_surf = font_small.render(recipe.output_name, True, text_color)
            self.surface.blit(name_surf, (row_rect.x + 8, row_rect.y + 6))
            
            self.surface.set_clip(old_clip)
            
            if click and is_hovered and not self.modal.get('is_dragging_scrollbar'):
                self.selected_recipe = recipe

        if track_rect and handle_rect:
            pygame.draw.rect(self.surface, (20, 20, 20), track_rect)
            handle_color = (100, 100, 100)
            if self.modal.get('is_dragging_scrollbar') or handle_rect.collidepoint(mouse_pos):
                handle_color = (140, 140, 140)
            pygame.draw.rect(self.surface, handle_color, handle_rect, border_radius=4)

        # 2. RIGHT PANEL: DETAILS
        details_x = list_x + self.list_width + self.padding
        details_y = list_y 
        details_w = self.modal_w - self.list_width - (self.padding * 3)
        
        active_tooltip_ingredients = None

        if self.selected_recipe:
            if self.selected_recipe != self.cached_recipe:
                self.cached_recipe = self.selected_recipe
                self.result_image = self.get_preview_image(self.selected_recipe.output_name)
                
                self.ingredient_images = {}
                for req in self.selected_recipe.ingredients:
                    primary_name = req['names'][0]
                    self.ingredient_images[primary_name] = self.get_preview_image(primary_name)

            r = self.selected_recipe
            
            self.warning_message = self._validate_ingredients(r, nearby_containers)

            title_surf = font.render(r.output_name, True, WHITE)
            self.surface.blit(title_surf, (details_x, details_y))
            
            if self.result_image:
                scaled_result = pygame.transform.scale(self.result_image, (32, 32))
                self.surface.blit(scaled_result, (details_x + details_w - 40, details_y))

            pygame.draw.line(self.surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)
            
            ing_y = details_y + 50
            lbl = font_small.render("Required Ingredients:", True, GRAY)
            self.surface.blit(lbl, (details_x, ing_y))
            
            curr_y = ing_y + 30
            can_craft = True
            
            for req in r.ingredients:
                needed = req['amount']
                valid_names = req['names'] 
                
                have = sum((item.load if item.load is not None else 1) 
                           for item in self.player.inventory 
                           if item.name in valid_names)
                
                if nearby_items:
                    have += sum((item.load if item.load is not None else 1) 
                           for item in nearby_items 
                           if item.name in valid_names)
                
                color = GREEN if have >= needed else RED
                if have < needed: can_craft = False
                
                primary_name = valid_names[0]
                img = self.ingredient_images.get(primary_name)
                
                text_x = details_x + 10
                if img:
                    scaled_icon = pygame.transform.scale(img, (32, 32))
                    self.surface.blit(scaled_icon, (text_x, curr_y))
                    text_x += 35

                if len(valid_names) > 1:
                    name_display = f"{primary_name} (Any)"
                else:
                    name_display = primary_name

                row_rect = pygame.Rect(details_x, curr_y, details_w, 32)
                if row_rect.collidepoint(mouse_pos) and len(valid_names) > 1:
                    active_tooltip_ingredients = valid_names
                    color = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))

                txt_str = f" {name_display}: {int(have)} / Need: {needed}"
                ing_surf = font_small.render(txt_str, True, color)
                self.surface.blit(ing_surf, (text_x, curr_y + 8))
                curr_y += 35
                
            # 1. Define Button Position (Fixed at bottom)
            btn_h = 40
            bottom_y = details_y + list_h
            btn_rect = pygame.Rect(details_x, bottom_y - btn_h, details_w, btn_h)
            
            # Cursor for elements strictly above the button
            element_cursor_y = btn_rect.top - 5

            # 2. Draw Loading Bar (Only if action is active)
            if self.player.action_timer > 0 and self.player.action_total_time > 0:
                bar_h = 10
                # Background
                pygame.draw.rect(self.surface, (30, 30, 30), (details_x, element_cursor_y - bar_h, details_w, bar_h))
                # Fill
                progress = 1.0 - (self.player.action_timer / self.player.action_total_time)
                fill_w = int(details_w * progress)
                pygame.draw.rect(self.surface, GREEN, (details_x, element_cursor_y - bar_h, fill_w, bar_h))
                
                element_cursor_y -= (bar_h + 10) # Move cursor up

            # 3. Magazine Requirement Text (If applicable)
            recipe_known = True
            if r.magazine:
                is_read = r.magazine in self.player.known_recipes
                if not is_read:
                    recipe_known = False
                    can_craft = False 
                
                mag_color = GREEN if is_read else RED
                mag_text = f"Requires Magazine: {r.magazine}"
                mag_surf = font_small.render(mag_text, True, mag_color)
                
                element_cursor_y -= 20 # Height of text
                self.surface.blit(mag_surf, (details_x, element_cursor_y))
                element_cursor_y -= 5 # Padding

            # 4. Craft Time Display (Always visible above everything else)
            time_text = f"Time: {r.time_required}s"
            time_surf = font_small.render(time_text, True, GRAY)
            element_cursor_y -= 20
            self.surface.blit(time_surf, (details_x, element_cursor_y))

            # 5. Warning Message Display
            if self.warning_message:
                warn_surf = font_small.render(self.warning_message, True, RED)
                # Ensure it fits or wrap? For now, simple render above Time
                element_cursor_y -= 20
                self.surface.blit(warn_surf, (details_x, element_cursor_y))

            # 6. Draw Button (Standard logic)
            btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
            border_color = WHITE if can_craft else GRAY
            
            pygame.draw.rect(self.surface, btn_color, btn_rect, border_radius=5)
            pygame.draw.rect(self.surface, border_color, btn_rect, 1, border_radius=5)
            
            if not recipe_known:
                btn_text = "UNKNOWN RECIPE"
            elif can_craft:
                if getattr(r, 'craft_type', 'create') == 'repair':
                    btn_text = "REPAIR ITEM"
                else:
                    btn_text = "CRAFT ITEM"
            else:
                btn_text = "MISSING RESOURCES"

            lbl = font.render(btn_text, True, WHITE if can_craft else GRAY)
            text_rect = lbl.get_rect(center=btn_rect.center)
            self.surface.blit(lbl, text_rect)
            
            if can_craft and click and not self.modal.get('is_dragging_scrollbar'):
                mouse_rect = pygame.Rect(mouse_pos[0], mouse_pos[1], 1, 1)
                if mouse_rect.colliderect(btn_rect):
                    self._craft(r)
        else:
            info_txt = font.render("Select a recipe to view details", True, GRAY)
            text_rect = info_txt.get_rect(center=(details_x + details_w//2, details_y + 100))
            self.surface.blit(info_txt, text_rect)

        if active_tooltip_ingredients:
            self._draw_ingredient_tooltip(active_tooltip_ingredients, mouse_pos)

        close_btn, min_btn = self.get_buttons()
        return None, close_btn, min_btn

    # [ADDED] Missing tooltip method
    def _draw_ingredient_tooltip(self, names, pos):
        line_height = 20
        padding = 10
        surfaces = []
        max_w = 0
        for name in names:
            s = font_small.render(f"- {name}", True, WHITE)
            surfaces.append(s)
            if s.get_width() > max_w:
                max_w = s.get_width()
        
        tt_w = max_w + (padding * 2)
        tt_h = (len(surfaces) * line_height) + (padding * 2)
        
        # Ensure tooltip stays within screen bounds
        x, y = pos[0] + 15, pos[1] + 15
        if x + tt_w > VIRTUAL_SCREEN_WIDTH:
            x = pos[0] - tt_w - 5
        if y + tt_h > VIRTUAL_GAME_HEIGHT:
            y = pos[1] - tt_h - 5
            
        tt_rect = pygame.Rect(x, y, tt_w, tt_h)
        pygame.draw.rect(self.surface, (20, 20, 25, 230), tt_rect)
        pygame.draw.rect(self.surface, (100, 100, 100), tt_rect, 1)
        curr_y = y + padding
        for s in surfaces:
            self.surface.blit(s, (x + padding, curr_y))
            curr_y += line_height


    def _validate_ingredients(self, recipe, nearby_containers=None):
        source_inventories_check = [self.player.inventory]
        
        if nearby_containers is None:
            nearby_containers = self.game.find_nearby_containers()
            
        if nearby_containers:
            for obj in nearby_containers:
                if hasattr(obj, 'inventory') and obj.inventory:
                    source_inventories_check.append(obj.inventory)

        for req in recipe.ingredients:
            if not req['destroy']: 
                continue

            to_remove = req['amount']
            valid_names = req['names']
            removed_check = 0
            
            for inv in source_inventories_check:
                if removed_check >= to_remove: break

                for i in range(len(inv) - 1, -1, -1):
                    item = inv[i]
                    if item.name in valid_names:
                        # Validation: Container with items
                        if hasattr(item, 'inventory') and item.inventory:
                             return f"Cannot use {item.name}: It contains items!"

                        item_qty = item.load if item.load is not None else 1
                        take = min(to_remove - removed_check, item_qty)
                        removed_check += take
                        
                        if removed_check >= to_remove:
                            break
        return None


    def _craft(self, recipe):
        if self.player.action_timer > 0: return

        # --- Validation Check ---
        error = self._validate_ingredients(recipe)
        if error:
            self.warning_message = error
            return

        def craft_complete():
            source_inventories = [self.player.inventory]
            nearby = self.game.find_nearby_containers()
            if nearby:
                for obj in nearby:
                    if hasattr(obj, 'inventory') and obj.inventory:
                        source_inventories.append(obj.inventory)

            if getattr(recipe, 'craft_type', 'create') == 'repair':
                target_item = None
                for item in self.player.inventory:
                    if item.name == recipe.output_name and item.durability is not None and item.durability < item.max_durability:
                        target_item = item
                        break
                
                if not target_item:
                    from core.messages import display_message_player
                    display_message_player(f"No damaged {recipe.output_name} found in inventory.")
                    return

                total_repair_amount = 0

                for req in recipe.ingredients:
                    if not req['destroy']: 
                        continue 

                    to_remove = req['amount']
                    valid_names = req['names']
                    removed = 0
                    
                    for inv in source_inventories:
                        if removed >= to_remove: break

                        for i in range(len(inv) - 1, -1, -1):
                            item = inv[i]
                            
                            if item.name in valid_names:
                                item_qty = item.load if item.load is not None else 1
                                take = min(to_remove - removed, item_qty)
                                
                                if item.min_restore is not None and item.max_restore is not None:
                                    restore_per_unit = random.randint(item.min_restore, item.max_restore)
                                    total_repair_amount += (restore_per_unit * take)
                                
                                if item.load is not None:
                                    item.load -= take
                                
                                removed += take
                                
                                if (item.load is not None and item.load <= 0) or (item.load is None and take > 0):
                                    inv.pop(i)
                                    
                                if removed >= to_remove:
                                    break
                
                old_durability = target_item.durability
                target_item.durability = min(target_item.max_durability, target_item.durability + total_repair_amount)
                restored = target_item.durability - old_durability
                
                if hasattr(self.player, 'progression'):
                    self.player.progression.add_xp(self.player, 'maintenance', 15)

                from core.messages import display_message_player
                display_message_player(f"Repaired {target_item.name} by {int(restored)} points.")

            else:
                for req in recipe.ingredients:
                    
                    if not req['destroy']:
                        continue

                    to_remove = req['amount']
                    valid_names = req['names']
                    removed = 0
                    
                    for inv in source_inventories:
                        if removed >= to_remove: break

                        for i in range(len(inv) - 1, -1, -1):
                            item = inv[i]
                            
                            if item.name in valid_names:
                                item_qty = item.load if item.load is not None else 1
                                take = min(to_remove - removed, item_qty)
                                
                                if item.load is not None:
                                    item.load -= take
                                
                                removed += take
                                
                                if (item.load is not None and item.load <= 0) or (item.load is None and take > 0):
                                    inv.pop(i)
                                    
                                if removed >= to_remove:
                                    break
                
                result = Item.create_from_name(recipe.output_name)
                if result:
                    result.load = recipe.output_amount
                    if len(self.player.inventory) < self.player.base_inventory_slots:
                        self.player.inventory.append(result)
                    else:
                        self.game.items_on_ground.append(result)
                        result.x, result.y = self.player.x, self.player.y
                        result.rect.topleft = (result.x, result.y)
                    from core.messages import display_message_player
                    display_message_player(f"Successfully crafted {result.name}!")

        verb = "Repairing" if getattr(recipe, 'craft_type', 'create') == 'repair' else "Crafting"
        self.player.start_action(f"{verb} {recipe.output_name}", recipe.time_required, craft_complete)