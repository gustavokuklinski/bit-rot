# core/map/procedural/generator_spawning.py

import random
from core.data.config import *

class ProceduralGeneratorSpawning:
    def _scatter_zombies(self, layers, mask, w, h):
        building_tiles = []
        street_tiles = []
        woods_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue 
                if ground == 'sand_01' or ground == 'dirty_01':
                    building_tiles.append((x, y))
                elif ground == 'asphalt_01':
                    street_tiles.append((x, y))
                elif ground == 'bg_grass':
                    woods_tiles.append((x, y))

        total_zombies = ZOMBIE_MAX_CHUNK
        count_building = int(total_zombies * 0.45)
        count_street = int(total_zombies * 0.25)
        count_woods = total_zombies - count_building - count_street
        
        def place_zombies(target_count, available_tiles):
            if not available_tiles: return
            chosen = random.sample(available_tiles, min(target_count, len(available_tiles)))
            for (zx, zy) in chosen:
                layers['spawn'][zy][zx] = 'Z'

        place_zombies(count_building, building_tiles)
        place_zombies(count_street, street_tiles)
        place_zombies(count_woods, woods_tiles)

    def _scatter_npcs(self, layers, mask, w, h):
        # 1. Configuration
        if NPC_MAX_CHUNK <= 0: return

        # Calculate Global Limit from Per Chunk Config
        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            max_npcs_global = NPC_MAX_CHUNK * total_chunks
        else:
            max_npcs_global = NPC_MAX_CHUNK

        # 2. Gather Candidates
        building_tiles = []
        outside_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                # Valid spots: Empty base (no walls), Empty spawn, Valid ground
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue 
                
                # Strict tile rules for NPC spawn placement
                if ground == 'house_floor_01':
                    building_tiles.append((x, y))
                elif ground in ['asphalt_01', 'sand_01', 'dirty_01', 'bg_grass']:
                    outside_tiles.append((x, y))
        
        total_candidates = len(building_tiles) + len(outside_tiles)
        if total_candidates == 0: return

        # 3. Calculate Counts & Types strictly reflecting the XML config
        count_to_spawn = min(total_candidates, max_npcs_global)
        
        num_static = int(count_to_spawn * NPC_STATIC_PERCENT)
        num_normal = int(count_to_spawn * NPC_HOSTILE_PERCENT)
        
        # Cap by strictly available tiles so we don't convert SNPCs into Hostile NPCs when space runs out
        num_static = min(num_static, len(building_tiles))
        num_normal = min(num_normal, len(outside_tiles))
        
        # 4. Safe Filtering (Zombies)
        zombie_locs = []
        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] == 'Z':
                    zombie_locs.append((x, y))
                    
        SAFE_DISTANCE_SQ = 15 * 15 
        
        def get_safe_candidates(candidates):
            safe = []
            for px, py in candidates:
                too_close = False
                for zx, zy in zombie_locs:
                    dist_sq = (px - zx)**2 + (py - zy)**2
                    if dist_sq < SAFE_DISTANCE_SQ:
                        too_close = True
                        break
                if not too_close: safe.append((px, py))
            return safe if len(safe) > 0 else candidates

        safe_building = get_safe_candidates(building_tiles) if building_tiles else []
        safe_outside = get_safe_candidates(outside_tiles) if outside_tiles else []

        # 5. Spawn
        spawned_static = 0
        if num_static > 0 and safe_building:
            chosen_indoor = random.sample(safe_building, min(num_static, len(safe_building)))
            for nx, ny in chosen_indoor:
                layers['spawn'][ny][nx] = 'SNPC'
                spawned_static += 1
                
        spawned_normal = 0
        if num_normal > 0 and safe_outside:
            chosen_normal = random.sample(safe_outside, min(num_normal, len(safe_outside)))
            for nx, ny in chosen_normal:
                layers['spawn'][ny][nx] = 'NPC'
                spawned_normal += 1
                
        print(f"  > NPC Scatter: Placed {spawned_static} Static (Indoor), {spawned_normal} Hostile (Outdoor).")

    def _scatter_npcs_l2(self, layers, w, h):
        """L2 specific NPC scattering using standard floor detection."""
        # 1. Config
        if NPC_MAX_CHUNK <= 0: return
        
        # Calculate Global Limit from Per Chunk Config
        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            max_npcs_global = NPC_MAX_CHUNK * total_chunks
        else:
            max_npcs_global = NPC_MAX_CHUNK
        
        # 2. Gather Candidates in L2 Layers
        potential_tiles = []
        ground = layers['ground_L2']
        base = layers['base_L2']
        spawn = layers['spawn_L2']
        
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                
                b_char = base[y][x]
                if b_char != ' ':
                    if b_char in defs and defs[b_char].get('is_obstacle', False): continue
                    if b_char == '@': continue

                if spawn[y][x] != ' ': continue
                
                g_char = ground[y][x]
                if g_char == ' ' or g_char == '@': continue 
                
                potential_tiles.append((x, y))

        if not potential_tiles: return

        # 3. Calculate Distribution
        count_to_spawn = min(len(potential_tiles), max_npcs_global)
        
        num_static = int(count_to_spawn * NPC_STATIC_PERCENT)
        num_normal = int(count_to_spawn * NPC_HOSTILE_PERCENT)
        
        total_valid = num_static + num_normal
        if total_valid <= 0: return
        
        # Cap to available tiles proportionally
        if total_valid > len(potential_tiles):
            ratio = len(potential_tiles) / total_valid
            num_static = int(num_static * ratio)
            num_normal = int(num_normal * ratio)

        # Build the exact array of markers
        spawn_types = ['SNPC'] * num_static + ['NPC'] * num_normal
        random.shuffle(spawn_types)
        
        # 4. Spawn
        chosen = random.sample(potential_tiles, len(spawn_types))
        for i, (nx, ny) in enumerate(chosen):
            spawn[ny][nx] = spawn_types[i]
                
        print(f"  > NPC Scatter L2: Placed {len(spawn_types)} NPCs ({num_static} Static, {num_normal} Hostile).")

    def _scatter_vehicles(self, layers, mask, w, h):
        """
        [NEW] Scatter vehicles on road/asphalt AND drunkard (dirty_01) tiles.
        """
        street_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                # Must be empty space (no walls, no existing spawn)
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                # Check for road keywords or SPECIFICALLY dirty_01 (Drunkard Paths)
                if 'asphalt' in ground or 'road' in ground or 'dirty_01' in ground:
                    street_tiles.append((x, y))

        if not street_tiles: 
            return

        # Determine limit (Global Limit calculated from Chunk config)
        if CHUNK_SIZE > 0:
            # W and H are in tiles.
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = num_chunks_w * num_chunks_h
            
            # If map size is weird, at least assume 1 chunk
            total_chunks = max(1, total_chunks)
            
            max_vehicles_global = MAX_VEH_CHUNK * total_chunks
        else:
            max_vehicles_global = 40 # Fallback default
        
        print(f"  > Vehicle Scatter: Global Limit {max_vehicles_global} (Chunks: {total_chunks} x {MAX_VEH_CHUNK})")

        count_to_spawn = min(len(street_tiles), max_vehicles_global)
        if count_to_spawn <= 0: return

        chosen = random.sample(street_tiles, count_to_spawn)
        
        for (vx, vy) in chosen:
            layers['spawn'][vy][vx] = 'VEH'
            
        print(f"  > Vehicle Scatter: Placed {count_to_spawn} vehicles on Roads/Paths.")
    

    def _scatter_quest_items(self, layers, mask, w, h, current_layer):
        """
        Dynamically distributes 'quest' type items across the map based on XML constraints.
        """
        from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
        
        if not ITEM_TEMPLATES:
            load_item_templates_data()
            
        # [NEW] Track spawned items globally across layers (L1 and L2)
        if not hasattr(self, 'quest_items_spawned'):
            self.quest_items_spawned = {}
            
        for item_name, data in ITEM_TEMPLATES.items():
            if data.get('type') != 'quest':
                continue
            
            # 1. Enforce Layer constraint
            allowed_layers = data.get('spawn_layer', [])
            if allowed_layers and current_layer not in allowed_layers:
                continue
            
            max_spawn = data.get('spawn_amount_global', 1)
            spawned_so_far = self.quest_items_spawned.get(item_name, 0)
            remaining_to_spawn = max_spawn - spawned_so_far
            
            # Stop trying if we've already hit the global limit on a previous layer
            if remaining_to_spawn <= 0:
                continue
                
            allowed_tiles = data.get('spawn_maptile', [])
            valid_spots = []
            
            # 2. Scan map for valid maptiles/containers
            for y in range(h):
                for x in range(w):
                    # Only spawn on empty spawn tiles
                    if layers['spawn'][y][x] != ' ': 
                        continue
                    
                    ground_tile = layers['ground'][y][x]
                    base_tile = layers['base'][y][x]
                    
                    # Match tile names against allowed XML maptiles directly!
                    if allowed_tiles:
                        if any(t in ground_tile for t in allowed_tiles) or any(t in base_tile for t in allowed_tiles):
                            valid_spots.append((x, y))
                    else:
                        # Fallback if XML doesn't specify a spawn_maptile
                        # You could add logic here to allow them to spawn on generic interior floors
                        pass
                        
            # 3. Scatter up to the global limit
            if valid_spots:
                chosen_spots = random.sample(valid_spots, min(remaining_to_spawn, len(valid_spots)))
                for cx, cy in chosen_spots:
                    layers['spawn'][cy][cx] = f"QI_{item_name}"
                
                # Update global tracker
                self.quest_items_spawned[item_name] = spawned_so_far + len(chosen_spots)
                print(f"  > Quest Scatter [Layer {current_layer}]: Placed {len(chosen_spots)} '{item_name}' (Total: {self.quest_items_spawned[item_name]}/{max_spawn}).")
            else:
                # [FIX] Always print an output so you know it attempted to spawn the item
                print(f"  > Quest Scatter [Layer {current_layer}]: Placed 0 '{item_name}'. (No valid '{allowed_tiles}' spots generated on this map layer)")

    def _scatter_animals(self, layers, mask, w, h):
        """
        [NEW] Scatter Animals ('ANM') based on ANIMAL_SPAWN_COUNT.
        Prefers natural tiles (Grass, Woods) but can spawn on Floor/Dirt.
        
        Calculates total limit based on map size to ensure 'Per Chunk' setting works globally.
        """
        if ANIMAL_SPAWN_COUNT <= 0: return

        valid_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                # Must be empty space (no walls, no existing spawn)
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue

                if ground == 'house_floor_01': 
                    continue
                
                # Check for natural or valid walking tiles
                # Grass, Dirty, Floor, Asphalt are all valid for animals generally (Rat can go anywhere)
                if 'grass' in ground or 'dirty' in ground:
                    valid_tiles.append((x, y))
                

        if not valid_tiles: return

        # Calculate Global Limit from Per Chunk Config
        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            global_limit = ANIMAL_SPAWN_COUNT * total_chunks
        else:
            global_limit = ANIMAL_SPAWN_COUNT

        count_to_spawn = min(len(valid_tiles), global_limit)
        
        chosen = random.sample(valid_tiles, count_to_spawn)
        
        for (ax, ay) in chosen:
            layers['spawn'][ay][ax] = 'ANM'
            
        print(f"  > Animal Scatter: Placed {count_to_spawn} animals (Target: {global_limit}).")