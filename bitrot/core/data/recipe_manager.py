# core/data/recipe_manager.py

import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH
from core.systems.mod_manager import mod_manager

class Recipe:
    def __init__(self, output_name, magazine, time_required, ingredients, output_amount=1, 
                 craft_type="create", req_level=None, gain_xp=None, results=None,
                 extra_ingredients=None, recipe_type="", is_cooking=False, effects=None):
        self.output_name = output_name
        self.magazine = magazine
        self.time_required = float(time_required)
        self.ingredients = ingredients 
        self.output_amount = int(output_amount)
        self.craft_type = craft_type 
        self.req_level = req_level if req_level else {}
        self.gain_xp = gain_xp if gain_xp else {}
        self.results = results if results else []
        self.extra_ingredients = extra_ingredients if extra_ingredients else []
        self.recipe_type = recipe_type
        self.is_cooking = is_cooking
        self.effects = effects if effects else []

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
        """Helper to split [A, B] into a list of strings, preserving wildcard specs."""
        if not raw_name: return []
        raw_clean = raw_name.strip()
        if 'baseitem' in raw_clean.lower():
            return [raw_clean]
        if raw_clean.startswith('[') and raw_clean.endswith(']'):
            return [n.strip() for n in raw_clean[1:-1].split(',')]
        return [raw_clean]

    @staticmethod
    def _process_recipe_node(recipe_node, is_cooking_dir=False):
        """Helper to parse a single <recipe> node and add it to the list."""
        raw_output_name = recipe_node.get('output')
        magazine = recipe_node.get('magazine')
        time_required = recipe_node.get('time', '1.0')
        output_amount = recipe_node.get('amount', '1')
        craft_type = recipe_node.get('craft', 'create')
        recipe_type = recipe_node.get('type', '')

        req_level_str = recipe_node.get('req_level', '')
        gain_xp_str = recipe_node.get('gain_xp', '')
        
        req_level = RecipeManager.parse_attribute_dict(req_level_str)
        gain_xp = RecipeManager.parse_attribute_dict(gain_xp_str)

        # --- Parse Required Ingredients ---
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

        # --- Parse Optional Extra Ingredients (Seasonings & Add-ins) ---
        extra_ingredients = []
        for extra_node in recipe_node.findall('extra_ingredient'):
            raw_name = extra_node.get('name')
            names_list = RecipeManager._parse_names(raw_name)
            extra_req_level = RecipeManager.parse_attribute_dict(extra_node.get('req_level', ''))
            extra_mag = extra_node.get('magazine')
            extra_destroy = extra_node.get('destroy', 'true').lower() == 'true'
            try:
                extra_amt = int(extra_node.get('amount', 1))
            except (ValueError, TypeError):
                extra_amt = 1

            extra_ingredients.append({
                'names': names_list,
                'amount': extra_amt,
                'destroy': extra_destroy,
                'req_level': extra_req_level,
                'magazine': extra_mag
            })

        # --- Check for Wildcard Specification ---
        parsed_wildcard = None
        if raw_output_name and 'baseitem' in raw_output_name.lower():
            from core.entities.item.item_factory import parse_wildcard_spec
            parsed_wildcard = parse_wildcard_spec(raw_output_name)

        # --- Parse Results ---
        results = []
        for res_node in recipe_node.findall('result'):
            r_name = res_node.get('name')
            r_amount = int(res_node.get('amount', 1))
            r_chance = float(res_node.get('chance', 1.0))
            
            results.append({
                'names': RecipeManager._parse_names(r_name),
                'amount': r_amount,
                'chance': r_chance
            })

        if not results and raw_output_name:
            results.append({
                'names': RecipeManager._parse_names(raw_output_name),
                'amount': int(output_amount),
                'chance': 1.0
            })

        # --- Determine Display Name ---
        if parsed_wildcard:
            display_name = parsed_wildcard['friendly_name']
        else:
            display_name = raw_output_name

        if not display_name:
            if craft_type == 'dismantle':
                display_name = f"Dismantle {first_ingredient_name}"
            elif results:
                display_name = results[0]['names'][0]
            else:
                display_name = "Unknown Recipe"

        # --- Parse Recipe-Level Effects (<restore> and <reduce>) ---
        recipe_effects = []
        for rest_node in recipe_node.findall('restore'):
            st_str = rest_node.get('status', '')
            targets = [t.strip().lower() for t in st_str.replace('[', '').replace(']', '').split(',') if t.strip()]
            val = int(rest_node.get('value', 0))
            if targets and val:
                recipe_effects.append({'type': 'restore', 'targets': targets, 'value': val})

        for red_node in recipe_node.findall('reduce'):
            st_str = red_node.get('status', '')
            targets = [t.strip().lower() for t in st_str.replace('[', '').replace(']', '').split(',') if t.strip()]
            val = int(red_node.get('value', 0))
            if targets and val:
                recipe_effects.append({'type': 'reduce', 'targets': targets, 'value': val})

        # Flag as cooking if loaded from cooking/ folder or defined as food/drink/cook
        is_cooking = (
            is_cooking_dir or
            craft_type == 'cook' or
            recipe_type in ('consumable_food', 'consumable_drink') or
            len(extra_ingredients) > 0
        )

        recipe = Recipe(
            display_name, magazine, time_required, ingredients, output_amount, 
            craft_type, req_level, gain_xp, results,
            extra_ingredients=extra_ingredients, recipe_type=recipe_type,
            is_cooking=is_cooking, effects=recipe_effects
        )
        
        if parsed_wildcard:
            recipe.base_item = parsed_wildcard['base_item']
            recipe.raw_output = raw_output_name
            recipe.wildcard_loot = parsed_wildcard['loot']
            recipe.is_wildcard = True

        RecipeManager.RECIPES.append(recipe)

    @staticmethod
    def load_recipes():
        """Loads crafting and cooking recipes from craft/ and cooking/ directories."""
        recipe_directories = [
            (os.path.join(DATA_PATH, 'craft'), False),
            (os.path.join(DATA_PATH, 'cooking'), True)
        ]

        RecipeManager.RECIPES.clear()

        for folder_path, is_cooking_dir in recipe_directories:
            if not os.path.exists(folder_path):
                if is_cooking_dir:
                    try:
                        os.makedirs(folder_path, exist_ok=True)
                    except OSError:
                        pass
                continue

            for root_dir, _, full_paths in mod_manager.vfs_walk(folder_path):
                for file_path in full_paths:
                    if not file_path.endswith('.xml'):
                        continue
                    try:
                        tree = ET.parse(file_path)
                        root = tree.getroot()

                        if root.tag == 'recipe':
                            RecipeManager._process_recipe_node(root, is_cooking_dir=is_cooking_dir)
                        else:
                            for recipe_node in root.findall('.//recipe'):
                                RecipeManager._process_recipe_node(recipe_node, is_cooking_dir=is_cooking_dir)
                    except Exception as e:
                        print(f"Error loading recipe file {file_path}: {e}")
        
        print(f"Loaded {len(RecipeManager.RECIPES)} total recipes (Craft & Cooking).")

    @staticmethod
    def get_recipes_by_magazine(magazine_name):
        return [r for r in RecipeManager.RECIPES if r.magazine == magazine_name]

    @staticmethod
    def get_known_recipes(known_list):
        return [r for r in RecipeManager.RECIPES if r.magazine in known_list or not r.magazine]