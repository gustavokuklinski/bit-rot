#!/usr/bin/env python3
# server.py - Bit Rot Dedicated Game Server (Terminal TUI Only)

import os
import sys

# Force headless / terminal-only execution before any pygame modules load
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Enable VT100 / ANSI escape sequences on Windows terminals
if sys.platform == "win32":
    os.system("")

import time
import signal
import socket
import select
import random
import uuid
import json
import shutil
import threading
from datetime import datetime
import pygame

import core.data.config
from core.data.config import (
    BASE_DIR, DATA_PATH, TILE_SIZE, get_writable_dir
)
from core.server.server import GameServer
from core.map.map_manager import MapManager
from core.map.tile_manager import TileManager
from core.map.world_time import WorldTime
from core.sound_manager import SoundManager
from core.systems.quadtree import Quadtree
from core.systems.spatial_manager import SpatialManager
from core.systems.load_manager import load_map as sys_load_map
from core.map.spawn_manager import (
    spawn_initial_zombies, spawn_l2_population, spawn_random_vehicles,
    manage_dynamic_npcs, async_spawner, spawn_animals
)
from core.map.procedural.generator import ProceduralGenerator
from core.entities.item.item import Item
from core.entities.zombie.zombie import Zombie
from core.entities.npc.npc import NPC
from core.data.radio_manager import RadioManager
from core.ui.helpers.trait_config_loader import load_config_data, save_config_xml
from core.update import update_game_state
from core.placement import find_free_tile
from core.entities.animal.animal import Animal
from core.entities.animal.animal_loader import AnimalLoader
from core.entities.zombie.zombie import Zombie
# ---------------------------------------------------------------------------
# ANSI Terminal Color Helpers
# ---------------------------------------------------------------------------
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

DEFAULT_SERVER_PORT = 7777


class ServerLogger:
    def info(self, msg): print(f"{GREEN}[Server]{RESET} {msg}")
    def warning(self, msg): print(f"{YELLOW}[Server Warning]{RESET} {msg}")
    def error(self, msg, exc_info=None): print(f"{RED}[Server Error]{RESET} {msg}")
    def critical(self, msg): print(f"{RED}{BOLD}[Server Critical]{RESET} {msg}")
    def crash(self, msg, e): print(f"{RED}{BOLD}[Server Crash]{RESET} {msg}: {e}")


def get_saved_sessions(server_dir_base):
    """Scans and extracts metadata from all previous server_<TIMESTAMP> sessions."""
    if not os.path.exists(server_dir_base):
        return []

    sessions = []
    try:
        entries = sorted(os.listdir(server_dir_base), reverse=True)
    except Exception:
        return []

    for d in entries:
        full_d = os.path.join(server_dir_base, d)
        if d.startswith("server_") and os.path.isdir(full_d):
            map_d = os.path.join(full_d, "map")
            world_rot = os.path.join(full_d, "world.rot")
            host_rot = os.path.join(full_d, "host.rot")

            if os.path.exists(map_d):
                ctime = os.path.getmtime(full_d)
                try:
                    ts_part = d.replace("server_", "")
                    dt_obj = datetime.strptime(ts_part, "%Y%m%d_%H%M%S")
                    dt_str = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt_str = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")

                days_survived = 0
                players_count = 0
                seed_str = "Unknown"

                if os.path.exists(world_rot):
                    try:
                        with open(world_rot, "r") as wf:
                            wdata = json.load(wf)
                            days_survived = wdata.get("time", {}).get("day_count", 0)
                    except Exception:
                        pass

                if os.path.exists(host_rot):
                    try:
                        with open(host_rot, "r") as hf:
                            hdata = json.load(hf)
                            players_count = len(hdata.get("remote", {}))
                    except Exception:
                        pass

                macro_path = os.path.join(full_d, "macro_world.json")
                if os.path.exists(macro_path):
                    try:
                        with open(macro_path, "r") as mf:
                            m_data = json.load(mf)
                            seed_str = m_data.get("seed", "Present")
                    except Exception:
                        pass

                sessions.append({
                    "name": d,
                    "path": full_d,
                    "created": dt_str,
                    "days": days_survived,
                    "players": players_count,
                    "seed": seed_str
                })
    return sessions


