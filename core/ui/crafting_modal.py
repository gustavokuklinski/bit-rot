import pygame
from core.ui.modals import BaseModal
from core.data.config import *
from core.entities.item.item import Item
from core.data.recipe_manager import RecipeManager

class CraftingModal(BaseModal):
    def __init__(self, surface, modal_data, assets, game):
        super().__init__(surface, modal_data, assets, "Crafting Station")
        self.game = game
        self.player = game.player
        
        # Dimensions for Split Layout
        self.modal_w = CRAFTING_MODAL_WIDTH
        self.modal_h = CRAFTING_MODAL_HEIGHT
        self.modal_rect.size = (self.modal_w, self.modal_h)
        
        # Layout Config
        self.list_width = 250
        self.padding = 20
        
        # Data
        self.selected_recipe = None
        
        # Ensure persistent scroll state in modal data
        if 'crafting_scroll_offset' not in self.modal:
            self.modal['crafting_scroll_offset'] = 0
            
        self.visible_items = 14  # Number of recipes visible at once
        
        # Ensure recipes are loaded
        if not RecipeManager.RECIPES:
            RecipeManager.load_recipes()
            
        # --- CHANGED: Create a local list copy to allow sorting ---
        self.recipes = list(RecipeManager.RECIPES)
        # ----------------------------------------------------------

        # Image Cache
        self.cached_recipe = None
        self.result_image = None
        self.ingredient_images = {}

    # --- NEW: Helper to check ingredients (used for sorting and color) ---
    def _has_ingredients(self, recipe):
        """Returns True if player has all ingredients for this recipe."""
        for req in recipe.ingredients:
            needed = req['amount']
            valid_names = req['names']
            
            # Sum quantity of all matching items in inventory
            have = sum((item.load if item.load is not None else 1) 
                       for item in self.player.inventory 
                       if item.name in valid_names)
            
            if have < needed:
                return False
        return True
    # -------------------------------------------------------------------

    def _get_scrollbar_rects(self):
        """Calculates the track and handle rectangles based on current state."""
        total_items = len(self.recipes)
        if total_items <= self.visible_items:
            return None, None

        mx, my = self.modal['position']
        
        # Scrollbar Geometry
        list_x = mx + self.padding
        list_y = my + 50
        list_h = self.modal_h - 70
        
        track_w = 12
        track_x = list_x + self.list_width - track_w - 2
        track_y = list_y + 2
        track_h = list_h - 4
        
        track_rect = pygame.Rect(track_x, track_y, track_w, track_h)

        # Handle Height
        visible_ratio = self.visible_items / total_items
        handle_h = max(20, int(track_h * visible_ratio))
        
        # Retrieve offset from modal data
        current_offset = self.modal.get('crafting_scroll_offset', 0)
        
        # Handle Y Position
        max_scroll = total_items - self.visible_items
        scroll_pct = current_offset / max_scroll if max_scroll > 0 else 0
        
        available_track = track_h - handle_h
        handle_y = track_y + int(available_track * scroll_pct)
        
        handle_rect = pygame.Rect(track_x, handle_y, track_w, handle_h)
        
        return track_rect, handle_rect

    def get_preview_image(self, name):
        """Helper to get the sprite image for an item name."""
        try:
            item = Item.create_from_name(name)
            return item.image if item else None
        except Exception:
            return None

    def draw(self):
        # 1. Sync Minimization State
        self.minimized = self.modal.get('minimized', False)

        # 2. Update Modal Positions
        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)
        
        # 3. Update Dimensions based on State
        if self.minimized:
            self.modal_rect.height = self.header_h
        else:
            self.modal_rect.height = self.modal_h

        # Update Buttons
        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        self.minimize_button_rect.topright = (self.close_button_rect.left - 10, self.modal_y + 10)

        self.draw_base()
        
        if self.minimized: 
            close_btn, min_btn = self.get_buttons()
            return None, close_btn, min_btn

        mouse_pos = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()[0]

        # --- NEW: Dynamic Sorting ---
        # Sort keys: 
        # 1. Has Ingredients (True first, so we use 'not' because False < True)
        # 2. Alphabetical by name
        self.recipes.sort(key=lambda r: (not self._has_ingredients(r), r.output_name))
        # ----------------------------

        # =================================================
        # 1. LEFT PANEL: RECIPE LIST
        # =================================================
        list_x = self.modal_x + self.padding
        list_y = self.modal_y + 50
        list_h = self.modal_h - 70
        
        # Draw Background for List
        pygame.draw.rect(self.surface, (30, 30, 30), (list_x, list_y, self.list_width, list_h))
        pygame.draw.rect(self.surface, GRAY, (list_x, list_y, self.list_width, list_h), 1)

        # Calculate Scrollbar Rects for Drawing
        track_rect, handle_rect = self._get_scrollbar_rects()
        
        # Export scrollbar data to modal dict for mouse.py to use
        self.modal['crafting_track_rect'] = track_rect
        self.modal['crafting_handle_rect'] = handle_rect
        self.modal['crafting_total_items'] = len(self.recipes)
        self.modal['crafting_visible_items'] = self.visible_items
        
        # Adjust list item width to not overlap scrollbar
        item_width_adj = 15 if track_rect else 0

        # Draw List Items
        row_h = 28
        
        # Use offset from modal data
        scroll_offset = self.modal.get('crafting_scroll_offset', 0)
        
        for i in range(self.visible_items):
            idx = i + scroll_offset
            if idx >= len(self.recipes): break
            
            recipe = self.recipes[idx]
            row_y = list_y + 2 + (i * row_h)
            row_rect = pygame.Rect(list_x + 2, row_y, self.list_width - 4 - item_width_adj, row_h - 2)
            
            # Highlight Logic
            is_selected = (self.selected_recipe == recipe)
            is_hovered = row_rect.collidepoint(mouse_pos)
            has_ingredients = self._has_ingredients(recipe)
            
            bg_color = (60, 60, 80) if is_selected else ((50, 50, 50) if is_hovered else (30, 30, 30))
            
            # --- MODIFIED: Text Color Logic ---
            if is_selected:
                text_color = YELLOW
            elif has_ingredients:
                text_color = GREEN
            elif is_hovered:
                text_color = WHITE
            else:
                text_color = GRAY
            # ----------------------------------
            
            pygame.draw.rect(self.surface, bg_color, row_rect, border_radius=3)
            
            # Truncate text if too long
            old_clip = self.surface.get_clip()
            self.surface.set_clip(row_rect)
            
            name_surf = font_small.render(recipe.output_name, True, text_color)
            self.surface.blit(name_surf, (row_rect.x + 8, row_rect.y + 6))
            
            self.surface.set_clip(old_clip)
            
            # Select Recipe on Click (if not dragging scrollbar)
            if click and is_hovered and not self.modal.get('is_dragging_scrollbar'):
                self.selected_recipe = recipe

        # Draw Scrollbar
        if track_rect and handle_rect:
            pygame.draw.rect(self.surface, (20, 20, 20), track_rect) # Track
            
            # Handle Color
            handle_color = (100, 100, 100)
            if self.modal.get('is_dragging_scrollbar') or handle_rect.collidepoint(mouse_pos):
                handle_color = (140, 140, 140)
            
            pygame.draw.rect(self.surface, handle_color, handle_rect, border_radius=4)

        # =================================================
        # 2. RIGHT PANEL: DETAILS
        # =================================================
        details_x = list_x + self.list_width + self.padding
        details_y = list_y
        details_w = self.modal_w - self.list_width - (self.padding * 3)
        
        # Helper to store tooltip data for drawing later
        active_tooltip_ingredients = None

        if self.selected_recipe:
            if self.selected_recipe != self.cached_recipe:
                self.cached_recipe = self.selected_recipe
                self.result_image = self.get_preview_image(self.selected_recipe.output_name)
                
                # Cache images using the first valid name
                self.ingredient_images = {}
                for req in self.selected_recipe.ingredients:
                    primary_name = req['names'][0]
                    self.ingredient_images[primary_name] = self.get_preview_image(primary_name)

            r = self.selected_recipe
            
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
                
                # Check if player has ANY item in the valid_names list
                have = sum((item.load if item.load is not None else 1) 
                           for item in self.player.inventory 
                           if item.name in valid_names)
                
                color = GREEN if have >= needed else RED
                if have < needed: can_craft = False
                
                # Use the first name for display/icon purposes
                primary_name = valid_names[0]
                img = self.ingredient_images.get(primary_name)
                
                text_x = details_x + 10
                if img:
                    scaled_icon = pygame.transform.scale(img, (32, 32))
                    self.surface.blit(scaled_icon, (text_x, curr_y))
                    text_x += 35

                # Adjust text if multiple options exist
                if len(valid_names) > 1:
                    name_display = f"{primary_name} (Any)"
                else:
                    name_display = primary_name

                # Hover detection for "Any" ingredients
                row_rect = pygame.Rect(details_x, curr_y, details_w, 32)
                if row_rect.collidepoint(mouse_pos) and len(valid_names) > 1:
                    active_tooltip_ingredients = valid_names
                    color = (min(255, color[0]+50), min(255, color[1]+50), min(255, color[2]+50))

                txt_str = f" {name_display}: {int(have)} / Need: {needed}"
                ing_surf = font_small.render(txt_str, True, color)
                self.surface.blit(ing_surf, (text_x, curr_y + 8))
                curr_y += 35
                
            # Magazine Requirement Logic
            recipe_known = True
            if r.magazine:
                is_read = r.magazine in self.player.known_recipes
                if not is_read:
                    recipe_known = False
                    can_craft = False 
                
                mag_color = GREEN if is_read else RED
                mag_text = f"Requires Magazine: {r.magazine}"
                mag_surf = font_small.render(mag_text, True, mag_color)
                
                mag_y = details_y + list_h - 65 
                self.surface.blit(mag_surf, (details_x, mag_y))

            btn_h = 40
            btn_rect = pygame.Rect(details_x, details_y + list_h - btn_h, details_w, btn_h)
            
            btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
            border_color = WHITE if can_craft else GRAY
            
            pygame.draw.rect(self.surface, btn_color, btn_rect, border_radius=5)
            pygame.draw.rect(self.surface, border_color, btn_rect, 1, border_radius=5)
            
            if not recipe_known:
                btn_text = "UNKNOWN RECIPE"
            elif can_craft:
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

        # Draw Tooltip for Multi-Ingredient Lists
        if active_tooltip_ingredients:
            self._draw_ingredient_tooltip(active_tooltip_ingredients, mouse_pos)

        close_btn, min_btn = self.get_buttons()
        return None, close_btn, min_btn

    def _draw_ingredient_tooltip(self, names, pos):
        """Draws a floating list of acceptable items."""
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

    def _craft(self, recipe):
        if self.player.action_timer > 0: return

        def craft_complete():
            for req in recipe.ingredients:
                
                if not req['destroy']:
                    continue

                to_remove = req['amount']
                valid_names = req['names']
                removed = 0
                
                for i in range(len(self.player.inventory) - 1, -1, -1):
                    item = self.player.inventory[i]
                    
                    if item.name in valid_names:
                        item_qty = item.load if item.load is not None else 1
                        take = min(to_remove - removed, item_qty)
                        
                        if item.load is not None:
                            item.load -= take
                        
                        removed += take
                        
                        if (item.load is not None and item.load <= 0) or (item.load is None and take > 0):
                            self.player.inventory.pop(i)
                            
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

        self.player.start_action(f"Crafting {recipe.output_name}", recipe.time_required, craft_complete)