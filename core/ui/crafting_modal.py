import pygame
from core.ui.modals import BaseModal
from core.data.config import *
from core.entities.item.item import Item
from core.data.recipe_manager import RecipeManager
from core.ui.container_modal import get_container_slot_rect

class CraftingModal(BaseModal):
    def __init__(self, surface, modal_data, assets, game):
        super().__init__(surface, modal_data, assets, "Crafting Station")
        self.game = game
        self.player = game.player
        
        # Internal container for ingredients (4 slots)
        self.ingredients_container = Item("Ingredients", "container", capacity=4)
        self.ingredients_container.inventory = [] 
        
        self.selected_recipe = None
        self.scroll_offset = 0
        
        # Dimensions
        self.modal_w = 500
        self.modal_h = 400
        self.modal_rect.size = (self.modal_w, self.modal_h)
        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        
        # Cache for result item to avoid recreating it every frame
        self.preview_item = None
        self.last_selected_recipe = None

    def draw(self):
        
        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)
        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)
        # [FIXED] Update minimize button position so it follows the window
        self.minimize_button_rect.topright = (self.close_button_rect.left - 10, self.modal_y + 10)

        self.draw_base()
        
        # [FIXED] Return buttons if minimized
        if self.minimized: 
            close_btn, min_btn = self.get_buttons()
            return None, close_btn, min_btn

        # 1. Draw Ingredient Slots (Left Side)
        slot_start_x = self.modal_x + 20
        slot_start_y = self.modal_y + 50
        
        text = font.render("Ingredients:", True, WHITE)
        self.surface.blit(text, (slot_start_x, slot_start_y - 25))
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Manually draw slots
        for i in range(4):
            slot_rect = get_container_slot_rect((slot_start_x, slot_start_y), i)
            
            # Hover effect
            color = (60, 60, 60)
            if slot_rect.collidepoint(mouse_pos):
                color = (80, 80, 80)
            
            pygame.draw.rect(self.surface, color, slot_rect)
            pygame.draw.rect(self.surface, GRAY, slot_rect, 1)
            
            # Draw Item if present
            if i < len(self.ingredients_container.inventory):
                item = self.ingredients_container.inventory[i]
                if item and item.image:
                    scaled_img = pygame.transform.scale(item.image, (32, 32))
                    self.surface.blit(scaled_img, (slot_rect.x + 4, slot_rect.y + 4))
                    if item.load > 1:
                        qty_txt = font_small.render(str(int(item.load)), True, WHITE)
                        self.surface.blit(qty_txt, (slot_rect.right - qty_txt.get_width() - 2, slot_rect.bottom - qty_txt.get_height() - 2))

        # 2. Draw Known Recipes List (Right Side)
        list_x = self.modal_x + 250
        list_y = self.modal_y + 50
        list_w = 230
        list_h = 230 # Slightly shorter to make room for preview
        
        pygame.draw.rect(self.surface, (30, 30, 30), (list_x, list_y, list_w, list_h))
        pygame.draw.rect(self.surface, GRAY, (list_x, list_y, list_w, list_h), 1)
        
        known = RecipeManager.get_known_recipes(self.player.known_recipes)
        
        # Scroll logic could be added here, for now basic list
        for i, recipe in enumerate(known):
            row_y = list_y + 5 + (i * 25)
            if row_y > list_y + list_h - 25: break
            
            color = WHITE
            if self.selected_recipe == recipe:
                color = YELLOW
                pygame.draw.rect(self.surface, (60, 60, 60), (list_x + 2, row_y, list_w - 4, 20))
            
            name_txt = font_small.render(recipe.output_name, True, color)
            self.surface.blit(name_txt, (list_x + 5, row_y + 2))
            
            # Click detection for recipes
            row_rect = pygame.Rect(list_x, row_y, list_w, 20)
            if pygame.mouse.get_pressed()[0] and row_rect.collidepoint(pygame.mouse.get_pos()):
                self.selected_recipe = recipe

        # 3. Selected Recipe Preview & Craft Button (Bottom Section)
        preview_y = self.modal_y + 300
        pygame.draw.line(self.surface, GRAY, (self.modal_x + 20, preview_y), (self.modal_x + self.modal_w - 20, preview_y))
        
        if self.selected_recipe:
            # Update preview item if selection changed
            if self.selected_recipe != self.last_selected_recipe:
                self.preview_item = Item.create_from_name(self.selected_recipe.output_name)
                self.last_selected_recipe = self.selected_recipe

            # Draw Result Preview
            if self.preview_item:
                # [FIXED] Scale result image to prevent "too large" issue
                if self.preview_item.image:
                    preview_img = pygame.transform.scale(self.preview_item.image, (48, 48))
                    self.surface.blit(preview_img, (self.modal_x + 30, preview_y + 15))
                else:
                    pygame.draw.rect(self.surface, self.preview_item.color, (self.modal_x + 30, preview_y + 15, 48, 48))
                
                # Result Text
                res_name = font.render(f"Result: {self.preview_item.name}", True, YELLOW)
                self.surface.blit(res_name, (self.modal_x + 90, preview_y + 20))
                
                res_qty = font_small.render(f"Quantity: {self.selected_recipe.output_amount}", True, GRAY)
                self.surface.blit(res_qty, (self.modal_x + 90, preview_y + 45))

            # Craft Button
            btn_rect = pygame.Rect(self.modal_x + 350, preview_y + 20, 100, 40)
            can_craft = self._can_craft(self.selected_recipe)
            
            btn_color = (0, 150, 0) if can_craft else (60, 60, 60)
            pygame.draw.rect(self.surface, btn_color, btn_rect, 0, 5)
            pygame.draw.rect(self.surface, WHITE if can_craft else GRAY, btn_rect, 1, 5)
            
            lbl = font.render("CRAFT", True, WHITE if can_craft else GRAY)
            self.surface.blit(lbl, (btn_rect.centerx - lbl.get_width()//2, btn_rect.centery - lbl.get_height()//2))
            
            # Click detection for craft button
            if can_craft and pygame.mouse.get_pressed()[0]:
                mouse_rect = pygame.Rect(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)
                if mouse_rect.colliderect(btn_rect):
                    self._craft(self.selected_recipe)
        else:
            # Placeholder text if no recipe selected
            info_txt = font_small.render("Select a recipe to craft", True, GRAY)
            self.surface.blit(info_txt, (self.modal_x + 30, preview_y + 30))

        # [FIXED] Return buttons to UI manager so they are clickable
        close_btn, min_btn = self.get_buttons()
        return None, close_btn, min_btn

    def _can_craft(self, recipe):
        # Check if ingredients_container has the required items
        temp_inv = [item for item in self.ingredients_container.inventory]
        
        for req in recipe.ingredients:
            needed = req['amount']
            found = 0
            for item in temp_inv:
                if item.name == req['name']:
                    found += item.load
            if found < needed:
                return False
        return True

    def _craft(self, recipe):
        if self.player.action_timer > 0: return

        def craft_complete():
             # Remove ingredients
            for req in recipe.ingredients:
                removed_count = 0
                to_remove = req['amount']
                
                # Iterate backwards to safely remove empty items
                for i in range(len(self.ingredients_container.inventory) - 1, -1, -1):
                    item = self.ingredients_container.inventory[i]
                    if item.name == req['name']:
                        take = min(to_remove - removed_count, item.load)
                        if req['destroy']:
                            item.load -= take
                        removed_count += take
                        
                        if item.load <= 0:
                             self.ingredients_container.inventory.pop(i)
                             
                        if removed_count >= to_remove:
                            break
            
            # Create Output
            result = Item.create_from_name(recipe.output_name)
            if result:
                result.load = recipe.output_amount
                
                # Add to player inventory or drop
                if len(self.player.inventory) < self.player.base_inventory_slots:
                    self.player.inventory.append(result)
                else:
                    self.game.items_on_ground.append(result)
                    result.x, result.y = self.player.x, self.player.y
                    result.rect.topleft = (result.x, result.y)
                    
                from core.messages import display_message_player
                display_message_player(f"Crafted {result.name}!")

        self.player.start_action(f"Crafting {recipe.output_name}", recipe.time_required, craft_complete)