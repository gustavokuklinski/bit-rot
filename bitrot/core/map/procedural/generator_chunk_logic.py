
import math
import random
import pygame
import core.data.config
from core.data.config import *

class ProceduralGeneratorChunk:

    def _generate_confusing_asphalt_maze(self, layers, occupied_mask, w, h, cx, cy, placed_rects=None):
        if placed_rects is None:
            placed_rects = []
        road_tile = 'dirty_01'
        road_width = 2
        num_arms = random.randint(2, 4)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        def is_area_beach_free(x, y, rw):
            for ox in range(-rw // 2, rw // 2 + 1):
                for oy in range(-rw // 2, rw // 2 + 1):
                    tx, ty = x + ox, y + oy
                    if 0 <= tx < w and 0 <= ty < h:
                        if any(pr.collidepoint(tx, ty) for pr in placed_rects):
                            return False
                        if layers.get('protected_mask') and layers['protected_mask'][ty][tx] == 1:
                            return False
                        if layers['base'][ty][tx] != ' ':
                            return False
                        ground = layers['ground'][ty][tx]
                        if ground == getattr(self, 'sand_tile', 'sand_01') or \
                           ground == getattr(self, 'water_tile', 'water_01'):
                            return False
                    else:
                        return False
            return True

        def paint_wide_segment(x1, y1, x2, y2):
            steps = max(abs(x2 - x1), abs(y2 - y1))
            if steps == 0: return
            dx = (x2 - x1) / steps
            dy = (y2 - y1) / steps
            for i in range(steps + 1):
                curr_x = int(x1 + dx * i)
                curr_y = int(y1 + dy * i)
                for ox in range(-road_width // 2, road_width // 2 + 1):
                    for oy in range(-road_width // 2, road_width // 2 + 1):
                        tx, ty = curr_x + ox, curr_y + oy
                        if 0 <= tx < w and 0 <= ty < h:
                            if any(pr.collidepoint(tx, ty) for pr in placed_rects):
                                continue
                            if layers.get('protected_mask') and layers['protected_mask'][ty][tx] == 1:
                                continue
                            if layers['base'][ty][tx] != ' ':
                                continue
                            if not self._is_in_connector_zone_internal(tx, ty, w, h, cx, cy):
                                layers['ground'][ty][tx] = road_tile
                                occupied_mask[ty][tx] = 1

        for _ in range(num_arms):
            curr_x, curr_y = cx, cy
            num_segments = random.randint(2, 4)
            for _ in range(num_segments):
                direction = random.choice(directions)
                dx, dy = direction
                length = random.randint(6, 14)
                target_x = curr_x + (dx * length)
                target_y = curr_y + (dy * length)
                can_paint = True
                for step in range(length + 1):
                    check_x = curr_x + (dx * step)
                    check_y = curr_y + (dy * step)
                    if not is_area_beach_free(check_x, check_y, road_width):
                        can_paint = False
                        break
                if can_paint:
                    paint_wide_segment(curr_x, curr_y, target_x, target_y)
                    curr_x, curr_y = target_x, target_y
                else:
                    break

    def _is_in_connector_zone_internal(self, tx, ty, w, h, cx, cy):
        depth = 5
        radius = 3
        if ty < depth and abs(tx - cx) <= radius: return True
        if ty >= h - depth and abs(tx - cx) <= radius: return True
        if tx < depth and abs(ty - cy) <= radius: return True
        if tx >= w - depth and abs(ty - cy) <= radius: return True
        return False

    def _resolve_boat_char(self):
        if hasattr(self.game, 'tile_manager') and hasattr(self.game.tile_manager, 'definitions'):
            for char, defn in self.game.tile_manager.definitions.items():
                if char in ('tp_boat', 'teleport_boat') or defn.get('type') == 'maptile_teleport' or defn.get('name') in ('tp_boat', 'teleport_boat'):
                    return char
        return 'tp_boat'

    def _place_default_cave_pair(self, layers, occupied_mask_L2, occupied_mask_L3, w, h, strip_stairs=False):
        c2_name = None
        for k in self.templates.keys():
            if k.lower() == 'cave_l2_02':
                c2_name = k
                break
        if not c2_name:
            for k in self.templates.keys():
                if 'cave' in k.lower() and ('l2_02' in k.lower() or 'l2_2' in k.lower()):
                    c2_name = k
                    break

        c3_name = None
        for k in self.templates.keys():
            if k.lower() == 'cave_l3_02':
                c3_name = k
                break
        if not c3_name:
            for k in self.templates.keys():
                if 'cave' in k.lower() and ('l3_02' in k.lower() or 'l3_2' in k.lower()):
                    c3_name = k
                    break

        if c2_name:
            tmpl_c2 = self.templates[c2_name]
            tmpl_c3 = self.templates.get(c3_name)
            c2_w, c2_h = tmpl_c2['width'], tmpl_c2['height']
            c3_w, c3_h = (tmpl_c3['width'], tmpl_c3['height']) if tmpl_c3 else (c2_w, c2_h)
            fit_cw = max(c2_w, c3_w)
            fit_ch = max(c2_h, c3_h)

            for pad_val in [2, 1]:
                for _ in range(80):
                    tx = random.randint(pad_val, max(pad_val, w - fit_cw - pad_val))
                    ty = random.randint(pad_val, max(pad_val, h - fit_ch - pad_val))

                    collision = False
                    for ly in range(max(0, ty - pad_val), min(h, ty + fit_ch + pad_val)):
                        for lx in range(max(0, tx - pad_val), min(w, tx + fit_cw + pad_val)):
                            if occupied_mask_L2[ly][lx] == 1 or occupied_mask_L3[ly][lx] == 1:
                                collision = True
                                break
                        if collision:
                            break

                    if not collision:
                        self._blit_template_mapped(layers, tmpl_c2, tx, ty, w, h, suffix='_L2', strip_stairs=strip_stairs)
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, c2_w, c2_h, w, h, suffix='_L2', margin=4)

                        if tmpl_c3:
                            self._blit_template_mapped(layers, tmpl_c3, tx, ty, w, h, suffix='_L3', strip_stairs=strip_stairs)
                            if hasattr(self, '_apply_l2_border'):
                                self._apply_l2_border(layers, tx, ty, c3_w, c3_h, w, h, suffix='_L3', margin=4)

                        for ly in range(max(0, ty - pad_val), min(h, ty + fit_ch + pad_val)):
                            for lx in range(max(0, tx - pad_val), min(w, tx + fit_cw + pad_val)):
                                occupied_mask_L2[ly][lx] = 1
                                occupied_mask_L3[ly][lx] = 1
                        return True
        return False

    def _get_stair_tile_for_layer(self, target_layer):
        defs = getattr(self.game.tile_manager, 'definitions', {}) if hasattr(self.game, 'tile_manager') else {}
        for char, t_def in defs.items():
            if t_def.get('is_stair') and t_def.get('target_layer') == target_layer:
                return char

        any_stair_char = None
        for char, t_def in defs.items():
            if t_def.get('is_stair'):
                any_stair_char = char
                break

        if any_stair_char:
            new_char = f"stair_to_L{target_layer}"
            if new_char not in defs:
                cloned_def = defs[any_stair_char].copy()
                cloned_def['target_layer'] = target_layer
                cloned_def['is_stair'] = True
                cloned_def['name'] = f"Stair to Layer {target_layer}"
                defs[new_char] = cloned_def
            return new_char

        return 'stair_down'

    def _find_stairs_in_template(self, tmpl):
        defs = getattr(self.game.tile_manager, 'definitions', {}) if hasattr(self.game, 'tile_manager') else {}
        stairs = []
        if not tmpl:
            return stairs
        tw = tmpl.get('width', 0)
        th = tmpl.get('height', 0)

        for r in range(th):
            for c in range(tw):
                bc = tmpl['base'][r][c] if r < len(tmpl.get('base', [])) and c < len(tmpl['base'][r]) else ' '
                gc = tmpl['ground'][r][c] if r < len(tmpl.get('ground', [])) and c < len(tmpl['ground'][r]) else ' '

                b_stair = (bc in defs and defs[bc].get('is_stair')) or 'stair' in str(bc).lower()
                g_stair = (gc in defs and defs[gc].get('is_stair')) or 'stair' in str(gc).lower()

                if b_stair:
                    stairs.append((c, r, 'base', bc))
                elif g_stair:
                    stairs.append((c, r, 'ground', gc))
        return stairs

    def _generate_lobby_chunk(self, gx, gy, w, h, assigned_l2_templates=None, assigned_l3_templates=None, conns_l2=None, conns_l3=None):
        boat_char = self._resolve_boat_char()
        water_tile = getattr(self, 'water_tile', 'water_01')

        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [[water_tile for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask': [[0 for _ in range(w)] for _ in range(h)],
            'base_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L2': [[0 for _ in range(w)] for _ in range(h)],
            'base_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L3': [[0 for _ in range(w)] for _ in range(h)],
        }

        # 1. Resolve Lobby_L1 template
        lobby_name = getattr(self, 'lobby_template', None)
        if not lobby_name:
            for k in self.templates.keys():
                if 'lobby' in k.lower() and 'l3' not in k.lower():
                    lobby_name = k
                    break

        tmpl_l1 = self.templates.get(lobby_name) if lobby_name else None

        # 2. Resolve Lobby_L3 template
        lobby_l3_name = getattr(self, 'lobby_l3_template', None)
        if not lobby_l3_name:
            for k in self.templates.keys():
                if 'lobby' in k.lower() and 'l3' in k.lower():
                    lobby_l3_name = k
                    break

        tmpl_l3 = self.templates.get(lobby_l3_name) if lobby_l3_name else None

        tw, th = 30, 30
        if tmpl_l1:
            tw, th = tmpl_l1['width'], tmpl_l1['height']
        elif tmpl_l3:
            tw, th = tmpl_l3['width'], tmpl_l3['height']

        tx = max(4, (w - tw) // 2)
        ty = max(4, (h - th) // 2)

        # 3. Stamp Lobby_L1 onto Layer 1
        if tmpl_l1:
            self._blit_template(layers, tmpl_l1, tx, ty, w, h, clear_base=True)
        else:
            for dy in range(th):
                for dx in range(tw):
                    layers['ground'][ty + dy][tx + dx] = 'house_floor_01'

        # 4. Stamp Lobby_L3 onto Layer 3 at the EXACT SAME (tx, ty) coordinates
        if tmpl_l3:
            self._blit_template_mapped(layers, tmpl_l3, tx, ty, w, h, suffix='_L3')
            if hasattr(self, '_apply_l2_border'):
                self._apply_l2_border(layers, tx, ty, tmpl_l3['width'], tmpl_l3['height'], w, h, suffix='_L3', margin=4)
            for dy in range(tmpl_l3['height']):
                for dx in range(tmpl_l3['width']):
                    if 0 <= tx + dx < w and 0 <= ty + dy < h:
                        layers['protected_mask_L3'][ty + dy][tx + dx] = 1

        # 5. Setup Lobby L1 <-> L3 Stair ONLY (No L3 -> L2 stair inside Lobby_L3)
        occupied_mask_L2 = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L3 = [[0 for _ in range(w)] for _ in range(h)]
        pad = 4
        for ly in range(max(0, ty - pad), min(h, ty + th + pad)):
            for lx in range(max(0, tx - pad), min(w, tx + tw + pad)):
                occupied_mask_L3[ly][lx] = 1

        stair_to_l3_char = self._get_stair_tile_for_layer(3)
        stair_to_l1_char = self._get_stair_tile_for_layer(1)

        l1_stairs = self._find_stairs_in_template(tmpl_l1)
        if l1_stairs:
            s1_c, s1_r, s1_loc, _ = l1_stairs[0]
        else:
            s1_c, s1_r = tw // 2, th // 2
            s1_loc = 'base'

        s1_gx = tx + s1_c
        s1_gy = ty + s1_r

        # L1 Stair -> climbs to Layer 3
        if s1_loc == 'ground':
            layers['ground'][s1_gy][s1_gx] = stair_to_l3_char
            layers['base'][s1_gy][s1_gx] = ' '
        else:
            layers['base'][s1_gy][s1_gx] = stair_to_l3_char

        # L3 Landing Stair -> returns to Layer 1
        layers['base_L3'][s1_gy][s1_gx] = stair_to_l1_char
        layers['ground_L3'][s1_gy][s1_gx] = 'house_floor_01'

        # 6. Clear L1 entity spawns and place Boat + Player Spawn on Lobby_L1
        for y in range(h):
            for x in range(w):
                sp = layers['spawn'][y][x]
                if sp in ('HNPC', 'FNPC', 'Z', 'ANM'):
                    layers['spawn'][y][x] = ' '

        boat_coords = None
        for y in range(h):
            for x in range(w):
                if layers['base'][y][x] in (boat_char, 'tp_boat', 'teleport_boat'):
                    boat_coords = (x, y)
                    layers['base'][y][x] = boat_char
                    break
            if boat_coords:
                break

        if not boat_coords:
            for dy in range(-2, th + 2):
                for dx in range(-2, tw + 2):
                    bx = tx + dx
                    by = ty + dy
                    if 0 <= bx < w and 0 <= by < h:
                        if layers['ground'][by][bx] == water_tile and layers['base'][by][bx] == ' ':
                            has_land_adj = False
                            for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                                nx, ny = bx + ox, by + oy
                                if 0 <= nx < w and 0 <= ny < h:
                                    if layers['ground'][ny][nx] != water_tile and layers['base'][ny][nx] == ' ':
                                        has_land_adj = True
                                        break
                            if has_land_adj:
                                layers['base'][by][bx] = boat_char
                                layers['spawn'][by][bx] = ' '
                                boat_coords = (bx, by)
                                break
                if boat_coords:
                    break

        player_spawn_tile = (tx + tw // 2, ty + th // 2)
        if boat_coords:
            bx, by = boat_coords
            candidates = []
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    cx_tile = bx + dx
                    cy_tile = by + dy
                    if 0 <= cx_tile < w and 0 <= cy_tile < h:
                        dist = math.hypot(dx, dy)
                        if 1.4 <= dist <= 2.8:
                            if layers['ground'][cy_tile][cx_tile] != water_tile and layers['base'][cy_tile][cx_tile] == ' ':
                                candidates.append((abs(dist - 2.0), cx_tile, cy_tile))

            if candidates:
                candidates.sort(key=lambda c: c[0])
                px, py = candidates[0][1], candidates[0][2]
                player_spawn_tile = (px, py)
                layers['spawn'][py][px] = 'P'
            else:
                layers['spawn'][player_spawn_tile[1]][player_spawn_tile[0]] = 'P'

        # 7. Generate a random Cave on Lobby L1 as a small island connecting L1 <-> L2
        self._place_lobby_cave_island(
            layers, occupied_mask_L2, occupied_mask_L3,
            tx, ty, tw, th, w, h,
            boat_coords=boat_coords,
            player_spawn_tile=player_spawn_tile,
            lobby_stair_tile=(s1_gx, s1_gy),
            water_tile=water_tile
        )

        # Clear any L1 hostiles/animals that the Cave template might have brought onto Lobby L1
        for y in range(h):
            for x in range(w):
                sp = layers['spawn'][y][x]
                if sp in ('HNPC', 'FNPC', 'Z', 'ANM'):
                    layers['spawn'][y][x] = ' '

        # 8. Spawn Builds Marked for L3 on Layer 3 (strip unpaired stairs)
        if assigned_l3_templates:
            for l3_name in assigned_l3_templates:
                if l3_name not in self.templates:
                    continue
                l3_tmpl = self.templates[l3_name]
                l3_w, l3_h = l3_tmpl['width'], l3_tmpl['height']

                for _ in range(60):
                    btx = random.randint(pad, max(pad, w - l3_w - pad))
                    bty = random.randint(pad, max(pad, h - l3_h - pad))

                    collision = False
                    for ly in range(max(0, bty - pad), min(h, bty + l3_h + pad)):
                        for lx in range(max(0, btx - pad), min(w, btx + l3_w + pad)):
                            if occupied_mask_L3[ly][lx] == 1:
                                collision = True
                                break
                        if collision:
                            break

                    if not collision:
                        self._blit_template_mapped(layers, l3_tmpl, btx, bty, w, h, suffix='_L3', strip_stairs=True)
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, btx, bty, l3_w, l3_h, w, h, suffix='_L3', margin=4)

                        for ly in range(max(0, bty - pad), min(h, bty + l3_h + pad)):
                            for lx in range(max(0, btx - pad), min(w, btx + l3_w + pad)):
                                occupied_mask_L3[ly][lx] = 1
                        break

        # 9. Stamp Default Game Cave Templates (Cave_L2_02 on L2 & Cave_L3_02 on L3) keeping L2 <-> L3 stairs
        self._place_default_cave_pair(layers, occupied_mask_L2, occupied_mask_L3, w, h)

        # 10. Stamp any assigned L2 builds (strip unpaired stairs)
        if assigned_l2_templates:
            for l2_name in assigned_l2_templates:
                if l2_name not in self.templates:
                    continue
                l2_tmpl = self.templates[l2_name]
                l2_w, l2_h = l2_tmpl['width'], l2_tmpl['height']

                for _ in range(60):
                    btx = random.randint(pad, max(pad, w - l2_w - pad))
                    bty = random.randint(pad, max(pad, h - l2_h - pad))

                    collision = False
                    for ly in range(max(0, bty - pad), min(h, bty + l2_h + pad)):
                        for lx in range(max(0, btx - pad), min(w, btx + l2_w + pad)):
                            if occupied_mask_L2[ly][lx] == 1:
                                collision = True
                                break
                        if collision:
                            break

                    if not collision:
                        self._blit_template_mapped(layers, l2_tmpl, btx, bty, w, h, suffix='_L2', strip_stairs=True)
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, btx, bty, l2_w, l2_h, w, h, suffix='_L2', margin=4)

                        for ly in range(max(0, bty - pad), min(h, bty + l2_h + pad)):
                            for lx in range(max(0, btx - pad), min(w, btx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1
                        break

        fnpc_candidates = []
        for dy in range(1, th - 1):
            for dx in range(1, tw - 1):
                lx = tx + dx
                ly = ty + dy
                if 0 <= lx < w and 0 <= ly < h:
                    if (layers['ground'][ly][lx] != water_tile and 
                        layers['base'][ly][lx] == ' ' and 
                        layers['spawn'][ly][lx] == ' '):
                        fnpc_candidates.append((lx, ly))

        if fnpc_candidates:
            random.shuffle(fnpc_candidates)
            chosen_npcs = []
            for cx_tile, cy_tile in fnpc_candidates:
                # Maintain at least 4 tiles (64px) between NPCs so they never spawn adjacent or stacked
                if all(math.hypot(cx_tile - ex, cy_tile - ey) >= 4.0 for ex, ey in chosen_npcs):
                    chosen_npcs.append((cx_tile, cy_tile))
                    layers['spawn'][cy_tile][cx_tile] = 'FNPC'
                    if len(chosen_npcs) == 3:
                        break

        for ly in range(h):
            for lx in range(w):
                if layers['spawn_L2'][ly][lx] == 'FNPC':
                    layers['spawn_L2'][ly][lx] = 'HNPC'
                if layers['spawn_L3'][ly][lx] == 'FNPC':
                    layers['spawn_L3'][ly][lx] = 'HNPC'

        return layers

    def _get_l2_counterpart(self, tmpl_name, is_forest=False):
        potential_l2_names = []
        if 'l1' in tmpl_name.lower():
            potential_l2_names.append(tmpl_name.replace('L1', 'L2').replace('l1', 'l2'))
        potential_l2_names.append(f"{tmpl_name}_L2")
        parts = tmpl_name.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            potential_l2_names.append(f"{parts[0]}_L2_{parts[1]}")
            potential_l2_names.append(f"{parts[0]}_L2")
        low = tmpl_name.lower()
        if is_forest:
            potential_l2_names.append("Forest_L2")
        else:
            if "petrol" in low and "building" in low: potential_l2_names.append("Petrol_Building_L2")
            elif "petrol" in low: potential_l2_names.append("Petrol_L2")
            if "building" in low: potential_l2_names.append("Building_L2")

        for pot in potential_l2_names:
            for k in self.templates.keys():
                if k.lower() == pot.lower():
                    return k
        return None

    def _get_l3_counterpart(self, tmpl_name, is_forest=False):
        potential_l3_names = []
        low = tmpl_name.lower()
        if 'l2' in low:
            potential_l3_names.append(tmpl_name.replace('L2', 'L3').replace('l2', 'l3'))
        elif 'l1' in low:
            potential_l3_names.append(tmpl_name.replace('L1', 'L3').replace('l1', 'l3'))
        potential_l3_names.append(f"{tmpl_name}_L3")
        parts = tmpl_name.rsplit('_', 1)
        if len(parts) == 2 and parts[1].isdigit():
            potential_l3_names.append(f"{parts[0]}_L3_{parts[1]}")
            potential_l3_names.append(f"{parts[0]}_L3")
        if is_forest:
            potential_l3_names.append("Forest_L3")
        else:
            if "cave" in low and ("02" in low or "2" in low):
                potential_l3_names.append("Cave_L3_02")
            if "bunker" in low: potential_l3_names.append("Bunker_L3")
            if "dungeon" in low: potential_l3_names.append("Dungeon_L3")

        for pot in potential_l3_names:
            for k in self.templates.keys():
                if k.lower() == pot.lower():
                    return k
        return None

    def _place_lobby_cave_island(self, layers, occupied_mask_L2, occupied_mask_L3,
                                 tx, ty, tw, th, w, h,
                                 boat_coords=None, player_spawn_tile=None,
                                 lobby_stair_tile=None, water_tile='water_01'):
        cave_temps = [
            t for t in self.categorized_templates.get('Cave', [])
            if 'l2' not in t.lower() and 'l3' not in t.lower()
        ]
        if not cave_temps:
            cave_temps = list(self.categorized_templates.get('Cave', []))
        cave_with_l2 = [t for t in cave_temps if self._get_l2_counterpart(t, is_forest=False)]
        if cave_with_l2:
            cave_temps = cave_with_l2
        if not cave_temps:
            return False

        cave_name = random.choice(cave_temps)
        cave_tmpl = self.templates.get(cave_name)
        if not cave_tmpl:
            return False

        l2_key = self._get_l2_counterpart(cave_name, is_forest=False)
        tmpl_l2 = self.templates.get(l2_key) if l2_key else None
        l3_key = self._get_l3_counterpart(cave_name, is_forest=False)
        tmpl_l3 = self.templates.get(l3_key) if l3_key else None

        cw_t, ch_t = cave_tmpl['width'], cave_tmpl['height']
        fit_w = max(cw_t, tmpl_l2['width'] if tmpl_l2 else 0, tmpl_l3['width'] if tmpl_l3 else 0)
        fit_h = max(ch_t, tmpl_l2['height'] if tmpl_l2 else 0, tmpl_l3['height'] if tmpl_l3 else 0)

        lobby_excl_rect = pygame.Rect(tx - 10, ty - 10, tw + 20, th + 20)
        lobby_cx, lobby_cy = tx + tw / 2.0, ty + th / 2.0
        pad = 4

        # Also pick a Forest building for the Lobby islet
        forest_tmpl = None
        forest_l2 = None
        forest_l3 = None
        if getattr(self, 'forest_templates', None):
            f_name = random.choice(self.forest_templates)
            forest_tmpl = self.templates.get(f_name)
            if forest_tmpl:
                f_l2_key = self._get_l2_counterpart(f_name, is_forest=True)
                if f_l2_key:
                    forest_l2 = self.templates.get(f_l2_key)
                f_l3_key = self._get_l3_counterpart(f_name, is_forest=True)
                if f_l3_key:
                    forest_l3 = self.templates.get(f_l3_key)

        fw_t = forest_tmpl['width'] if forest_tmpl else 0
        fh_t = forest_tmpl['height'] if forest_tmpl else 0
        fit_fw = max(fw_t, forest_l2['width'] if forest_l2 else 0, forest_l3['width'] if forest_l3 else 0)
        fit_fh = max(fh_t, forest_l2['height'] if forest_l2 else 0, forest_l3['height'] if forest_l3 else 0)

        if forest_tmpl:
            place_horiz = random.random() < 0.5
            forest_rel_x = (fit_w + 2) if place_horiz else 0
            forest_rel_y = 0 if place_horiz else (fit_h + 2)
            comb_w = max(fit_w, forest_rel_x + fit_fw)
            comb_h = max(fit_h, forest_rel_y + fit_fh)
        else:
            forest_rel_x, forest_rel_y = 0, 0
            comb_w, comb_h = fit_w, fit_h

        def is_valid_cave_spot(cx0, cy0):
            if cx0 < 10 or cy0 < 10 or cx0 + comb_w > w - 10 or cy0 + comb_h > h - 10:
                return False
            c_rect = pygame.Rect(cx0 - 6, cy0 - 6, comb_w + 12, comb_h + 12)
            if c_rect.colliderect(lobby_excl_rect):
                return False
            if boat_coords:
                bx, by = boat_coords
                if (cx0 - 6 <= bx <= cx0 + comb_w + 6) and (cy0 - 6 <= by <= cy0 + comb_h + 6):
                    return False
            for ly in range(max(0, cy0 - pad), min(h, cy0 + comb_h + pad)):
                for lx in range(max(0, cx0 - pad), min(w, cx0 + comb_w + pad)):
                    if occupied_mask_L2[ly][lx] == 1 or occupied_mask_L3[ly][lx] == 1:
                        return False
            return True

        chosen_pos = None
        for _ in range(160):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(max(tw, th) / 2.0 + max(comb_w, comb_h) / 2.0 + 12.0,
                                  max(tw, th) / 2.0 + max(comb_w, comb_h) / 2.0 + 26.0)
            cand_x = int(lobby_cx + math.cos(angle) * dist - comb_w / 2.0)
            cand_y = int(lobby_cy + math.sin(angle) * dist - comb_h / 2.0)
            if is_valid_cave_spot(cand_x, cand_y):
                chosen_pos = (cand_x, cand_y)
                break

        if not chosen_pos:
            for _ in range(200):
                cand_x = random.randint(10, max(10, w - comb_w - 10))
                cand_y = random.randint(10, max(10, h - comb_h - 10))
                if is_valid_cave_spot(cand_x, cand_y):
                    chosen_pos = (cand_x, cand_y)
                    break

        if not chosen_pos:
            return False

        cave_tx, cave_ty = chosen_pos
        forest_tx, forest_ty = cave_tx + forest_rel_x, cave_ty + forest_rel_y

        # 1. Paint small organic island landmass on L1 around the cave & forest footprints
        icx = cave_tx + comb_w / 2.0
        icy = cave_ty + comb_h / 2.0
        rx_grass = comb_w / 2.0 + 3.5
        ry_grass = comb_h / 2.0 + 3.5
        rx_sand = rx_grass + 3.0
        ry_sand = ry_grass + 3.0
        noise_phase = random.uniform(0, 2 * math.pi)

        min_iy = max(2, int(icy - ry_sand - 3))
        max_iy = min(h - 2, int(icy + ry_sand + 4))
        min_ix = max(2, int(icx - rx_sand - 3))
        max_ix = min(w - 2, int(icx + rx_sand + 4))

        island_walkable_tiles = []
        for iy in range(min_iy, max_iy):
            for ix in range(min_ix, max_ix):
                if layers['protected_mask'][iy][ix] == 1:
                    continue
                if boat_coords and (ix, iy) == boat_coords:
                    continue
                if tx <= ix < tx + tw and ty <= iy < ty + th:
                    continue

                dx_n = (ix - icx) / max(1.0, rx_grass)
                dy_n = (iy - icy) / max(1.0, ry_grass)
                ang = math.atan2(dy_n, dx_n)
                wobble = 0.14 * math.sin(ang * 3 + noise_phase) + 0.09 * math.cos(ang * 5 - noise_phase)
                norm_grass = math.hypot(dx_n, dy_n) + wobble

                dx_s = (ix - icx) / max(1.0, rx_sand)
                dy_s = (iy - icy) / max(1.0, ry_sand)
                norm_sand = math.hypot(dx_s, dy_s) + wobble

                if norm_grass <= 1.0:
                    layers['ground'][iy][ix] = 'bg_grass'
                    island_walkable_tiles.append((ix, iy))
                elif norm_sand <= 1.0:
                    if layers['ground'][iy][ix] == water_tile:
                        layers['ground'][iy][ix] = 'beach_sand_01'
                    island_walkable_tiles.append((ix, iy))

        # 2. Stamp Cave and Forest building onto L1, L2, and L3
        self._blit_template(layers, cave_tmpl, cave_tx, cave_ty, w, h, clear_base=True)
        if forest_tmpl:
            self._blit_template(layers, forest_tmpl, forest_tx, forest_ty, w, h, clear_base=True)

        if tmpl_l2:
            self._blit_template_mapped(layers, tmpl_l2, cave_tx, cave_ty, w, h, suffix='_L2')
            l2_w, l2_h = tmpl_l2['width'], tmpl_l2['height']
            if hasattr(self, '_apply_l2_border'):
                self._apply_l2_border(layers, cave_tx, cave_ty, l2_w, l2_h, w, h, suffix='_L2', margin=4)
            for ly in range(max(0, cave_ty - pad), min(h, cave_ty + l2_h + pad)):
                for lx in range(max(0, cave_tx - pad), min(w, cave_tx + l2_w + pad)):
                    occupied_mask_L2[ly][lx] = 1

        if tmpl_l3:
            self._blit_template_mapped(layers, tmpl_l3, cave_tx, cave_ty, w, h, suffix='_L3')
            l3_w, l3_h = tmpl_l3['width'], tmpl_l3['height']
            if hasattr(self, '_apply_l2_border'):
                self._apply_l2_border(layers, cave_tx, cave_ty, l3_w, l3_h, w, h, suffix='_L3', margin=4)
            for ly in range(max(0, cave_ty - pad), min(h, cave_ty + l3_h + pad)):
                for lx in range(max(0, cave_tx - pad), min(w, cave_tx + l3_w + pad)):
                    occupied_mask_L3[ly][lx] = 1

        if forest_l2:
            self._blit_template_mapped(layers, forest_l2, forest_tx, forest_ty, w, h, suffix='_L2')
            fl2_w, fl2_h = forest_l2['width'], forest_l2['height']
            if hasattr(self, '_apply_l2_border'):
                self._apply_l2_border(layers, forest_tx, forest_ty, fl2_w, fl2_h, w, h, suffix='_L2', margin=4)
            for ly in range(max(0, forest_ty - pad), min(h, forest_ty + fl2_h + pad)):
                for lx in range(max(0, forest_tx - pad), min(w, forest_tx + fl2_w + pad)):
                    occupied_mask_L2[ly][lx] = 1

        if forest_l3:
            self._blit_template_mapped(layers, forest_l3, forest_tx, forest_ty, w, h, suffix='_L3')
            fl3_w, fl3_h = forest_l3['width'], forest_l3['height']
            if hasattr(self, '_apply_l2_border'):
                self._apply_l2_border(layers, forest_tx, forest_ty, fl3_w, fl3_h, w, h, suffix='_L3', margin=4)
            for ly in range(max(0, forest_ty - pad), min(h, forest_ty + fl3_h + pad)):
                for lx in range(max(0, forest_tx - pad), min(w, forest_tx + fl3_w + pad)):
                    occupied_mask_L3[ly][lx] = 1

        # 3. Grass and sand decorations strictly outside the 2-tile walkway around the cave and forest
        deco_pool = ['garden_tree_16', 'garden_stone', 'garden_grass_1', 'garden_grass_2']
        sand_deco_pool = ['garden_tree_16', 'garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass', 'garden_stone']
        for (ix, iy) in island_walkable_tiles:
            if layers['protected_mask'][iy][ix] == 1 or layers['base'][iy][ix] != ' ':
                continue
            if (cave_tx - 2 <= ix < cave_tx + cw_t + 2) and (cave_ty - 2 <= iy < cave_ty + ch_t + 2):
                continue
            if forest_tmpl and (forest_tx - 2 <= ix < forest_tx + fw_t + 2) and (forest_ty - 2 <= iy < forest_ty + fh_t + 2):
                continue
            if layers['ground'][iy][ix] == 'bg_grass' and random.random() < 0.08:
                layers['base'][iy][ix] = random.choice(deco_pool)
            elif layers['ground'][iy][ix] == 'beach_sand_01' and random.random() < 0.06:
                layers['base'][iy][ix] = random.choice(sand_deco_pool)

        # 4. Smooth coastal borders around the Cave island (protected_mask preserves Lobby_L1 & cave_tmpl)
        self._apply_sand_smoothing(layers, w, h, 'beach_sand_01')
        self._apply_terrain_smoothing(layers, w, h)
        return True

    def _generate_islet_chunk(self, gx, gy, w, h, conns, assigned_l2_templates=None, assigned_l3_templates=None, conns_l2=None, conns_l3=None):
        water_tile = getattr(self, 'water_tile', 'water_01')
        sand_tile = getattr(self, 'sand_tile', 'beach_sand_01')
        road_tile = 'asphalt_01'
        cx, cy = w // 2, h // 2

        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [[water_tile for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask': [[0 for _ in range(w)] for _ in range(h)],
            'base_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L2': [[0 for _ in range(w)] for _ in range(h)],
            'base_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L3': [[0 for _ in range(w)] for _ in range(h)],
        }
        occupied_mask_L2 = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L3 = [[0 for _ in range(w)] for _ in range(h)]

        # 1. Select Cave (preferring L2 counterpart) and Forest building
        cave_temps = [
            t for t in self.categorized_templates.get('Cave', [])
            if 'l2' not in t.lower() and 'l3' not in t.lower()
        ]
        if not cave_temps:
            cave_temps = list(self.categorized_templates.get('Cave', []))
        cave_with_l2 = [t for t in cave_temps if self._get_l2_counterpart(t, is_forest=False)]
        if cave_with_l2:
            cave_temps = cave_with_l2

        cave_name = random.choice(cave_temps) if cave_temps else None
        cave_tmpl = self.templates.get(cave_name) if cave_name else None
        tmpl_l2 = self.templates.get(self._get_l2_counterpart(cave_name, is_forest=False)) if cave_name else None
        tmpl_l3 = self.templates.get(self._get_l3_counterpart(cave_name, is_forest=False)) if cave_name else None

        forest_name = random.choice(self.forest_templates) if getattr(self, 'forest_templates', None) else None
        forest_tmpl = self.templates.get(forest_name) if forest_name else None
        forest_l2 = self.templates.get(self._get_l2_counterpart(forest_name, is_forest=True)) if forest_name else None
        forest_l3 = self.templates.get(self._get_l3_counterpart(forest_name, is_forest=True)) if forest_name else None

        cw_t = cave_tmpl['width'] if cave_tmpl else 0
        ch_t = cave_tmpl['height'] if cave_tmpl else 0
        fw_t = forest_tmpl['width'] if forest_tmpl else 0
        fh_t = forest_tmpl['height'] if forest_tmpl else 0

        # 2. Protected bridge corridors (4-tile bridge + 1-tile clearance around hub, only when bridged)
        asphalt_bridge_dirs = [
            k for k in ('top', 'bottom', 'left', 'right')
            if conns.get(k) and conns.get(f'{k}_type') in ('asphalt', 'asphalt_bridge')
        ]
        sand_bridge_dirs = [
            k for k in ('top', 'bottom', 'left', 'right')
            if conns.get(k) and conns.get(f'{k}_type') == 'sand_bridge'
        ]
        has_any_bridge = bool(asphalt_bridge_dirs)
        bridge_rects = [pygame.Rect(cx - 3, cy - 3, 6, 6)] if has_any_bridge else []
        if 'top' in asphalt_bridge_dirs:
            bridge_rects.append(pygame.Rect(cx - 3, 0, 6, cy + 3))
        if 'bottom' in asphalt_bridge_dirs:
            bridge_rects.append(pygame.Rect(cx - 3, cy - 3, 6, h - (cy - 3)))
        if 'left' in asphalt_bridge_dirs:
            bridge_rects.append(pygame.Rect(0, cy - 3, cx + 3, 6))
        if 'right' in asphalt_bridge_dirs:
            bridge_rects.append(pygame.Rect(cx - 3, cy - 3, w - (cx - 3), 6))

        def find_spot_near_top(tw, th, extra_rects=None):
            if tw <= 0 or th <= 0:
                return None
            excl = list(bridge_rects) + (extra_rects or [])
            candidates = [
                (cx - tw // 2, cy - 4 - th),
                (cx - 4 - tw, cy - 4 - th),
                (cx + 4, cy - 4 - th),
                (cx - 4 - tw, cy - th // 2),
                (cx + 4, cy - th // 2),
                (cx - 4 - tw, cy + 4),
                (cx + 4, cy + 4),
                (cx - tw // 2, cy + 4),
            ]
            for ox in range(-20, 21, 4):
                for oy in range(-24, 16, 4):
                    candidates.append((cx + ox - tw // 2, cy + oy - th // 2))
            for cand_x, cand_y in candidates:
                if cand_x < 10 or cand_y < 10 or cand_x + tw > w - 10 or cand_y + th > h - 10:
                    continue
                rect = pygame.Rect(cand_x, cand_y, tw, th)
                if not any(rect.colliderect(er) for er in excl):
                    return (cand_x, cand_y)
            return None

        cave_pos = find_spot_near_top(cw_t, ch_t) if cave_tmpl else None
        cave_excl = [pygame.Rect(cave_pos[0] - 2, cave_pos[1] - 2, cw_t + 4, ch_t + 4)] if cave_pos else []
        forest_pos = find_spot_near_top(fw_t, fh_t, extra_rects=cave_excl) if forest_tmpl else None

        # 3. Paint small organic grass + beach sand islet covering hub (if bridged), cave, and forest
        bounds_rects = [pygame.Rect(cx - 3, cy - 3, 6, 6)] if has_any_bridge else []
        if cave_pos:
            bounds_rects.append(pygame.Rect(cave_pos[0], cave_pos[1], cw_t, ch_t))
        if forest_pos:
            bounds_rects.append(pygame.Rect(forest_pos[0], forest_pos[1], fw_t, fh_t))
        if not bounds_rects:
            bounds_rects.append(pygame.Rect(cx - 3, cy - 3, 6, 6))

        min_bx = min(r.left for r in bounds_rects)
        min_by = min(r.top for r in bounds_rects)
        max_bx = max(r.right for r in bounds_rects)
        max_by = max(r.bottom for r in bounds_rects)

        icx = (min_bx + max_bx) / 2.0
        icy = (min_by + max_by) / 2.0
        rx_grass = max(8.0, (max_bx - min_bx) / 2.0 + 3.0)
        ry_grass = max(8.0, (max_by - min_by) / 2.0 + 3.0)
        rx_sand = rx_grass + 3.5
        ry_sand = ry_grass + 3.5
        noise_phase = random.uniform(0, 2 * math.pi)

        min_iy = max(2, int(icy - ry_sand - 4))
        max_iy = min(h - 2, int(icy + ry_sand + 5))
        min_ix = max(2, int(icx - rx_sand - 4))
        max_ix = min(w - 2, int(icx + rx_sand + 5))

        islet_walkable_tiles = []
        for iy in range(min_iy, max_iy):
            for ix in range(min_ix, max_ix):
                dx_n = (ix - icx) / max(1.0, rx_grass)
                dy_n = (iy - icy) / max(1.0, ry_grass)
                ang = math.atan2(dy_n, dx_n)
                wobble = 0.14 * math.sin(ang * 3 + noise_phase) + 0.09 * math.cos(ang * 5 - noise_phase)
                norm_grass = math.hypot(dx_n, dy_n) + wobble

                dx_s = (ix - icx) / max(1.0, rx_sand)
                dy_s = (iy - icy) / max(1.0, ry_sand)
                norm_sand = math.hypot(dx_s, dy_s) + wobble

                if norm_grass <= 1.0:
                    layers['ground'][iy][ix] = 'bg_grass'
                    islet_walkable_tiles.append((ix, iy))
                elif norm_sand <= 1.0:
                    layers['ground'][iy][ix] = sand_tile
                    islet_walkable_tiles.append((ix, iy))

        for br in bounds_rects[1:]:
            for iy in range(max(2, br.top - 1), min(h - 2, br.bottom + 1)):
                for ix in range(max(2, br.left - 1), min(w - 2, br.right + 1)):
                    layers['ground'][iy][ix] = 'bg_grass'
                    if (ix, iy) not in islet_walkable_tiles:
                        islet_walkable_tiles.append((ix, iy))

        # 4. Carve 4-tile-wide asphalt bridges connecting active bridge edges to central hub
        if has_any_bridge:
            for gy_pos in range(cy - 2, cy + 2):
                for gx_pos in range(cx - 2, cx + 2):
                    layers['ground'][gy_pos][gx_pos] = road_tile
                    layers['base'][gy_pos][gx_pos] = ' '

        bridge_tiles = set()
        if 'top' in asphalt_bridge_dirs:
            for gy_pos in range(0, cy + 2):
                for gx_pos in range(cx - 2, cx + 2):
                    layers['ground'][gy_pos][gx_pos] = road_tile
                    layers['base'][gy_pos][gx_pos] = ' '
                    bridge_tiles.add((gx_pos, gy_pos))
        if 'bottom' in asphalt_bridge_dirs:
            for gy_pos in range(cy - 2, h):
                for gx_pos in range(cx - 2, cx + 2):
                    layers['ground'][gy_pos][gx_pos] = road_tile
                    layers['base'][gy_pos][gx_pos] = ' '
                    bridge_tiles.add((gx_pos, gy_pos))
        if 'left' in asphalt_bridge_dirs:
            for gx_pos in range(0, cx + 2):
                for gy_pos in range(cy - 2, cy + 2):
                    layers['ground'][gy_pos][gx_pos] = road_tile
                    layers['base'][gy_pos][gx_pos] = ' '
                    bridge_tiles.add((gx_pos, gy_pos))
        if 'right' in asphalt_bridge_dirs:
            for gx_pos in range(cx - 2, w):
                for gy_pos in range(cy - 2, cy + 2):
                    layers['ground'][gy_pos][gx_pos] = road_tile
                    layers['base'][gy_pos][gx_pos] = ' '
                    bridge_tiles.add((gx_pos, gy_pos))

        # 5. Stamp Cave and Forest building (and their L2/L3 counterparts)
        pad = 4
        if cave_tmpl and cave_pos:
            ctx, cty = cave_pos
            self._blit_template(layers, cave_tmpl, ctx, cty, w, h, clear_base=True)
            if tmpl_l2:
                self._blit_template_mapped(layers, tmpl_l2, ctx, cty, w, h, suffix='_L2')
                if hasattr(self, '_apply_l2_border'):
                    self._apply_l2_border(layers, ctx, cty, tmpl_l2['width'], tmpl_l2['height'], w, h, suffix='_L2', margin=4)
                for ly in range(max(0, cty - pad), min(h, cty + tmpl_l2['height'] + pad)):
                    for lx in range(max(0, ctx - pad), min(w, ctx + tmpl_l2['width'] + pad)):
                        occupied_mask_L2[ly][lx] = 1
            if tmpl_l3:
                self._blit_template_mapped(layers, tmpl_l3, ctx, cty, w, h, suffix='_L3')
                if hasattr(self, '_apply_l2_border'):
                    self._apply_l2_border(layers, ctx, cty, tmpl_l3['width'], tmpl_l3['height'], w, h, suffix='_L3', margin=4)
                for ly in range(max(0, cty - pad), min(h, cty + tmpl_l3['height'] + pad)):
                    for lx in range(max(0, ctx - pad), min(w, ctx + tmpl_l3['width'] + pad)):
                        occupied_mask_L3[ly][lx] = 1

        if forest_tmpl and forest_pos:
            ftx, fty = forest_pos
            self._blit_template(layers, forest_tmpl, ftx, fty, w, h, clear_base=True)
            if forest_l2:
                self._blit_template_mapped(layers, forest_l2, ftx, fty, w, h, suffix='_L2')
                if hasattr(self, '_apply_l2_border'):
                    self._apply_l2_border(layers, ftx, fty, forest_l2['width'], forest_l2['height'], w, h, suffix='_L2', margin=4)
                for ly in range(max(0, fty - pad), min(h, fty + forest_l2['height'] + pad)):
                    for lx in range(max(0, ftx - pad), min(w, ftx + forest_l2['width'] + pad)):
                        occupied_mask_L2[ly][lx] = 1
            if forest_l3:
                self._blit_template_mapped(layers, forest_l3, ftx, fty, w, h, suffix='_L3')
                if hasattr(self, '_apply_l2_border'):
                    self._apply_l2_border(layers, ftx, fty, forest_l3['width'], forest_l3['height'], w, h, suffix='_L3', margin=4)
                for ly in range(max(0, fty - pad), min(h, fty + forest_l3['height'] + pad)):
                    for lx in range(max(0, ftx - pad), min(w, ftx + forest_l3['width'] + pad)):
                        occupied_mask_L3[ly][lx] = 1

        # 6. Scatter grass/sand decorations outside templates and bridges
        grass_decos = ['garden_tree_16', 'garden_stone', 'garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        sand_decos = ['garden_tree_16', 'garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        # 5.5 Generate 4 to 7 extra mini-islets (5 to 8 islets total) connected by drunkard-walk sandbars
        num_extra_islets = random.randint(4, 7)
        main_open_tiles = [
            (ix, iy) for (ix, iy) in islet_walkable_tiles
            if (ix, iy) not in bridge_tiles and layers['protected_mask'][iy][ix] == 0
        ]
        archipelago_islets = [{
            'cx': icx,
            'cy': icy,
            'tiles': main_open_tiles if main_open_tiles else [(int(icx), int(icy))]
        }]
        extra_islet_tiles = []
        sandbar_tiles = set()
        main_excl_dist = max(rx_sand, ry_sand) + 6.0

        for _ in range(num_extra_islets):
            chosen_mini = None
            mr_gx = random.uniform(3.5, 5.5)
            mr_gy = random.uniform(3.5, 5.5)
            mr_sx = mr_gx + 2.5
            mr_sy = mr_gy + 2.5

            for attempt in range(180):
                min_other_dist = 14.5 if attempt < 110 else 11.5
                min_main_dist = main_excl_dist if attempt < 110 else max(rx_sand, ry_sand) + 4.0
                cand_mx = random.randint(12, w - 13)
                cand_my = random.randint(12, h - 13)

                if math.hypot(cand_mx - icx, cand_my - icy) < min_main_dist:
                    continue

                mini_rect = pygame.Rect(
                    int(cand_mx - mr_sx - 1), int(cand_my - mr_sy - 1),
                    int((mr_sx + 1) * 2), int((mr_sy + 1) * 2)
                )
                if any(mini_rect.colliderect(br.inflate(3, 3)) for br in bridge_rects):
                    continue
                if any(math.hypot(cand_mx - isl['cx'], cand_my - isl['cy']) < min_other_dist for isl in archipelago_islets[1:]):
                    continue

                chosen_mini = (cand_mx, cand_my, mr_gx, mr_gy, mr_sx, mr_sy)
                break

            if not chosen_mini:
                continue

            mx, my, m_gx, m_gy, m_sx, m_sy = chosen_mini
            m_phase = random.uniform(0, 2 * math.pi)
            mini_tiles = []

            for iy in range(max(4, int(my - m_sy - 3)), min(h - 4, int(my + m_sy + 4))):
                for ix in range(max(4, int(mx - m_sx - 3)), min(w - 4, int(mx + m_sx + 4))):
                    if (ix, iy) in bridge_tiles or layers['protected_mask'][iy][ix] == 1:
                        continue
                    dx_n = (ix - mx) / max(1.0, m_gx)
                    dy_n = (iy - my) / max(1.0, m_gy)
                    ang = math.atan2(dy_n, dx_n)
                    wob = 0.16 * math.sin(ang * 3 + m_phase) + 0.10 * math.cos(ang * 5 - m_phase)
                    norm_g = math.hypot(dx_n, dy_n) + wob
                    norm_s = math.hypot((ix - mx) / max(1.0, m_sx), (iy - my) / max(1.0, m_sy)) + wob

                    if norm_g <= 1.0:
                        layers['ground'][iy][ix] = 'bg_grass'
                        mini_tiles.append((ix, iy))
                    elif norm_s <= 1.0 and layers['ground'][iy][ix] == water_tile:
                        layers['ground'][iy][ix] = sand_tile
                        mini_tiles.append((ix, iy))

            if not mini_tiles:
                layers['ground'][my][mx] = 'bg_grass'
                mini_tiles.append((mx, my))

            extra_islet_tiles.extend(mini_tiles)

            # Connect to the nearest already-connected islet via Drunkard's Walk sand pathway
            anchor_isl = min(archipelago_islets, key=lambda isl: (isl['cx'] - mx) ** 2 + (isl['cy'] - my) ** 2)
            start_pt = min(anchor_isl['tiles'], key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
            end_pt = min(mini_tiles, key=lambda p: (p[0] - start_pt[0]) ** 2 + (p[1] - start_pt[1]) ** 2)

            self._carve_sand_drunkard_path(
                layers, start_pt, end_pt, bridge_tiles, sand_tile, water_tile, w, h, sandbar_tiles=sandbar_tiles
            )
            archipelago_islets.append({'cx': mx, 'cy': my, 'tiles': mini_tiles})

        # Add 1-2 extra sandbar loops between nearby mini-islets for natural archipelago connectivity
        if len(archipelago_islets) >= 3:
            for _ in range(min(2, len(archipelago_islets) - 2)):
                isl_a = random.choice(archipelago_islets[1:])
                other_isls = [isl for isl in archipelago_islets[1:] if isl is not isl_a]
                isl_b = min(other_isls, key=lambda isl: (isl['cx'] - isl_a['cx']) ** 2 + (isl['cy'] - isl_a['cy']) ** 2)
                s_pt = min(isl_a['tiles'], key=lambda p: (p[0] - isl_b['cx']) ** 2 + (p[1] - isl_b['cy']) ** 2)
                e_pt = min(isl_b['tiles'], key=lambda p: (p[0] - s_pt[0]) ** 2 + (p[1] - s_pt[1]) ** 2)
                self._carve_sand_drunkard_path(
                    layers, s_pt, e_pt, bridge_tiles, sand_tile, water_tile, w, h, sandbar_tiles=sandbar_tiles
                )

        islet_walkable_tiles.extend(extra_islet_tiles)

        # 5.6 Connect the archipelago out to every 'sand_bridge' chunk portal via Drunkard's Walk sandbars
        sand_bridge_targets = []
        for s_dir in sand_bridge_dirs:
            if s_dir == 'top':
                p_tiles = [(tx, ty) for ty in range(0, 4) for tx in range(cx - 2, cx + 2)]
                portal_pt = (cx, 2)
            elif s_dir == 'bottom':
                p_tiles = [(tx, ty) for ty in range(h - 4, h) for tx in range(cx - 2, cx + 2)]
                portal_pt = (cx, h - 3)
            elif s_dir == 'left':
                p_tiles = [(tx, ty) for ty in range(cy - 2, cy + 2) for tx in range(0, 4)]
                portal_pt = (2, cy)
            else:
                p_tiles = [(tx, ty) for ty in range(cy - 2, cy + 2) for tx in range(w - 4, w)]
                portal_pt = (w - 3, cy)

            for px, py in p_tiles:
                if (px, py) not in bridge_tiles and layers['protected_mask'][py][px] == 0:
                    layers['ground'][py][px] = sand_tile
                    layers['base'][py][px] = ' '
                    sandbar_tiles.add((px, py))

            nearest_isl = min(archipelago_islets, key=lambda isl: (isl['cx'] - portal_pt[0]) ** 2 + (isl['cy'] - portal_pt[1]) ** 2)
            start_pt = min(nearest_isl['tiles'], key=lambda p: (p[0] - portal_pt[0]) ** 2 + (p[1] - portal_pt[1]) ** 2)
            self._carve_sand_drunkard_path(
                layers, start_pt, portal_pt, bridge_tiles, sand_tile, water_tile, w, h,
                sandbar_tiles=sandbar_tiles, margin=1, clear_obstacles=True
            )
            sand_bridge_targets.append({'cx': portal_pt[0], 'cy': portal_pt[1], 'tiles': p_tiles})

        walkable_sand_decos = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        for (ix, iy) in islet_walkable_tiles:
            if (ix, iy) in bridge_tiles or layers['protected_mask'][iy][ix] == 1 or layers['base'][iy][ix] != ' ':
                continue
            if cave_pos and (cave_pos[0] - 1 <= ix < cave_pos[0] + cw_t + 1) and (cave_pos[1] - 1 <= iy < cave_pos[1] + ch_t + 1):
                continue
            if forest_pos and (forest_pos[0] - 1 <= ix < forest_pos[0] + fw_t + 1) and (forest_pos[1] - 1 <= iy < forest_pos[1] + fh_t + 1):
                continue
            if (ix, iy) in sandbar_tiles:
                if random.random() < 0.04:
                    layers['base'][iy][ix] = random.choice(walkable_sand_decos)
                continue
            if layers['ground'][iy][ix] == 'bg_grass' and random.random() < 0.10:
                layers['base'][iy][ix] = random.choice(grass_decos)
            elif layers['ground'][iy][ix] == sand_tile and random.random() < 0.06:
                layers['base'][iy][ix] = random.choice(sand_decos)

        # 6.5 Verify 100% walkable connectivity from main islet to every mini-islet and repair any gap
        defs = self.game.tile_manager.definitions if hasattr(self.game, 'tile_manager') else {}

        def _is_walkable_tile(tx, ty):
            g = layers['ground'][ty][tx]
            if g == water_tile or 'water' in str(g).lower():
                return False
            b = layers['base'][ty][tx]
            if b in ('@', '#'):
                return False
            if b != ' ' and defs.get(b, {}).get('is_obstacle', False):
                return False
            return True

        def _bfs_reachable(seeds):
            vis = set()
            q = []
            for sx, sy in seeds:
                if 0 <= sx < w and 0 <= sy < h and _is_walkable_tile(sx, sy) and (sx, sy) not in vis:
                    vis.add((sx, sy))
                    q.append((sx, sy))
            while q:
                qx, qy = q.pop(0)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = qx + dx, qy + dy
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in vis and _is_walkable_tile(nx, ny):
                        vis.add((nx, ny))
                        q.append((nx, ny))
            return vis

        seed_tiles = [p for p in archipelago_islets[0]['tiles'] if _is_walkable_tile(p[0], p[1])]
        if has_any_bridge:
            seed_tiles.append((cx, cy))
        reachable = _bfs_reachable(seed_tiles)

        for isl in archipelago_islets[1:] + sand_bridge_targets:
            if not any(pt in reachable for pt in isl['tiles']):
                if not reachable:
                    break
                t_pt = min(isl['tiles'], key=lambda p: (p[0] - icx) ** 2 + (p[1] - icy) ** 2)
                r_pt = min(reachable, key=lambda p: (p[0] - t_pt[0]) ** 2 + (p[1] - t_pt[1]) ** 2)
                self._carve_sand_drunkard_path(
                    layers, r_pt, t_pt, bridge_tiles, sand_tile, water_tile, w, h,
                    sandbar_tiles=sandbar_tiles, force_direct=True, clear_obstacles=True, margin=1
                )
                reachable = _bfs_reachable(list(reachable))

        # 6.8 Spawn a random maptile_teleport (char="tp_boat") on top of Sand on the islet
        boat_defs = getattr(getattr(self.game, 'tile_manager', None), 'definitions', {})
        boat_char = 'tp_boat' if 'tp_boat' in boat_defs else self._resolve_boat_char()

        def _count_walkable_neighbors(tx, ty):
            cnt = 0
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < w and 0 <= ny < h and _is_walkable_tile(nx, ny):
                    cnt += 1
            return cnt

        def _has_adjacent_water(tx, ty):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = tx + dx, ty + dy
                if 0 <= nx < w and 0 <= ny < h:
                    g = str(layers['ground'][ny][nx]).lower()
                    if layers['ground'][ny][nx] == water_tile or 'water' in g:
                        return True
            return False

        boat_tier1 = []  # Shoreline sand on islet (not sandbar), >=2 walkable exits
        boat_tier2 = []  # Any sand on islet (not sandbar), >=2 walkable exits
        boat_tier3 = []  # Fallback: any reachable sand tile

        for (sx, sy) in reachable:
            if not (4 <= sx < w - 4 and 4 <= sy < h - 4):
                continue
            if (sx, sy) in bridge_tiles or layers['protected_mask'][sy][sx] == 1:
                continue
            if self._is_in_connector_zone_internal(sx, sy, w, h, cx, cy):
                continue
            if layers['base'][sy][sx] != ' ' or layers['spawn'][sy][sx] != ' ':
                continue
            if 'sand' not in str(layers['ground'][sy][sx]).lower():
                continue

            boat_tier3.append((sx, sy))
            if (sx, sy) not in sandbar_tiles and _count_walkable_neighbors(sx, sy) >= 2:
                boat_tier2.append((sx, sy))
                if _has_adjacent_water(sx, sy):
                    boat_tier1.append((sx, sy))

        chosen_boat_pool = boat_tier1 or boat_tier2 or boat_tier3
        if chosen_boat_pool:
            bx, by = random.choice(chosen_boat_pool)
            layers['base'][by][bx] = boat_char
            layers['spawn'][by][bx] = ' '
            layers['protected_mask'][by][bx] = 1

        # 7. Set zombie spawns on walkable islet tiles (excluding edge connector portals)
        z_candidates = []
        for iy in range(6, h - 6):
            for ix in range(6, w - 6):
                g_tile = layers['ground'][iy][ix]
                if g_tile != water_tile and 'water' not in g_tile.lower() and layers['base'][iy][ix] == ' ' and layers['spawn'][iy][ix] == ' ':
                    z_candidates.append((ix, iy))

        z_limit = max(3, getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6))
        if z_candidates and z_limit > 0:
            for (zx, zy) in random.sample(z_candidates, min(z_limit, len(z_candidates))):
                layers['spawn'][zy][zx] = 'Z'

        # 8. Populate L2 and L3 buildings so the player can explore underground
        if assigned_l2_templates:
            for l2_name in assigned_l2_templates:
                if l2_name not in self.templates:
                    continue
                l2_tmpl = self.templates[l2_name]
                l2_w, l2_h = l2_tmpl['width'], l2_tmpl['height']
                for _ in range(40):
                    tx = random.randint(pad, max(pad, w - l2_w - pad))
                    ty = random.randint(pad, max(pad, h - l2_h - pad))
                    collision = any(
                        occupied_mask_L2[ly][lx] == 1
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad))
                        for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad))
                    )
                    if not collision:
                        self._blit_template_mapped(layers, l2_tmpl, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h, suffix='_L2', margin=4)
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1
                        break

        if assigned_l3_templates:
            for l3_name in assigned_l3_templates:
                if l3_name not in self.templates:
                    continue
                l3_tmpl = self.templates[l3_name]
                l3_w, l3_h = l3_tmpl['width'], l3_tmpl['height']
                for _ in range(40):
                    tx = random.randint(pad, max(pad, w - l3_w - pad))
                    ty = random.randint(pad, max(pad, h - l3_h - pad))
                    collision = any(
                        occupied_mask_L3[ly][lx] == 1
                        for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad))
                        for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad))
                    )
                    if not collision:
                        self._blit_template_mapped(layers, l3_tmpl, tx, ty, w, h, suffix='_L3')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l3_w, l3_h, w, h, suffix='_L3', margin=4)
                        for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad)):
                                occupied_mask_L3[ly][lx] = 1
                        break

        if hasattr(self, '_scatter_npcs_l2'):
            self._scatter_npcs_l2(layers, w, h, suffix='_L2')
            self._scatter_npcs_l2(layers, w, h, suffix='_L3')

        return layers

    def _carve_sand_drunkard_path(self, layers, start_pos, end_pos, bridge_tiles, sand_tile, water_tile, w, h, sandbar_tiles=None, force_direct=False, clear_obstacles=False, margin=4, occupied_mask=None):
        cur_x, cur_y = int(start_pos[0]), int(start_pos[1])
        tx, ty = int(end_pos[0]), int(end_pos[1])
        ground = layers['ground']
        base = layers['base']
        protected = layers['protected_mask']
        min_b = max(0, int(margin))
        max_bx = w - min_b
        max_by = h - min_b
        step_min = min_b + 1 if min_b > 0 else 1
        step_maxx = w - step_min - 1
        step_maxy = h - step_min - 1

        wander_budget = 0 if force_direct else ((abs(tx - cur_x) + abs(ty - cur_y)) * 3 + 25)
        hard_cap = wander_budget + abs(tx - cur_x) + abs(ty - cur_y) + 80
        steps = 0

        def stamp_sand(px, py):
            brush = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]
            for dx, dy in brush:
                nx, ny = px + dx, py + dy
                if min_b <= nx < max_bx and min_b <= ny < max_by:
                    if (nx, ny) in bridge_tiles or protected[ny][nx] == 1:
                        continue
                    if ground[ny][nx] == water_tile:
                        ground[ny][nx] = sand_tile
                        if sandbar_tiles is not None:
                            sandbar_tiles.add((nx, ny))
                        if occupied_mask is not None:
                            occupied_mask[ny][nx] = 1
                    elif ground[ny][nx] == sand_tile and sandbar_tiles is not None:
                        sandbar_tiles.add((nx, ny))
                        if occupied_mask is not None:
                            occupied_mask[ny][nx] = 1
                    if clear_obstacles and base[ny][nx] not in (' ', '@', '#'):
                        base[ny][nx] = ' '

        while (cur_x != tx or cur_y != ty) and steps < hard_cap:
            steps += 1
            stamp_sand(cur_x, cur_y)

            dx_goal = tx - cur_x
            dy_goal = ty - cur_y
            if dx_goal == 0 and dy_goal == 0:
                break

            use_greedy = (steps >= wander_budget) or (random.random() < 0.65)
            if use_greedy:
                if abs(dx_goal) >= abs(dy_goal) and dx_goal != 0:
                    step_x = 1 if dx_goal > 0 else -1
                    step_y = 0
                elif dy_goal != 0:
                    step_x = 0
                    step_y = 1 if dy_goal > 0 else -1
                else:
                    step_x = 1 if dx_goal > 0 else -1
                    step_y = 0
            else:
                step_x, step_y = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])

            cand_x = max(step_min, min(step_maxx, cur_x + step_x))
            cand_y = max(step_min, min(step_maxy, cur_y + step_y))

            # Avoid stepping through Cave/Forest protected tiles when an unblocked neighbor exists
            if protected[cand_y][cand_x] == 1:
                alts = []
                for adx, ady in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ax = max(step_min, min(step_maxx, cur_x + adx))
                    ay = max(step_min, min(step_maxy, cur_y + ady))
                    if protected[ay][ax] == 0:
                        alts.append(((tx - ax) ** 2 + (ty - ay) ** 2, ax, ay))
                if alts:
                    alts.sort(key=lambda a: a[0])
                    cand_x, cand_y = alts[0][1], alts[0][2]

            cur_x, cur_y = cand_x, cand_y

        stamp_sand(tx, ty)

    def _world_noise_2d(self, wx, wy, scale, seed_int):
        def _hash2(ix, iy):
            n = (ix * 374761393 + iy * 668265263 + seed_int * 1442695041) & 0xFFFFFFFF
            n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
            return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0

        sx = wx / float(scale)
        sy = wy / float(scale)
        ix = int(math.floor(sx))
        iy = int(math.floor(sy))
        fx = sx - ix
        fy = sy - iy
        u = fx * fx * (3.0 - 2.0 * fx)
        v = fy * fy * (3.0 - 2.0 * fy)

        a = _hash2(ix, iy)
        b = _hash2(ix + 1, iy)
        c = _hash2(ix, iy + 1)
        d = _hash2(ix + 1, iy + 1)
        val = (a * (1.0 - u) + b * u) * (1.0 - v) + (c * (1.0 - u) + d * u) * v
        return (val * 2.0) - 1.0

    def _get_chunk_island_profile(self, cgx, cgy, w, h):
        seed_str = str(getattr(self, '_world_seed_str', getattr(self.game, 'world_seed', 'DEFAULT')))
        rng = random.Random(f"island_{seed_str}_{cgx}_{cgy}")

        is_forest = (cgx, cgy) in getattr(self, 'forest_chunks', set())
        is_mil = (cgx, cgy) == getattr(self, 'military_chunk', None)

        if is_forest:
            ox = rng.uniform(-11.0, 11.0)
            oy = rng.uniform(-11.0, 11.0)
            rx = rng.uniform(30.0, 44.0)
            ry = rng.uniform(26.0, 42.0)
        elif is_mil:
            ox = rng.uniform(-5.0, 5.0)
            oy = rng.uniform(-5.0, 5.0)
            rx = rng.uniform(44.0, 51.0)
            ry = rng.uniform(42.0, 50.0)
        else:
            ox = rng.uniform(-7.0, 7.0)
            oy = rng.uniform(-7.0, 7.0)
            rx = rng.uniform(37.0, 50.0)
            ry = rng.uniform(34.0, 47.0)

        rot = rng.uniform(0.0, math.pi)
        h2_amp = rng.uniform(0.06, 0.16)
        h2_phase = rng.uniform(0.0, 2.0 * math.pi)
        h3_amp = rng.uniform(0.05, 0.14)
        h3_phase = rng.uniform(0.0, 2.0 * math.pi)

        base_wx = cgx * w + (w / 2.0) + ox
        base_wy = cgy * h + (h / 2.0) + oy

        sub_lobes = []
        for _ in range(rng.randint(1, 2)):
            la = rng.uniform(0.0, 2.0 * math.pi)
            ld = rng.uniform(14.0, 24.0)
            lr = rng.uniform(16.0, 25.0) if not is_forest else rng.uniform(14.0, 22.0)
            sub_lobes.append((base_wx + math.cos(la) * ld, base_wy + math.sin(la) * ld, lr))

        return {
            'cx': base_wx,
            'cy': base_wy,
            'rx': rx,
            'ry': ry,
            'cos_r': math.cos(-rot),
            'sin_r': math.sin(-rot),
            'h2_amp': h2_amp,
            'h2_phase': h2_phase,
            'h3_amp': h3_amp,
            'h3_phase': h3_phase,
            'sub_lobes': sub_lobes
        }

    def _compute_world_landmass_grid(self, layers, occupied_mask, gx, gy, w, h, conns,
                                     coast_left, coast_right, coast_top, coast_bottom,
                                     road_tile, sand_tile, water_tile, skip_fn):
        seed_str = str(getattr(self, '_world_seed_str', getattr(self.game, 'world_seed', 'DEFAULT')))
        seed_int = sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed_str)) & 0x7FFFFFFF

        self_prof = self._get_chunk_island_profile(gx, gy, w, h)

        # Gather land-connected continent neighbors (non-bridge L1 links)
        continent_links = []
        dir_checks = [
            ('left', -1, 0, coast_left),
            ('right', 1, 0, coast_right),
            ('top', 0, -1, coast_top),
            ('bottom', 0, 1, coast_bottom)
        ]
        for dkey, dx, dy, is_coast in dir_checks:
            if not is_coast and conns.get(dkey) and conns.get(f"{dkey}_type") != 'asphalt_bridge':
                nx, ny = gx + dx, gy + dy
                n_prof = self._get_chunk_island_profile(nx, ny, w, h)
                continent_links.append(n_prof)

        def _eval_lobe(wx, wy, prof):
            dx = wx - prof['cx']
            dy = wy - prof['cy']
            lx = dx * prof['cos_r'] - dy * prof['sin_r']
            ly = dx * prof['sin_r'] + dy * prof['cos_r']
            ang = math.atan2(ly, lx)
            r_scale = 1.0 + prof['h2_amp'] * math.sin(2.0 * ang + prof['h2_phase']) + prof['h3_amp'] * math.sin(3.0 * ang + prof['h3_phase'])
            dist_norm = math.hypot(lx / (prof['rx'] * r_scale), ly / (prof['ry'] * r_scale))
            best = 1.0 / max(0.25, dist_norm)
            for scx, scy, sr in prof['sub_lobes']:
                d_sub = math.hypot(wx - scx, wy - scy) / sr
                best = max(best, 1.0 / max(0.25, d_sub))
            return best

        def _dist_to_seg(wx, wy, ax, ay, bx, by):
            vx, vy = bx - ax, by - ay
            len_sq = vx * vx + vy * vy
            if len_sq <= 1e-6:
                return math.hypot(wx - ax, wy - ay)
            t = max(0.0, min(1.0, ((wx - ax) * vx + (wy - ay) * vy) / len_sq))
            return math.hypot(wx - (ax + t * vx), wy - (ay + t * vy))

        cap_radius = 30.0
        tree_chance = 0.05
        cx, cy = w // 2, h // 2

        for y in range(h):
            wy = gy * h + y
            d_top = y if coast_top else 999
            d_bottom = (h - 1 - y) if coast_bottom else 999

            for x in range(w):
                if skip_fn(x, y):
                    continue
                if layers['ground'][y][x] == road_tile:
                    continue

                wx = gx * w + x
                field_val = _eval_lobe(wx, wy, self_prof)

                for n_prof in continent_links:
                    field_val = max(field_val, _eval_lobe(wx, wy, n_prof))
                    seg_d = _dist_to_seg(wx, wy, self_prof['cx'], self_prof['cy'], n_prof['cx'], n_prof['cy'])
                    field_val = max(field_val, cap_radius / max(8.0, seg_d))

                # World-space continuous 2D multi-octave noise for organic coves and headlands
                noise_val = (
                    self._world_noise_2d(wx, wy, 18.0, seed_int) * 0.16 +
                    self._world_noise_2d(wx, wy, 8.0, seed_int + 7919) * 0.08
                )
                field_val += noise_val

                # Guarantee central hub stays on grass
                if math.hypot(x - cx, y - cy) <= 10.0:
                    field_val = max(field_val, 1.15)

                # Smooth falloff near coastal chunk borders so individual islands never touch edges as squares
                if skip_fn(x, y):
                    field_val = max(field_val, 1.15)

                # Smooth falloff near coastal chunk borders so individual islands never touch edges as squares
                d_left = x if coast_left else 999
                d_right = (w - 1 - x) if coast_right else 999
                edge_dist = min(d_top, d_bottom, d_left, d_right)
                if edge_dist < 14:
                    t_edge = max(0.0, (edge_dist - 4.0) / 10.0)
                    field_val *= (0.45 + 0.55 * t_edge)

                if field_val >= 1.0:
                    if layers['ground'][y][x] in (' ', ''):
                        layers['ground'][y][x] = 'bg_grass'
                elif field_val >= 0.84:
                    if layers['ground'][y][x] != water_tile:
                        layers['ground'][y][x] = sand_tile
                        layers['base'][y][x] = 'garden_tree_16' if random.random() < tree_chance else ' '
                        occupied_mask[y][x] = 1
                else:
                    layers['ground'][y][x] = water_tile
                    layers['base'][y][x] = ' '
                    occupied_mask[y][x] = 1

    def _place_single_teleport_boat(self, layers, w, h):
        boat_char = self._resolve_boat_char()
        for y in range(h):
            for x in range(w):
                if layers['base'][y][x] in (boat_char, 'tp_boat', 'teleport_boat'):
                    return

        cx, cy = w // 2, h // 2
        for y in range(2, h - 2):
            for x in range(2, w - 2):
                if self._is_in_connector_zone_internal(x, y, w, h, cx, cy):
                    continue
                g_tile = layers['ground'][y][x].lower()
                b_tile = layers['base'][y][x]
                if 'water' in g_tile and b_tile in (' ', ''):
                    layers['base'][y][x] = boat_char
                    layers['spawn'][y][x] = ' '
                    return

    def _place_port_at_shore(self, layers, occupied_mask, placed_rects, w, h, coast_left, coast_right, coast_top, coast_bottom, draw_secondary_maze_road, sandbar_tiles=None):        
        port_name = getattr(self, 'port_template', None)
        if not port_name or port_name not in self.templates:
            for k in ['Port_L1', 'Port_01', 'port_l1', 'port_01', 'Port', 'port']:
                if k in self.templates:
                    port_name = k
                    break
        if not port_name or port_name not in self.templates:
            for k in self.templates.keys():
                if 'port' in k.lower():
                    port_name = k
                    break

        port_tmpl = self.templates.get(port_name) if port_name else None
        if not port_tmpl:
            self._place_single_teleport_boat(layers, w, h)
            return

        pw, ph = port_tmpl['width'], port_tmpl['height']
        cx, cy = w // 2, h // 2

        available_coasts = []
        if coast_bottom: available_coasts.append('bottom')
        if coast_top: available_coasts.append('top')
        if coast_left: available_coasts.append('left')
        if coast_right: available_coasts.append('right')
        if not available_coasts:
            available_coasts = ['bottom', 'top', 'left', 'right']

        random.shuffle(available_coasts)

        best_candidate = None
        best_score = -999999
        chosen_side = available_coasts[0]

        water_tile = getattr(self, 'water_tile', 'water_01')

        def _find_shoreline_spots(side_name):
            spots = []
            if side_name == 'bottom':
                for sx in range(6, w - 6, 2):
                    for sy in range(h - 3, cy + 4, -1):
                        if 'water' not in layers['ground'][sy][sx].lower() and layers['ground'][sy + 1][sx] == water_tile:
                            spots.append((sx - pw // 2, sy - ph // 2))
                            break
            elif side_name == 'top':
                for sx in range(6, w - 6, 2):
                    for sy in range(3, cy - 4):
                        if 'water' not in layers['ground'][sy][sx].lower() and layers['ground'][sy - 1][sx] == water_tile:
                            spots.append((sx - pw // 2, sy - ph // 2))
                            break
            elif side_name == 'left':
                for sy in range(6, h - 6, 2):
                    for sx in range(3, cx - 4):
                        if 'water' not in layers['ground'][sy][sx].lower() and layers['ground'][sy][sx - 1] == water_tile:
                            spots.append((sx - pw // 2, sy - ph // 2))
                            break
            else:
                for sy in range(6, h - 6, 2):
                    for sx in range(w - 3, cx + 4, -1):
                        if 'water' not in layers['ground'][sy][sx].lower() and layers['ground'][sy][sx + 1] == water_tile:
                            spots.append((sx - pw // 2, sy - ph // 2))
                            break
            return spots

        for side in available_coasts:
            shore_spots = _find_shoreline_spots(side)
            random.shuffle(shore_spots)
            if not shore_spots:
                if side == 'bottom':
                    shore_spots = [(random.randint(6, max(7, w - pw - 6)), random.randint(max(2, h - ph - 12), max(2, h - ph - 2))) for _ in range(30)]
                elif side == 'top':
                    shore_spots = [(random.randint(6, max(7, w - pw - 6)), random.randint(2, min(h - ph - 2, 12))) for _ in range(30)]
                elif side == 'left':
                    shore_spots = [(random.randint(2, min(w - pw - 2, 12)), random.randint(6, max(7, h - ph - 6))) for _ in range(30)]
                else:
                    shore_spots = [(random.randint(max(2, w - pw - 12), max(2, w - pw - 2)), random.randint(6, max(7, h - ph - 6))) for _ in range(30)]

            for cand_tx, cand_ty in shore_spots[:50]:
                tx = max(2, min(w - pw - 2, cand_tx))
                ty = max(2, min(h - ph - 2, cand_ty))

                collides_conn = False
                for ry in range(ty, ty + ph):
                    for rx in range(tx, tx + pw):
                        if self._is_in_connector_zone_internal(rx, ry, w, h, cx, cy):
                            collides_conn = True
                            break
                        if str(layers['ground'][ry][rx]).startswith('asphalt'):
                            collides_conn = True
                            break
                    if sandbar_tiles and (rx, ry) in sandbar_tiles:
                            collides_conn = True
                            break
                    if collides_conn: break
                if collides_conn: continue

                p_rect = pygame.Rect(tx, ty, pw, ph)
                if any(p_rect.colliderect(pr) for pr in placed_rects):
                    continue

                water_count = 0
                land_count = 0
                for ry in range(ty, ty + ph):
                    for rx in range(tx, tx + pw):
                        gt = layers['ground'][ry][rx].lower()
                        if 'water' in gt:
                            water_count += 1
                        else:
                            land_count += 1

                score = 0
                if water_count > 0 and land_count > 0:
                    score = 2000 - abs(water_count - land_count)
                elif water_count > 0:
                    score = 100 + water_count
                elif land_count > 0:
                    score = 50 + land_count

                if score > best_score:
                    best_score = score
                    best_candidate = (tx, ty)
                    chosen_side = side

        if not best_candidate:
            tx = max(4, min(w - pw - 4, cx - pw // 2))
            ty = max(4, min(h - ph - 4, h - ph - 6))
            best_candidate = (tx, ty)

        tx, ty = best_candidate
        
        self._blit_template(layers, port_tmpl, tx, ty, w, h, clear_base=True)
        port_rect = pygame.Rect(tx, ty, pw, ph)
        placed_rects.append(port_rect)

        for ry in range(ty, ty + ph):
            for rx in range(tx, tx + pw):
                if 0 <= rx < w and 0 <= ry < h:
                    occupied_mask[ry][rx] = 1
                    layers['protected_mask'][ry][rx] = 1
                    if layers['base'][ry][rx] == '@':
                        layers['base'][ry][rx] = ' '

        boat_char = self._resolve_boat_char()
        has_boat = False
        boat_pos = None
        for ry in range(ty, ty + ph):
            for rx in range(tx, tx + pw):
                if 0 <= rx < w and 0 <= ry < h:
                    b_tile = layers['base'][ry][rx]
                    g_tile = layers['ground'][ry][rx]
                    if b_tile in (boat_char, 'tp_boat', 'teleport_boat') or g_tile in (boat_char, 'tp_boat', 'teleport_boat'):
                        has_boat = True
                        boat_pos = (rx, ry)
                        layers['base'][ry][rx] = boat_char
                        layers['spawn'][ry][rx] = ' '
                        break
            if has_boat: break

        if not has_boat:
            water_tile = getattr(self, 'water_tile', 'water_01')
            for ry in range(max(0, ty - 2), min(h, ty + ph + 2)):
                for rx in range(max(0, tx - 2), min(w, tx + pw + 2)):
                    if layers['ground'][ry][rx] == water_tile and layers['base'][ry][rx] == ' ':
                        layers['base'][ry][rx] = boat_char
                        layers['spawn'][ry][rx] = ' '
                        has_boat = True
                        boat_pos = (rx, ry)
                        break
                if has_boat: break

        sand_tile_type = getattr(self, 'sand_tile', 'beach_sand_01')
        ref_x = boat_pos[0] if boat_pos else (tx + pw // 2)
        ref_y = boat_pos[1] if boat_pos else (ty + ph // 2)

        sand_candidates = []
        for ry in range(max(0, ty - 3), min(h, ty + ph + 3)):
            for rx in range(max(0, tx - 3), min(w, tx + pw + 3)):
                gt = layers['ground'][ry][rx].lower()
                bt = layers['base'][ry][rx]
                if ('sand' in gt or 'beach' in gt) and bt == ' ':
                    d = math.hypot(rx - ref_x, ry - ref_y)
                    sand_candidates.append((d, rx, ry))

        if sand_candidates:
            sand_candidates.sort(key=lambda c: c[0])
            chosen_sand = (sand_candidates[0][1], sand_candidates[0][2])
        else:
            if chosen_side == 'bottom':
                chosen_sand = (tx + pw // 2, max(2, ty - 1))
            elif chosen_side == 'top':
                chosen_sand = (tx + pw // 2, min(h - 3, ty + ph))
            elif chosen_side == 'left':
                chosen_sand = (min(w - 3, tx + pw), ty + ph // 2)
            else:
                chosen_sand = (max(2, tx - 1), ty + ph // 2)
            layers['ground'][chosen_sand[1]][chosen_sand[0]] = sand_tile_type
            layers['base'][chosen_sand[1]][chosen_sand[0]] = ' '

        for y in range(h):
            for x in range(w):
                if layers['spawn'][y][x] in ('P', 'P2'):
                    layers['spawn'][y][x] = ' '

        layers['spawn'][chosen_sand[1]][chosen_sand[0]] = 'P2'

        if chosen_side == 'bottom':
            ent_x = max(2, min(w - 3, tx + pw // 2))
            ent_y = max(2, ty - 1)
        elif chosen_side == 'top':
            ent_x = max(2, min(w - 3, tx + pw // 2))
            ent_y = min(h - 3, ty + ph)
        elif chosen_side == 'left':
            ent_x = min(w - 3, tx + pw)
            ent_y = max(2, min(h - 3, ty + ph // 2))
        else:
            ent_x = max(2, tx - 1)
            ent_y = max(2, min(h - 3, ty + ph // 2))

        draw_secondary_maze_road(ent_x, ent_y, cx, cy, 'dirty_01', path_width=2)

    def _generate_chunk_data(self, gx, gy, conns, is_start=False, assigned_templates=None, assigned_l2_templates=None, assigned_l3_templates=None, allow_buildings=True, force_forest=False, cell_w=None, cell_h=None, coast_left=False, coast_right=False, coast_top=False, coast_bottom=False, conns_l2=None, conns_l3=None):
        w = cell_w if cell_w is not None else 128
        h = cell_h if cell_h is not None else 128

        cx, cy = w // 2, h // 2
        connector_depth = 5
        connector_radius = 3

        def is_in_connector_zone(tx, ty):
            if conns['top'] and ty < connector_depth and (cx - 2 <= tx <= cx + 1):
                return True
            if conns['bottom'] and ty >= h - connector_depth and (cx - 2 <= tx <= cx + 1):
                return True
            if conns['left'] and tx < connector_depth and (cy - 2 <= ty <= cy + 1):
                return True
            if conns['right'] and tx >= w - connector_depth and (cy - 2 <= ty <= cy + 1):
                return True
            return False

        def is_in_non_bridge_connector_zone(tx, ty):
            if conns['top'] and conns.get('top_type') not in ('asphalt_bridge', 'sand_bridge') and ty < connector_depth and (cx - 2 <= tx <= cx + 1):
                return True
            if conns['bottom'] and conns.get('bottom_type') not in ('asphalt_bridge', 'sand_bridge') and ty >= h - connector_depth and (cx - 2 <= tx <= cx + 1):
                return True
            if conns['left'] and conns.get('left_type') not in ('asphalt_bridge', 'sand_bridge') and tx < connector_depth and (cy - 2 <= ty <= cy + 1):
                return True
            if conns['right'] and conns.get('right_type') not in ('asphalt_bridge', 'sand_bridge') and tx >= w - connector_depth and (cy - 2 <= ty <= cy + 1):
                return True
            return False

        layers = {
            'base': [[' ' for _ in range(w)] for _ in range(h)],
            'ground': [['bg_grass' for _ in range(w)] for _ in range(h)],
            'spawn': [[' ' for _ in range(w)] for _ in range(h)],
            'roof': [[' ' for _ in range(w)] for _ in range(h)],
            'light': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask': [[0 for _ in range(w)] for _ in range(h)],
            
            # L2 Layers
            'base_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L2': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L2': [[0 for _ in range(w)] for _ in range(h)],

            # L3 Layers (Same architecture as L2)
            'base_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'ground_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'spawn_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'roof_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'light_L3': [[' ' for _ in range(w)] for _ in range(h)],
            'protected_mask_L3': [[0 for _ in range(w)] for _ in range(h)],
        }
        occupied_mask = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L2 = [[0 for _ in range(w)] for _ in range(h)]
        occupied_mask_L3 = [[0 for _ in range(w)] for _ in range(h)]

        placed_rects = []
        road_tile = 'asphalt_01'
        dirt_tile = 'dirty_01'
        sand_tile = getattr(self, 'sand_tile', 'sand_01')

        def carve_straight_segment(x1, y1, x2, y2, tile_type, path_width=4):
            if path_width >= 4:
                r_min, r_max = -2, 2
            elif path_width == 3:
                r_min, r_max = -1, 2
            elif path_width == 2:
                r_min, r_max = -1, 1
            else:
                r_min, r_max = 0, 1

            cur_x, cur_y = x1, y1
            pts = [(cur_x, cur_y)]
            while cur_x != x2 or cur_y != y2:
                if cur_x < x2: cur_x += 1
                elif cur_x > x2: cur_x -= 1
                if cur_y < y2: cur_y += 1
                elif cur_y > y2: cur_y -= 1
                pts.append((cur_x, cur_y))

            for px, py in pts:
                for oy in range(r_min, r_max):
                    for ox in range(r_min, r_max):
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            layers['ground'][gy_pos][gx_pos] = tile_type
                            layers['base'][gy_pos][gx_pos] = ' '
                            occupied_mask[gy_pos][gx_pos] = 1

        def draw_secondary_maze_road(start_x, start_y, target_x, target_y, tile_type=dirt_tile, path_width=None):
            if path_width is None:
                path_width = 4 if tile_type == road_tile else 2
                
            current_x, current_y = start_x, start_y
            path = [(current_x, current_y)]
            
            if tile_type == road_tile:
                while current_x != target_x:
                    current_x += 1 if target_x > current_x else -1
                    if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                        break
                    path.append((current_x, current_y))
                
                if not any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                    while current_y != target_y:
                        current_y += 1 if target_y > current_y else -1
                        if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                            break
                        path.append((current_x, current_y))
            else:
                steps = 0
                max_steps = w * 6
                while steps < max_steps:
                    steps += 1
                    if not (0 <= current_x < w and 0 <= current_y < h): break
                    if any(pr.collidepoint(current_x, current_y) for pr in placed_rects):
                        break
                    if layers['ground'][current_y][current_x] == tile_type and steps > 5: break 
                    if layers['ground'][current_y][current_x] == getattr(self, 'water_tile', 'water_01'): break 

                    if math.hypot(target_x - current_x, target_y - current_y) < 2: break

                    moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    valid_moves = []
                    for dx, dy in moves:
                        nx, ny = current_x + dx, current_y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            if layers['base'][ny][nx] == ' ' and layers['ground'][ny][nx] != getattr(self, 'water_tile', 'water_01'):
                                valid_moves.append((dx, dy))
                    
                    if not valid_moves: break 
                    
                    scored_moves = []
                    for dx, dy in valid_moves:
                        nx, ny = current_x + dx, current_y + dy
                        dist = math.hypot(target_x - nx, target_y - ny)
                        noise = random.uniform(-10.0, 10.0) 
                        score = dist + noise
                        scored_moves.append((score, dx, dy))
                    
                    scored_moves.sort(key=lambda x: x[0])
                    _, best_dx, best_dy = scored_moves[0]
                    current_x += best_dx; current_y += best_dy
                    path.append((current_x, current_y))

            for px, py in path:
                if path_width >= 4:
                    r_min, r_max = -2, 2
                elif path_width == 3:
                    r_min, r_max = -1, 2
                elif path_width == 2:
                    r_min, r_max = -1, 1
                else:
                    r_min, r_max = 0, 1

                for oy in range(r_min, r_max):
                    for ox in range(r_min, r_max):
                        gx_pos, gy_pos = px + ox, py + oy
                        if 0 <= gx_pos < w and 0 <= gy_pos < h:
                            if any(pr.collidepoint(gx_pos, gy_pos) for pr in placed_rects):
                                continue
                            if layers.get('protected_mask') and layers['protected_mask'][gy_pos][gx_pos] == 1:
                                continue
                            if layers['base'][gy_pos][gx_pos] == ' ' and layers['ground'][gy_pos][gx_pos] != road_tile:
                                if layers['ground'][gy_pos][gx_pos] != getattr(self, 'water_tile', 'water_01'):
                                    layers['ground'][gy_pos][gx_pos] = tile_type
                                    occupied_mask[gy_pos][gx_pos] = 1

        # 1. Central Hub
        hub_tile = road_tile if not force_forest else dirt_tile
        for y in range(cy-2, cy+3):
            for x in range(cx-2, cx+3):
                layers['ground'][y][x] = hub_tile
                occupied_mask[y][x] = 1

        # 2. Connections with Guaranteed Straight Padding
        lead_in = 4
        if conns['top'] and conns.get('top_type') != 'sand_bridge':
            conn_type = road_tile if conns['top_type'] in ('asphalt', 'asphalt_bridge') else (sand_tile if conns['top_type'] == 'sand' else dirt_tile)
            carve_straight_segment(cx, 0, cx, lead_in, conn_type)
            draw_secondary_maze_road(cx, lead_in, cx, cy, conn_type)
            
        if conns['bottom'] and conns.get('bottom_type') != 'sand_bridge':
            conn_type = road_tile if conns['bottom_type'] in ('asphalt', 'asphalt_bridge') else (sand_tile if conns['bottom_type'] == 'sand' else dirt_tile)
            carve_straight_segment(cx, h - 1, cx, h - 1 - lead_in, conn_type)
            draw_secondary_maze_road(cx, h - 1 - lead_in, cx, cy, conn_type)
            
        if conns['left'] and conns.get('left_type') != 'sand_bridge':
            conn_type = road_tile if conns['left_type'] in ('asphalt', 'asphalt_bridge') else (sand_tile if conns['left_type'] == 'sand' else dirt_tile)
            carve_straight_segment(0, cy, lead_in, cy, conn_type)
            draw_secondary_maze_road(lead_in, cy, cx, cy, conn_type)
            
        if conns['right'] and conns.get('right_type') != 'sand_bridge':
            conn_type = road_tile if conns['right_type'] in ('asphalt', 'asphalt_bridge') else (sand_tile if conns['right_type'] == 'sand' else dirt_tile)
            carve_straight_segment(w - 1, cy, w - 1 - lead_in, cy, conn_type)
            draw_secondary_maze_road(w - 1 - lead_in, cy, cx, cy, conn_type)

        # 4. World-Space Organic Island & Continent Landmass Generation
        water_tile_name = getattr(self, 'water_tile', 'water_01')
        beach_sand_tile = getattr(self, 'sand_tile', 'beach_sand_01')

        if not (getattr(self, 'lobby_chunk', None) == (gx, gy) or (gx, gy) in getattr(self, 'islet_chunks', set())):
            self._compute_world_landmass_grid(
                layers, occupied_mask, gx, gy, w, h, conns,
                coast_left, coast_right, coast_top, coast_bottom,
                road_tile, beach_sand_tile, water_tile_name, is_in_non_bridge_connector_zone
            )

        if getattr(self, 'lobby_chunk', None) and (gx, gy) == self.lobby_chunk:
            return self._generate_lobby_chunk(
                gx, gy, w, h,
                assigned_l2_templates=assigned_l2_templates,
                assigned_l3_templates=assigned_l3_templates,
                conns_l2=conns_l2,
                conns_l3=conns_l3
            )

        if (gx, gy) in getattr(self, 'islet_chunks', set()):
            return self._generate_islet_chunk(
                gx, gy, w, h, conns,
                assigned_l2_templates=assigned_l2_templates,
                assigned_l3_templates=assigned_l3_templates,
                conns_l2=conns_l2,
                conns_l3=conns_l3
            )

        # 4.2 Carve drunkard sandbars connecting continent/island shores to any 'sand_bridge' chunk boundary
        sandbar_tiles = set()
        sand_bridge_dirs = [
            dkey for dkey in ('top', 'bottom', 'left', 'right')
            if conns.get(dkey) and conns.get(f'{dkey}_type') == 'sand_bridge'
        ]
        if sand_bridge_dirs:
            land_pool = [
                (lx, ly) for ly in range(6, h - 6) for lx in range(6, w - 6)
                if layers['ground'][ly][lx] in ('bg_grass', beach_sand_tile, dirt_tile, road_tile)
                and layers['protected_mask'][ly][lx] == 0
                and layers['base'][ly][lx] == ' '
            ]
            for dkey in sand_bridge_dirs:
                if dkey == 'top':
                    p_tiles = [(tx, ty) for ty in range(0, 4) for tx in range(cx - 2, cx + 2)]
                    portal_pt = (cx, 2)
                elif dkey == 'bottom':
                    p_tiles = [(tx, ty) for ty in range(h - 4, h) for tx in range(cx - 2, cx + 2)]
                    portal_pt = (cx, h - 3)
                elif dkey == 'left':
                    p_tiles = [(tx, ty) for ty in range(cy - 2, cy + 2) for tx in range(0, 4)]
                    portal_pt = (2, cy)
                else:
                    p_tiles = [(tx, ty) for ty in range(cy - 2, cy + 2) for tx in range(w - 4, w)]
                    portal_pt = (w - 3, cy)

                for px, py in p_tiles:
                    layers['ground'][py][px] = beach_sand_tile
                    layers['base'][py][px] = ' '
                    occupied_mask[py][px] = 1
                    sandbar_tiles.add((px, py))

                if land_pool:
                    anchor_pt = min(land_pool, key=lambda p: (p[0] - portal_pt[0]) ** 2 + (p[1] - portal_pt[1]) ** 2)
                else:
                    anchor_pt = (cx, cy)

                self._carve_sand_drunkard_path(
                    layers, anchor_pt, portal_pt, bridge_tiles=set(), sand_tile=beach_sand_tile,
                    water_tile=water_tile_name, w=w, h=h, sandbar_tiles=sandbar_tiles,
                    margin=1, clear_obstacles=True, occupied_mask=occupied_mask
                )
                draw_secondary_maze_road(anchor_pt[0], anchor_pt[1], cx, cy, dirt_tile, path_width=2)

        # 4.5 Place Port_L1 at the shore of all non-military chunks BEFORE buildings and walls
        is_military = (getattr(self, 'military_chunk', None) == (gx, gy))
        if not is_military:
            self._place_port_at_shore(
                layers, occupied_mask, placed_rects, w, h,
                coast_left, coast_right, coast_top, coast_bottom,
                draw_secondary_maze_road, sandbar_tiles=sandbar_tiles
            )
        # 5. Organic Trade Routes for Urban Chunks
        if allow_buildings and not force_forest:
            num_routes = 4
            safe_margin = getattr(self, 'coast_width', 15) + 3 
            for _ in range(num_routes):
                rx1 = random.randint(safe_margin, max(safe_margin + 1, w - safe_margin))
                ry1 = random.randint(safe_margin, max(safe_margin + 1, h - safe_margin))
                rx2 = random.randint(safe_margin, max(safe_margin + 1, w - safe_margin))
                ry2 = random.randint(safe_margin, max(safe_margin + 1, h - safe_margin))
                draw_secondary_maze_road(rx1, ry1, rx2, ry2, tile_type=dirt_tile)

        get_l2_counterpart = self._get_l2_counterpart
        get_l3_counterpart = self._get_l3_counterpart

        # 6. Place Buildings (TETRIS METHOD)
        def get_tetris_candidates(tw, th, gap=1):
            candidates = []
            if not placed_rects:
                candidates.extend([
                    (cx + 3, cy + 3),
                    (cx - tw - 3, cy - th - 3),
                    (cx + 3, cy - th - 3),
                    (cx - tw - 3, cy + 3)
                ])
                return candidates
            
            for pr in placed_rects:
                candidates.extend([
                    (pr.x + pr.width + gap, pr.y),
                    (pr.x + pr.width + gap, pr.y + pr.height - th),
                    (pr.x + pr.width + gap, pr.y + (pr.height - th) // 2),
                    (pr.x - tw - gap, pr.y), 
                    (pr.x - tw - gap, pr.y + pr.height - th), 
                    (pr.x - tw - gap, pr.y + (pr.height - th) // 2),
                    (pr.x, pr.y + pr.height + gap), 
                    (pr.x + pr.width - tw, pr.y + pr.height + gap),
                    (pr.x + (pr.width - tw) // 2, pr.y + pr.height + gap),
                    (pr.x, pr.y - th - gap), 
                    (pr.x + pr.width - tw, pr.y - th - gap),
                    (pr.x + (pr.width - tw) // 2, pr.y - th - gap)
                ])
                    
            candidates.sort(key=lambda c: (c[0] + tw/2.0 - cx)**2 + (c[1] + th/2.0 - cy)**2)
            
            seen = set()
            unique_candidates = []
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    unique_candidates.append(c)
            return unique_candidates

        def is_area_free(tx, ty, tw, th, gap=1, ignore_mask=False, is_center_override=False):
            if tx < 2 or tx + tw > w - 2 or ty < 2 or ty + th > h - 2: return False
            
            t_rect = pygame.Rect(tx, ty, tw, th)
            
            for ry in range(ty, ty + th):
                for rx in range(tx, tx + tw):
                    if is_in_connector_zone(rx, ry):
                        return False
            
            if not is_center_override:
                hub_rect = pygame.Rect(cx-2, cy-2, 5, 5)
                if t_rect.colliderect(hub_rect): return False
            
            for pr in placed_rects:
                if t_rect.inflate(gap*2, gap*2).colliderect(pr): 
                    return False
                    
            if not ignore_mask:
                for ry in range(ty, ty+th):
                    for rx in range(tx, tx+tw):
                        if layers.get('protected_mask') and layers['protected_mask'][ry][rx] == 1:
                            return False
                        ground_tile = layers['ground'][ry][rx]
                        if ground_tile == getattr(self, 'water_tile', 'water_01'): return False
                        if layers['base'][ry][rx] == '@': return False
                        if occupied_mask[ry][rx] == 1: 
                            return False
            return True

        petrol_pos = None

        if allow_buildings and assigned_templates:
            sorted_templates = []
            for t_name in assigned_templates:
                if hasattr(self, 'templates') and t_name in self.templates:
                    t = self.templates[t_name]
                    area = t['width'] * t['height']
                    sorted_templates.append((area, t_name))
            sorted_templates.sort(key=lambda x: x[0], reverse=True)
            ordered_names = [x[1] for x in sorted_templates]

            for tmpl_name in ordered_names:
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']
                is_building2 = "building2" in tmpl_name.lower()
                is_cave = 'cave' in tmpl_name.lower()
                is_military_base = "military" in tmpl_name.lower() or "heli" in tmpl_name.lower()

                found_l2_key = get_l2_counterpart(tmpl_name, is_forest=False)
                tmpl_l2 = self.templates.get(found_l2_key) if found_l2_key else None
                found_l3_key = get_l3_counterpart(tmpl_name, is_forest=False)
                tmpl_l3 = self.templates.get(found_l3_key) if found_l3_key else None

                fit_w = max(tw, tmpl_l2['width'] if tmpl_l2 else tw, tmpl_l3['width'] if tmpl_l3 else tw)
                fit_h = max(th, tmpl_l2['height'] if tmpl_l2 else th, tmpl_l3['height'] if tmpl_l3 else th)

                placed = False
                
                if is_military_base:
                    tx = max(4, min(cx - (fit_w // 2), w - fit_w - 4))
                    ty = max(4, min(cy - (fit_h // 2), h - fit_h - 4))
                    if is_area_free(tx, ty, fit_w, fit_h, gap=1, ignore_mask=True, is_center_override=True):
                        self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, False, sand_tile, draw_secondary_maze_road)
                        placed = True

                if not placed and not is_cave:
                    # Tight packing: test gap=1 first for maximum urban building density
                    for g in [1, 2]:
                        candidates = get_tetris_candidates(fit_w, fit_h, gap=g)
                        for tx, ty in candidates:
                            if is_area_free(tx, ty, fit_w, fit_h, gap=g):
                                self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                                placed = True
                                break
                        if placed:
                            break

                if not placed:
                    for _ in range(120): 
                        tx = random.randint(4, max(4, w - fit_w - 4))
                        ty = random.randint(4, max(4, h - fit_h - 4))
                        if is_area_free(tx, ty, fit_w, fit_h, gap=1):
                            self._finalize_placement(layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road)
                            placed = True
                            break
                
                if placed:
                    if 'petrol' in tmpl_name.lower() or 'gas' in tmpl_name.lower():
                        petrol_pos = (tx + tw // 2, ty + th // 2)

                    if tmpl_l2:
                        self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                        l2_w, l2_h = tmpl_l2['width'], tmpl_l2['height']
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h, suffix='_L2', margin=4)
                        pad = 4
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1

                    if tmpl_l3:
                        self._blit_template_mapped(layers, tmpl_l3, tx, ty, w, h, suffix='_L3')
                        l3_w, l3_h = tmpl_l3['width'], tmpl_l3['height']
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l3_w, l3_h, w, h, suffix='_L3', margin=4)
                        pad = 4
                        for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad)):
                                occupied_mask_L3[ly][lx] = 1

        # 7. Forest Areas & Nature Placement
        # 7. Forest Areas & Nature Placement
        if force_forest:
            self._generate_confusing_asphalt_maze(layers, occupied_mask, w, h, cx, cy, placed_rects=placed_rects)

        # Densely place Forest_ templates in forest chunks (and near Petrol_)
        if hasattr(self, 'forest_templates') and self.forest_templates:
            # Much denser allocation for forest chunks: 25-40 patches, clustering near Petrol
            num_forest_patches = random.randint(25, 40) if force_forest else max(4, min(14, (w * h) // 400))
            for _ in range(num_forest_patches):
                tmpl_name = random.choice(self.forest_templates)
                tmpl = self.templates[tmpl_name]
                tw, th = tmpl['width'], tmpl['height']

                placed_patch = False
                for _ in range(30):
                    # If Petrol is present, 60% chance to place Forest_ directly in its vicinity (radius 10-25 tiles)
                    if petrol_pos and random.random() < 0.60:
                        angle = random.uniform(0, 2 * math.pi)
                        dist = random.uniform(8, 24)
                        tx = int(petrol_pos[0] + dist * math.cos(angle) - tw // 2)
                        ty = int(petrol_pos[1] + dist * math.sin(angle) - th // 2)
                    else:
                        tx = random.randint(2, max(3, w - tw - 2))
                        ty = random.randint(2, max(3, h - th - 2))

                    if is_area_free(tx, ty, tw, th, gap=1):
                        self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)

                        found_l2_key = get_l2_counterpart(tmpl_name, is_forest=True)
                        if found_l2_key:
                            tmpl_l2 = self.templates[found_l2_key]
                            self._blit_template_mapped(layers, tmpl_l2, tx, ty, w, h, suffix='_L2')
                            l2_w, l2_h = tmpl_l2.get('width', 10), tmpl_l2.get('height', 10)
                            if hasattr(self, '_apply_l2_border'):
                                self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h, suffix='_L2', margin=4)
                            pad = 4
                            for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                                for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                    occupied_mask_L2[ly][lx] = 1

                        found_l3_key = get_l3_counterpart(tmpl_name, is_forest=True)
                        if found_l3_key:
                            tmpl_l3 = self.templates[found_l3_key]
                            self._blit_template_mapped(layers, tmpl_l3, tx, ty, w, h, suffix='_L3')
                            l3_w, l3_h = tmpl_l3.get('width', 10), tmpl_l3.get('height', 10)
                            if hasattr(self, '_apply_l2_border'):
                                self._apply_l2_border(layers, tx, ty, l3_w, l3_h, w, h, suffix='_L3', margin=4)
                            pad = 4
                            for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad)):
                                for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad)):
                                    occupied_mask_L3[ly][lx] = 1

                        placed_rects.append(pygame.Rect(tx, ty, tw, th))
                        for ry in range(ty, ty + th):
                            for rx in range(tx, tx + tw):
                                occupied_mask[ry][rx] = 1
                        placed_patch = True
                        break

        # 8. Ground Formatting
        if force_forest:
            for y in range(h):
                for x in range(w):
                    # Never overwrite protected building templates or existing floors
                    if layers.get('protected_mask') and layers['protected_mask'][y][x] == 1:
                        continue
                    ground_tile = layers['ground'][y][x]
                    if ground_tile in ('house_floor_01', road_tile, sand_tile, dirt_tile, getattr(self, 'water_tile', 'water_01')) or 'floor' in ground_tile:
                        continue
                    layers['ground'][y][x] = 'bg_grass'

        # Border enforcement on Layer 1: '@' walls on top of sand, only on land
        sand_border_tile = getattr(self, 'sand_tile', 'beach_sand_01')
        water_tile_name = getattr(self, 'water_tile', 'water_01')

        def apply_border_wall(bx, by, is_horizontal):
            # Check if this perimeter tile is part of an active connection corridor
            is_connection_open = False
            if is_horizontal:
                if (by == 0 and conns['top']) or (by == h - 1 and conns['bottom']):
                    if cx - 2 <= bx <= cx + 1:
                        is_connection_open = True
            else:
                if (bx == 0 and conns['left']) or (bx == w - 1 and conns['right']):
                    if cy - 2 <= by <= cy + 1:
                        is_connection_open = True

            # If it is the active connection corridor, keep passage open for road
            if is_connection_open or is_in_connector_zone(bx, by):
                layers['base'][by][bx] = ' '
                return

            # Keep templates/structures protected (e.g. port docks)
            if layers.get('protected_mask') and layers['protected_mask'][by][bx] == 1:
                return
            if any(pr.collidepoint(bx, by) for pr in placed_rects):
                return

            ground_char = layers['ground'][by][bx]

            # "Only place the border if the chunk is land" -> If water, do not place '@'
            if ground_char == water_tile_name or 'water' in str(ground_char).lower():
                layers['base'][by][bx] = ' '
                return

            if layers['ground'][by][bx] in (' ', ''):
                layers['ground'][by][bx] = sand_border_tile
            layers['base'][by][bx] = '@'
            occupied_mask[by][bx] = 1

        for x in range(w):
            apply_border_wall(x, 0, True)
            apply_border_wall(x, h - 1, True)

        for y in range(h):
            apply_border_wall(0, y, False)
            apply_border_wall(w - 1, y, False)

        # 9. Spawns
        if hasattr(self, '_scatter_zombies'):
            self._scatter_zombies(layers, occupied_mask, w, h)
        if hasattr(self, '_scatter_npcs'):
            self._scatter_npcs(layers, occupied_mask, w, h)

        # --- 9.5. CONNECT CAVE_L2_02 TO CAVE_L3_02 ON EVERY CHUNK (INCLUDING MILITARY) ---
        self._place_default_cave_pair(layers, occupied_mask_L2, occupied_mask_L3, w, h)

        # 10. Assigned L2 Spawning (Dungeons and Bunkers with 2-tile margin)
        if assigned_l2_templates:
            for l2_name in assigned_l2_templates:
                l2_tmpl = self.templates[l2_name]
                l2_w, l2_h = l2_tmpl['width'], l2_tmpl['height']
                
                placed_l2 = False
                pad = 4  # 2-tile margin
                for _ in range(40): 
                    tx = random.randint(pad, max(pad, w - l2_w - pad))
                    ty = random.randint(pad, max(pad, h - l2_h - pad))
                    
                    collision = False
                    for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                        for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                            if occupied_mask_L2[ly][lx] == 1:
                                collision = True
                                break
                        if collision: break
                    
                    if not collision:
                        self._blit_template_mapped(layers, l2_tmpl, tx, ty, w, h, suffix='_L2')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l2_w, l2_h, w, h, suffix='_L2', margin=4)
                            
                        for ly in range(max(0, ty - pad), min(h, ty + l2_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l2_w + pad)):
                                occupied_mask_L2[ly][lx] = 1
                        placed_l2 = True
                        break

        # 10.5. Assigned L3 Spawning (Dungeons and Bunkers with 2-tile margin)
        if assigned_l3_templates:
            for l3_name in assigned_l3_templates:
                l3_tmpl = self.templates[l3_name]
                l3_w, l3_h = l3_tmpl['width'], l3_tmpl['height']
                
                placed_l3 = False
                pad = 4  # 2-tile margin
                for _ in range(40): 
                    tx = random.randint(pad, max(pad, w - l3_w - pad))
                    ty = random.randint(pad, max(pad, h - l3_h - pad))
                    
                    collision = False
                    for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad)):
                        for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad)):
                            if occupied_mask_L3[ly][lx] == 1:
                                collision = True
                                break
                        if collision: break
                    
                    if not collision:
                        self._blit_template_mapped(layers, l3_tmpl, tx, ty, w, h, suffix='_L3')
                        if hasattr(self, '_apply_l2_border'):
                            self._apply_l2_border(layers, tx, ty, l3_w, l3_h, w, h, suffix='_L3', margin=4)
                            
                        for ly in range(max(0, ty - pad), min(h, ty + l3_h + pad)):
                            for lx in range(max(0, tx - pad), min(w, tx + l3_w + pad)):
                                occupied_mask_L3[ly][lx] = 1
                        placed_l3 = True
                        break
        
        if hasattr(self, '_scatter_npcs_l2'):
            self._scatter_npcs_l2(layers, w, h, suffix='_L2')
            self._scatter_npcs_l2(layers, w, h, suffix='_L3')

        # 11. Scatter Decorations & Vegetation
        building_mask = [[False for _ in range(w)] for _ in range(h)]
        for pr in placed_rects:
            for ry in range(max(0, pr.y - 1), min(h, pr.y + pr.height + 1)):
                for rx in range(max(0, pr.x - 1), min(w, pr.x + pr.width + 1)):
                    building_mask[ry][rx] = True

        dirty_decos = ['garden_stone', 'garden_stone_iron', 'garden_stone_powder', 'garden_grass_1' , 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        wall_decos = ['garden_tree_6', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3']
        sand_decos = ['garden_grass_1', 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']
        asphalt_decos = ['garden_stone', 'garden_dirty_1', 'garden_dirty_2', 'garden_dirty_3', 'garden_grass_1' , 'garden_grass_2', 'garden_grass_3', 'garden_tall_grass']

        path_tiles = set()
        for y in range(h):
            for x in range(w):
                gt = layers['ground'][y][x]
                if 'asphalt' in gt or 'dirty' in gt:
                    path_tiles.add((x, y))

        for y in range(h):
            for x in range(w):
                if is_in_connector_zone(x, y):
                    layers['base'][y][x] = ' '
                    continue

                if not building_mask[y][x] and layers['base'][y][x] == ' ':
                    ground_tile = layers['ground'][y][x]
                    
                    if 'water' in ground_tile or 'beach_sand' in ground_tile:
                        continue
                        
                    if 'sand_' in ground_tile:
                        if random.random() < 0.05:
                            layers['base'][y][x] = random.choice(sand_decos)
                        continue

                    if (x, y) in path_tiles:
                        if 'dirty' in ground_tile and random.random() < 0.05:
                            layers['base'][y][x] = random.choice(dirty_decos)
                        elif 'asphalt' in ground_tile and random.random() < 0.05:
                            near_coast = any(
                                0 <= y + dy < h and 0 <= x + dx < w and (
                                    'water' in layers['ground'][y + dy][x + dx] or
                                    'beach_sand' in layers['ground'][y + dy][x + dx]
                                )
                                for dy in range(-2, 3) for dx in range(-2, 3)
                            )
                            if not near_coast:
                                layers['base'][y][x] = random.choice(asphalt_decos)
                    else:
                        dist_to_path = 999
                        for dy in range(-2, 3):
                            for dx in range(-2, 3):
                                if (x+dx, y+dy) in path_tiles:
                                    d = max(abs(dx), abs(dy))
                                    if d < dist_to_path:
                                        dist_to_path = d
                        
                        if dist_to_path == 1:
                            if random.random() < 0.6:
                                layers['base'][y][x] = random.choice(dirty_decos)
                        elif dist_to_path >= 2:
                            if random.random() < 0.90:
                                layers['base'][y][x] = random.choice(wall_decos)

        return layers

    def _finalize_placement(self, layers, occupied_mask, placed_rects, tmpl, tmpl_name, tx, ty, tw, th, cx, cy, w, h, is_building2, sand_tile, draw_secondary_maze_road):
        is_cave = 'cave' in tmpl_name.lower()
        road_tile = 'asphalt_01'
        b_rect = pygame.Rect(tx, ty, tw, th)

        # 1. Blit the building template first so its ground and base take priority
        self._blit_template(layers, tmpl, tx, ty, w, h, clear_base=True)
        placed_rects.append(b_rect)
        for ry in range(ty, ty + th):
            for rx in range(tx, tx + tw):
                occupied_mask[ry][rx] = 1
                if 'protected_mask' in layers:
                    layers['protected_mask'][ry][rx] = 1

        # Ensure interior building footprint gets default building floor
        if not is_cave:
            for ry in range(ty, ty + th):
                for rx in range(tx, tx + tw):
                    if layers['roof'][ry][rx] != ' ' or (layers['base'][ry][rx] != ' ' and layers['base'][ry][rx] not in ('@', '#')):
                        if layers['ground'][ry][rx] in (' ', ''):
                            layers['ground'][ry][rx] = 'house_floor_01'

        # 2. Paint pavement lot around the exterior perimeter only (never overwrite building interior)
        if not is_cave:
            lot_m = 2
            for ry in range(ty - lot_m, ty + th + lot_m):
                for rx in range(tx - lot_m, tx + tw + lot_m):
                    if 1 <= rx < w - 1 and 1 <= ry < h - 1:
                        if b_rect.collidepoint(rx, ry):
                            continue
                        if layers.get('protected_mask') and layers['protected_mask'][ry][rx] == 1:
                            continue
                        if layers['ground'][ry][rx] != getattr(self, 'water_tile', 'water_01'):
                            layers['ground'][ry][rx] = road_tile
                            occupied_mask[ry][rx] = 1

            # Connect road from the exterior border of the building toward the hub
            conn_x = max(1, min(w - 2, tx + tw // 2))
            conn_y = min(h - 2, ty + th + 1) if cy > ty + th else max(1, ty - 2)
            draw_secondary_maze_road(conn_x, conn_y, cx, cy, road_tile)
        else:
            conn_x = max(1, min(w - 2, tx + tw // 2))
            conn_y = min(h - 2, ty + th + 1) if cy > ty + th else max(1, ty - 2)
            draw_secondary_maze_road(conn_x, conn_y, cx, cy, 'dirty_01', path_width=2)