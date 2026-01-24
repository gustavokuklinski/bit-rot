import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH

class Recipe:
    def __init__(self, output_name, magazine, time_required, ingredients, output_amount=1):
        self.output_name = output_name
        self.magazine = magazine
        self.time_required = float(time_required)
        self.ingredients = ingredients # List of dicts: {'name': str, 'amount': int, 'destroy': bool}
        self.output_amount = int(output_amount)

class RecipeManager:
    RECIPES = []

    @staticmethod
    def load_recipes():
        recipe_path = os.path.join(DATA_PATH, 'craft/recipes.xml') # Assuming a recipes.xml exists in data
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

            ingredients = []
            for ing_node in recipe_node.findall('ingredient'):
                ingredients.append({
                    'name': ing_node.get('name'),
                    'amount': int(ing_node.get('amount', 1)),
                    'destroy': ing_node.get('destroy', 'true').lower() == 'true'
                })

            recipe = Recipe(output_name, magazine, time_required, ingredients, output_amount)
            RecipeManager.RECIPES.append(recipe)
        
        print(f"Loaded {len(RecipeManager.RECIPES)} recipes.")

    @staticmethod
    def get_recipes_by_magazine(magazine_name):
        return [r for r in RecipeManager.RECIPES if r.magazine == magazine_name]

    @staticmethod
    def get_known_recipes(known_list):
        # Returns recipes that are either known by the player or don't require a magazine (if any)
        return [r for r in RecipeManager.RECIPES if r.magazine in known_list or not r.magazine]