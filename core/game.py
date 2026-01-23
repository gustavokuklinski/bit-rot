import pygame
import random
import time
import math
import uuid
import os
import asyncio
import shutil
import json
import glob
import re
from datetime import datetime
from core.data.config import *
import core.data.config
from core.entities.player.player import Player
from core.entities.zombie.zombie import Zombie
from core.entities.item.item import Item, Projectile
from core.entities.zombie.corpse import Corpse
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.game_over import draw_game_over
from core.ui.helpers.player_setup import run_player_setup
from core.ui.inventory_modal import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect, get_invcontainer_slot_rect
from core.ui.container_modal import draw_container_view, get_container_slot_rect
from core.ui.status_modal import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.data.player_xml_parser import parse_player_data
from core.ui.assets import load_assets
from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.map.tile_manager import TileManager
from core.map.map_manager import MapManager
from core.map.map_loader import load_map_from_file, parse_layered_map_layout
from core.entities.npc.npc import NPC
from core.map.spawn_manager import spawn_initial_items, spawn_initial_zombies, manage_dynamic_npcs
from core.map.world_layers import load_all_map_layers, set_active_layer, load_giant_map
from core.map.world_time import WorldTime
from core.ui.mobile_modal import draw_mobile_modal
from core.sound_manager import SoundManager
from core.ui.helpers.trait_config_loader import load_config_data
from core.ui.helpers.load_game_screen import draw_load_game_screen, get_save_files, delete_save
from core.messages import display_message, init_messages
from core.map.generator import ProceduralGenerator
from core.entities.vehicle.vehicle import Vehicle
from core.ui.helpers.start_loading import draw_loading_screen
from core.logger import GameLogger