class DedicatedServerGame:
    """Headless Game instance managing the authoritative game state on the server."""

    def __init__(self, port=DEFAULT_SERVER_PORT, custom_seed=None, session_name=None):
        pygame.init()
        self.game_screen = pygame.display.set_mode((1280, 720))

        self.logger = ServerLogger()
        self.is_server = True
        self.is_client = False
        self.is_dedicated = True
        self.player = None
        self.remote_players = {}

        self.zoom_level = 1.0
        self.dt_ms = 16
        self.dt_mult = 1.0
        self.clock = pygame.time.Clock()
        self.frame_count = 0
        self.running = True

        self.world_min_x = 0
        self.world_min_y = 0
        self.CHUNK_SIZE = getattr(core.data.config, 'CHUNK_SIZE', 128)
        self.map_width_pixels = self.CHUNK_SIZE * TILE_SIZE
        self.map_height_pixels = self.CHUNK_SIZE * TILE_SIZE

        self.GRID_CELL_SIZE = 1024
        self.GRID_REBUILD_THRESHOLD = self.GRID_CELL_SIZE // 4
        self.last_zombie_grid_positions = {}
        self.last_item_grid_positions = {}
        self.last_container_grid_positions = {}

        self.zombie_grid = {}
        self.item_grid = {}
        self.container_grid = {}

        self.zombies = []
        self.active_zombies = []
        self.active_npcs = []
        self.active_animals = []
        self.visible_items = []
        self.visible_containers = []
        self.items_on_ground = []
        self.containers = []
        self.vehicles = []
        self.obstacles = []
        self.projectiles = []
        self.splashes = []
        self.blood_stains = []
        self.corpses = []
        self.map_lights = []
        self.renderable_tiles = []
        self.npcs = pygame.sprite.Group()
        self.npc_spawn_timer = 0

        self.current_layer_index = 1
        self.all_map_layers = {}
        self.all_ground_layers = {}
        self.all_spawn_layers = {}
        self.all_roof_layers = {}
        self.all_light_layers = {}
        self.layer_items = {}
        self.layer_zombies = {}
        self.layer_npcs = {}
        self.layer_spawn_triggers = {}
        self.triggered_spawns = set()
        self.current_zombie_spawns = []
        self.player_spawn = None
        self.roof_data = []
        self.roof_tiles = []
        self.npc_spawn_points = []
        self.spawn_point_grid = {}
        self.SPAWN_GRID_SIZE = 512
        self.map_states = {}
        self.zombies_killed = 0
        self.modals = []
        self.last_modal_positions = {}
        self.app_state = {'slots': [None] * 5}
        self.cached_obstacle_grid = {}
        self.cached_obstacle_count = -1

        self.sound_manager = SoundManager()
        self.map_manager = MapManager(self)
        self.tile_manager = TileManager()
        self.spatial_manager = SpatialManager(self)

        # 1. Resolve Canonical Server Directory
        self.server_dir_base = os.path.join(get_writable_dir(), "data.rot", "server")
        os.makedirs(self.server_dir_base, exist_ok=True)

        server_xml_path = os.path.join(self.server_dir_base, "server_world.xml")
        base_server_xml = os.path.join(BASE_DIR, "data.rot", "server", "server_world.xml")

        is_invalid = not os.path.exists(server_xml_path) or os.path.getsize(server_xml_path) < 50
        if is_invalid:
            if os.path.exists(base_server_xml) and os.path.getsize(base_server_xml) > 50:
                if os.path.abspath(base_server_xml) != os.path.abspath(server_xml_path):
                    shutil.copyfile(base_server_xml, server_xml_path)
            else:
                default_path = core.data.config.get_world_config_path("world")
                default_data = load_config_data(default_path)
                if default_data:
                    save_config_xml(default_data, server_xml_path)

        active_xml_source = server_xml_path if os.path.exists(server_xml_path) and os.path.getsize(server_xml_path) > 50 else base_server_xml
        core.data.config.load_settings(active_xml_source)
        self.world_settings = load_config_data(active_xml_source)

        # 2. Session Handling (Resume Existing vs Create New)
        self.is_resuming = bool(session_name and os.path.exists(os.path.join(self.server_dir_base, session_name)))

        if self.is_resuming:
            self.save_name = session_name
            self.current_save_folder_name = self.save_name
            self.save_dir_base = self.server_dir_base
            self.save_path = os.path.join(self.server_dir_base, self.save_name)
            self.map_path = os.path.join(self.save_path, "map")
            self.player_dir = os.path.join(self.save_path, "player", "remote")
            os.makedirs(self.map_path, exist_ok=True)
            os.makedirs(self.player_dir, exist_ok=True)
            self.map_manager.map_folder = self.map_path
            self.map_manager.refresh_maps()

            # Load world configuration from the resumed session if present
            session_xml = os.path.join(self.save_path, "world.xml")
            if os.path.exists(session_xml):
                core.data.config.load_settings(session_xml)
                self.world_settings = load_config_data(session_xml)

            # Discover starting chunk map
            start_map = next((f for f in sorted(self.map_manager.map_files.keys()) if f.startswith("map_L1_")), "map_L1_0_0_map.csv")
            self.map_manager.current_map_filename = start_map
            self.generator = ProceduralGenerator(self, output_folder=self.map_path)
            self.generator.generate_world(regenerate=False)
            self.world_seed = getattr(self.generator, 'world_seed', 'RESUMED')
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_name = f"server_{timestamp}"
            self.current_save_folder_name = self.save_name
            self.save_dir_base = self.server_dir_base
            self.save_path = os.path.join(self.server_dir_base, self.save_name)
            self.map_path = os.path.join(self.save_path, "map")
            self.player_dir = os.path.join(self.save_path, "player", "remote")
            os.makedirs(self.map_path, exist_ok=True)
            os.makedirs(self.player_dir, exist_ok=True)

            session_world_xml = os.path.join(self.save_path, "world.xml")
            if os.path.exists(active_xml_source):
                shutil.copyfile(active_xml_source, session_world_xml)
            self.map_manager.map_folder = self.map_path

            Item.load_item_templates()
            Zombie.load_templates()

            self.generator = ProceduralGenerator(self, output_folder=self.map_path)
            raw_seed = custom_seed or "".join(str(random.randint(0, 9)) for _ in range(12))
            chunks = core.data.config.MAP_CHUNKS
            self.world_seed = raw_seed if str(raw_seed).startswith(f"{chunks}-") else f"{chunks}-{raw_seed}"

            start_map = self.generator.generate_world(seed_pattern=self.world_seed, regenerate=True)
            self.map_manager.refresh_maps()
            self.map_manager.current_map_filename = start_map or "map_L1_0_0_map.csv"

        # 3. Load Map Layers & Subsystems
        self.load_map(self.map_manager.current_map_filename)
        self.quadtree = Quadtree(pygame.Rect(0, 0, getattr(self, 'map_width_pixels', 3000), getattr(self, 'map_height_pixels', 3000)))

        # 4. Populate or Restore Entities
        if self.is_resuming:
            self._restore_saved_session_entities()
        else:
            self._spawn_world_population()

        # 5. World Time & Radio Synchronization
        self.world_time = WorldTime(self)
        if self.is_resuming:
            world_rot = os.path.join(self.save_path, "world.rot")
            if os.path.exists(world_rot):
                try:
                    with open(world_rot, "r") as wf:
                        wdata = json.load(wf)
                        time_data = wdata.get("time", {})
                        self.world_time.game_time_ms = time_data.get("game_time_ms", 0)
                        self.world_time.day_count = time_data.get("day_count", 0)
                except Exception:
                    pass

        if not RadioManager.STATIONS:
            RadioManager.load_radios()
        RadioManager.sync_game_frequencies(self)

        # 6. Bind Network Server
        self.server = GameServer(self)
        self.server.port = int(port) if (port and port > 0) else DEFAULT_SERVER_PORT
        success, ip, assigned_port = self.server.start()

        if not success:
            raise RuntimeError(f"Could not bind server socket on port {self.server.port}.")

        self.port = assigned_port
        self.ip = ip

    def _restore_saved_session_entities(self):
        """Restores world items, barricades, vehicles, and NPCs from the resumed session files."""
        # Restore Containers & Items
        world_rot = os.path.join(self.save_path, "world.rot")
        if os.path.exists(world_rot):
            try:
                with open(world_rot, "r") as wf:
                    wdata = json.load(wf)

                # Explored memory
                if 'explored_tiles' in wdata:
                    self.explored_tiles_dict = {
                        k: bytearray.fromhex(v) for k, v in wdata['explored_tiles'].items()
                    }

                # Barricades
                for b in wdata.get('barricades', []):
                    m_name = b['map']
                    self.map_states.setdefault(m_name, {}).setdefault('barricades', {})
                    item_obj = Item.create_from_name(b['item_name'])
                    self.map_states[m_name]['barricades'][(b['gx'], b['gy'])] = {
                        'item_name': b['item_name'],
                        'health': b['health'],
                        'max_health': b['max_health'],
                        'remove_items': b.get('remove_items', ['Crowbar', 'Hammer']),
                        'remove_time': b.get('remove_time', 1.5),
                        'sprite': item_obj.image if item_obj else None
                    }

                # Ground items
                for it_entry in wdata.get('items', []):
                    d = it_entry.get('data', {})
                    it = Item.from_dict(d) if d else Item.create_from_name(it_entry.get('name'))
                    if it:
                        it.x = it_entry.get('x', 0)
                        it.y = it_entry.get('y', 0)
                        it.rect.topleft = (it.x, it.y)
                        it.layer = it_entry.get('layer', 1)
                        self.items_on_ground.append(it)
            except Exception as e:
                self.logger.warning(f"Error restoring world.rot: {e}")

        # Restore Zombies
        zombies_rot = os.path.join(self.save_path, "zombies.rot")
        if os.path.exists(zombies_rot):
            try:
                with open(zombies_rot, "r") as zf:
                    z_list = json.load(zf)
                for zd in z_list:
                    tmpl = {
                        'name': zd.get('name', 'Zombie'),
                        'health': zd.get('max_health', 10),
                        'speed': zd.get('speed', 0.3),
                        'min_xp': 1, 'max_xp': 5,
                        'min_attack': 1, 'max_attack': 3,
                        'min_infection': 0, 'max_infection': 1,
                        'loot': zd.get('loot_table', [])
                    }
                    z = Zombie(zd['x'], zd['y'], tmpl)
                    z.id = zd.get('id', str(uuid.uuid4()))
                    z.layer = zd.get('layer', 1)
                    z.map_filename = zd.get('map_filename', '')      # NEW
                    z.health = zd.get('health', z.max_health)
                    self.zombies.append(z)
            except Exception as e:
                self.logger.warning(f"Error restoring zombies.rot: {e}")

        # Restore NPCs
        npc_rot = os.path.join(self.save_path, "npc.rot")
        if os.path.exists(npc_rot):
            try:
                with open(npc_rot, "r") as nf:
                    n_list = json.load(nf)
                for nd in n_list:
                    npc = NPC(nd['x'], nd['y'], self, is_static=nd.get('is_static', False), layer=nd.get('layer', 1))
                    npc.id = nd.get('id', str(uuid.uuid4()))
                    npc.name = nd.get('name', 'Survivor')
                    npc.health = nd.get('health', 100)
                    npc.max_health = nd.get('max_health', 100)
                    npc.is_friendly = nd.get('is_friendly', True)
                    npc.map_filename = nd.get('map_filename', '')
                    self.npcs.add(npc)
            except Exception as e:
                self.logger.warning(f"Error restoring npc.rot: {e}")

        if hasattr(self, 'spatial_manager'):
            self.spatial_manager.rebuild_zombie_grid(force=True)
            self.spatial_manager.rebuild_item_grid(force=True)
            self.spatial_manager.rebuild_container_grid()

    def _spawn_world_population(self):
        """Populates all active world chunks, layers, and islands across the server."""
        from core.map.map_loader import load_map_from_file
        from core.entities.vehicle.vehicle_data import VehicleData
        from core.entities.vehicle.vehicle import Vehicle

        active_chunks = getattr(self.generator, 'active_chunks', {(0, 0)})
        lobby_coord = getattr(self.generator, 'lobby_chunk', None)

        self.zombies.clear()
        self.npcs.empty()
        self.active_animals.clear()
        self.vehicles.clear()
        self.items_on_ground.clear()
        if hasattr(self.map_manager, 'vehicles'):
            self.map_manager.vehicles.clear()

        for (gx, gy) in sorted(list(active_chunks)):
            is_lobby = ((gx, gy) == lobby_coord)

            for layer_idx in (1, 2, 3):
                chunk_map_name = f"map_L{layer_idx}_{gx}_{gy}_map.csv"
                base_path = os.path.join(self.map_path, chunk_map_name)
                spawn_path = os.path.join(self.map_path, f"map_L{layer_idx}_{gx}_{gy}_spawn.csv")
                ground_path = os.path.join(self.map_path, f"map_L{layer_idx}_{gx}_{gy}_ground.csv")

                if not os.path.exists(base_path) or not os.path.exists(spawn_path):
                    continue

                base_data = load_map_from_file(base_path)
                spawn_data = load_map_from_file(spawn_path)
                ground_data = load_map_from_file(ground_path) if os.path.exists(ground_path) else []

                if not base_data or not spawn_data:
                    continue

                h = len(base_data)
                w = len(base_data[0]) if h > 0 else 0

                chunk_obstacles = []
                for y in range(h):
                    for x in range(w):
                        b_char = base_data[y][x]
                        if b_char and b_char != ' ':
                            defn = self.tile_manager.definitions.get(b_char)
                            if defn and defn.get('is_obstacle', False) and not defn.get('is_stair', False):
                                chunk_obstacles.append(pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

                # 1. Lobby Chunk Layer 1: Spawn exclusively 3 stationary FNPCs
                if is_lobby and layer_idx == 1:
                    occupied = set()
                    spawned_fnpcs = 0
                    for y in range(h):
                        for x in range(w):
                            if spawn_data[y][x].strip() == 'FNPC' and spawned_fnpcs < 3:
                                px, py = x * TILE_SIZE, y * TILE_SIZE
                                npc = NPC(px, py, self, is_static=True, layer=1)
                                npc.is_friendly = True
                                npc.map_filename = chunk_map_name
                                free_p = find_free_tile(npc.rect, chunk_obstacles, initial_pos=(px, py), max_radius=6)
                                if free_p and free_p not in occupied:
                                    occupied.add(free_p)
                                    npc.rect.topleft = free_p
                                    npc.x, npc.y = free_p
                                    self.npcs.add(npc)
                                    spawned_fnpcs += 1
                    continue

                if is_lobby and layer_idx == 2:
                    continue

                # 2. Island & World Chunks:
                # A. Vehicles (Layer 1 only)
                if layer_idx == 1 and not is_lobby:
                    veh_tiles = []
                    for y in range(h):
                        for x in range(w):
                            if spawn_data[y][x] == 'VEH':
                                veh_tiles.append((x, y))
                    if not veh_tiles and ground_data:
                        for y in range(h):
                            for x in range(min(w, len(ground_data[y]))):
                                gt = ground_data[y][x].lower()
                                if 'asphalt' in gt or 'road' in gt or 'dirty_01' in gt:
                                    veh_tiles.append((x, y))

                    if veh_tiles:
                        random.shuffle(veh_tiles)
                        max_v = min(len(veh_tiles), getattr(core.data.config, 'MAX_VEH_CHUNK', 6))
                        for i in range(max_v):
                            tx, ty = veh_tiles[i]
                            defn = VehicleData.get_random_definition()
                            if defn:
                                images = defn.get('images', {})
                                facing = random.choice(['top', 'down', 'left', 'right'])
                                base_img = images.get(facing) or (next(iter(images.values())) if images else None)
                                vw = base_img.get_width() if base_img else TILE_SIZE * 2
                                vh = base_img.get_height() if base_img else TILE_SIZE * 3
                                v_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, vw, vh)
                                if not any(v_rect.colliderect(ob) for ob in chunk_obstacles):
                                    v = Vehicle(
                                        name=defn['name'],
                                        x=tx * TILE_SIZE, y=ty * TILE_SIZE,
                                        width=vw, height=vh,
                                        image=images, stats=defn['stats'],
                                        capacity=defn['capacity'],
                                        loot_table=defn['loot_table'],
                                        facing=facing
                                    )
                                    v.map_filename = chunk_map_name
                                    self.vehicles.append(v)
                                    self.containers.append(v)
                                    if hasattr(self.map_manager, 'vehicles'):
                                        self.map_manager.vehicles.append(v)
                                    chunk_obstacles.append(v.rect)

                # B. Zombies
                z_spawns = []
                for y in range(h):
                    for x in range(w):
                        if spawn_data[y][x] == 'Z':
                            z_spawns.append((x * TILE_SIZE, y * TILE_SIZE))

                if z_spawns:
                    max_z = getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6)
                    random.shuffle(z_spawns)
                    for zx, zy in z_spawns[:max_z]:
                        z = Zombie.create_random(zx, zy)
                        if z:
                            z.layer = layer_idx
                            z.map_filename = chunk_map_name
                            free_z = find_free_tile(z.rect, chunk_obstacles, initial_pos=(zx, zy), max_radius=8)
                            if free_z:
                                z.rect.topleft = free_z
                                z.x, z.y = free_z
                            self.zombies.append(z)

                # C. Animals
                anm_tiles = []
                for y in range(h):
                    for x in range(w):
                        if spawn_data[y][x] == 'ANM':
                            anm_tiles.append((x, y))

                if not anm_tiles and ground_data and layer_idx in (1, 2, 3):
                    for y in range(2, h - 2):
                        for x in range(2, min(w, len(ground_data[y]) - 2)):
                            gt = ground_data[y][x].lower()
                            bt = base_data[y][x]
                            if bt == ' ' and ('grass' in gt or 'dirty' in gt or 'cave' in gt) and 'water' not in gt:
                                anm_tiles.append((x, y))

                if anm_tiles:
                    AnimalLoader.load_animals()
                    valid_types = [a_name for a_name, a_def in AnimalLoader.definitions.items() if layer_idx in a_def.get('spawn_layers', [1, 2])]
                    if valid_types:
                        random.shuffle(anm_tiles)
                        max_a = min(len(anm_tiles), getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6))
                        for i in range(max_a):
                            ax, ay = anm_tiles[i]
                            a_type = random.choice(valid_types)
                            animal = Animal(ax * TILE_SIZE, ay * TILE_SIZE, a_type, game=self, layer=layer_idx)
                            animal.map_filename = chunk_map_name
                            free_a = find_free_tile(animal.rect, chunk_obstacles, initial_pos=(ax * TILE_SIZE, ay * TILE_SIZE), max_radius=8)
                            if free_a:
                                animal.rect.topleft = free_a
                                animal.x, animal.y = free_a
                            self.active_animals.append(animal)
                            self.items_on_ground.append(animal)

                # D. NPCs
                npc_spawns = []
                for y in range(h):
                    for x in range(w):
                        char_str = spawn_data[y][x].strip()
                        if char_str in ('HNPC', 'FNPC'):
                            npc_spawns.append((x * TILE_SIZE, y * TILE_SIZE, char_str))

                if npc_spawns:
                    max_n = getattr(core.data.config, 'NPC_MAX_CHUNK', 6)
                    random.shuffle(npc_spawns)
                    for nx, ny, n_type in npc_spawns[:max_n]:
                        is_static = (n_type == 'FNPC') if layer_idx == 1 else False
                        is_friendly = is_static
                        npc = NPC(nx, ny, self, is_static=is_static, layer=layer_idx)
                        npc.is_friendly = is_friendly
                        npc.is_static = is_static
                        npc.map_filename = chunk_map_name
                        free_n = find_free_tile(npc.rect, chunk_obstacles, initial_pos=(nx, ny), max_radius=8)
                        if free_n:
                            npc.rect.topleft = free_n
                            npc.x, npc.y = free_n
                        self.npcs.add(npc)

        if hasattr(self, 'spatial_manager'):
            self.spatial_manager.rebuild_zombie_grid(force=True)
            self.spatial_manager.rebuild_item_grid(force=True)
            self.spatial_manager.rebuild_container_grid()

    def load_map(self, map_filename):
        result = sys_load_map(self, map_filename)
        if self.map_manager:
            self.map_manager.clear_cache()
            if hasattr(self, 'map_width_pixels') and hasattr(self, 'map_height_pixels'):
                self.quadtree = Quadtree(pygame.Rect(0, 0, self.map_width_pixels, self.map_height_pixels))

        self.zombie_grid = {}
        self.item_grid = {}
        self.container_grid = {}
        self.spatial_manager.rebuild_zombie_grid()
        self.spatial_manager.rebuild_item_grid()
        self.spatial_manager.rebuild_container_grid()

        self.cached_obstacle_grid = {}
        self.cached_obstacle_count = -1
        return result

    def save_game(self):
        from core.systems.save_manager import save_game
        return save_game(self)

    def find_nearby_containers(self):
        from core.systems.utils import find_nearby_containers
        return find_nearby_containers(self)

    def screen_to_world(self, screen_pos):
        from core.systems.utils import screen_to_world
        return screen_to_world(self, screen_pos)

    def _get_scaled_mouse_pos(self):
        return (0, 0)

    def get_events(self):
        return pygame.event.get()

    def emit_noise(self, source_pos, radius, source_type="noise", map_filename=None):
        if not source_pos:
            return
        
        def same_area(e):
            if not map_filename:
                return True
            em = getattr(e, 'map_filename', '') or ''
            return (not em) or em == map_filename

        rad_sq = radius * radius
        for z in getattr(self, 'active_zombies', []) + getattr(self, 'zombies', []):
            if getattr(z, 'is_dead', False) or not same_area(z):
                continue
            dx = z.rect.centerx - source_pos[0]
            dy = z.rect.centery - source_pos[1]
            if (dx * dx + dy * dy) <= rad_sq:
                if hasattr(z, 'alert_to_noise'):
                    z.alert_to_noise(source_pos, source_type=source_type)

        for npc in getattr(self, 'active_npcs', []):
            if getattr(npc, 'is_dead', False) or not same_area(npc):
                continue
            if not getattr(npc, 'is_friendly', True) and not getattr(npc, 'is_static', False):
                dx = npc.rect.centerx - source_pos[0]
                dy = npc.rect.centery - source_pos[1]
                if (dx * dx + dy * dy) <= rad_sq:
                    if hasattr(npc, 'alert_to_noise'):
                        npc.alert_to_noise(source_pos, source_type=source_type)

    def tick(self):
        self.dt_ms = self.clock.tick(60)
        self.dt_mult = (self.dt_ms / 1000.0) * 60.0
        self.frame_count += 1

        self.world_time.update()
        self.server.update()
        update_game_state(self)

        self.npc_spawn_timer += 1
        if self.npc_spawn_timer >= 30:
            manage_dynamic_npcs(self)
            self.npc_spawn_timer = 0

        for npc in list(self.npcs):
            npc.update(self)

        if self.frame_count % 30 == 0:
            self.quadtree.clear()
            for z in getattr(self, 'active_zombies', self.zombies):
                self.quadtree.insert(z)
            for a in getattr(self, 'active_animals', []):
                self.quadtree.insert(a)
            for n in getattr(self, 'npcs', []):
                self.quadtree.insert(n)
            for p in self.projectiles:
                self.quadtree.insert(p)


