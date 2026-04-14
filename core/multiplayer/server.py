# core/multiplayer/server.py
import os
import uuid
import time
import threading

# [CRITICAL PATTERN] 
# Force Pygame into a dummy headless mode BEFORE any core game imports happen.
# This allows the ProceduralGenerator to create surfaces and heatmaps in a pure console environment.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# Now we safely import your existing codebase
from core.data.config import load_settings, get_writable_dir
from core.map.procedural.generator import ProceduralGenerator
from core.multiplayer.network import GameNetworkServer

class HeadlessGame:
    """
    A minimalist mock container mimicking the Game class.
    Provides the essential attributes needed by map generation layers
    without initializing graphical/UI sub-systems.
    """
    def __init__(self):
        self.vehicles = []
        self.items_on_ground = []
        self.obstacles = []
        self.zombies = []
        self.npcs = []
        self.containers = []
        self.map_data = []

def start_dedicated_server(server_name=None):
    if not server_name:
        server_name = f"Server_{uuid.uuid4().hex[:6].upper()}"

    print("==================================================")
    print(f" Starting Dedicated Local Server: {server_name}")
    print("==================================================")

    # 1. Load Server Configuration
    # Calling your existing load_settings with the preset "server"
    # automatically targets game/save/config/server.xml
    print("[System] Loading server configuration (server.xml)...")
    load_settings(preset="server")

    # 2. Setup Save Directories
    writable_root = get_writable_dir()
    server_dir = os.path.join(writable_root, "game", "save", "server", server_name)
    map_output_dir = os.path.join(server_dir, "map")
    
    os.makedirs(map_output_dir, exist_ok=True)
    print(f"[System] World map data path mapped to: {map_output_dir}")

    # 3. Initialize Headless Environment
    game_context = HeadlessGame()

    # 4. Procedurally Generate World
    print("[World] Initializing Procedural Generator...")
    generator = ProceduralGenerator(
        game=game_context,
        output_folder=map_output_dir
    )
    
    print("[World] Generating server terrain chunks. Please wait...")
    # Generate the world using the configurations just like single player
    starting_chunk = generator.generate_world(seed_pattern=None, regenerate=True)
    print(f"[World] Map generated successfully! Global spawn defined at: {starting_chunk}")

    # 5. Start Network Listener
    # Passing port 0 assigns an available random port
    network = GameNetworkServer(host="0.0.0.0", port=0)
    server_thread = threading.Thread(target=network.start, daemon=True)
    server_thread.start()

    # 6. Main Server Event Loop
    try:
        print("[System] Server is running. Press Ctrl+C to shutdown.")
        while True:
            # Future steps: Server ticks (Zombie wandering AI, weather, time progression)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[System] Gracefully shutting down...")
        network.stop()
        print("[System] Goodbye!")

if __name__ == "__main__":
    start_dedicated_server()