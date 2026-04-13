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
            self.forest_tiles = ['garden_tree_1', 'garden_tree_8', 'garden_stone', 'bg_grass', 'garden_dirty_1', 'garden_dirty_2', 'garden_grass_3', 'garden_tall_grass','garden_grass_1', 'garden_grass_2']

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
            #'Bunker': [], # L1 Bunker
        }
        
        # NEW: Categorized L2 Templates
        self.categorized_l2_templates = {
            'Bunker': [],
            'Dungeon': [],
        }
        
        self.forest_templates = []
        self.l2_templates = [] # Generic L2

        print("--- Template Discovery & Categorization ---")
        for name in self.templates.keys():
            lower_name = name.lower()
            
            # --- SEPARATE L2 TEMPLATES ---
            if "l2" in lower_name:
                # FIX: Exclude Caves from random L2 pool so they only spawn via links
                if "cave" not in lower_name:
                    assigned_l2 = False
                    # Categorize specific L2 types
                    if "bunker" in lower_name:
                        self.categorized_l2_templates['Bunker'].append(name)
                        assigned_l2 = True
                    elif "dungeon" in lower_name:
                        self.categorized_l2_templates['Dungeon'].append(name)
                        assigned_l2 = True
                    
                    # If not specific, add to generic pool
                    if not assigned_l2:
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
            
        for cat, lst in self.categorized_l2_templates.items():
            print(f"L2 Category {cat}: Found {len(lst)} templates.")
            
        print(f"L2 Generic Templates (Random Spawn): Found {len(self.l2_templates)} templates.")