class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        
        self.screen = pygame.display.set_mode((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT), pygame.RESIZABLE)
        self.virtual_screen = pygame.Surface((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT))
        
        pygame.display.set_caption("Bit Rot")
        try:
            icon_image = pygame.image.load('./game/icons/favicon.png')
            pygame.display.set_icon(icon_image)
        except:
            pass
        
        self.logger = GameLogger()
        self.logger.info("Bit Rot - Developed by Gustavo Kuklinski")
        self.logger.info("Initializing Rot Engine...")

        init_messages(self)

        self.clock = pygame.time.Clock()
        self.assets = load_assets()
        self.game_state = 'MENU'
        self.running = True

        self.map_manager = MapManager(self)
        self.tile_manager = TileManager()

        self.player = None
        self.zombies = []
        self.items_on_ground = []

        self.npcs = pygame.sprite.Group()
        self.npc_spawn_timer = 0 

        self.projectiles = []
        self.obstacles = []
        self.renderable_tiles = []
        self.containers = []
        self.corpses = []
        self.splashes = []
        self.blood_stains = []
        
        self.map_lights = [] 
        
        self.all_light_layers = {} 
        self.light_data = []
        
        self.zombies_killed = 0

        self.modals = []
        self.context_menu = {
            'active': False,
            'item': None,
            'source': None,
            'index': -1,
            'options': [],
            'rects': [],
            'position': (0, 0)
        }

        self.is_dragging = False
        self.dragged_item = None
        self.drag_origin = None
        self.drag_offset = (0, 0)
        self.drag_candidate = None
        self.drag_start_pos = (0, 0)
        self.DRAG_THRESHOLD = 5

        self.last_modal_positions = {
            'status': (65, 10),
            'inventory': (1050, 10),
            'gear': (830, 10),
            'container': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150),
            'nearby': (1050, 360),
            'messages': (10, 360),
            'text': (VIRTUAL_SCREEN_WIDTH / 2 - 200, VIRTUAL_GAME_HEIGHT / 2 - 150),
            'mobile': (VIRTUAL_SCREEN_WIDTH / 2 - 125, VIRTUAL_GAME_HEIGHT / 2 - 200)
        }

        self.status_button_rect = None
        self.inventory_button_rect = None
        self.nearby_button_rect = None
        self.messages_button_rect = None
        self.camera = None
        self.map_states = {}
        self.layer_items = {}
        self.layer_zombies = {}
        self.player_name = ""
        self.name_input_active = False
        self.selected_profession = None
        self.hovered_item = None
        self.hovered_container = None
        self.hovered_npc = None
        self.hovered_interactable_tile_rect = None

        self.message_log = []

        self.current_layer_index = 1
        self.all_map_layers = {} 
        self.all_ground_layers = {}
        self.all_spawn_layers = {}
        self.all_roof_layers = {}
        self.layer_spawn_triggers = {} 
        self.triggered_spawns = set()
        
        self.current_zombie_spawns = []
        self.roof_data = []
        self.roof_tiles = []
        
        self.npc_spawn_points = [] 

        self.spawn_point_grid = {}
        self.SPAWN_GRID_SIZE = 512

        self.player_setup_state = {}
        self.load_game_state = {} 

        self.player_view_radius = core.data.config.BASE_PLAYER_VIEW_RADIUS
        self.world_time = WorldTime(self)
        self.sound_manager = SoundManager()

        self.world_min_x = 0
        self.world_min_y = 0

        self.is_giant_map = False
        self.paused_surface = None
        
        self.current_save_folder_name = None

        self.is_aiming = False
        self.camera_pan_x = 0
        self.camera_pan_y = 0

        self.message_logs = {
            'All': [],
            'Chat': [],
            'Player': [],
            'Zombie': []
        }
        self.message_log = self.message_logs['All']

        self.chat_active = False
        self.chat_input_text = ""

        self.loading_data = None
        self.loading_done = False
        self.loading_saved_game_folder = None

    def capture_pause_screen(self):
        """Creates a black and white version of the current screen for the pause menu."""
        self.paused_surface = self.virtual_screen.copy()
        try:
            self.paused_surface = pygame.transform.grayscale(self.paused_surface)
        except AttributeError:
            bw = pygame.Surface(self.paused_surface.get_size())
            bw.fill((255, 255, 255))
            self.paused_surface.blit(bw, (0,0), special_flags=pygame.BLEND_RGB_MULT)

    def save_game(self):
        if self.current_save_folder_name:
            save_name = self.current_save_folder_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"save_{timestamp}"
            self.current_save_folder_name = save_name

        save_path = os.path.join("game", "save", "game", save_name)
        self.logger.info(f"Saving game to {save_path}...")

        try:
            os.makedirs(save_path, exist_ok=True)

            map_src = os.path.abspath(self.map_manager.map_folder)
            map_dst = os.path.abspath(os.path.join(save_path, "map"))
            
            if map_src != map_dst:
                if os.path.exists(map_dst):
                     shutil.rmtree(map_dst)
                shutil.copytree(map_src, map_dst, dirs_exist_ok=True)
                self.map_manager.map_folder = map_dst
            else:
                self.logger.info("Map folder is already in the save directory. Skipping map copy.")
            
            attributes_base = {
                "strength": self.player.progression.strength['level'],
                "fitness": self.player.progression.fitness['level'],
                "melee": self.player.progression.melee['level'],
                "ranged": self.player.progression.ranged['level'],
                "lucky": self.player.progression.lucky['level'],
                "speed": self.player.progression.speed['level']
            }
            
            progression_data = {
                "strength": self.player.progression.strength,
                "fitness": self.player.progression.fitness,
                "melee": self.player.progression.melee,
                "ranged": self.player.progression.ranged,
                "lucky": self.player.progression.lucky,
                "speed": self.player.progression.speed
            }

            player_data = {
                "name": self.player.name,
                "world_seed": getattr(self, 'world_seed', "4-B1TR07"),
                "profession": self.player.profession,
                "sex": self.player.sex,
                "x": self.player.x,
                "y": self.player.y,
                "map_filename": self.map_manager.current_map_filename,
                "zombies_killed": self.zombies_killed,
                "stats": {
                    "health": self.player.health,
                    "water": self.player.water,
                    "food": self.player.food,
                    "stamina": self.player.stamina,
                    "tireness": self.player.tireness,
                    "infection": self.player.infection,
                    "anxiety": self.player.anxiety
                },
                "attributes": attributes_base,
                "progression": progression_data,
                "traits": self.player.traits,
                "visuals": self.player.visuals,
                "sounds": self.player.sounds_data,
                # [SAFE] Check for to_dict before calling
                "inventory": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.player.inventory if item],
                "belt": [(item.to_dict() if hasattr(item, 'to_dict') else item) if item else None for item in self.player.belt],
                "clothes": {slot: ((item.to_dict() if hasattr(item, 'to_dict') else item)) if item else None for slot, item in self.player.clothes.items()},
            }
            
            if self.player.backpack:
                 # Check if backpack is Item object
                 if hasattr(self.player.backpack, 'to_dict'):
                     player_data["backpack"] = self.player.backpack.to_dict()
                 else:
                     player_data["backpack"] = self.player.backpack

            with open(os.path.join(save_path, "player.rot"), "w") as f:
                json.dump(player_data, f, indent=4)

            # --- NPC Save [ROBUST FIX] ---
            npc_data = []
            for npc in self.npcs:
                # Safely handle clothes and inventory that might be dicts instead of Items
                safe_clothes = {}
                for slot, item in npc.clothes.items():
                    if item:
                        if hasattr(item, 'to_dict'):
                            safe_clothes[slot] = item.to_dict()
                        else:
                            safe_clothes[slot] = item # Save raw data/dict/string if not an Item object
                    else:
                        safe_clothes[slot] = None

                safe_inventory = []
                for i in npc.inventory:
                    if hasattr(i, 'to_dict'):
                        safe_inventory.append(i.to_dict())
                    else:
                        safe_inventory.append(i)

                safe_weapon = None
                if npc.equipped_weapon:
                    if hasattr(npc.equipped_weapon, 'to_dict'):
                        safe_weapon = npc.equipped_weapon.to_dict()
                    else:
                        safe_weapon = npc.equipped_weapon

                npc_entry = {
                    "x": npc.rect.x,
                    "y": npc.rect.y,
                    "name": npc.name,
                    "health": npc.health,
                    "is_following": npc.is_following,
                    "is_friendly": npc.is_friendly,
                    "inventory": safe_inventory,
                    "equipped_weapon": safe_weapon,
                    "clothes": safe_clothes
                }
                npc_data.append(npc_entry)
            
            with open(os.path.join(save_path, "npc.rot"), "w") as f:
                json.dump(npc_data, f, indent=4)

            # --- Vehicle Save ---
            vehicle_data = []
            #vehicles_to_save = getattr(self.map_manager, 'vehicles', [])
            vehicles_to_save = [obj for obj in self.containers if isinstance(obj, Vehicle)]
            for v in vehicles_to_save:
                safe_inv = []
                if hasattr(v, 'inventory'):
                    for i in v.inventory:
                        if hasattr(i, 'to_dict'):
                            safe_inv.append(i.to_dict())
                        else:
                            safe_inv.append(i)

                safe_equipment = {}
                if hasattr(v, 'equipment'):
                    for slot, item in v.equipment.items():
                        if item:
                            if hasattr(item, 'to_dict'):
                                safe_equipment[slot] = item.to_dict()
                            else:
                                # Fallback for non-Item objects or raw strings
                                safe_equipment[slot] = item
                        else:
                            safe_equipment[slot] = None

                v_entry = {
                    "x": v.rect.x,
                    "y": v.rect.y,
                    "name": v.name, 
                    "inventory": safe_inv,
                    "equipment": safe_equipment, # [CHANGED] - Add equipment to save data
                    "lights": getattr(v, 'lights', 'off') # [CHANGED] - Save light state
                }
                vehicle_data.append(v_entry)

            with open(os.path.join(save_path, "vehicles.rot"), "w") as f:
                json.dump(vehicle_data, f, indent=4)

            # --- World Data Save ---
            # Safe checking for items on ground
            safe_ground_items = []
            for i in self.items_on_ground:
                item_data = i.to_dict() if hasattr(i, 'to_dict') else i
                safe_ground_items.append({
                    "data": item_data, 
                    "x": i.rect.x if hasattr(i, 'rect') else i.x, 
                    "y": i.rect.y if hasattr(i, 'rect') else i.y
                })

            world_data = {
                "time": {
                    "game_time_ms": self.world_time.game_time_ms,
                    "day_count": self.world_time.day_count
                },
                "layer_spawn_triggers": {str(k): list(v) for k, v in self.layer_spawn_triggers.items()},
                "items": safe_ground_items,
                "modal_positions": self.last_modal_positions,
                "zombies": [{"x": z.x, "y": z.y, "health": z.health} for z in self.zombies]
            }
            with open(os.path.join(save_path, "world.rot"), "w") as f:
                json.dump(world_data, f, indent=4)

            self.logger.info("Game saved successfully!")
            return True
            
        except Exception as e:
            self.logger.info(f"Error saving game: {e}")
            import traceback
            traceback.print_exc()
            return False


    def load_game(self, save_folder_name):
        save_path = os.path.join("game", "save", "game", save_folder_name)
        map_path = os.path.join(save_path, "map")
        
        self.logger.info(f"Loading game from {save_path}...")

        try:
            with open(os.path.join(save_path, "player.rot"), "r") as f:
                player_data = json.load(f)

            # 1. Initialize Game
            self.start_new_game(player_data, save_dir_name=save_folder_name)
            self.zombies_killed = player_data.get('zombies_killed', 0)

            # 2. [CHANGED] Load the correct map IMMEDIATELY, before loading items/zombies
            # This prevents load_map from wiping out the restored entities later.
            target_map = player_data.get('map_filename')
            if target_map and target_map != self.map_manager.current_map_filename:
                self.logger.info(f"Switching to saved map: {target_map}")
                self.load_map(target_map)
                load_giant_map(self)
            
            self.map_manager.map_folder = map_path
            self.map_manager.refresh_maps()

            # 3. Parse Map Layout (Obstacles, Containers, etc.)
            # We do this after ensuring we are on the correct map.
            layer_idx = self.current_layer_index
            base_layout = self.all_map_layers.get(layer_idx)
            ground_layout = self.all_ground_layers.get(layer_idx)
            spawn_layout = self.all_spawn_layers.get(layer_idx)
            roof_layout = self.all_roof_layers.get(layer_idx)
            light_layout = self.all_light_layers.get(layer_idx)

            obstacles, renderable_tiles, player_spawn, zombie_spawns, item_spawns, containers, roofs, lights, npc_spawns = parse_layered_map_layout(
                base_layout, ground_layout, spawn_layout, roof_layout, light_layout, self.tile_manager
            )

            # Separate vehicles from static containers
            map_vehicles = [obj for obj in containers if isinstance(obj, Vehicle)]
            for v in map_vehicles:
                if v in containers:
                    containers.remove(v)
                if v.rect in obstacles:
                    obstacles.remove(v.rect)
            
            self.obstacles = obstacles
            self.containers = containers
            self.renderable_tiles = renderable_tiles
            self.npc_spawn_points = npc_spawns

            # 4. Restore Player State
            if 'progression' in player_data:
                prog_data = player_data['progression']
                self.player.progression.strength = prog_data.get('strength', self.player.progression.strength)
                self.player.progression.fitness = prog_data.get('fitness', self.player.progression.fitness)
                self.player.progression.melee = prog_data.get('melee', self.player.progression.melee)
                self.player.progression.ranged = prog_data.get('ranged', self.player.progression.ranged)
                self.player.progression.lucky = prog_data.get('lucky', self.player.progression.lucky)
                self.player.progression.speed = prog_data.get('speed', self.player.progression.speed)
            
            self.player.x = player_data['x']
            self.player.y = player_data['y']
            self.player.rect.topleft = (self.player.x, self.player.y)
            
            # Inventory restoration
            self.player.inventory = []
            for item_data in player_data['inventory']:
                if isinstance(item_data, dict):
                    item = Item.from_dict(item_data)
                else:
                    item = Item.create_from_name(item_data)
                if item: self.player.inventory.append(item)

            self.player.belt = []
            for item_data in player_data.get('belt', [None]*5):
                if item_data:
                    if isinstance(item_data, dict):
                        self.player.belt.append(Item.from_dict(item_data))
                    else:
                        self.player.belt.append(Item.create_from_name(item_data))
                else:
                    self.player.belt.append(None)
            
            self.player.clothes = {}
            for slot, item_data in player_data.get('clothes', {}).items():
                if item_data:
                    if isinstance(item_data, dict):
                        self.player.clothes[slot] = Item.from_dict(item_data)
                    else:
                        self.player.clothes[slot] = Item.create_from_name(item_data)
                else:
                    self.player.clothes[slot] = None

            if "backpack" in player_data:
                 bp_data = player_data["backpack"]
                 if isinstance(bp_data, dict):
                     self.player.backpack = Item.from_dict(bp_data)
                 else:
                     self.player.backpack = Item.create_from_name(bp_data["name"])
                     if self.player.backpack:
                         self.player.backpack.inventory = [Item.create_from_name(name) for name in bp_data.get("inventory", [])]

            # 5. Load World Data (Items, Zombies)
            with open(os.path.join(save_path, "world.rot"), "r") as f:
                world_data = json.load(f)
            
            time_data = world_data.get('time', {})
            self.world_time.game_time_ms = time_data.get('game_time_ms', 0)
            self.world_time.day_count = time_data.get('day_count', 0)
            
            # Triggers
            raw_layer_triggers = world_data.get('layer_spawn_triggers', {})
            self.layer_spawn_triggers = {}
            for layer_str, coords_list in raw_layer_triggers.items():
                try:
                    layer_int = int(layer_str)
                    self.layer_spawn_triggers[layer_int] = set(tuple(c) for c in coords_list)
                except Exception as e:
                    self.logger.info(f"Error restoring triggers for layer {layer_str}: {e}")
            
            # Items on Ground
            self.items_on_ground = [] # Clear any items spawned by load_map
            saved_items = world_data.get('items', [])
            self.logger.info(f"Found {len(saved_items)} items to load from save file.")

            for i_data in saved_items:
                try:
                    item = None
                    if 'data' in i_data:
                        if isinstance(i_data['data'], dict):
                            item = Item.from_dict(i_data['data'])
                        else:
                            item = Item.create_from_name(i_data['data'])
                    else:
                        item = Item.create_from_name(i_data['name'])
                        
                    if item:
                        item.x = int(i_data.get('x', 0))
                        item.y = int(i_data.get('y', 0))
                        item.rect.topleft = (item.x, item.y)
                        self.items_on_ground.append(item)
                    else:
                        self.logger.info(f"Warning: Failed to recreate item: {i_data}")
                except Exception as e:
                    self.logger.info(f"Error loading an item on ground: {e}")
            
            # Zombies
            self.zombies = [] # Clear any zombies spawned by load_map
            for z_data in world_data.get('zombies', []):
                z = Zombie.create_random(z_data['x'], z_data['y']) 
                if z:
                    z.health = z_data['health']
                    self.zombies.append(z)
            
            if 'modal_positions' in world_data:
                saved_positions = world_data['modal_positions']
                self.last_modal_positions.update(saved_positions)
                
                for modal in self.modals:
                    m_type = modal['type']
                    if m_type in saved_positions:
                        pos = saved_positions[m_type]
                        # Ensure we have valid coordinates
                        if isinstance(pos, (list, tuple)) and len(pos) == 2:
                            modal['position'] = (int(pos[0]), int(pos[1]))
                            modal['rect'].topleft = modal['position']

            # 6. Load NPCs
            if os.path.exists(os.path.join(save_path, "npc.rot")):
                 with open(os.path.join(save_path, "npc.rot"), "r") as f:
                     npc_list = json.load(f)
                 self.npcs.empty()
                 for n_data in npc_list:
                     npc = NPC(n_data['x'], n_data['y'], self)
                     npc.name = n_data.get('name', 'Survivor')
                     npc.health = n_data.get('health', 100)
                     
                     npc.is_following = n_data.get('is_following', False)
                     npc.is_friendly = n_data.get('is_friendly', True)
                     if npc.is_following:
                         npc.state = 'following'
                     
                     npc.inventory = []
                     for i_data in n_data.get('inventory', []):
                         if isinstance(i_data, dict):
                             item = Item.from_dict(i_data)
                         else:
                             item = Item.create_from_name(i_data)
                         if item: npc.inventory.append(item)
                     
                     w_data = n_data.get('equipped_weapon')
                     if w_data:
                         if isinstance(w_data, dict):
                             npc.equipped_weapon = Item.from_dict(w_data)
                         else:
                             npc.equipped_weapon = Item.create_from_name(w_data)
                         
                     clothes_data = n_data.get('clothes', {})
                     npc.clothes = {}
                     for slot, c_data in clothes_data.items():
                         if c_data:
                             if isinstance(c_data, dict):
                                 npc.clothes[slot] = Item.from_dict(c_data)
                             else:
                                 npc.clothes[slot] = Item.create_from_name(c_data)
                             
                     self.npcs.add(npc)
            
            # 7. Load Vehicles
            if os.path.exists(os.path.join(save_path, "vehicles.rot")):
                with open(os.path.join(save_path, "vehicles.rot"), "r") as f:
                    v_list = json.load(f)
                 
                self.map_manager.vehicles = [] 
                
                for v_data in v_list:
                    vehicle_def = self.tile_manager.definitions.get(v_data.get('name').lower().replace(" ", "_"), None)
                    v_img = vehicle_def['image'] if vehicle_def else None 
                    v_w, v_h = TILE_SIZE, TILE_SIZE
                     
                    vehicle = Vehicle(
                        name=v_data.get('name'),
                        x=v_data.get('x'),
                        y=v_data.get('y'),
                        width=v_w,
                        height=v_h,
                        image=v_img, 
                        stats={}, 
                        capacity=20
                    )
                    
                    if hasattr(vehicle, 'inventory'):
                        vehicle.inventory = []
                        for i_data in v_data.get('inventory', []):
                            if isinstance(i_data, dict):
                                item = Item.from_dict(i_data)
                            else:
                                item = Item.create_from_name(i_data)
                            if item: vehicle.inventory.append(item)
                    
                    if 'equipment' in v_data:
                        loaded_equipment = v_data['equipment']
                        for slot, item_data in loaded_equipment.items():
                            if item_data:
                                if isinstance(item_data, dict):
                                    item = Item.from_dict(item_data)
                                else:
                                    item = Item.create_from_name(item_data)
                                 
                                if item:
                                    vehicle.equipment[slot] = item
                            else:
                                vehicle.equipment[slot] = None
                        
                        vehicle.update_stats_from_equipment()
                     
                    if 'lights' in v_data:
                        vehicle.lights = v_data['lights']

                    self.map_manager.vehicles.append(vehicle)
                    self.containers.append(vehicle)
                    self.obstacles.append(vehicle.rect)

            self.game_state = 'PLAYING'
            self.logger.info("Game loaded successfully!")

        except Exception as e:
            self.logger.info(f"Error loading game: {e}")
            import traceback
            traceback.print_exc()
            self.game_state = 'MENU'


    def _cleanup_modals(self):
        """Removes the Vehicle modal if the player moves too far from the vehicle."""
        modals_to_remove = []
        if not self.player: return

        for modal in self.modals:
            if modal['type'] == 'vehicle':
                vehicle = modal['vehicle']
                # Check distance between player and vehicle (center to center)
                dist = math.hypot(self.player.rect.centerx - vehicle.rect.centerx, self.player.rect.centery - vehicle.rect.centery)
                
                # Close modal if player is farther than 2 tiles
                if dist > TILE_SIZE * 2: 
                    modals_to_remove.append(modal)
            
        for modal in modals_to_remove:
            self.modals.remove(modal)
            self.logger.info(f"Closed {modal['vehicle'].name} modal: player moved away.")


    def run_paused(self):
        if self.paused_surface:
            self.virtual_screen.blit(self.paused_surface, (0, 0))
        else:
            self.virtual_screen.fill((50, 50, 50))

        overlay = pygame.Surface((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.virtual_screen.blit(overlay, (0, 0))

        center_x = VIRTUAL_SCREEN_WIDTH // 2
        center_y = VIRTUAL_GAME_HEIGHT // 2
        btn_w, btn_h = 220, 50
        spacing = 20
        
        btn_continue = pygame.Rect(center_x - btn_w//2, center_y - btn_h - spacing, btn_w, btn_h)
        btn_save     = pygame.Rect(center_x - btn_w//2, center_y, btn_w, btn_h)
        btn_quit     = pygame.Rect(center_x - btn_w//2, center_y + btn_h + spacing, btn_w, btn_h)

        mouse_pos = self._get_scaled_mouse_pos()

        def draw_btn(rect, text, color_base, color_hover):
            color = color_hover if rect.collidepoint(mouse_pos) else color_base
            pygame.draw.rect(self.virtual_screen, color, rect, border_radius=5)
            pygame.draw.rect(self.virtual_screen, WHITE, rect, 1, border_radius=5)
            txt_surf = large_font.render(text, True, WHITE)
            self.virtual_screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

        draw_btn(btn_continue, "Continue", (80, 80, 80), (60, 60, 60))
        draw_btn(btn_save, "Save Game", (80, 80, 80), (60, 60, 60))
        draw_btn(btn_quit, "Quit", (80, 80, 80), (60, 60, 60))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                self.game_state = 'PLAYING' 
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_continue.collidepoint(mouse_pos):
                    self.game_state = 'PLAYING'
                elif btn_save.collidepoint(mouse_pos):
                    if self.save_game():
                        pass
                elif btn_quit.collidepoint(mouse_pos):
                    self.running = False

        self._update_screen()

    def load_map(self, map_filename):
        self.all_map_layers.clear()
        self.all_ground_layers.clear()
        self.all_spawn_layers.clear()
        self.layer_items.clear()
        self.layer_zombies.clear()
        # self.current_save_folder_name = None
        self.map_manager.current_map_filename = map_filename
        
        # Pass the current map folder (save folder) to the loader
        self.all_map_layers, self.all_ground_layers, self.all_spawn_layers, self.all_roof_layers, self.all_light_layers = \
            load_all_map_layers(map_filename, base_path=self.map_manager.map_folder)

        if 1 not in self.all_map_layers:
            raise FileNotFoundError(f"Base map file {map_filename} (Layer 1) could not be loaded from {self.map_manager.map_folder}.")

        match = re.search(r'map_L(\d+)_', map_filename)
        layer_index = int(match.group(1)) if match else 1
        
        set_active_layer(self, layer_index)
        return None

    def start_new_game(self, player_data, save_dir_name=None):

        self.is_giant_map = False
        
        # 1. Clear Map & Layer Data
        self.all_map_layers = {}
        self.all_ground_layers = {}
        self.all_spawn_layers = {}
        self.all_roof_layers = {}
        self.all_light_layers = {}
        self.layer_spawn_triggers = {}
        self.triggered_spawns = set()
        
        # 2. Clear Entity & World State (CRITICAL: map_states holds old save data)
        self.map_states = {}  
        self.spawn_point_grid = {}
        self.items_on_ground = []
        self.zombies = []
        self.obstacles = []
        self.containers = []
        self.renderable_tiles = []
        self.map_lights = []
        self.projectiles = []
        self.corpses = []
        self.splashes = []
        self.blood_stains = []
        self.npcs.empty()
        
        # 3. Clear Visual Caches
        if hasattr(self, '_tile_cache_surface'):
            self._tile_cache_surface = None
        self.tiles_dirty = True
        
        # 4. Reset MapManager cache so it doesn't remember old file paths
        if hasattr(self, 'map_manager'):
            self.map_manager.map_files = {}


        if save_dir_name:
            # We are loading an existing game
            save_name = save_dir_name
            regenerate_map = False # Don't overwrite existing map
            should_initial_save = False # Don't save immediately (wait for load_game to finish)
        else:
            # We are starting a brand new game
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"save_{timestamp}"
            regenerate_map = True
            should_initial_save = True
        self.current_save_folder_name = save_name
        
        # 2. Create the specific save directory structure
        # Path: game/save/game/save_YYYYMMDD_HHMMSS/map/
        save_path = os.path.join("game", "save", "game", save_name)
        map_path = os.path.join(save_path, "map")
        
        try:
            os.makedirs(map_path, exist_ok=True)
            self.logger.info(f"Created new save environment at: {map_path}")
        except OSError as e:
            self.logger.info(f"Error creating save directory: {e}")
            # Fallback to default if write fails, though this is critical
            map_path = MAP_DIR 

        # 3. Point the MapManager to this new folder
        # The manager will now look for maps here, not in lib/map
        self.map_manager.map_folder = map_path

        if 'attributes' not in player_data:
            player_data['attributes'] = {} 

        preset = self.player_setup_state.get('selected_config_preset', 'default')
        try:
            self.logger.info(f"Loading config preset: {preset}")
            
            core.data.config.load_settings(preset)


        except Exception as e:
            self.logger.info(f"Error applying custom config '{preset}': {e}")
           

        # 4. Initialize Generator with the specific OUTPUT folder
        gen_building_counts = self.player_setup_state.get('building_counts_config', None)
        gen_chunk_settings = self.player_setup_state.get('chunk_settings_config', None)
        
        generator = ProceduralGenerator(
            self, 
            output_folder=map_path,
            building_counts=gen_building_counts, # Pass the building counts dictionary
            chunk_settings=gen_chunk_settings    # Pass the chunk settings dictionary
        )
        
        if save_dir_name:
             # Loading: Use seed from data or fallback to default
             raw_seed = player_data.get('world_seed', "4-B1TR07")
        else:
             # New Game: Check if user provided a seed in player_data
             # If empty or matches the default placeholder, randomize it
             raw_seed = player_data.get('world_seed')
             if not raw_seed or raw_seed == "4-B1TR07":
                 raw_seed = str(uuid.uuid4())
        
        # Prepend '30' to force 3x3 grid size for the generator
        world_seed = raw_seed
        self.world_seed = world_seed
        self.logger.info(f"Generating world with Seed Pattern: {world_seed}")
        
        # Generate the world directly into the save folder
        start_map = generator.generate_world(seed_pattern=world_seed, regenerate=regenerate_map)

        # 5. Refresh MapManager to see the newly generated files in the save folder
        self.map_manager.refresh_maps()

        if start_map:
            self.map_manager.current_map_filename = start_map
            self.logger.info(f"Starting map set to generated file: {start_map}")
        else:
            self.logger.info("Warning: Generator did not return a start map.")

        self.player_name = player_data.get('name', "Player")
        self.player = Player(player_data=player_data)
        self.zoom_level = core.data.config.START_ZOOM
        
        # ... (Rest of the function remains exactly the same: inventory setup, etc.) ...
        initial_loot = player_data.get('initial_loot', [])
        self.player.inventory = [Item.create_from_name(name) for name in initial_loot if Item.create_from_name(name)]

        # starter_items = ["Mobile off", "Shotgun", "Car Fuel", "Car Key Jeep", "Powerbank"]
        starter_items = ["Mobile off", "M4A1", "556 Ammo", "Car Key Jeep","Car Key Pickup"]
        for name in starter_items:
             try:
                item = Item.create_from_name(name)
                if item and len(self.player.inventory) < self.player.get_total_inventory_slots():
                    if not any(i.name == name for i in self.player.inventory):
                        self.player.inventory.append(item)
             except: pass

        self.zombies_killed = 0
        stat_pos = self.last_modal_positions.get('status', (50, 50))
        inv_pos = self.last_modal_positions.get('inventory', (400, 50))
        nearby_pos = self.last_modal_positions.get('nearby', (1050, 360))
        gear_pos = self.last_modal_positions.get('gear', (830, 10))

        self.modals = [
            {
                'type': 'status', 
                'id': str(uuid.uuid4()), 
                'position': stat_pos,
                'rect': pygame.Rect(stat_pos, (STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)),
                'is_dragging': False,
                'drag_offset': (0, 0),
                'minimized': False
            },
            {
                'type': 'inventory', 
                'id': str(uuid.uuid4()), 
                'position': inv_pos,
                'rect': pygame.Rect(inv_pos, (INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT)),
                'is_dragging': False,
                'drag_offset': (0, 0),
                'minimized': False,
                'active_tab': 'Inventory'
            },
            {
                'type': 'nearby', 
                'id': str(uuid.uuid4()), 
                'position': nearby_pos,
                'rect': pygame.Rect(nearby_pos, (NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)),
                'is_dragging': False,
                'drag_offset': (0, 0),
                'minimized': False,
                'active_tab': 'Ground'
            },
            {
                'type': 'gear', 
                'id': str(uuid.uuid4()), 
                'position': gear_pos,
                'rect': pygame.Rect(gear_pos, (GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)),
                'is_dragging': False,
                'drag_offset': (0, 0),
                'minimized': False
            }
        ]
        self.map_states = {}
        
        self.load_map(self.map_manager.current_map_filename)
        load_giant_map(self)
        
        self.npc_spawn_points = []
        if self.current_layer_index in self.all_spawn_layers:
            spawn_layer = self.all_spawn_layers[self.current_layer_index]
            for y, row in enumerate(spawn_layer):
                for x, char in enumerate(row):
                    if char.strip() == 'NPC':
                        self.npc_spawn_points.append((x * TILE_SIZE, y * TILE_SIZE))
        
        if self.player_spawn:
            self.logger.info(f"Player spawn point found at {self.player_spawn}. Setting player position.")
            self.player.x, self.player.y = self.player_spawn
            self.player.rect.topleft = self.player_spawn
        else:
            self.logger.info("CRITICAL WARNING: No player spawn ('P') found in starting chunk!")
            self.player.x, self.player.y = (10 * TILE_SIZE, 10 * TILE_SIZE)
            self.player.rect.topleft = (10 * TILE_SIZE, 10 * TILE_SIZE)

        # --- FIX: Immediate Zombie Spawn around Player (Populates Start Chunk) ---
        # Fetch spawns from grid that are near the player (5x5 chunks around)
        nearby_spawns = []
        GRID_SIZE_SPAWNS = getattr(self, 'SPAWN_GRID_SIZE', 512)
        p_grid_x = int(self.player.x // GRID_SIZE_SPAWNS)
        p_grid_y = int(self.player.y // GRID_SIZE_SPAWNS)
        
        for i in range(-2, 3): 
            for j in range(-2, 3):
                 cell = (p_grid_x + i, p_grid_y + j)
                 if cell in self.spawn_point_grid:
                     nearby_spawns.extend(self.spawn_point_grid[cell])
                     
        if nearby_spawns:
             # Ensure triggers set exists
             if self.current_layer_index not in self.layer_spawn_triggers:
                 self.layer_spawn_triggers[self.current_layer_index] = set()
             
             # Mark these points as triggered so dynamic spawner doesn't double-count them later
             for pos in nearby_spawns:
                 self.layer_spawn_triggers[self.current_layer_index].add(pos)

             # Spawn them immediately (ignoring min_dist, but respecting SAFE_RADIUS via spawn_initial_zombies)
             initial_zombies = spawn_initial_zombies(
                self.obstacles, 
                nearby_spawns, 
                self.items_on_ground + [self.player],
                limit=1000, 
                spawns_per_marker=core.data.config.ZOMBIES_PER_SPAWN,
                map_width_px=self.map_width_pixels,
                map_height_px=self.map_height_pixels,
                player=self.player, # Pass player for Safe Radius check (15 tiles)
                obstacle_grid=getattr(self, 'cached_obstacle_grid', None)
             )
             self.zombies.extend(initial_zombies)
             self.layer_zombies[self.current_layer_index] = self.zombies[:]
             self.logger.info(f"Initial Start Chunk Population: Spawned {len(initial_zombies)} zombies around player.")

        # --- FIX: Immediate NPC Spawn (Removes Delay) ---
        manage_dynamic_npcs(self)

        self.world_time = WorldTime(self)
        self.game_start_time = pygame.time.get_ticks()

        if should_initial_save:
            if self.current_save_folder_name is None:
                 self.current_save_folder_name = save_name
            self.save_game()



    async def run(self):
        self.logger.info("Entering Main Game Loop")
        try:
            while self.running:
                if self.game_state == 'MENU':
                    self.run_menu()
                elif self.game_state == 'LOAD_GAME_MENU':
                    self.run_load_game_menu()
                elif self.game_state == 'PLAYER_SETUP':
                    self.run_player_setup()
                elif self.game_state == 'LOADING':
                    self.run_loading()
                elif self.game_state == 'PLAYING':
                    self.run_playing()
                elif self.game_state == 'PAUSED':
                    self.run_paused()
                elif self.game_state == 'GAME_OVER':
                    self.run_game_over()
                await asyncio.sleep(0)

        except Exception as e:
            self.logger.crash("CRITICAL GAME CRASH DETECTED", e)
            self.running = False
            raise e
        finally:
            self.logger.info("Game Execution Ended safely.")

    def run_loading(self):
        """
        Handles the loading screen logic.
        1. Renders 'Loading...'
        2. Runs the blocking start_new_game logic
        3. Renders 'Click to start' and waits for input
        """
        mouse_pos = self._get_scaled_mouse_pos()
        
        # Draw the screen
        start_btn = draw_loading_screen(self.virtual_screen, self.loading_done, mouse_pos)
        self._update_screen()
        
        # Logic
        if not self.loading_done:
            # If we have data, start the generation
            # This is a blocking operation, but since we just called _update_screen(), 
            # the "Loading..." text will be visible to the user while this runs.
            # Case 1: New Game
            if self.loading_data:
                self.start_new_game(self.loading_data)
                
                # start_new_game sets state to 'PLAYING', we override it back to stay in loading screen
                self.game_state = 'LOADING'
                self.loading_done = True
                self.loading_data = None # Clear data
            
            # [NEW] Case 2: Loading Saved Game
            elif self.loading_saved_game_folder:
                self.load_game(self.loading_saved_game_folder)
                
                # load_game sets state to 'PLAYING', override it back to wait for user click
                self.game_state = 'LOADING'
                self.loading_done = True
                self.loading_saved_game_folder = None
        else:
            # Loading is done, wait for User click on the button
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if start_btn and start_btn.collidepoint(mouse_pos):
                        self.game_state = 'PLAYING'
                        
    def run_menu(self):
        mouse_pos = self._get_scaled_mouse_pos()
        save_dir = os.path.join("game", "save", "game")
        saves = sorted(glob.glob(os.path.join(save_dir, "save_*"))) if os.path.exists(save_dir) else []
        has_save = len(saves) > 0

        # Unpack the 4 return values (start, load, settings, quit)
        start_btn, load_btn, settings_btn, quit_btn = draw_menu(self.virtual_screen, mouse_pos, has_save)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
                if start_btn.collidepoint(mouse_pos):
                    self.player_setup_state = {} # Reset Setup State so seed clears
                    self.game_state = 'PLAYER_SETUP'
                    # Ensure we start on the player tab if returning from elsewhere
                    self.player_setup_state['current_tab'] = 'Player' 
                    
                elif has_save and load_btn.collidepoint(mouse_pos):
                    self.game_state = 'LOAD_GAME_MENU'
                    if 'save_list' in self.load_game_state:
                         del self.load_game_state['save_list']
                         
                elif settings_btn.collidepoint(mouse_pos):
                    self.game_state = 'PLAYER_SETUP'
                    # Force the state to the Settings tab
                    self.player_setup_state['current_tab'] = 'Settings'
                    
                elif quit_btn.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

    def run_load_game_menu(self):
        """Handles input and drawing for the Load Game screen."""
        mouse_pos = self._get_scaled_mouse_pos()
        
        clickable_rects = draw_load_game_screen(self, self.load_game_state, mouse_pos)
        
        # [NEW] Initialize dragging state if missing
        if 'is_dragging_scrollbar' not in self.load_game_state:
            self.load_game_state['is_dragging_scrollbar'] = False
            self.load_game_state['scroll_drag_start_y'] = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            
            if event.type == pygame.MOUSEWHEEL:
                 scroll_amount = event.y * 35 
                 current_scroll = self.load_game_state.get('scroll_y', 0)
                 max_scroll = self.load_game_state.get('max_scroll', 0)
                 self.load_game_state['scroll_y'] = max(0, min(current_scroll - scroll_amount, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
                # [NEW] Scrollbar Click Logic
                if clickable_rects.get('scrollbar_handle') and clickable_rects['scrollbar_handle'].collidepoint(mouse_pos):
                    self.load_game_state['is_dragging_scrollbar'] = True
                    self.load_game_state['scroll_drag_start_y'] = mouse_pos[1]
                    continue # Skip other clicks if dragging scrollbar

                # Check Save Items
                for index, filename, rect in clickable_rects['save_items']:
                    if rect.collidepoint(mouse_pos):
                        self.load_game_state['selected_save_index'] = index
                        break
                
                if clickable_rects['load_button'] and clickable_rects['load_button'].collidepoint(mouse_pos):
                    idx = self.load_game_state.get('selected_save_index')
                    if idx is not None and idx < len(self.load_game_state['save_list']):
                        save_folder = self.load_game_state['save_list'][idx]['filename']
                        self.load_game(save_folder)

                        self.loading_saved_game_folder = save_folder
                        self.loading_done = False
                        self.game_state = 'LOADING'
                
                elif clickable_rects['delete_button'] and clickable_rects['delete_button'].collidepoint(mouse_pos):
                    idx = self.load_game_state.get('selected_save_index')
                    if idx is not None and idx < len(self.load_game_state['save_list']):
                        filename = self.load_game_state['save_list'][idx]['filename']
                        if delete_save(filename):
                            self.load_game_state['save_list'] = get_save_files()
                            self.load_game_state['selected_save_index'] = None
                
                elif clickable_rects['back_button'] and clickable_rects['back_button'].collidepoint(mouse_pos):
                    self.game_state = 'MENU'

            if event.type == pygame.MOUSEBUTTONUP:
                self.load_game_state['is_dragging_scrollbar'] = False

            if event.type == pygame.MOUSEMOTION:
                if self.load_game_state.get('is_dragging_scrollbar'):
                    mouse_delta_y = mouse_pos[1] - self.load_game_state['scroll_drag_start_y']
                    self.load_game_state['scroll_drag_start_y'] = mouse_pos[1]
                    
                    track_rect = clickable_rects.get('scrollbar_track')
                    handle_rect = clickable_rects.get('scrollbar_handle')
                    max_scroll = self.load_game_state.get('max_scroll', 0)

                    if track_rect and handle_rect and max_scroll > 0:
                        track_height = track_rect.height - handle_rect.height
                        if track_height > 0:
                            scroll_amount = mouse_delta_y * (max_scroll / track_height)
                            self.load_game_state['scroll_y'] = max(0, min(self.load_game_state['scroll_y'] + scroll_amount, max_scroll))

        self._update_screen()

    def run_player_setup(self):
        run_player_setup(self)

    def run_game_over(self):
        mouse_pos = self._get_scaled_mouse_pos()
        menu_button = draw_game_over(self.virtual_screen, self.zombies_killed, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
                if menu_button.collidepoint(mouse_pos):
                    self.game_state = 'MENU'
                    return
        self._update_screen()

    def run_playing(self):
        self.world_time.update()
        handle_input(self)
        update_game_state(self)
        
        # --- NEW: Dynamic NPC Spawning ---
        # Run spawn logic every 30 frames (approx 0.5s) to save performance
        self.npc_spawn_timer += 1
        if self.npc_spawn_timer >= 30:
            manage_dynamic_npcs(self)
            self.npc_spawn_timer = 0
        # ---------------------------------

        for npc in self.npcs:
            npc.update(self)

        self._cleanup_modals()
        draw_game(self)
        self._update_screen()

    def _get_scaled_mouse_pos(self):
        real_mouse_pos = pygame.mouse.get_pos()
        current_w, current_h = self.screen.get_size()
        scale = min(current_w / VIRTUAL_SCREEN_WIDTH, current_h / VIRTUAL_GAME_HEIGHT)
        scaled_w, scaled_h = int(VIRTUAL_SCREEN_WIDTH * scale), int(VIRTUAL_GAME_HEIGHT * scale)
        blit_x = (current_w - scaled_w) // 2
        blit_y = (current_h - scaled_h) // 2
        return ((real_mouse_pos[0] - blit_x) / scale, (real_mouse_pos[1] - blit_y) / scale)

    def get_player_facing_tile(self):
        if not self.player: return None, None
        player_grid_x = self.player.rect.centerx // TILE_SIZE
        player_grid_y = self.player.rect.centery // TILE_SIZE
        facing_x, facing_y = getattr(self.player, 'facing_direction', (0, 1))
        return player_grid_x + facing_x, player_grid_y + facing_y

    def find_interactable_tile(self):
        """Finds a statable tile (door) in front of or near the player."""
        if not self.player: return None

        # 1. Check Facing Tile (Priority)
        facing_x, facing_y = self.get_player_facing_tile()
        if facing_x is not None:
            t = self.map_manager.get_tile_at(facing_x, facing_y)
            if t and t.get('is_statable'):
                 return (facing_x, facing_y)

        # 2. Check Surrounding Tiles (Radius Check)
        # If facing tile isn't valid, check immediate surroundings (3x3 grid)
        player_pos = self.player.rect.center
        p_grid_x = int(player_pos[0] // TILE_SIZE)
        p_grid_y = int(player_pos[1] // TILE_SIZE)
        
        best_tile = None
        best_dist = float('inf')
        
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                tx, ty = p_grid_x + dx, p_grid_y + dy
                t = self.map_manager.get_tile_at(tx, ty)
                
                # Must be statable (e.g. a door)
                if t and t.get('is_statable'):
                     tile_center_x = (tx * TILE_SIZE) + (TILE_SIZE / 2)
                     tile_center_y = (ty * TILE_SIZE) + (TILE_SIZE / 2)
                     dist = math.hypot(player_pos[0] - tile_center_x, player_pos[1] - tile_center_y)
                     
                     # Radius threshold (1.5 tiles covers adjacent and diagonals comfortably)
                     if dist <= TILE_SIZE * 1.5 and dist < best_dist:
                         best_dist = dist
                         best_tile = (tx, ty)
        
        return best_tile    


    def find_nearby_containers(self):
        nearby_containers = []
        for item in self.items_on_ground + self.containers:
            if hasattr(item, 'inventory'):
                dist = math.hypot(self.player.rect.centerx - item.rect.centerx, self.player.rect.centery - item.rect.centery)
                if dist <= TILE_SIZE * 1.5:
                    nearby_containers.append(item)
        return nearby_containers

    def screen_to_world(self, screen_pos):
        screen_x, screen_y = screen_pos
        screen_x -= GAME_OFFSET_X
        relative_screen_x = screen_x - (GAME_WIDTH / 2)
        relative_screen_y = screen_y - (GAME_HEIGHT / 2)

        return (self.player.rect.centerx + self.camera_pan_x + relative_screen_x / self.zoom_level,
                self.player.rect.centery + self.camera_pan_y + relative_screen_y / self.zoom_level)


    def _update_screen(self):
        current_w, current_h = self.screen.get_size()
        scale = min(current_w / VIRTUAL_SCREEN_WIDTH, current_h / VIRTUAL_GAME_HEIGHT)
        scaled_w, scaled_h = int(VIRTUAL_SCREEN_WIDTH * scale), int(VIRTUAL_GAME_HEIGHT * scale)
        scaled_surf = pygame.transform.smoothscale(self.virtual_screen, (scaled_w, scaled_h))
        blit_x = (current_w - scaled_w) // 2
        blit_y = (current_h - scaled_h) // 2
        self.screen.fill(BLACK)
        self.screen.blit(scaled_surf, (blit_x, blit_y))
        pygame.display.flip()
        self.clock.tick(60)

    def update_messages(self):
        pass