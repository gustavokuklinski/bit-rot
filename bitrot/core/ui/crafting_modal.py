# core/ui/crafting_modal.py
import pygame
import random 
from core.ui.modals import BaseModal, draw_scrollbar
from core.data.config import *
from core.entities.item.item import Item
from core.data.recipe_manager import RecipeManager
from core.ui.tabs import Tabs 
from core.ui.dropdown import draw_context_menu

from core.ui.crafting_know_recipes_tab import CraftingKnowRecipesTab
from core.ui.crafting_craft_tab import CraftingCraftTab
from core.ui.crafting_repair_tab import CraftingRepairTab
from core.ui.crafting_dismantle_tab import CraftingDismantleTab
from core.data.localization import tr

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
        self.yield_images = {}
        self.yield_colors = {}

        self.tabs_data = [
            {'label': tr('tab', "Known Recipes")},
            {'label': tr('tab', "Craft")},
            {'label': tr('tab', "Repair")},
            {'label': tr('tab', "Dismantle")}
        ]
        self.tabs_manager = Tabs(surface, self.modal, self.tabs_data, assets)
        
        if 'active_tab' not in self.modal:
            self.modal['active_tab'] = tr('tab', "Known Recipes")

        # Search State
        if 'search_text' not in self.modal:
            self.modal['search_text'] = ""
        if 'search_active' not in self.modal:
            self.modal['search_active'] = False
            
        self.search_text = self.modal['search_text']
        self.search_active = self.modal['search_active']

        self.search_rect = None

        # Dropdown selection state
        self.dropdown_state = {'active': False, 'options': [], 'position': (0,0), 'req_idx': -1, 'items': [], 'rects': []}
        self.selected_ingredients = {} 
        self.selected_target = None 
        self.dropdown_just_closed = False
        
        # ---> FIX: Memory flag to catch synthetic Joystick events <---
        self._force_click = False

        self.tab_handlers = {
            tr('tab', "Known Recipes"): CraftingKnowRecipesTab(self),
            tr('tab', "Craft"): CraftingCraftTab(self),
            tr('tab', "Repair"): CraftingRepairTab(self),
            tr('tab', "Dismantle"): CraftingDismantleTab(self)
        }

    def handle_event(self, event):
        mouse_pos = self.game._get_scaled_mouse_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Ensure we only process Left Clicks (Hardware or Synthetic Joystick)
            is_left_click = getattr(event, 'button', 1) == 1
            
            if self.dropdown_state.get('active'):
                if is_left_click and 'rects' in self.dropdown_state:
                    for i, rect in enumerate(self.dropdown_state['rects']):
                        if rect.collidepoint(mouse_pos):
                            item_id = self.dropdown_state['items'][i]
                            req_idx = self.dropdown_state['req_idx']
                            if req_idx == 'target':
                                self.selected_target = item_id
                            else:
                                self.selected_ingredients[req_idx] = item_id
                            break
                self.dropdown_state['active'] = False
                self.dropdown_just_closed = True
                return True 

            if is_left_click and self.tabs_manager.check_click(mouse_pos):
                self.modal['crafting_scroll_offset'] = 0 
                return True
            
            if is_left_click and self.search_rect:
                if self.search_rect.collidepoint(mouse_pos):
                    self.search_active = True
                    self.modal['search_active'] = True
                    pygame.key.set_repeat(500, 50) 
                    return True
                else:
                    self.search_active = False
                    self.modal['search_active'] = False
                    pygame.key.set_repeat() 
                    
            # ---> FIX: If the click wasn't consumed by UI elements above, flag it for the drawing loop <---
            if is_left_click:
                self._force_click = True
        
        elif event.type == pygame.KEYDOWN and self.search_active:
            if event.key == pygame.K_BACKSPACE:
                self.search_text = self.search_text[:-1]
                self.modal['search_text'] = self.search_text  # <--- UPDATE
            elif event.key == pygame.K_RETURN:
                self.search_active = False
                self.modal['search_active'] = False           # <--- UPDATE
                pygame.key.set_repeat()
            elif event.key == pygame.K_ESCAPE:
                self.search_active = False
                self.modal['search_active'] = False           # <--- UPDATE
                pygame.key.set_repeat()
                return True 
            else:
                if len(self.search_text) < 20 and len(event.unicode) > 0 and event.unicode.isprintable():
                    self.search_text += event.unicode
                    self.modal['search_text'] = self.search_text  # <--- UPDATE
            
            self.modal['crafting_scroll_offset'] = 0 
            return True
            
        return False

    def _get_all_item_locations(self, include_nearby=False, nearby_containers=None):
        locations = []
        
        def extract_list(container_list, path):
            for i in range(len(container_list) - 1, -1, -1):
                item = container_list[i]
                if item:
                    locations.append((container_list, i, item, 'list', path))
                    if hasattr(item, 'inventory') and item.inventory:
                        extract_list(item.inventory, path + [tr('item', item.name)])

        extract_list(self.player.inventory, ["Inventory"])
        
        for i in range(len(self.player.belt) - 1, -1, -1):
            item = self.player.belt[i]
            if item:
                locations.append((self.player.belt, i, item, 'fixed_list', ["Belt"]))
                if hasattr(item, 'inventory') and item.inventory:
                    extract_list(item.inventory, ["Belt", tr('item', item.name)])
                    
        protected_slots = ['arms', 'legs', 'body', 'feet', 'hands']
        for k in list(self.player.clothes.keys()):
            item = self.player.clothes[k]
            if item:
                if str(k).lower() not in protected_slots:
                    locations.append((self.player.clothes, k, item, 'dict', ["Gear", str(k).capitalize()]))
                if hasattr(item, 'inventory') and item.inventory:
                    extract_list(item.inventory, ["Gear", str(k).capitalize(), tr('item', item.name)])
                    
        
        if include_nearby:
            if nearby_containers is None:
                nearby_containers = self.game.find_nearby_containers()
            if nearby_containers:
                for obj in nearby_containers:
                    if hasattr(obj, 'inventory') and obj.inventory:
                        obj_name = getattr(obj, 'name', 'Ground')
                        extract_list(obj.inventory, ["Nearby", obj_name])
                        
        return locations

    def _has_ingredients(self, recipe, player_items, nearby_items=None):
        search_items = player_items
        if nearby_items:
            search_items = search_items + nearby_items

        for req in recipe.ingredients:
            needed = req['amount']
            valid_names = req['names']
            
            have = sum((item.load if (item.load is not None and item.is_stackable()) else 1) 
                       for item in search_items 
                       if tr('item', item.name) in valid_names)
            
            if have < needed: return False
        return True
    
    def _check_skill_reqs(self, recipe):
        if not recipe.req_level: return True
        
        for attr, level_req in recipe.req_level.items():
            player_level = self.player.progression.get_level(attr)
            if player_level < level_req: return False
        return True

    def _get_scrollbar_rects(self, total_items, list_rect):
        if total_items <= self.visible_items: return None, None

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
        self.tabs_manager.surface = self.surface

        self.modal_x, self.modal_y = self.modal['position']
        self.modal_rect.topleft = (self.modal_x, self.modal_y)


        self.close_button_rect.topright = (self.modal_x + self.modal_w - 10, self.modal_y + 10)

        self.draw_base()
        
        

        # ---> FIX: Read dynamically scaled screen coordinates for UI matching <---
        mouse_pos = self.game._get_scaled_mouse_pos() if hasattr(self.game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
        
        # ---> FIX: Exclusively use the event-dispatched click flag to respect Z-Index!
        # Do NOT poll raw pygame.mouse.get_pressed() here, otherwise background modals will intercept it.
        click = getattr(self, '_force_click', False)
        self._force_click = False # Consume flag

        if getattr(self, 'dropdown_just_closed', False):
            if not click: self.dropdown_just_closed = False
            click = False

        list_x = self.modal_x + self.padding
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
        if self.search_active and (pygame.time.get_ticks() // 500) % 2 == 0: display_text += "_"
            
        if not self.search_text and not self.search_active:
            display_text = tr('ui', "Search...")
            txt_col = (80, 80, 80)
        else:
            txt_col = WHITE
            
        s_surf = font_12.render(display_text, False, txt_col)
        
        old_clip = self.surface.get_clip()
        self.surface.set_clip(self.search_rect.inflate(-4, -4))
        self.surface.blit(s_surf, (self.search_rect.x + 5, self.search_rect.y + 4))
        self.surface.set_clip(old_clip)

        list_y = search_y + search_h + 10
        list_h = self.modal_h - (list_y - self.modal_y) - 20 
        
        pygame.draw.rect(self.surface, (30, 30, 30), (list_x, list_y, self.list_width, list_h))
        pygame.draw.rect(self.surface, GRAY, (list_x, list_y, self.list_width, list_h), 1)

        active_tab = self.modal.get('active_tab', tr('tab', 'Known Recipes'))
        tab_handler = self.tab_handlers.get(active_tab)

        nearby_items = []
        nearby_containers = self.game.find_nearby_containers()
        if nearby_containers:
            for cont in nearby_containers:
                if hasattr(cont, 'inventory') and cont.inventory:
                    def extract_nearby(inv):
                        for it in inv:
                            if it:
                                nearby_items.append(it)
                                if hasattr(it, 'inventory') and it.inventory: extract_nearby(it.inventory)
                    extract_nearby(cont.inventory)

        player_items = [loc[2] for loc in self._get_all_item_locations()]

        filtered_recipes = tab_handler.filter_recipes(self.recipes, self.search_text)

        filtered_recipes.sort(key=lambda r: (
            not self._has_ingredients(r, player_items, None),          
            not self._has_ingredients(r, player_items, nearby_items),  
            r.output_name
        ))

        row_h = 28
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
            has_ingredients_local = self._has_ingredients(recipe, player_items, None)          
            has_ingredients_global = self._has_ingredients(recipe, player_items, nearby_items) 
            
            bg_color = (60, 60, 80) if is_selected else ((50, 50, 50) if is_hovered else (30, 30, 30))
            
            if is_selected: text_color = YELLOW
            elif has_ingredients_local: text_color = GREEN   
            elif has_ingredients_global: text_color = YELLOW  
            elif is_hovered: text_color = WHITE
            else: text_color = GRAY
            
            pygame.draw.rect(self.surface, bg_color, row_rect, border_radius=3)
            
            old_clip = self.surface.get_clip()
            self.surface.set_clip(row_rect)
            name_surf = font_12.render(recipe.output_name, False, text_color)
            self.surface.blit(name_surf, (row_rect.x + 8, row_rect.y + 6))
            self.surface.set_clip(old_clip)
            
            if click and is_hovered and not self.modal.get('is_dragging_scrollbar'):
                self.selected_recipe = recipe

        bar_rect = pygame.Rect(list_rect.right - 10, list_rect.top + 2, 8, list_rect.height - 4)
        draw_scrollbar(self.surface, self.modal, bar_rect, self.visible_items, len(filtered_recipes), scroll_offset)
        
        # Ensure legacy drag inputs for crafting still hook into the new rect
        self.modal['crafting_handle_rect'] = self.modal.get('scrollbar_handle_rect')

        details_x = list_x + self.list_width + self.padding
        details_y = list_y 
        details_w = self.modal_w - self.list_width - (self.padding * 3)
        
        active_tooltip_ingredients = None

        if self.selected_recipe:
            if self.selected_recipe != self.cached_recipe:
                self.cached_recipe = self.selected_recipe
                self.selected_ingredients = {}
                self.selected_target = None

                if self.selected_recipe.craft_type == 'dismantle':
                     first_ing = self.selected_recipe.ingredients[0]['names'][0]
                     self.result_image = self.get_preview_image(first_ing)
                else:
                    self.result_image = self.get_preview_image(self.selected_recipe.output_name)
                
                self.ingredient_images = {}
                for req in self.selected_recipe.ingredients:
                    primary_name = req['names'][0]
                    self.ingredient_images[primary_name] = self.get_preview_image(primary_name)
                    
                self.yield_images = {}
                self.yield_colors = {}
                if getattr(self.selected_recipe, 'craft_type', 'create') == 'dismantle' and getattr(self.selected_recipe, 'results', None):
                    for res in self.selected_recipe.results:
                        res_name = res['names'][0] if res['names'] else None
                        if res_name:
                            try:
                                temp_item = Item.create_from_name(res_name)
                                if temp_item:
                                    self.yield_images[res_name] = temp_item.image
                                    self.yield_colors[res_name] = temp_item.color
                            except Exception:
                                pass

            r = self.selected_recipe
            self.warning_message = self._validate_ingredients(r, nearby_containers)

            active_tooltip_ingredients = tab_handler.draw_details(
                details_x, details_y, details_w, list_h, 
                mouse_pos, click, nearby_containers, player_items, nearby_items
            )
        else:
            info_txt = font_12.render(tr('ui', "Select a recipe to view details"), False, GRAY)
            text_rect = info_txt.get_rect(center=(details_x + details_w//2, details_y + 100))
            self.surface.blit(info_txt, text_rect)

        if active_tooltip_ingredients:
            self._draw_ingredient_tooltip(active_tooltip_ingredients, mouse_pos, nearby_containers)

        if self.dropdown_state['active']:
            draw_context_menu(self.surface, self.dropdown_state, mouse_pos)

        return None, self.get_buttons()

    def _draw_ingredient_tooltip(self, names, pos, nearby_containers):
        locs = self._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
        
        available_items = []
        for container, key, item, ctype, path in locs:
            if tr('item', item.name) in names:
                available_items.append((item, path))
        
        line_height = 24
        padding = 10
        items_data = []
        max_w = 0
        
        dash_s = font_12.render("- ", False, WHITE)
        dash_w = dash_s.get_width()
        
        if not available_items:
            for name in names:
                img = self.get_preview_image(name)
                if img: img = pygame.transform.scale(img, (20, 20))
                s = font_12.render(f"{name} {tr('ui', '(None available)')}", False, GRAY)
                
                row_w = dash_w + (25 if img else 0) + s.get_width()
                if row_w > max_w: max_w = row_w
                items_data.append((img, s))
        else:
            for item, path in available_items:
                img = item.image
                if img: img = pygame.transform.scale(img, (20, 20))
                
                qty_str = f"x{item.load}" if item.is_stackable() else f"Dur: {int(item.durability or 0)}"
                breadcrumb = " > ".join(path)
                s = font_12.render(f"{tr('item', item.name)} ({qty_str}) | {breadcrumb}", False, WHITE)
                
                row_w = dash_w + (25 if img else 0) + s.get_width()
                if row_w > max_w: max_w = row_w
                items_data.append((img, s))

        tt_w = max_w + (padding * 2)
        tt_h = (len(items_data) * line_height) + (padding * 2)
        
        x, y = pos[0], pos[1]
        if x + tt_w > GAME_WIDTH: x = pos[0] - tt_w - 5
        if y + tt_h > GAME_HEIGHT: y = pos[1] - tt_h - 5
            
        tt_rect = pygame.Rect(x, y, tt_w, tt_h)
        pygame.draw.rect(self.surface, BLACK, tt_rect)
        pygame.draw.rect(self.surface, WHITE, tt_rect, 1)
        
        curr_y = y + padding
        for img, s in items_data:
            cx = x + padding
            self.surface.blit(dash_s, (cx, curr_y + (line_height - dash_s.get_height()) // 2))
            cx += dash_w
            if img:
                self.surface.blit(img, (cx, curr_y + (line_height - 20) // 2))
                cx += 25
            self.surface.blit(s, (cx, curr_y + (line_height - s.get_height()) // 2))
            curr_y += line_height

    def prioritize_locations(self, locs, preferred_id):
        if not preferred_id: return locs
        return sorted(locs, key=lambda loc: 0 if loc[2].id == preferred_id else 1)

    def _validate_ingredients(self, recipe, nearby_containers=None):
        for r_idx, req in enumerate(recipe.ingredients):
            if not req['destroy']: continue

            to_remove = req['amount']
            valid_names = req['names']
            removed_check = 0
            
            locations = self._get_all_item_locations(include_nearby=True, nearby_containers=nearby_containers)
            pref_id = self.selected_ingredients.get(r_idx)
            locations = self.prioritize_locations(locations, pref_id)
            
            for container, key, item, ctype, path in locations:
                if removed_check >= to_remove: break

                if tr('item', item.name) in valid_names:
                    if hasattr(item, 'inventory') and item.inventory: return f"{tr('msg', 'Cannot use')} {tr('item', item.name)}: {tr('msg', 'It contains items!')}"

                    item_qty = item.load if (item.load is not None and item.is_stackable()) else 1
                    take = min(to_remove - removed_check, item_qty)
                    removed_check += take
                    
            #if removed_check < to_remove: return f"{tr('msg', 'Missing')} {to_remove - removed_check} {tr('msg', 'of')} {valid_names[0]}"
        return None