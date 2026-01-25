import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH

class Recipe:
    # [CHANGED] Added craft_type parameter with default "create"
    def __init__(self, output_name, magazine, time_required, ingredients, output_amount=1, craft_type="create"):
        self.output_name = output_name
        self.magazine = magazine
        self.time_required = float(time_required)
        self.ingredients = ingredients 
        self.output_amount = int(output_amount)
        self.craft_type = craft_type # [ADDED] Store the type (create/repair)

class RecipeManager:
    RECIPES = []

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
            
            # [ADDED] Parse the craft type (default to "create")
            craft_type = recipe_node.get('craft', 'create')

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

            # [CHANGED] Pass craft_type to constructor
            recipe = Recipe(output_name, magazine, time_required, ingredients, output_amount, craft_type)
            RecipeManager.RECIPES.append(recipe)
        
        print(f"Loaded {len(RecipeManager.RECIPES)} recipes.")

    @staticmethod
    def get_recipes_by_magazine(magazine_name):
        return [r for r in RecipeManager.RECIPES if r.magazine == magazine_name]

    @staticmethod
    def get_known_recipes(known_list):
        return [r for r in RecipeManager.RECIPES if r.magazine in known_list or not r.magazine]