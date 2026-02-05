import os
from core.data.config import *
from core.map.building_loader import load_building_templates

class ProceduralGeneratorTemplate:
    def _init_templates(self):
        # 1. Identify Forest Tiles
        self.forest_tiles = []
        if hasattr(self.game, 'tile_manager'):
            self.forest_tiles = [k for k in self.game.tile_manager.definitions.keys() if k.startswith('Forest_')]
        
        if not self.forest_tiles:
            self.forest_tiles = ['garden_tree_1', 'garden_tree_8', 'garden_stone', 'bg_grass', 'garden_dirty_1', 'garden_dirty_2', 'garden_grass_3', 'garden_grass_1', 'garden_grass_2']

        # 2. Identify & Categorize Templates
        self.categorized_templates = {
            'Warehouse': [],
            'Stores': [],
            'Shed': [],
            'Building': [],
            'Petrol': [],
            'Heli': [],
            'Military': [],
            'Cave': [],
            'Bunker': [],
        }
        self.forest_templates = []
        self.l2_templates = [] 

        print("--- Template Discovery & Categorization ---")
        for name in self.templates.keys():
            lower_name = name.lower()
            
            # --- SEPARATE L2 TEMPLATES ---
            if "l2" in lower_name:
                # FIX: Exclude Caves from random L2 pool so they only spawn via links
                if "cave" not in lower_name:
                    self.l2_templates.append(name)
                continue # Do not add to L1 pools

            if name.startswith("Forest_"):
                self.forest_templates.append(name)
                continue

            assigned = False
            
            if "heli" in lower_name:
                self.categorized_templates['Heli'].append(name)
                assigned = True
            elif "cave" in lower_name: 
                self.categorized_templates['Cave'].append(name)
                assigned = True
            elif "military" in lower_name:
                self.categorized_templates['Military'].append(name)
                assigned = True
            elif "warehouse" in lower_name:
                self.categorized_templates['Warehouse'].append(name)
                assigned = True
            elif "store" in lower_name:
                self.categorized_templates['Stores'].append(name)
                assigned = True
            elif "shed" in lower_name:
                self.categorized_templates['Shed'].append(name)
                assigned = True
            elif "petrol" in lower_name or "gas" in lower_name:
                self.categorized_templates['Petrol'].append(name)
                assigned = True
            elif "bunker" in lower_name:
                self.categorized_templates['Bunker'].append(name)
                assigned = True
            elif "condo" in lower_name:
                self.categorized_templates['Building'].append(name)
                assigned = True
            
            if not assigned and "l1" in lower_name:
                self.categorized_templates['Building'].append(name)

        for cat, lst in self.categorized_templates.items():
            print(f"Category {cat}: Found {len(lst)} templates.")
        print(f"L2 Specific Templates (Random Spawn): Found {len(self.l2_templates)} templates.")