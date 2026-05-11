# core/ui/crafting_know_recipes_tab.py
from core.ui.crafting_craft_tab import CraftingCraftTab
from core.ui.crafting_repair_tab import CraftingRepairTab
from core.ui.crafting_dismantle_tab import CraftingDismantleTab
from core.data.localization import tr

class CraftingKnowRecipesTab:
    def __init__(self, modal):
        self.modal = modal
        self.craft_tab = CraftingCraftTab(modal)
        self.repair_tab = CraftingRepairTab(modal)
        self.dismantle_tab = CraftingDismantleTab(modal)
        
    def filter_recipes(self, recipes, search_text):
        filtered = []
        for r in recipes:
            knows_magazine = True
            if r.magazine:
                knows_magazine = r.magazine in self.modal.player.known_recipes
            skills_met = self.modal._check_skill_reqs(r)

            is_unlocked = True
            if r.magazine:
                if r.req_level:
                    if not knows_magazine and not skills_met:
                        is_unlocked = False
                else:
                    if not knows_magazine:
                        is_unlocked = False
            elif r.req_level:
                if not skills_met:
                    is_unlocked = False
            
            if not is_unlocked:
                continue
        
            if search_text:
                st = search_text.lower()
                matches_output = st in r.output_name.lower()
                matches_ing = any(any(st in n.lower() for n in ing['names']) for ing in r.ingredients)
                if not (matches_output or matches_ing):
                    continue
                    
            filtered.append(r)

        return filtered
        
    def draw_details(self, details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items):
        craft_type = getattr(self.modal.selected_recipe, 'craft_type', 'create')
        if craft_type == 'repair':
            return self.repair_tab.draw_details(details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items)
        elif craft_type == 'dismantle':
            return self.dismantle_tab.draw_details(details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items)
        else:
            return self.craft_tab.draw_details(details_x, details_y, details_w, list_h, mouse_pos, click, nearby_containers, player_items, nearby_items)

    def execute_craft(self, recipe):
        craft_type = getattr(recipe, 'craft_type', 'create')
        if craft_type == 'repair':
            self.repair_tab.execute_craft(recipe)
        elif craft_type == 'dismantle':
            self.dismantle_tab.execute_craft(recipe)
        else:
            self.craft_tab.execute_craft(recipe)