#!/usr/bin/env python3
# server.py - Bit Rot Dedicated Game Server (Terminal Only)

import os
import sys

# Force headless / terminal-only execution before any pygame modules load
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

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


class ServerLogger:
    def info(self, msg): print(f"[Server] {msg}")
    def warning(self, msg): print(f"[Server Warning] {msg}")
    def error(self, msg, exc_info=None): print(f"[Server Error] {msg}")
    def critical(self, msg): print(f"[Server Critical] {msg}")
    def crash(self, msg, e): print(f"[Server Crash] {msg}: {e}")

class DedicatedServerGame:
    """Headless Game instance managing the authoritative game state on the server."""

    def __init__(self, port=0, custom_seed=None):
        # 1. Initialize Pygame display headlessly so convert() and convert_alpha() work without a window
        pygame.init()
        self.game_screen = pygame.display.set_mode((1280, 720))

        self.logger = ServerLogger()
        self.is_server = True
        self.is_client = False
        self.is_dedicated = True
        self.player = None  # No local player character on a dedicated server
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

        # Layer tracking collections (prevents AttributeError in world_layers)
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

        # Core subsystem managers
        self.sound_manager = SoundManager()
        self.map_manager = MapManager(self)
        self.tile_manager = TileManager()
        self.spatial_manager = SpatialManager(self)

        # 2. Resolve world config from data.rot/server/world.xml
        self.server_dir_base = os.path.join(get_writable_dir(), "data.rot", "server")
        os.makedirs(self.server_dir_base, exist_ok=True)

        server_xml_path = os.path.join(self.server_dir_base, "server_world.xml")
        if not os.path.exists(server_xml_path):
            candidates = [
                os.path.join(get_writable_dir(), "data.rot", "save", "config", "world.xml"),
                os.path.join(DATA_PATH, "world.xml"),
                os.path.join(DATA_PATH, "config", "world.xml"),
                os.path.join(BASE_DIR, "data.rot", "lib", "data", "world.xml"),
                os.path.join(BASE_DIR, "data.rot", "lib", "data", "world_builds", "world_default.xml"),
            ]
            src_xml = next((p for p in candidates if os.path.exists(p)), None)
            if src_xml:
                shutil.copyfile(src_xml, server_xml_path)
            else:
                default_data = load_config_data(core.data.config.get_world_config_path("world"))
                save_config_xml(default_data, server_xml_path)

        core.data.config.load_settings(server_xml_path)
        self.world_settings = load_config_data(server_xml_path)

        # 3. Setup server session folder: data.rot/server/server_<TIMESTAMP>/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_name = f"server_{timestamp}"
        self.current_save_folder_name = self.save_name
        self.save_dir_base = self.server_dir_base
        self.save_path = os.path.join(self.server_dir_base, self.save_name)
        self.map_path = os.path.join(self.save_path, "map")
        self.player_dir = os.path.join(self.save_path, "player", "remote")
        os.makedirs(self.map_path, exist_ok=True)
        os.makedirs(self.player_dir, exist_ok=True)

        # Copy the active server_world.xml into the session directory as world.xml
        shutil.copyfile(server_xml_path, os.path.join(self.save_path, "world.xml"))
        self.map_manager.map_folder = self.map_path

        # 4. Generate world
        Item.load_item_templates()
        Zombie.load_templates()

        self.generator = ProceduralGenerator(self, output_folder=self.map_path)
        raw_seed = custom_seed or "".join(str(random.randint(0, 9)) for _ in range(12))
        chunks = core.data.config.MAP_CHUNKS
        self.world_seed = raw_seed if str(raw_seed).startswith(f"{chunks}-") else f"{chunks}-{raw_seed}"

        start_map = self.generator.generate_world(seed_pattern=self.world_seed, regenerate=True)
        self.map_manager.refresh_maps()
        self.map_manager.current_map_filename = start_map or "map_L1_0_0_map.csv"

        # 5. Load map layers
        self.load_map(self.map_manager.current_map_filename)
        self.quadtree = Quadtree(pygame.Rect(0, 0, getattr(self, 'map_width_pixels', 3000), getattr(self, 'map_height_pixels', 3000)))

        # 6. Populate world
        self._spawn_world_population()

        # 7. World time and radio
        self.world_time = WorldTime(self)
        if not RadioManager.STATIONS:
            RadioManager.load_radios()
        RadioManager.sync_game_frequencies(self)

        # 8. Start GameServer
        self.server = GameServer(self)
        if port and port > 0:
            self.server.port = int(port)
        success, ip, assigned_port = self.server.start()

        if not success:
            raise RuntimeError("Could not bind server socket.")

        self.port = assigned_port
        self.ip = ip

    def _spawn_world_population(self):
        """Populates the initial world without requiring a local player character."""
        if 1 in self.all_map_layers:
            spawn_random_vehicles(self, count=getattr(core.data.config, 'MAX_VEH_CHUNK', 6))

        if 2 in self.all_map_layers:
            spawn_l2_population(self, count=getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6) * 3, target_layer=2)
        if 3 in self.all_map_layers:
            spawn_l2_population(self, count=getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6) * 3, target_layer=3)

        if getattr(self, 'current_zombie_spawns', None):
            zombies = spawn_initial_zombies(
                self.obstacles,
                self.current_zombie_spawns,
                self.items_on_ground,
                limit=getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500),
                spawns_per_marker=getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 3),
                map_width_px=getattr(self, 'map_width_pixels', 3000),
                map_height_px=getattr(self, 'map_height_pixels', 3000),
                game=self
            )
            self.zombies.extend(zombies)
            self.layer_zombies[self.current_layer_index] = self.zombies[:]

        spawn_animals(self, count=getattr(core.data.config, 'ANIMAL_MAX_CHUNK', 6))

        if hasattr(self, 'npc_spawn_points') and self.npc_spawn_points:
            for spawn_data in self.npc_spawn_points:
                nx, ny = spawn_data[0], spawn_data[1]
                npc_type = spawn_data[2] if len(spawn_data) == 3 else 'HNPC'
                is_static = (npc_type == 'FNPC')
                npc = NPC(nx, ny, self, is_static=is_static)
                npc.is_friendly = is_static
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

    def emit_noise(self, source_pos, radius, source_type="noise"):
        if not source_pos:
            return
        rad_sq = radius * radius
        for z in getattr(self, 'active_zombies', []) + getattr(self, 'zombies', []):
            if getattr(z, 'is_dead', False):
                continue
            dx = z.rect.centerx - source_pos[0]
            dy = z.rect.centery - source_pos[1]
            if (dx * dx + dy * dy) <= rad_sq:
                if hasattr(z, 'alert_to_noise'):
                    z.alert_to_noise(source_pos, source_type=source_type)

        for npc in getattr(self, 'active_npcs', []):
            if getattr(npc, 'is_dead', False):
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

        # NPC management
        self.npc_spawn_timer += 1
        if self.npc_spawn_timer >= 30:
            manage_dynamic_npcs(self)
            self.npc_spawn_timer = 0

        # Update NPCs
        for npc in list(self.npcs):
            npc.update(self)

        # Maintain Quadtree with active entities
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


