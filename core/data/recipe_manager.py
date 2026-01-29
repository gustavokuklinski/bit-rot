import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH

class Recipe:
    # [CHANGED] Added req_level and gain_xp to constructor
    def __init__(self, output_name, magazine, time_required, ingredients, output_amount=1, craft_type="create", req_level=None, gain_xp=None):
        self.output_name = output_name
        self.magazine = magazine
        self.time_required = float(time_required)
        self.ingredients = ingredients 
        self.output_amount = int(output_amount)
        self.craft_type = craft_type 
        self.req_level = req_level if req_level else {} # [ADDED] Dictionary of required attribute levels
        self.gain_xp = gain_xp if gain_xp else {}       # [ADDED] Dictionary of XP rewards

class RecipeManager:
    RECIPES = []

    # [ADDED] Helper to parse string format "[key:val, key2:val2]" into dict
    @staticmethod
    def parse_attribute_dict(text_str):
        result = {}
        if not text_str or not text_str.startswith('[') or not text_str.endswith(']'):
            return result
        
        content = text_str[1:-1].strip()
        if not content:
            return result
            
        pairs = content.split(',')
        for pair in pairs:
            if ':' in pair:
                try:
                    key, val = pair.split(':')
                    result[key.strip()] = float(val.strip())
                except ValueError:
                    pass
        return result

    @staticmethod
    def load_recipes():
        recipe_path = os.path.join(DATA_PATH, 'craft/recipes.xml') 
        if not os.path.exists(recipe_path):
            print("Warning: recipes.xml not found.")
            return

        tree = ET.parse(recipe_path)
        root = tree.getroot()

        RecipeManager.RECIPES.clear()

        for recipe_node in root.findall('recipe'):
            output_name = recipe_node.get('output')
            magazine = recipe_node.get('magazine')
            time_required = recipe_node.get('time', '1.0')
            output_amount = recipe_node.get('amount', '1')
            craft_type = recipe_node.get('craft', 'create')

            # [ADDED] Parse new attributes
            req_level_str = recipe_node.get('req_level', '')
            gain_xp_str = recipe_node.get('gain_xp', '')
            
            req_level = RecipeManager.parse_attribute_dict(req_level_str)
            gain_xp = RecipeManager.parse_attribute_dict(gain_xp_str)

            ingredients = []
            for ing_node in recipe_node.findall('ingredient'):
                raw_name = ing_node.get('name')
                
                if raw_name.startswith('[') and raw_name.endswith(']'):
                    names_list = [n.strip() for n in raw_name[1:-1].split(',')]
                else:
                    names_list = [raw_name]
                
                ingredients.append({
                    'names': names_list, 
                    'amount': int(ing_node.get('amount', 1)),
                    'destroy': ing_node.get('destroy', 'true').lower() == 'true'
                })

            # [CHANGED] Pass new attributes to constructor
            recipe = Recipe(output_name, magazine, time_required, ingredients, output_amount, craft_type, req_level, gain_xp)
            RecipeManager.RECIPES.append(recipe)
        
        print(f"Loaded {len(RecipeManager.RECIPES)} recipes.")

    @staticmethod
    def get_recipes_by_magazine(magazine_name):
        return [r for r in RecipeManager.RECIPES if r.magazine == magazine_name]

    @staticmethod
    def get_known_recipes(known_list):
        # [NOTE] Logic remains: if it has no magazine, it's "known" by default in terms of discovery, 
        # but crafting it might still require skills (handled in UI).
        return [r for r in RecipeManager.RECIPES if r.magazine in known_list or not r.magazine]