# ---------------------------------------------------------------------------
# Interactive TUI Startup Menus & Dashboard
# ---------------------------------------------------------------------------
def print_banner():
    print(f"{CYAN}{BOLD}")
    print("  ================================================================")
    print("             BIT ROT - DEDICATED GAME SERVER (TUI)                ")
    print("  ================================================================")
    print(f"{RESET}")


def interactive_startup_menu(default_port=DEFAULT_SERVER_PORT):
    """Displays the interactive CLI startup menu when running directly in a terminal."""
    server_dir = os.path.join(get_writable_dir(), "data.rot", "server")
    chosen_port = default_port
    chosen_seed = None
    chosen_session = None

    while True:
        print_banner()
        print(f"  {BOLD}[1]{RESET} Start New Server Session      {DIM}(Port: {chosen_port}){RESET}")
        print(f"  {BOLD}[2]{RESET} Resume Saved Session          {DIM}(Browse server_<TIMESTAMP>){RESET}")
        print(f"  {BOLD}[3]{RESET} Change Server Port            {DIM}(Current: {chosen_port}){RESET}")
        print(f"  {BOLD}[4]{RESET} Set Custom World Seed         {DIM}(Current: {chosen_seed or 'Random'}){RESET}")
        print(f"  {BOLD}[5]{RESET} Exit")
        print()

        try:
            choice = input(f"{YELLOW}Select option [1-5]: {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)

        if choice == "1":
            return chosen_port, chosen_seed, None

        elif choice == "2":
            sessions = get_saved_sessions(server_dir)
            if not sessions:
                print(f"\n{RED}[Notice]{RESET} No previous server sessions found at:")
                print(f"         {server_dir}")
                print(f"{YELLOW}Press Enter to return to menu...{RESET}")
                input()
                continue

            print()
            print(f"  {BOLD}AVAILABLE PREVIOUS SESSIONS:{RESET}")
            print("  " + "-" * 66)
            print(f"  {BOLD}{'#':<3} {'Session Directory':<26} {'Created':<20} {'Days':<6} {'Players'}{RESET}")
            print("  " + "-" * 66)

            for idx, s in enumerate(sessions):
                print(f"  [{idx + 1}] {s['name']:<26} {s['created']:<20} {s['days']:<6} {s['players']}")
            print("  " + "-" * 66)
            print(f"  [0] Cancel / Return to Menu\n")

            try:
                pick = input(f"{YELLOW}Select session [1-{len(sessions)}] or 0: {RESET}").strip()
                if pick == "0" or not pick:
                    continue
                pick_idx = int(pick) - 1
                if 0 <= pick_idx < len(sessions):
                    chosen_session = sessions[pick_idx]['name']
                    return chosen_port, chosen_seed, chosen_session
                else:
                    print(f"{RED}Invalid selection.{RESET}")
                    time.sleep(1)
            except ValueError:
                print(f"{RED}Invalid number.{RESET}")
                time.sleep(1)

        elif choice == "3":
            print(f"\n{BOLD}Recommended Dedicated Ports:{RESET}")
            print(f"  • {GREEN}7777{RESET}  - Default standard game server port")
            print(f"  • {GREEN}7778{RESET}  - Secondary server instance")
            print(f"  • {GREEN}27015{RESET} - Steam/Source default port")
            print(f"  • {GREEN}30000{RESET} - High custom port\n")

            try:
                p_in = input(f"Enter port number [1024-65535] (default {DEFAULT_SERVER_PORT}): ").strip()
                if p_in:
                    p_val = int(p_in)
                    if 1024 <= p_val <= 65535:
                        chosen_port = p_val
                        print(f"{GREEN}Port set to {chosen_port}.{RESET}\n")
                        time.sleep(0.8)
                    else:
                        print(f"{RED}Port out of range. Must be between 1024 and 65535.{RESET}\n")
                        time.sleep(1.2)
            except ValueError:
                print(f"{RED}Invalid integer.{RESET}\n")
                time.sleep(1)

        elif choice == "4":
            s_in = input(f"Enter custom seed (or leave blank for random): ").strip()
            chosen_seed = s_in if s_in else None
            print(f"{GREEN}Seed set to: {chosen_seed or 'Random'}{RESET}\n")
            time.sleep(0.8)

        elif choice in ("5", "q", "exit"):
            print("Exiting.")
            sys.exit(0)


def print_dashboard_status(server_game, start_time):
    """Renders an authoritative TUI status report."""
    uptime_sec = int(time.time() - start_time)
    m, s = divmod(uptime_sec, 60)
    h, m = divmod(m, 60)

    clients_count = len(server_game.server.clients)
    z_count = len(server_game.zombies)
    npc_count = len(server_game.npcs)
    animal_count = len(getattr(server_game, 'active_animals', []))
    veh_count = len(getattr(server_game, 'vehicles', []))
    day_count = getattr(server_game.world_time, 'day_count', 0)
    weather = getattr(server_game.world_time, 'weather', 'CLEAR')
    fps = int(server_game.clock.get_fps())

    print()
    print(f"{CYAN}{BOLD}┌──────────────────────── BIT ROT SERVER STATUS ────────────────────────┐{RESET}")
    print(f"{CYAN}│{RESET} {BOLD}Address:{RESET}   {server_game.ip}:{server_game.port:<18} {BOLD}Uptime:{RESET} {h:02d}h {m:02d}m {s:02d}s            {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET} {BOLD}Session:{RESET}   {server_game.save_name:<28} {BOLD}FPS:{RESET}    {fps:<18} {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET} {BOLD}World:{RESET}     Day {day_count} | Weather: {weather:<12} {BOLD}Seed:{RESET}   {server_game.world_seed:<18} {CYAN}│{RESET}")
    print(f"{CYAN}├───────────────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{CYAN}│{RESET} {BOLD}Entities:{RESET}  Zombies: {z_count:<5} | NPCs: {npc_count:<5} | Animals: {animal_count:<5} | Veh: {veh_count:<3} {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET} {BOLD}Players:{RESET}   {clients_count} Connected                                                {CYAN}│{RESET}")

    if server_game.server.clients:
        print(f"{CYAN}├───────────────────────────────────────────────────────────────────────┤{RESET}")
        for s_sock, info in list(server_game.server.clients.items()):
            p_name = info.get('name', 'Unknown')
            p_id = (info.get('id') or 'N/A')[:8]
            uip = info.get('uip', 'N/A')
            last_d = info.get('last_data', {})
            px, py = last_d.get('x', 0), last_d.get('y', 0)
            hp = last_d.get('health', 100)
            print(f"{CYAN}│{RESET}   • {BOLD}{p_name:<16}{RESET} (ID: {p_id}.. | IP: {uip:<15}) Pos: ({int(px)}, {int(py)}) HP: {int(hp)} {CYAN}│{RESET}")

    print(f"{CYAN}{BOLD}└───────────────────────────────────────────────────────────────────────┘{RESET}")
    print()


def main():
    target_port = None
    custom_seed = None
    target_session = None
    force_new = False
    skip_menu = False

    # 1. Parse Command Line Flags
    idx = 1
    while idx < len(sys.argv):
        arg = sys.argv[idx]
        if arg.startswith("--port:") or arg.startswith("--port="):
            sep = ":" if ":" in arg else "="
            val = arg.split(sep, 1)[1].strip()
            try:
                target_port = int(val)
                skip_menu = True
            except ValueError:
                print(f"[Warning] Invalid port '{val}'. Defaulting to {DEFAULT_SERVER_PORT}.")
                target_port = DEFAULT_SERVER_PORT

        elif arg in ("-p", "--port"):
            if idx + 1 < len(sys.argv):
                try:
                    target_port = int(sys.argv[idx + 1].strip())
                    idx += 1
                    skip_menu = True
                except ValueError:
                    target_port = DEFAULT_SERVER_PORT

        elif arg.startswith("--seed:") or arg.startswith("--seed="):
            sep = ":" if ":" in arg else "="
            custom_seed = arg.split(sep, 1)[1].strip()
            skip_menu = True

        elif arg.startswith("--session:") or arg.startswith("--session=") or arg.startswith("--resume:") or arg.startswith("--resume="):
            sep = ":" if ":" in arg else "="
            target_session = arg.split(sep, 1)[1].strip()
            skip_menu = True

        elif arg in ("--new", "-n"):
            force_new = True
            skip_menu = True

        elif arg in ("--help", "-h"):
            print_banner()
            print("Usage: python server.py [OPTIONS]")
            print()
            print("Options:")
            print(f"  --port:<PORT>       Bind to custom port (e.g. --port:7777, default: {DEFAULT_SERVER_PORT})")
            print("  --session:<NAME>    Resume saved session (e.g. --session:server_20261016_120000)")
            print("  --seed:<SEED>       Set custom procedural world seed")
            print("  --new               Create a new session immediately without prompting")
            print("  -h, --help          Show this help message and exit")
            print()
            sys.exit(0)

        idx += 1

    # 2. Interactive Startup Menu (if launched without flags and attached to a terminal)
    if not skip_menu and not force_new and sys.stdin.isatty():
        chosen_port, chosen_seed, chosen_session = interactive_startup_menu(
            default_port=target_port or DEFAULT_SERVER_PORT
        )
        target_port = chosen_port
        custom_seed = chosen_seed
        target_session = chosen_session
    else:
        if target_port is None:
            target_port = DEFAULT_SERVER_PORT

    print_banner()
    if target_session:
        print(f"[Server] Resuming saved world session: {BOLD}{target_session}{RESET}")
    else:
        print(f"[Server] Initializing world engine and map generation...")

    # 3. Instantiate Game Server
    try:
        server_game = DedicatedServerGame(
            port=target_port,
            custom_seed=custom_seed,
            session_name=target_session
        )
    except Exception as e:
        print(f"{RED}{BOLD}[Fatal Error]{RESET} Failed to start dedicated server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    def _shutdown_handler(signum, frame):
        print(f"\n{YELLOW}[Server]{RESET} Shutdown signal received. Saving world...")
        server_game.running = False

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    print(f"  {CYAN}├─{RESET} Status        : {GREEN}ONLINE{RESET}")
    print(f"  {CYAN}├─{RESET} World Config  : {os.path.join(server_game.server_dir_base, 'server_world.xml')}")
    print(f"  {CYAN}├─{RESET} Session Path  : {server_game.save_path}")
    print(f"  {CYAN}├─{RESET} World Seed    : {server_game.world_seed}")
    print(f"  {CYAN}├─{RESET} Binding (TCP) : {server_game.ip}:{server_game.port}")
    print(f"  {CYAN}├─{RESET} Binding (UDP) : {server_game.ip}:{server_game.port}")
    print(f"  {CYAN}└─{RESET} Direct Join   : {BOLD}./bitrot.py --connect={server_game.ip}:{server_game.port}{RESET}")
    print()
    print(f"Type {YELLOW}'status'{RESET} for dashboard, {YELLOW}'help'{RESET} for commands, or {YELLOW}'stop'{RESET} to exit.\n")

    # 4. Asynchronous Stdin Thread
    cmd_queue = []
    cmd_lock = threading.Lock()

    def _stdin_reader():
        while server_game.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                cmd = line.strip()
                if cmd:
                    with cmd_lock:
                        cmd_queue.append(cmd)
            except Exception:
                break

    input_thread = threading.Thread(target=_stdin_reader, daemon=True)
    input_thread.start()

    start_time = time.time()

    # 5. Main Execution Loop
    try:
        while server_game.running:
            server_game.tick()

            commands_to_run = []
            with cmd_lock:
                if cmd_queue:
                    commands_to_run = list(cmd_queue)
                    cmd_queue.clear()

            for cmd in commands_to_run:
                parts = cmd.split()
                action = parts[0].lower()

                if action in ("stop", "exit", "quit"):
                    print(f"{YELLOW}[Server]{RESET} Stopping server...")
                    server_game.running = False
                    break

                elif action == "status":
                    print_dashboard_status(server_game, start_time)

                elif action == "clear":
                    if sys.platform == "win32":
                        os.system("cls")
                    else:
                        os.system("clear")
                    print_dashboard_status(server_game, start_time)

                elif action == "players":
                    if not server_game.server.clients:
                        print(f"{YELLOW}[Players]{RESET} No players currently connected.")
                    else:
                        print(f"\n{BOLD}CONNECTED PLAYERS ({len(server_game.server.clients)}):{RESET}")
                        print("  " + "-" * 62)
                        for s_sock, info in list(server_game.server.clients.items()):
                            p_name = info.get('name', 'Unknown')
                            p_id = info.get('id', 'N/A')
                            uip = info.get('uip', 'N/A')
                            print(f"  • {BOLD}{p_name:<16}{RESET} ID: {p_id[:8]}.. | IP: {uip}")
                        print("  " + "-" * 62 + "\n")

                elif action == "say":
                    msg_text = " ".join(parts[1:])
                    if msg_text:
                        from core.server.network import NetMsg
                        server_game.server.broadcast_queue.put(({
                            'type': NetMsg.CHAT_BROADCAST,
                            'sender': '[SERVER]',
                            'text': msg_text
                        }, None))
                        print(f"{MAGENTA}[Server Chat]{RESET} {msg_text}")

                elif action == "save":
                    server_game.save_game()
                    print(f"{GREEN}[Server]{RESET} World successfully saved to disk.")

                elif action == "kick":
                    if len(parts) > 1:
                        target = parts[1].strip()
                        kicked = False
                        for s_sock, info in list(server_game.server.clients.items()):
                            if info.get('id') == target or info.get('name', '').lower() == target.lower():
                                server_game.server._handle_client_disconnect(s_sock)
                                print(f"{YELLOW}[Server]{RESET} Kicked player: {info.get('name')}")
                                kicked = True
                                break
                        if not kicked:
                            print(f"{RED}[Server]{RESET} Player '{target}' not found.")
                    else:
                        print("Usage: kick <player_id or name>")

                elif action == "help":
                    print(f"\n{BOLD}SERVER COMMAND REFERENCE:{RESET}")
                    print(f"  {YELLOW}status{RESET}          Show formatted real-time status dashboard")
                    print(f"  {YELLOW}players{RESET}         List all connected remote players")
                    print(f"  {YELLOW}say <msg>{RESET}       Broadcast an announcement message to all players")
                    print(f"  {YELLOW}save{RESET}            Save world, player states, and maps to disk")
                    print(f"  {YELLOW}kick <target>{RESET}   Disconnect a player by name or ID")
                    print(f"  {YELLOW}clear{RESET}           Clear console screen")
                    print(f"  {YELLOW}stop{RESET} / {YELLOW}exit{RESET}     Save world state and terminate the server\n")
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for commands.")

    finally:
        server_game.server.stop()
        server_game.save_game()
        async_spawner.stop()
        print(f"{GREEN}[Server]{RESET} Clean shutdown complete. Session preserved.")


if __name__ == "__main__":
    main()