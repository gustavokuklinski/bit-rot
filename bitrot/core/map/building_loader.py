# core/map/building_loader.py
import os
import csv

def load_building_templates(buildings_dir):
    """
    Loads building templates from the specified directory.
    Returns a dictionary where keys are building names and values are dicts containing layers.
    """
    templates = {}
    
    if not os.path.exists(buildings_dir):
        print(f"Warning: Building directory not found: {buildings_dir}")
        return templates

    # Get all unique prefixes (e.g., 'house_1' from 'house_1_map.csv')
    files = os.listdir(buildings_dir)
    prefixes = set()
    for f in files:
        if f.endswith('.csv'):
            # Remove the layer suffix to get the base name
            # Assumes format: name_layer.csv (e.g., house1_map.csv)
            # If your buildings are just 'house1.csv', adjust splitting
            base = f.replace('_map.csv', '').replace('_ground.csv', '').replace('_spawn.csv', '').replace('_roof.csv', '').replace('_light.csv', '')
            prefixes.add(base)

    for name in prefixes:
        template = {
            'base': [],
            'ground': [],
            'spawn': [],
            'roof': [],
            'light': []
        }
        
        # Helper to load a specific layer
        def load_layer(suffix):
            path = os.path.join(buildings_dir, f"{name}{suffix}")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return list(csv.reader(f))
            return []

        # Load all 4 potential layers
        template['base'] = load_layer('_map.csv')
        template['ground'] = load_layer('_ground.csv')
        template['spawn'] = load_layer('_spawn.csv')
        template['roof'] = load_layer('_roof.csv')
        template['light'] = load_layer('_light.csv')

        # Only add if we found at least a base or ground layer
        if template['base'] or template['ground']:
            
            height = 0
            width = 0
            
            # [FIX] Calculate max width across ALL rows and ALL layers
            # This prevents truncation from ragged CSV files that drop trailing commas
            for layer_key in ['base', 'ground', 'spawn', 'roof', 'light']:
                if template[layer_key]:
                    height = max(height, len(template[layer_key]))
                    width = max([width] + [len(row) for row in template[layer_key]])
            
            template['width'] = width
            template['height'] = height
            templates[name] = template
            print(f"Loaded building template: {name} ({width}x{height})")

    return templates