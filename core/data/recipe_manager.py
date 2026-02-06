import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH

class Recipe:
    # [CHANGED] Added results to constructor
    def __init__(self, output_name, magazine, time_required, ingredients, output_amount=1, craft_type="create", req_level=None, gain_xp=None, results=None):
        self.output_name = output_name
        self.magazine = magazine
        self.time_required = float(time_required)
        self.ingredients = ingredients 
        self.output_amount = int(output_amount)
        self.craft_type = craft_type 
        self.req_level = req_level if req_level else {}
        self.gain_xp = gain_xp if gain_xp else {}
        # [ADDED] List of result dicts: [{'names': ['Stone'], 'amount': 1, 'chance': 1.0}]
        self.results = results if results else []

class RecipeManager:
    RECIPES = []

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
    def _parse_names(raw_name):
        """Helper to split [A, B] into a list of strings."""
        if not raw_name: return []
        if raw_name.startswith('[') and raw_name.endswith(']'):
            return [n.strip() for n in raw_name[1:-1].split(',')]
        return [raw_name]

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
            raw_output_name = recipe_node.get('output')
            magazine = recipe_node.get('magazine')
            time_required = recipe_node.get('time', '1.0')
            output_amount = recipe_node.get('amount', '1')
            craft_type = recipe_node.get('craft', 'create')

            req_level_str = recipe_node.get('req_level', '')
            gain_xp_str = recipe_node.get('gain_xp', '')
            
            req_level = RecipeManager.parse_attribute_dict(req_level_str)
            gain_xp = RecipeManager.parse_attribute_dict(gain_xp_str)

            # --- Parse Ingredients ---
            ingredients = []
            first_ingredient_name = "Unknown"

            for ing_node in recipe_node.findall('ingredient'):
                raw_name = ing_node.get('name')
                names_list = RecipeManager._parse_names(raw_name)
                
                if first_ingredient_name == "Unknown" and names_list:
                    first_ingredient_name = names_list[0]
                
                ingredients.append({
                    'names': names_list, 
                    'amount': int(ing_node.get('amount', 1)),
                    'destroy': ing_node.get('destroy', 'true').lower() == 'true'
                })

            # --- Parse Results (New Logic) ---
            results = []
            
            # 1. Look for explicit <result> tags
            for res_node in recipe_node.findall('result'):
                r_name = res_node.get('name')
                r_amount = int(res_node.get('amount', 1))
                r_chance = float(res_node.get('chance', 1.0))
                
                results.append({
                    'names': RecipeManager._parse_names(r_name),
                    'amount': r_amount,
                    'chance': r_chance
                })

            # 2. Backward Compatibility: If no results, use the 'output' attribute
            if not results and raw_output_name:
                results.append({
                    'names': RecipeManager._parse_names(raw_output_name),
                    'amount': int(output_amount),
                    'chance': 1.0
                })

            # --- Determine Display Name ---
            # If explicit output name exists, use it.
            # If not (common for dismantle), generate one.
            display_name = raw_output_name
            if not display_name:
                if craft_type == 'dismantle':
                    display_name = f"Dismantle {first_ingredient_name}"
                elif results:
                    # Just use the name of the first result
                    display_name = results[0]['names'][0]
                else:
                    display_name = "Unknown Recipe"

            recipe = Recipe(display_name, magazine, time_required, ingredients, output_amount, craft_type, req_level, gain_xp, results)
            RecipeManager.RECIPES.append(recipe)
        
        print(f"Loaded {len(RecipeManager.RECIPES)} recipes.")

    @staticmethod
    def get_recipes_by_magazine(magazine_name):
        return [r for r in RecipeManager.RECIPES if r.magazine == magazine_name]

    @staticmethod
    def get_known_recipes(known_list):
        return [r for r in RecipeManager.RECIPES if r.magazine in known_list or not r.magazine]