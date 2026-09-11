# core/map/procedural/generator_spawning.py

import random
from core.data.config import *

def is_connector_zone(x, y, w, h):
    cx, cy = w // 2, h // 2
    if (y < 6 or y >= h - 6) and abs(x - cx) <= 3:
        return True
    if (x < 6 or x >= w - 6) and abs(y - cy) <= 3:
        return True
    return False

class ProceduralGeneratorSpawning:
    def _scatter_zombies(self, layers, mask, w, h):
        valid_tiles = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}
        
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w - 2 or y < 2 or y >= h - 2: continue
                if is_connector_zone(x, y, w, h): continue
                
                # Base must be completely empty: no walls, no obstacles, no @ or #
                b_char = layers['base'][y][x]
                if b_char != ' ': continue
                if b_char in ['@', '#']: continue
                if b_char in defs and defs[b_char].get('is_obstacle', False): continue

                if layers['spawn'][y][x] != ' ': continue
                
                # Ground must NOT be void, @, #, water, or obstacle
                ground = layers['ground'][y][x]
                if ground in ['@', '#', ' ', '']: continue
                if ground == self.water_tile or 'water' in ground.lower(): continue
                if ground in defs and defs[ground].get('is_obstacle', False): continue
                
                t_def = defs.get(ground)
                t_name = t_def.get('name', '').lower() if t_def else ground.lower()
                
                # ZOMBIES: Spawn ONLY on pathways and deep background grass
                if 'asphalt' in t_name or 'dirty' in t_name or 'bg' in t_name or 'path' in t_name or \
                   'asphalt' in ground or 'dirty' in ground or 'bg' in ground or 'path' in ground:
                    valid_tiles.append((x, y))

        total_zombies = ZOMBIE_MAX_CHUNK
        if not valid_tiles: return
        
        chosen = random.sample(valid_tiles, min(total_zombies, len(valid_tiles)))
        for (zx, zy) in chosen:
            layers['spawn'][zy][zx] = 'Z'

    def _scatter_npcs(self, layers, mask, w, h):
        if NPC_MAX_CHUNK <= 0: return

        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            max_npcs_global = NPC_MAX_CHUNK * total_chunks
        else:
            max_npcs_global = NPC_MAX_CHUNK

        building_tiles = []
        outside_tiles = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}
        
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w - 2 or y < 2 or y >= h - 2: continue
                if is_connector_zone(x, y, w, h): continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                g_char = layers['ground'][y][x]
                t_def = defs.get(g_char)
                t_name = t_def.get('name', '').lower() if t_def else g_char.lower()
                
                if 'water' in t_name or 'water' in g_char.lower(): continue 
                
                if g_char == 'house_floor_01' or 'house_floor_01' in t_name:
                    building_tiles.append((x, y))
                elif 'asphalt' in t_name or 'dirty' in t_name or 'bg' in t_name or 'path' in t_name or \
                     'asphalt' in g_char or 'dirty' in g_char or 'bg' in g_char or 'path' in g_char:
                    outside_tiles.append((x, y))
        
        total_candidates = len(building_tiles) + len(outside_tiles)
        if total_candidates == 0: return

        count_to_spawn = min(total_candidates, max_npcs_global)
        
        num_static = int(count_to_spawn * NPC_STATIC_PERCENT)
        num_normal = int(count_to_spawn * NPC_HOSTILE_PERCENT)
        
        num_static = min(num_static, len(building_tiles))
        num_normal = min(num_normal, len(outside_tiles))
        
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
        if NPC_MAX_CHUNK <= 0: return

        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            max_npcs_global = NPC_MAX_CHUNK * total_chunks
        else:
            max_npcs_global = NPC_MAX_CHUNK
        
        potential_tiles = []
        ground = layers.get('ground_L2', layers.get('ground'))
        base = layers.get('base_L2', layers.get('base'))
        spawn = layers.get('spawn_L2', layers.get('spawn'))
        
        if not ground or not base or not spawn: return

        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if is_connector_zone(x, y, w, h): continue
                b_char = base[y][x]
                g_char = ground[y][x]
                s_char = spawn[y][x]

                # Base must be empty (no walls, no @, no #, no obstacles)
                if b_char != ' ': continue
                if b_char in ['@', '#']: continue
                if b_char in defs and defs[b_char].get('is_obstacle', False): continue

                # Ground must NOT be void, @, #, or obstacle
                if g_char in ['@', '#', ' ', '']: continue
                if g_char in defs and defs[g_char].get('is_obstacle', False): continue

                if s_char != ' ': continue
                
                potential_tiles.append((x, y))

        if not potential_tiles: return

        count_to_spawn = min(len(potential_tiles), max_npcs_global)
        
        num_static = int(count_to_spawn * NPC_STATIC_PERCENT)
        num_normal = int(count_to_spawn * NPC_HOSTILE_PERCENT)
        
        total_valid = num_static + num_normal
        if total_valid <= 0: return
        
        if total_valid > len(potential_tiles):
            ratio = len(potential_tiles) / total_valid
            num_static = int(num_static * ratio)
            num_normal = int(num_normal * ratio)

        spawn_types = ['SNPC'] * num_static + ['NPC'] * num_normal
        random.shuffle(spawn_types)
        
        chosen = random.sample(potential_tiles, len(spawn_types))
        for i, (nx, ny) in enumerate(chosen):
            spawn[ny][nx] = spawn_types[i]
                
        print(f"  > NPC Scatter L2: Placed {len(spawn_types)} NPCs ({num_static} Static, {num_normal} Hostile).")

    def _scatter_vehicles(self, layers, mask, w, h):
        street_tiles = []
        for y in range(h):
            for x in range(w):
                if x < 2 or x >= w - 2 or y < 2 or y >= h - 2: continue
                if is_connector_zone(x, y, w, h): continue
                if layers['base'][y][x] != ' ' or layers['spawn'][y][x] != ' ': continue
                
                ground = layers['ground'][y][x]
                if 'asphalt' in ground or 'road' in ground or 'dirty_01' in ground:
                    street_tiles.append((x, y))

        if not street_tiles: 
            return

        if CHUNK_SIZE > 0:
            num_chunks_w = w // CHUNK_SIZE
            num_chunks_h = h // CHUNK_SIZE
            total_chunks = max(1, num_chunks_w * num_chunks_h)
            max_vehicles_global = MAX_VEH_CHUNK * total_chunks
        else:
            max_vehicles_global = 40
        
        count_to_spawn = min(len(street_tiles), max_vehicles_global)
        if count_to_spawn <= 0: return

        chosen = random.sample(street_tiles, count_to_spawn)
        for (vx, vy) in chosen:
            layers['spawn'][vy][vx] = 'VEH'
            
        print(f"  > Vehicle Scatter: Placed {count_to_spawn} vehicles on Roads/Paths.")

    def _scatter_quest_items(self, layers, mask, w, h, current_layer):
        from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
        
        if not ITEM_TEMPLATES:
            load_item_templates_data()
            
        if not hasattr(self, 'quest_items_spawned'):
            self.quest_items_spawned = {}
            
        for item_name, data in ITEM_TEMPLATES.items():
            if data.get('type') != 'quest':
                continue
            
            allowed_layers = data.get('spawn_layer', [])
            if allowed_layers and current_layer not in allowed_layers:
                continue
            
            max_spawn = data.get('spawn_amount_global', 1)
            spawned_so_far = self.quest_items_spawned.get(item_name, 0)
            remaining_to_spawn = max_spawn - spawned_so_far
            
            if remaining_to_spawn <= 0:
                continue
                
            allowed_tiles = data.get('spawn_maptile', [])
            valid_spots = []
            
            for y in range(h):
                for x in range(w):
                    if is_connector_zone(x, y, w, h): continue
                    if layers['spawn'][y][x] != ' ': 
                        continue
                    
                    ground_tile = layers['ground'][y][x]
                    base_tile = layers['base'][y][x]
                    
                    if allowed_tiles:
                        if any(t in ground_tile for t in allowed_tiles) or any(t in base_tile for t in allowed_tiles):
                            valid_spots.append((x, y))
                        
            if valid_spots:
                chosen_spots = random.sample(valid_spots, min(remaining_to_spawn, len(valid_spots)))
                for cx, cy in chosen_spots:
                    layers['spawn'][cy][cx] = f"QI_{item_name}"
                
                self.quest_items_spawned[item_name] = spawned_so_far + len(chosen_spots)
                print(f"  > Quest Scatter [Layer {current_layer}]: Placed {len(chosen_spots)} '{item_name}' (Total: {self.quest_items_spawned[item_name]}/{max_spawn}).")

    def _scatter_animals(self, layers, mask, w, h):
        """
        Scatter Animals ('ANM') strictly on the borders of pathways.
        Guarantees NO animals spawn on obstacles, '@', '#', or void.
        """
        if ANIMAL_SPAWN_COUNT <= 0: return

        valid_tiles = []
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if is_connector_zone(x, y, w, h): continue

                b_char = layers['base'][y][x]
                g_char = layers['ground'][y][x]
                s_char = layers['spawn'][y][x]

                # Base must be empty (no obstacles, no walls, no @, no #)
                if b_char != ' ': continue
                if b_char in ['@', '#']: continue
                if b_char in defs and defs[b_char].get('is_obstacle', False): continue

                # Ground must NOT be void, @, #, water, or obstacle
                if g_char in ['@', '#', ' ', '']: continue
                if g_char == self.water_tile or 'water' in g_char.lower(): continue
                if g_char in defs and defs[g_char].get('is_obstacle', False): continue

                if s_char != ' ': continue

                t_def = defs.get(g_char)
                t_name = t_def.get('name', '').lower() if t_def else g_char.lower()
                if 'floor' in t_name or g_char == 'house_floor_01': continue

                # Animals spawn strictly OUTSIDE the paths, but immediately ADJACENT to them
                is_path = 'asphalt' in g_char or 'dirty' in g_char or 'path' in g_char
                is_border = False
                
                if not is_path:
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dy == 0 and dx == 0: continue
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w:
                                adj_g = layers['ground'][ny][nx]
                                if 'asphalt' in adj_g or 'dirty' in adj_g or 'path' in adj_g:
                                    is_border = True
                                    break
                        if is_border: break
                
                if is_border:
                    valid_tiles.append((x, y))

        if not valid_tiles: return

        count_to_spawn = min(len(valid_tiles), ANIMAL_SPAWN_COUNT)
        chosen = random.sample(valid_tiles, count_to_spawn)
        
        for (ax, ay) in chosen:
            layers['spawn'][ay][ax] = 'ANM'
            
        print(f"  > Animal Scatter: Placed {count_to_spawn} animals (Target: {ANIMAL_SPAWN_COUNT}).")