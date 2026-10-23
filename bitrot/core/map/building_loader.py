# core/map/building_loader.py
import os
import csv

def load_building_templates(buildings_dir):
    """
    Loads building templates from the specified directory utilizing the ModManager virtual file system.
    Returns a dictionary where keys are building names and values are dicts containing layers.
    """
    from core.systems.mod_manager import mod_manager
    templates = {}
    
    if not os.path.exists(buildings_dir):
        print(f"Warning: Building directory not found: {buildings_dir}")
        return templates

    # Collect prefixes via VFS walking
    prefixes = set()
    for root_dir, _, full_paths in mod_manager.vfs_walk(buildings_dir):
        for full_path in full_paths:
            f = os.path.basename(full_path)
            if f.endswith('.csv'):
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
        
        def load_layer(suffix):
            path = mod_manager.get_override_path(os.path.join(buildings_dir, f"{name}{suffix}"))
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