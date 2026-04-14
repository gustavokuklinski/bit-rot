# core/multiplayer/server.py
import os
import uuid
import time
import threading

# Force Pygame into a dummy headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from core.data.config import load_settings, get_writable_dir
from core.map.procedural.generator import ProceduralGenerator
from core.multiplayer.network import GameNetworkServer
from core.systems.save_manager import save_game

# --- Mock Classes to appease save_manager.py ---
class DummyProgression:
    def __init__(self):
        self.attributes = {}
    def get_level(self, attr): return 1

class DummyPlayer:
    def __init__(self):
        self.progression = DummyProgression()
        self.name = "ServerHost"
        self.sex = "None"
        self.x, self.y = 0, 0
        self.health, self.water, self.food, self.stamina = 100, 100, 100, 100
        self.tireness, self.infection, self.anxiety = 0, 0, 0
        self.traits, self.known_recipes = [], []
        self.visuals, self.sounds_data = {}, {}
        self.inventory, self.belt = [], []
        self.clothes = {}
        self.quests, self.completed_quests = [], []
        self.dialog_history, self.special_dialogs = [], []

class DummyMapManager:
    def __init__(self, map_folder, starting_map):
        self.map_folder = map_folder
        self.current_map_filename = starting_map
    def save_map_to_file(self, dst): pass

class DummyWorldTime:
    def __init__(self):
        self.game_time_ms = 0
        self.day_count = 1

class DummyLogger:
    def info(self, msg):
        print(f"[SaveManager] {msg}")

# --- Headless Game Context ---
class HeadlessGame:
    def __init__(self, server_name, map_folder):
        # The save manager hardcodes the path to: /save/game/[current_save_folder_name]
        # We use a path traversal trick to redirect it to: /save/server/[server_name]
        self.current_save_folder_name = os.path.join("..", "server", server_name)
        
        self.logger = DummyLogger()
        self.player = DummyPlayer()
        self.map_manager = DummyMapManager(map_folder, "map_L1_world_map.csv")
        self.world_time = DummyWorldTime()
        
        # World Entities populated by the generator
        self.vehicles = []
        self.items_on_ground = []
        self.obstacles = []
        self.zombies = []
        self.npcs = []
        self.containers = []
        self.layer_spawn_triggers = {}
        self.last_modal_positions = {}
        self.zombies_killed = 0


def start_dedicated_server(server_name=None):
    if not server_name:
        server_name = f"Server_{uuid.uuid4().hex[:6].upper()}"

    print("==================================================")
    print(f" Starting Dedicated Local Server: {server_name}")
    print("==================================================")

    load_settings(preset="server")

    writable_root = get_writable_dir()
    server_dir = os.path.join(writable_root, "game", "save", "server", server_name)
    map_output_dir = os.path.join(server_dir, "map")
    
    os.makedirs(map_output_dir, exist_ok=True)
    print(f"[System] World map data path mapped to: {map_output_dir}")

    # 1. Initialize Headless Environment
    game_context = HeadlessGame(server_name, map_output_dir)

    # 2. Procedurally Generate World & Entities
    print("[World] Initializing Procedural Generator...")
    generator = ProceduralGenerator(
        game=game_context,
        output_folder=map_output_dir
    )
    
    print("[World] Generating server terrain chunks and spawning entities. Please wait...")
    starting_chunk = generator.generate_world(seed_pattern=None, regenerate=True)
    game_context.map_manager.current_map_filename = starting_chunk
    print(f"[World] Map generated successfully! Global spawn defined at: {starting_chunk}")

    # 3. Call existing save_manager to build .rot files from generated entities
    print("[System] Finalizing world state and writing .rot files...")
    save_game(game_context)

    # 4. Start Network Listener
    network = GameNetworkServer(host="0.0.0.0", port=0)
    server_thread = threading.Thread(target=network.start, daemon=True)
    server_thread.start()

    # 5. Main Server Event Loop
    try:
        print("[System] Server is running. Press Ctrl+C to shutdown.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[System] Gracefully shutting down...")
        network.stop()
        print("[System] Goodbye!")

if __name__ == "__main__":
    start_dedicated_server()