def main():
    target_port = 0
    custom_seed = None

    for arg in sys.argv[1:]:
        if arg.startswith("--port="):
            try:
                target_port = int(arg.split("=", 1)[1].strip())
            except ValueError:
                pass
        elif arg.startswith("--seed="):
            custom_seed = arg.split("=", 1)[1].strip()

    print("==================================================================")
    print("           BIT ROT - DEDICATED GAME SERVER (HEADLESS)            ")
    print("==================================================================")
    print("[Server] Initializing world engine and map generation...")

    server_game = DedicatedServerGame(port=target_port, custom_seed=custom_seed)

    def _shutdown_handler(signum, frame):
        print("\n[Server] Shutdown signal received. Saving world...")
        server_game.running = False

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    print("------------------------------------------------------------------")
    print(f"[Server] World Config : {os.path.join(server_game.server_dir_base, 'world.xml')}")
    print(f"[Server] Session Dir  : {server_game.save_path}")
    print(f"[Server] World Seed   : {server_game.world_seed}")
    print(f"[Server] Listening on : {server_game.ip}:{server_game.port}")
    print(f"[Server] Direct Join  : ./bitrot.py --connect={server_game.ip}:{server_game.port}")
    print("------------------------------------------------------------------")
    print("Commands: status | players | say <msg> | save | kick <id> | stop")
    print("==================================================================")

    # Background stdin reader for terminal console interaction
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

    try:
        while server_game.running:
            server_game.tick()

            # Process terminal console commands
            commands_to_run = []
            with cmd_lock:
                if cmd_queue:
                    commands_to_run = list(cmd_queue)
                    cmd_queue.clear()

            for cmd in commands_to_run:
                parts = cmd.split()
                action = parts[0].lower()

                if action in ("stop", "exit", "quit"):
                    print("[Server] Stopping server...")
                    server_game.running = False
                    break

                elif action == "status":
                    uptime = int(time.time() - start_time)
                    m, s = divmod(uptime, 60)
                    h, m = divmod(m, 60)
                    clients_num = len(server_game.server.clients)
                    z_count = len(server_game.zombies)
                    npc_count = len(server_game.npcs)
                    fps = int(server_game.clock.get_fps())
                    print(f"[Status] FPS: {fps} | Uptime: {h:02d}:{m:02d}:{s:02d} | Clients: {clients_num} | Zombies: {z_count} | NPCs: {npc_count}")

                elif action == "players":
                    if not server_game.server.clients:
                        print("[Players] No players currently connected.")
                    else:
                        print(f"[Players] Connected ({len(server_game.server.clients)}):")
                        for s, info in server_game.server.clients.items():
                            p_name = info.get('name', 'Unknown')
                            p_id = info.get('id', 'N/A')
                            uip = info.get('uip', 'N/A')
                            print(f"  - {p_name} (ID: {p_id[:8] if p_id else 'N/A'}... | IP: {uip})")

                elif action == "say":
                    msg_text = " ".join(parts[1:])
                    if msg_text:
                        from core.server.network import NetMsg
                        server_game.server.broadcast_queue.put(({
                            'type': NetMsg.CHAT_BROADCAST,
                            'sender': '[SERVER]',
                            'text': msg_text
                        }, None))
                        print(f"[Server Chat] {msg_text}")

                elif action == "save":
                    server_game.save_game()
                    print(f"[Server] World successfully saved to {server_game.save_path}")

                elif action == "kick":
                    if len(parts) > 1:
                        target = parts[1]
                        kicked = False
                        for s, info in list(server_game.server.clients.items()):
                            if info.get('id') == target or info.get('name', '').lower() == target.lower():
                                server_game.server._handle_client_disconnect(s)
                                print(f"[Server] Kicked player {info.get('name')}")
                                kicked = True
                                break
                        if not kicked:
                            print(f"[Server] Player '{target}' not found.")
                    else:
                        print("Usage: kick <player_id or name>")

                elif action == "help":
                    print("Available commands:")
                    print("  status         - Show server performance and entity statistics")
                    print("  players        - List all connected players")
                    print("  say <msg>      - Broadcast chat message to all players")
                    print("  save           - Save the world state to disk")
                    print("  kick <player>  - Disconnect a player")
                    print("  stop / exit    - Save world and shutdown the server")
                else:
                    print(f"Unknown command: '{cmd}'. Type 'help' for available commands.")

    finally:
        server_game.server.stop()
        server_game.save_game()
        async_spawner.stop()
        print("[Server] Server cleanly terminated. World saved.")


if __name__ == "__main__":
    main()