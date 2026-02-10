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
        # [UPDATED] NPC Scattering with strict distribution limits
        
        # 1. Configuration
        max_npcs = NPC_MAX_CHUNK
        static_chance = NPC_STATIC_SPAWN
        
        if max_npcs <= 0: return

        # 2. Gather Candidates
        potential_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w-2 or y < 2 or y >= h-2: continue
                # Valid spots: Empty base (no walls), Empty spawn, Valid ground
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                ground = layers['ground'][y][x]
                if ground == self.water_tile: continue 
                if ground in ['asphalt_01', 'sand_01', 'dirty_01']:
                    potential_tiles.append((x, y))
        
        if not potential_tiles: return

        # 3. Calculate Counts & Types
        count_to_spawn = min(len(potential_tiles), max_npcs)
        
        num_static = 0
        if static_chance > 0:
            expected = int(count_to_spawn * static_chance)
            num_static = max(1, expected) # At least 1 Static if chance > 0
        
        num_static = min(num_static, count_to_spawn)
        num_normal = count_to_spawn - num_static
        
        spawn_types = ['S'] * num_static + ['NPC'] * num_normal
        random.shuffle(spawn_types)
        
        # 4. Safe Filtering (Zombies)
        # We try to keep distance from Zombies if possible
        zombie_locs = []
        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] == 'Z':
                    zombie_locs.append((x, y))
                    
        safe_candidates = []
        SAFE_DISTANCE_SQ = 15 * 15 
        
        for px, py in potential_tiles:
            too_close = False
            for zx, zy in zombie_locs:
                dist_sq = (px - zx)**2 + (py - zy)**2
                if dist_sq < SAFE_DISTANCE_SQ:
                    too_close = True
                    break
            if not too_close:
                safe_candidates.append((px, py))

        # Fallback to all candidates if safe ones are too few
        if len(safe_candidates) < count_to_spawn:
            safe_candidates = potential_tiles
            
        # 5. Spawn
        chosen = random.sample(safe_candidates, min(count_to_spawn, len(safe_candidates)))
        
        # If we selected fewer tiles than types (edge case), truncate types
        for i, (nx, ny) in enumerate(chosen):
            if i < len(spawn_types):
                layers['spawn'][ny][nx] = spawn_types[i]

    def _scatter_npcs_l2(self, layers, w, h):
        """
        [NEW] L2 specific NPC scattering using standard floor detection.
        Replaces the complex candidate collection logic.
        """
        # 1. Config
        max_npcs = NPC_MAX_CHUNK
        static_chance = NPC_STATIC_SPAWN
        if max_npcs <= 0: return
        
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
                if g_char == ' ' or g_char == '@': continue # Must not be void or border
                
                potential_tiles.append((x, y))

        if not potential_tiles: return

        # 3. Calculate Distribution (Copied logic from _scatter_npcs)
        count_to_spawn = min(len(potential_tiles), max_npcs)
        
        num_static = 0
        if static_chance > 0:
            expected = int(count_to_spawn * static_chance)
            num_static = max(1, expected) 
        
        num_static = min(num_static, count_to_spawn)
        num_normal = count_to_spawn - num_static
        
        spawn_types = ['S'] * num_static + ['NPC'] * num_normal
        random.shuffle(spawn_types)
        
        # 4. Spawn
        chosen = random.sample(potential_tiles, count_to_spawn)
        for i, (nx, ny) in enumerate(chosen):
            if i < len(spawn_types):
                spawn[ny][nx] = spawn_types[i]
                
        print(f"  > NPC Scatter L2: Placed {count_to_spawn} NPCs ({num_static} Static).")

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