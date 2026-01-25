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
        self.scroll_offset = 0
        self.visible_items = 14  # Number of recipes visible at once
        
        # Cache known recipes
        self.known_recipes = RecipeManager.get_known_recipes(self.player.known_recipes)

    def handle_events(self, event):
        """Handle scrolling and specific inputs."""
        # Note: BaseModal does not have handle_events, so we removed the super() call to prevent crashes.
        # super().handle_events(event) 
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Scroll Wheel Logic
            if self.modal_rect.collidepoint(pygame.mouse.get_pos()):
                if event.button == 4: # Scroll Up
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif event.button == 5: # Scroll Down
                    max_scroll = max(0, len(self.known_recipes) - self.visible_items)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 1)

    def draw(self):
        # 1. Sync Minimization State
        # We must check the shared modal data to see if the minimize button was clicked externally
        self.minimized = self.modal.get('minimized', False)

        # 2. Update Modal Positions
        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)
        
        # 3. Update Dimensions based on State
        # If minimized, shrink the rect so the border draws correctly and clicks pass through below
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

        # =================================================
        # 1. LEFT PANEL: RECIPE LIST
        # =================================================
        list_x = self.modal_x + self.padding
        list_y = self.modal_y + 50
        list_h = self.modal_h - 70
        
        # Draw Background for List
        pygame.draw.rect(self.surface, (30, 30, 30), (list_x, list_y, self.list_width, list_h))
        pygame.draw.rect(self.surface, GRAY, (list_x, list_y, self.list_width, list_h), 1)

        # Draw List Items
        row_h = 28
        for i in range(self.visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.known_recipes): break
            
            recipe = self.known_recipes[idx]
            row_y = list_y + 2 + (i * row_h)
            row_rect = pygame.Rect(list_x + 2, row_y, self.list_width - 4, row_h - 2)
            
            # Highlight Logic
            is_selected = (self.selected_recipe == recipe)
            is_hovered = row_rect.collidepoint(mouse_pos)
            
            bg_color = (60, 60, 80) if is_selected else ((50, 50, 50) if is_hovered else (30, 30, 30))
            text_color = YELLOW if is_selected else (WHITE if is_hovered else GRAY)
            
            pygame.draw.rect(self.surface, bg_color, row_rect, border_radius=3)
            
            # Truncate text if too long
            name_surf = font_small.render(recipe.output_name, True, text_color)
            self.surface.blit(name_surf, (row_rect.x + 8, row_rect.y + 6))
            
            # Select Recipe on Click
            if click and is_hovered:
                self.selected_recipe = recipe

        # =================================================
        # 2. RIGHT PANEL: DETAILS
        # =================================================
        details_x = list_x + self.list_width + self.padding
        details_y = list_y
        details_w = self.modal_w - self.list_width - (self.padding * 3)
        
        if self.selected_recipe:
            r = self.selected_recipe
            
            # Title
            title_surf = font.render(r.output_name, True, WHITE)
            self.surface.blit(title_surf, (details_x, details_y))
            
            pygame.draw.line(self.surface, GRAY, (details_x, details_y + 35), (details_x + details_w, details_y + 35), 1)
            
            # Ingredients Header
            ing_y = details_y + 50
            lbl = font_small.render("Required Ingredients:", True, GRAY)
            self.surface.blit(lbl, (details_x, ing_y))
            
            # Ingredients List with Live Check
            curr_y = ing_y + 30
            can_craft = True
            
            for req in r.ingredients:
                needed = req['amount']
                name = req['name']
                
                # Check Player Inventory
                have = sum(item.load for item in self.player.inventory if item.name == name)
                
                # Color Logic
                color = GREEN if have >= needed else RED
                if have < needed: can_craft = False
                
                txt_str = f"• {name}: {int(have)} / {needed}"
                ing_surf = font_small.render(txt_str, True, color)
                self.surface.blit(ing_surf, (details_x + 10, curr_y))
                curr_y += 25
                
            # Craft Button (Bottom Right)
            btn_h = 40
            btn_rect = pygame.Rect(details_x, details_y + list_h - btn_h, details_w, btn_h)
            
            btn_color = (0, 100, 0) if can_craft else (60, 60, 60)
            border_color = WHITE if can_craft else GRAY
            
            pygame.draw.rect(self.surface, btn_color, btn_rect, border_radius=5)
            pygame.draw.rect(self.surface, border_color, btn_rect, 1, border_radius=5)
            
            btn_text = "CRAFT ITEM" if can_craft else "MISSING RESOURCES"
            lbl = font.render(btn_text, True, WHITE if can_craft else GRAY)
            text_rect = lbl.get_rect(center=btn_rect.center)
            self.surface.blit(lbl, text_rect)
            
            # Craft Action
            if can_craft and click:
                mouse_rect = pygame.Rect(mouse_pos[0], mouse_pos[1], 1, 1)
                if mouse_rect.colliderect(btn_rect):
                    self._craft(r)
                    
        else:
            # Empty State
            info_txt = font.render("Select a recipe to view details", True, GRAY)
            text_rect = info_txt.get_rect(center=(details_x + details_w//2, details_y + 100))
            self.surface.blit(info_txt, text_rect)

        close_btn, min_btn = self.get_buttons()
        return None, close_btn, min_btn

    def _craft(self, recipe):
        if self.player.action_timer > 0: return

        def craft_complete():
            # Deduct Ingredients from Inventory
            for req in recipe.ingredients:
                to_remove = req['amount']
                removed = 0
                
                # Iterate backwards to safely remove
                for i in range(len(self.player.inventory) - 1, -1, -1):
                    item = self.player.inventory[i]
                    if item.name == req['name']:
                        take = min(to_remove - removed, item.load)
                        item.load -= take
                        removed += take
                        
                        if item.load <= 0:
                            self.player.inventory.pop(i)
                            
                        if removed >= to_remove:
                            break
            
            # Create Result
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

        # Start Action Timer
        self.player.start_action(f"Crafting {recipe.output_name}", recipe.time_required, craft_complete)