# core/map/map_manager.py

import os
import re
import csv
import pygame
import random
import time
from core.data.config import *
from core.messages import display_message
from core.entities.item.item import Item
from core.placement import find_free_tile
from core.data.localization import tr

class MapManager:
    def __init__(self, game, map_folder=f"{os.path.join(BASE_DIR, 'game', 'lib', 'map')}"):
        
        self.game = game
        self.map_folder = map_folder
        self.current_map_filename = 'map_L1_world_map.csv' 
        self.map_files = self._discover_maps()
        self.shaking_tiles = {}
        
        # [NEW] Chunk Caching System
        self.chunk_surfaces = {} 
        self.CHUNK_SIZE = CHUNK_SIZE if 'CHUNK_SIZE' in globals() else 32

        # [NEW] Performance: Chunk Generation Throttling
        self.chunks_generated_this_frame = 0
        self.MAX_CHUNKS_PER_FRAME = 2  # Throttling limit per frame

        if not hasattr(self.game, 'vehicles'):
            self.game.vehicles = []

    def refresh_maps(self):
        """Re-scans the map folder and updates the map_files list."""
        print("Refreshing map file list...")
        self.map_files = self._discover_maps()
        print(f"Found {len(self.map_files)} map files.")

    def _discover_maps(self):
        maps = {}
        # Regex for single world map
        pattern_world = re.compile(r'map_L(\d+)_world_map\.csv')
        # Regex for separated chunks
        pattern_chunk = re.compile(r'map_L(\d+)_(\d+)_(\d+)_map\.csv')

        if not os.path.exists(self.map_folder):
            print(f"Warning: Map folder '{self.map_folder}' does not exist.")
            return maps

        for filename in os.listdir(self.map_folder):
            match_world = pattern_world.match(filename)
            match_chunk = pattern_chunk.match(filename)
            
            if match_chunk:
                try:
                    layer = int(match_chunk.group(1))
                    maps[filename] = {
                        'filename': filename,
                        'layer': layer,
                        'gx': int(match_chunk.group(2)),
                        'gy': int(match_chunk.group(3)),
                        'position': 0,
                    }
                except ValueError:
                    print(f"Warning: Could not parse chunk map filename {filename}")
            elif match_world:
                try:
                    layer = int(match_world.group(1))
                    maps[filename] = {
                        'filename': filename,
                        'layer': layer,
                        'position': 0,
                    }
                except ValueError:
                    print(f"Warning: Could not parse world map filename {filename}")
        return maps

    def get_current_map_connections(self):
        return None

    def transition(self, direction):
        return None

    # [NEW] Chunk Caching Methods
    def clear_cache(self):
        """Clears all cached chunk surfaces."""
        self.chunk_surfaces.clear()

    def reset_frame_metrics(self):
        """Called by Game loop every frame to reset generation limits."""
        self.chunks_generated_this_frame = 0

    def update_chunks(self, player_center_pos):
        """
        Proactively manages chunk generation around the player.
        Generates next chunks BEFORE they are fully visible to avoid stutter.
        """
        if self.chunks_generated_this_frame >= self.MAX_CHUNKS_PER_FRAME:
            return

        px, py = player_center_pos
        
        # Current chunk coords
        curr_cx = int(px // (self.CHUNK_SIZE * TILE_SIZE))
        curr_cy = int(py // (self.CHUNK_SIZE * TILE_SIZE))
        
        # Radius to pre-load (slightly larger than view)
        LOAD_RADIUS = 2 
        
        # Spiral out or check nearby chunks
        chunks_to_check = []
        for dy in range(-LOAD_RADIUS, LOAD_RADIUS + 1):
            for dx in range(-LOAD_RADIUS, LOAD_RADIUS + 1):
                chunks_to_check.append((curr_cx + dx, curr_cy + dy))
        
        # Sort by distance to center to load closest first
        chunks_to_check.sort(key=lambda p: (p[0] - curr_cx)**2 + (p[1] - curr_cy)**2)
        
        layer_idx = self.game.current_layer_index
        
        for cx, cy in chunks_to_check:
            # [FIX] Do not process negative chunk coordinates
            if cx < 0 or cy < 0:
                continue

            # Check World Layer
            key = (layer_idx, cx, cy, 'world')
            if key not in self.chunk_surfaces:
                # Generate it now if we have budget
                if self.chunks_generated_this_frame < self.MAX_CHUNKS_PER_FRAME:
                     # get_chunk_surface handles generation and caching
                     self.get_chunk_surface(cx, cy, layer_idx, 'world')
                else:
                    break
            
            # Check Roof Layer (if applicable)
            key_roof = (layer_idx, cx, cy, 'roof')
            if key_roof not in self.chunk_surfaces:
                 if self.chunks_generated_this_frame < self.MAX_CHUNKS_PER_FRAME:
                      self.get_chunk_surface(cx, cy, layer_idx, 'roof')
                 else:
                     break
                     
        # Optional: Unload very far chunks
        self.unload_far_chunks(curr_cx, curr_cy, LOAD_RADIUS + 1)

    def unload_far_chunks(self, center_cx, center_cy, keep_radius):
        """Unloads chunks outside the keep_radius to free memory."""
        keys_to_remove = []
        for key in self.chunk_surfaces:
            l, cx, cy, mode = key
            if abs(cx - center_cx) > keep_radius or abs(cy - center_cy) > keep_radius:
                keys_to_remove.append(key)
        
        for k in keys_to_remove:
            del self.chunk_surfaces[k]

    def invalidate_chunk(self, grid_x, grid_y, layer_idx=None):
        """Removes the cached surface for the chunk containing (grid_x, grid_y) so it redraws next frame."""
        if layer_idx is None: 
            layer_idx = self.game.current_layer_index
            
        cx = grid_x // self.CHUNK_SIZE
        cy = grid_y // self.CHUNK_SIZE
        
        # Identify keys to remove (matching layer and chunk coordinates)
        keys_to_remove = [k for k in self.chunk_surfaces if k[0] == layer_idx and k[1] == cx and k[2] == cy]
        
        for k in keys_to_remove:
            del self.chunk_surfaces[k]

    def _get_adjacent_bg(self, grid, x, y):
        """Helper to find the adjacent solid terrain to fill transparent gaps in live chunks."""
        h = len(grid)
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= ny < h:
                row = grid[ny]
                if 0 <= nx < len(row):
                    neighbor = row[nx]
                    # [UPDATED] Include asphalt in the transparency check
                    is_transparent_overlay = neighbor and (
                        neighbor.startswith('dirty_') or 
                        neighbor.startswith('beach_sand_') or 
                        neighbor.startswith('sand_') or 
                        neighbor.startswith('asphalt_')
                    )
                    if neighbor and not is_transparent_overlay and neighbor != ' ':
                        return neighbor
        return 'bg_grass'

    def get_chunk_surface(self, cx, cy, layer_idx, layer_type='world'):
        """
        Returns a cached surface for a specific chunk. 
        layer_type: 'world' (Ground + Base objects) or 'roof'
        """
        key = (layer_idx, cx, cy, layer_type)
        if key in self.chunk_surfaces:
            return self.chunk_surfaces[key]

        # [NEW] Throttling: If we generated too many chunks this frame, postpone this one.
        if self.chunks_generated_this_frame >= self.MAX_CHUNKS_PER_FRAME:
            return None

        self.chunks_generated_this_frame += 1

        # Calculate dimensions
        pixel_size = self.CHUNK_SIZE * TILE_SIZE
        surface = pygame.Surface((pixel_size, pixel_size), pygame.SRCALPHA)
        
        min_x = cx * self.CHUNK_SIZE
        min_y = cy * self.CHUNK_SIZE
        max_x = min_x + self.CHUNK_SIZE
        max_y = min_y + self.CHUNK_SIZE

        # Determine data sources
        ground_data = None
        base_data = None
        roof_data = None
        light_data = None

        # If requesting the currently active layer, use the direct references for speed
        if layer_idx == self.game.current_layer_index:
            ground_data = getattr(self.game, 'ground_data', None)
            base_data = getattr(self.game, 'map_data', None)
            roof_data = getattr(self.game, 'roof_data', None)
            light_data = getattr(self.game, 'light_data', None)
        else:
            # Otherwise fetch from storage
            if hasattr(self.game, 'all_ground_layers'):
                ground_data = self.game.all_ground_layers.get(layer_idx)
            if hasattr(self.game, 'all_map_layers'):
                base_data = self.game.all_map_layers.get(layer_idx)
            if hasattr(self.game, 'all_roof_layers'):
                roof_data = self.game.all_roof_layers.get(layer_idx)
            if hasattr(self.game, 'all_light_layers'):
                light_data = self.game.all_light_layers.get(layer_idx)

        tm = self.game.tile_manager

        # Render Tiles to Surface
        if layer_type == 'world':
            # 1. Ground Layer
            if ground_data:
                # [FIX] Safer bounds checking (ragged array support + negative index prevention)
                y_start = max(0, min_y)
                y_end = min(max_y, len(ground_data))
                
                for y in range(y_start, y_end):
                    row_data = ground_data[y]
                    # Calculate row length per row to prevent IndexError on ragged maps
                    row_len = len(row_data) 
                    
                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)
                    
                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            is_dirty_overlay = char.startswith('dirty_') and char != 'dirty_01'
                            is_sand_overlay = char.startswith('sand_') and char != 'sand_01'
                            is_beach_sand_overlay = char.startswith('beach_sand_') and char != 'beach_sand_01'
                            # [UPDATED] Add Asphalt overlay check
                            is_asphalt_overlay = char.startswith('asphalt_') and char != 'asphalt_01'
                            
                            if is_dirty_overlay or is_sand_overlay or is_beach_sand_overlay or is_asphalt_overlay:
                                bg_tile = self._get_adjacent_bg(ground_data, x, y)
                                if bg_tile in tm.definitions:
                                    surface.blit(tm.definitions[bg_tile]['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))
            
            # 2. Base Layer (Walls, Objects)
            if base_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(base_data))

                for y in range(y_start, y_end):
                    row_data = base_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

            # 3. Light Layer (Light source tiles)
            if light_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(light_data))

                for y in range(y_start, y_end):
                    row_data = light_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

        elif layer_type == 'roof':
            if roof_data:
                y_start = max(0, min_y)
                y_end = min(max_y, len(roof_data))
                
                for y in range(y_start, y_end):
                    row_data = roof_data[y]
                    row_len = len(row_data)

                    x_start = max(0, min_x)
                    x_end = min(max_x, row_len)

                    for x in range(x_start, x_end):
                        char = row_data[x]
                        if char and char != ' ':
                            defn = tm.definitions.get(char)
                            if defn:
                                surface.blit(defn['image'], ((x - min_x) * TILE_SIZE, (y - min_y) * TILE_SIZE))

        surface = surface.convert_alpha() 
        self.chunk_surfaces[key] = surface
        return surface

    def get_vehicle_at(self, grid_x, grid_y):
        """
        Finds a dynamic vehicle object located at the given grid coordinates.
        Used by handle_right_click in mouse.py.
        """
        for vehicle in self.game.vehicles:
            veh_grid_x = int(vehicle.x // TILE_SIZE)
            veh_grid_y = int(vehicle.y // TILE_SIZE)
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            if vehicle.rect.colliderect(tile_rect):
                return vehicle
        return None

    def get_tile_at(self, grid_x, grid_y):
        """Gets the tile definition at a specific grid coordinate."""
        if self.game.map_data and 0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0]):
            char = self.game.map_data[grid_y][grid_x]
            if char in self.game.tile_manager.definitions:
                return self.game.tile_manager.definitions[char]
        return None

    def save_map_to_file(self, save_dir):
        """Saves the current state of map layers to CSV files in the save directory."""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        def write_layer(layout, filename):
            path = os.path.join(save_dir, filename)
            try:
                with open(path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(layout)
                print(f"Saved map layer to {path}")
            except Exception as e:
                print(f"Error saving map layer {filename}: {e}")

        # Extract base prefix to save using chunk nomenclature
        current_name = self.current_map_filename
        chunk_match = re.match(r'map_L\d+_(\d+)_(\d+)_map\.csv', current_name)

        if hasattr(self.game, 'all_map_layers'):
            for layer_idx, layout in self.game.all_map_layers.items():
                if chunk_match:
                    gx, gy = chunk_match.groups()
                    filename = f'map_L{layer_idx}_{gx}_{gy}_map.csv'
                else:
                    filename = f'map_L{layer_idx}_world_map.csv'
                write_layer(layout, filename)
        
        if hasattr(self.game, 'all_spawn_layers'):
            for layer_idx, layout in self.game.all_spawn_layers.items():
                if chunk_match:
                    gx, gy = chunk_match.groups()
                    filename = f'map_L{layer_idx}_{gx}_{gy}_spawn.csv'
                else:
                    filename = f'map_L{layer_idx}_world_spawn.csv'
                write_layer(layout, filename)

    def toggle_door_state(self, grid_x, grid_y):
        """Toggles a 'statable' tile (like a door) between its states."""
        if not self.game.map_data: return

        current_char = self.game.map_data[grid_y][grid_x]
        current_def = self.game.tile_manager.definitions.get(current_char)

        if not current_def or not current_def.get('is_statable'):
            return

        current_state = current_def.get('state')
        new_state = "open" if current_state == "close" else "close"

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        if new_state == "close":
            entities_in_door = []
            
            # [FIX] Use a slightly relaxed hitbox to catch edge-clipping entities that need pushing
            door_hitbox = tile_rect.inflate(-8, -8)

            if getattr(self.game, 'player', None) and self.game.player.rect.colliderect(door_hitbox):
                entities_in_door.append(self.game.player)
            
            for z in getattr(self.game, 'zombies', []):
                if z.rect.colliderect(door_hitbox):
                    entities_in_door.append(z)
                    
            for n in getattr(self.game, 'npcs', []):
                if n.rect.colliderect(door_hitbox):
                    entities_in_door.append(n)

            if entities_in_door:
                for entity in entities_in_door:
                    ex = getattr(entity, 'x', float(entity.rect.centerx))
                    ey = getattr(entity, 'y', float(entity.rect.centery))
                    door_cx = tile_rect.centerx
                    door_cy = tile_rect.centery
                    
                    # [NEW] "Dead Center" Check
                    # If the player is standing solidly in the middle of the doorway, 
                    # do not push them. Block the door and display the exact message requested.
                    dist_sq = (ex - door_cx)**2 + (ey - door_cy)**2
                    dead_center_threshold = (TILE_SIZE // 3) ** 2  # Represents the middle core of the tile
                    
                    if entity == getattr(self.game, 'player', None) and dist_sq <= dead_center_threshold:
                        display_message(tr('msg', "Player is in the doorway, cannot close."))
                        return 
                    
                    # [PUSH LOGIC] If they are off-center (or are a zombie), gracefully push them out
                    bias_x, bias_y = 0, 0
                    facing = getattr(entity, 'facing', '')
                    if facing == 'up': bias_y = 5      
                    elif facing == 'down': bias_y = -5 
                    elif facing == 'left': bias_x = 5  
                    elif facing == 'right': bias_x = -5 
                    
                    eff_ex = ex + bias_x
                    eff_ey = ey + bias_y
                    
                    valid_targets = []
                    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                    
                    for d_gx, d_gy in dirs:
                        tgt_gx = grid_x + d_gx
                        tgt_gy = grid_y + d_gy
                        
                        if 0 <= tgt_gy < len(self.game.map_data) and 0 <= tgt_gx < len(self.game.map_data[0]):
                            tgt_char = self.game.map_data[tgt_gy][tgt_gx]
                            tgt_def = self.game.tile_manager.definitions.get(tgt_char)
                            if tgt_def and not tgt_def.get('is_obstacle'):
                                tgt_cx = tgt_gx * TILE_SIZE + TILE_SIZE / 2
                                tgt_cy = tgt_gy * TILE_SIZE + TILE_SIZE / 2
                                dist = (eff_ex - tgt_cx)**2 + (eff_ey - tgt_cy)**2
                                valid_targets.append((dist, tgt_gx, tgt_gy))
                                
                    pushed = False
                    if valid_targets:
                        valid_targets.sort(key=lambda x: x[0])
                        best_target = valid_targets[0]
                        tgt_rect = pygame.Rect(best_target[1] * TILE_SIZE, best_target[2] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        
                        entity.rect.centerx = tgt_rect.centerx
                        entity.rect.centery = tgt_rect.centery
                        if hasattr(entity, 'x'): entity.x = float(entity.rect.x)
                        if hasattr(entity, 'y'): entity.y = float(entity.rect.y)
                        pushed = True
                    
                    # Fallback if they are entirely boxed in by obstacles
                    if not pushed:
                        if entity == getattr(self.game, 'player', None):
                            display_message(tr('msg', "Door is completely blocked, cannot close."))
                        return 
        
        base_name = current_char.replace("_open", "").replace("_close", "")
        new_char = f"{base_name}_{new_state}"

        if new_char in self.game.tile_manager.definitions:
            new_def = self.game.tile_manager.definitions[new_char]
            
            self.game.map_data[grid_y][grid_x] = new_char
            
            self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
            if new_def['is_obstacle']:
                self.game.obstacles.append(tile_rect)
            
            if new_def.get('sound_src'):
                self.game.sound_manager.play_sound(
                    new_def['sound_src'],
                    subdir='map',
                    game=self.game,
                    source_pos=tile_rect.center,
                    base_volume=1.0,
                    pitch_variance=0.15,
                    is_critical=True
                )
            
            self.invalidate_chunk(grid_x, grid_y)

        else:
            print(f"Warning: Could not find matching door state '{new_char}'")
    
    # [FIX] Added the 'attacker' argument and conditional checks for stamina drain
    def hit_tile(self, grid_x, grid_y, damage, weapon=None, is_projectile=False, attacker=None):
        if not self.game.map_data or not (0 <= grid_y < len(self.game.map_data) and 0 <= grid_x < len(self.game.map_data[0])):
            return False

        char = self.game.map_data[grid_y][grid_x]
        definition = self.game.tile_manager.definitions.get(char)
        
        if not definition or not definition.get('destructible'):
            return False
            
        # Determine if the entity hitting the tile is the player
        # If attacker is not provided, assume it's the player for backward compatibility
        is_player = (attacker is None) or (attacker == getattr(self.game, 'player', None))
            
        # Only drain stamina and durability if it's a manual melee hit (not a bullet) AND performed by the player
        if not is_projectile and is_player:
            STAMINA_COST = 0.05
            if self.game.player.stamina < STAMINA_COST:
                display_message(tr('msg', "You are too exhausted to chop/mine!"))
                return True

            self.game.player.stamina = max(0, self.game.player.stamina - STAMINA_COST)
            self.game.player.tireness = min(self.game.player.max_tireness, self.game.player.tireness + 0.5)

            if weapon and weapon.durability is not None:
                DURABILITY_COST = 0.05
                weapon.durability = max(0, weapon.durability - DURABILITY_COST)
                if weapon.durability <= 0:
                    self.game.player.active_weapon = None
                    display_message(f"{weapon.name} {tr('msg', 'is broken and unequipped.')}")
                    return True
        
        if definition.get('sound_src'):
            tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            self.game.sound_manager.play_sound(
                definition['sound_src'],
                subdir='map',
                game=self.game,
                source_pos=tile_rect.center,
                base_volume=1.0,
                pitch_variance=0.15
            )

        self.shaking_tiles[(grid_x, grid_y)] = time.time()

        map_name = self.current_map_filename
        if map_name not in self.game.map_states:
            self.game.map_states[map_name] = {}
        if 'tile_health' not in self.game.map_states[map_name]:
            self.game.map_states[map_name]['tile_health'] = {}
        
        pos_key = (grid_x, grid_y)
        if pos_key not in self.game.map_states[map_name]['tile_health']:
            self.game.map_states[map_name]['tile_health'][pos_key] = random.randint(
                definition.get('health_min', 60), 
                definition.get('health_max', 100)
            )
        
        self.game.map_states[map_name]['tile_health'][pos_key] -= damage
        current_hp = self.game.map_states[map_name]['tile_health'][pos_key]
        print(f"Maptile Destructible ({max(0, current_hp)} HP left)")
        
        if current_hp <= 0:
            del self.game.map_states[map_name]['tile_health'][pos_key]
            
            if (grid_x, grid_y) in self.shaking_tiles:
                del self.shaking_tiles[(grid_x, grid_y)]

            # [NEW] Check for barricade reversion or a broken variant
            if '_barricate' in char:
                if '_broke_barricate' in char:
                    target_char = char.replace('_broke_barricate', '_broke')
                else:
                    target_char = char.replace('_barricate', '_close')
            else:
                base_name = char.replace("_open", "").replace("_close", "")
                broken_char = f"{base_name}_broke"
                
                if broken_char in self.game.tile_manager.definitions:
                    target_char = broken_char
                else:
                    try:
                        ground_char = self.game.all_ground_layers[self.game.current_layer_index][grid_y][grid_x]
                    except (KeyError, IndexError, AttributeError):
                        ground_char = "." 
                    target_char = ground_char

            # Replace with the new state
            self._replace_tile(grid_x, grid_y, char, target_char)

            if 'drops' in definition:
                for drop in definition['drops']:
                     if random.random() <= drop['chance']:
                         qty = random.randint(drop.get('min_qty', 1), drop.get('max_qty', 1))
                         for _ in range(qty):
                             item = Item.create_from_name(drop['item'])
                             if item:
                                 center_x = grid_x * TILE_SIZE + TILE_SIZE // 2
                                 center_y = grid_y * TILE_SIZE + TILE_SIZE // 2
                                 item.rect.center = (center_x, center_y)
                                 
                                 if find_free_tile(item.rect, self.game.obstacles, self.game.items_on_ground, initial_pos=(item.rect.x, item.rect.y), max_radius=2):
                                     self.game.items_on_ground.append(item)
                                 else:
                                     print(f"Warning: Could not place dropped item {tr('item', item.name)}")
                             else:
                                 print(f"Warning: Drop item '{drop['item']}' not found in templates.")

        return True

    def _replace_tile(self, grid_x, grid_y, old_char, new_char):
        new_def = self.game.tile_manager.definitions.get(new_char)
        old_def = self.game.tile_manager.definitions.get(old_char)
        if not new_def or not old_def: return

        tile_rect = pygame.Rect(grid_x * TILE_SIZE, grid_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)

        self.game.map_data[grid_y][grid_x] = new_char
        
        self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
        if new_def['is_obstacle']:
            self.game.obstacles.append(tile_rect)
            
        # [NEW] Invalidate chunk to redraw with new tile
        self.invalidate_chunk(grid_x, grid_y)
    
    def remove_vehicle_tile(self, grid_x, grid_y):
        """
        Call this when a player starts driving to remove the static tile 
        representation of the car from the map data.
        """
        try:
            ground_char = self.game.all_ground_layers[self.game.current_layer_index][grid_y][grid_x]
        except (KeyError, IndexError, AttributeError):
            ground_char = "."
            
        self._replace_tile(grid_x, grid_y, self.game.map_data[grid_y][grid_x], ground_char)