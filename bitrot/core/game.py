import pygame
import asyncio
import os
import math
import core.data.config
from core.data.config import *
from core.ui.assets import load_assets
from core.map.tile_manager import TileManager
from core.map.map_manager import MapManager
from core.sound_manager import SoundManager
from core.messages import init_messages
from core.logger import GameLogger
from core.systems.quadtree import Quadtree
from core.systems.save_manager import save_game
from core.systems.load_manager import load_game, start_new_game, load_map
from core.systems.utils import (
    capture_pause_screen, get_scaled_mouse_pos, find_interactable_tile, 
    find_nearby_containers, screen_to_world, get_player_facing_tile
)
from core.data.localization import load_language
from core.map.world_time import WorldTime
from core.events.joystick import JoystickHandler
from core.ui.helpers.player_setup import run_player_setup

# The newly refactored systems
from core.systems.spatial_manager import SpatialManager
from core.states.menu import run_menu
from core.states.load_game_menu import run_load_game_menu
from core.states.loading import run_loading
from core.states.playing import run_playing
from core.states.paused import run_paused
from core.states.game_over import run_game_over

class Game:
    def __init__(self):
        os.environ['SDL_RENDER_SCALE_QUALITY'] = '0'
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()

        display_flags = pygame.SCALED | pygame.DOUBLEBUF
        if WINDOW_MODE.lower() == "fullscreen":
            display_flags |= pygame.FULLSCREEN
        else:
            display_flags |= pygame.RESIZABLE
        
        self.game_screen = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT), display_flags)
        pygame.display.set_caption("Bit Rot - v." + GAME_VERSION)
        icon_image = pygame.image.load(os.path.join(BASE_DIR, "data.rot", "icons", "favicon.png")).convert_alpha()
        pygame.display.set_icon(icon_image)
        
        self.logger = GameLogger()
        self.logger.info("Bit Rot - Developed by Gustavo Kuklinski")
        self.logger.info("Initializing Rot Engine...")
        
        self.joystick_handler = JoystickHandler(logger=self.logger)
        self.logger.info("PC detected: Hardware Joystick enabled.")

        try:
            cursor_surface = pygame.image.load(SPRITE_PATH + 'ui/cursor.png').convert_alpha()
            custom_cursor = pygame.cursors.Cursor((0, 0), cursor_surface)
            pygame.mouse.set_cursor(custom_cursor)
        except Exception as e:
            print(f"Could not load custom cursor: {e}")

        init_messages(self)
        load_language(core.data.config.GAME_LANGUAGE)

        self.clock = pygame.time.Clock()
        self.dt_ms = 16 
        self.dt_mult = 1.0
        self.assets = load_assets()
        self.game_state = 'MENU'
        self.running = True
        
        self.CHUNK_SIZE = CHUNK_SIZE if 'CHUNK_SIZE' in globals() else 128

        self.map_manager = MapManager(self)
        self.tile_manager = TileManager()
        
        c_size = getattr(core.data.config, 'CHUNK_SIZE', 128)
        m_chunks = getattr(core.data.config, 'MAP_CHUNKS', 3) 
        t_size = getattr(core.data.config, 'TILE_SIZE', 16)
        
        total_world_size = m_chunks * c_size * t_size
        self.quadtree = Quadtree(pygame.Rect(0, 0, total_world_size, total_world_size))

        self.player = None
        self.zombies = []
        self.items_on_ground = []

        self.active_zombies = []
        self.active_npcs = []
        self.visible_items = []
        self.visible_containers = []

        self.zombie_grid = {}
        self.item_grid = {}
        self.container_grid = {}
        
        self.GRID_CELL_SIZE = max(512, min(2048, c_size * t_size * 3))
        self.last_zombie_grid_positions = {}  
        self.last_item_grid_positions = {}
        self.last_container_grid_positions = {}
        self.GRID_REBUILD_THRESHOLD = self.GRID_CELL_SIZE // 4  

        # Initializes the spatial logic that used to live in here
        self.spatial_manager = SpatialManager(self)

        self.frame_count = 0
        self.npcs = pygame.sprite.Group()
        self.npc_spawn_timer = 0 

        self.projectiles = []
        self.obstacles = []
        self.renderable_tiles = []
        self.containers = []
        self.corpses = []
        self.splashes = []
        self.blood_stains = []
        self.rain_particles = []
        self.map_lights = [] 
        self.all_light_layers = {} 
        self.light_data = []
        self.zombies_killed = 0

        self.modals = []
        self.saved_modals = [] 

        right_panel_x = GAME_WIDTH - 244
        messages_panel_y = GAME_HEIGHT - 244
        
        self.last_modal_positions = {
            'gear': (GAME_WIDTH - GEAR_MODAL_WIDTH, 0),
            'inventory': (GAME_WIDTH - INVENTORY_MODAL_WIDTH, GEAR_MODAL_HEIGHT),
            'nearby': (GAME_WIDTH - NEARBY_MODAL_WIDTH, GEAR_MODAL_HEIGHT + INVENTORY_MODAL_HEIGHT),
            'messages': (0, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT),
            'status': (0, 0),
            'slots': (MESSAGES_MODAL_WIDTH + STATUS_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
            'container': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
            'text': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
            'mobile': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - SLOTS_MODAL_HEIGHT),
            'vehicle': (MESSAGES_MODAL_WIDTH, GAME_HEIGHT - MESSAGES_MODAL_HEIGHT),
            'crafting': (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2),
            'help': (GAME_WIDTH / 2 - CRAFTING_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - CRAFTING_MODAL_HEIGHT / 2),
        }
        if UI_SHOW_TUTORIAL_DEFAULT:
            help_pos = self.last_modal_positions['help']
            self.modals.append({
                'type': 'help',
                'rect': pygame.Rect(help_pos[0], help_pos[1], HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT)
            })

        self.modals.append({
            'type': 'belt',
            'rect': pygame.Rect(GAME_WIDTH // 2 - 150, GAME_HEIGHT - 60, 300, 60),
            'id': 'belt_hud' 
        })

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

        self.pause_button_rect = None
        self.status_button_rect = None
        self.inventory_button_rect = None
        self.nearby_button_rect = None
        self.messages_button_rect = None
        self.crafting_button_rect = None
        self.slots_button_rect = None
        self.help_button_rect = None
        self.gear_button_rect = None
        self.camera = None
        self.map_states = {}
        self.layer_items = {}
        self.layer_zombies = {}
        self.player_name = ""
        self.name_input_active = False

        self.hovered_item = None
        self.hovered_container = None
        self.hovered_npc = None
        self.hovered_interactable_tile_rect = None

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

        self.player_view_radius = BASE_PLAYER_VIEW_RADIUS
        self.sound_manager = SoundManager()
        
        if core.data.config.UI_BACKGROUND_MUSIC:
            self.sound_manager.play_music('data.rot/lib/sfx/ui/music.ogg', volume=core.data.config.VOLUME_MUSIC)

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
        
        self.world_time = WorldTime(self)

        self.viewport_left_offset = 0
        self.dynamic_w = GAME_WIDTH
        self.dynamic_h = GAME_HEIGHT

    def get_events(self):
        return pygame.event.get()

    def save_game(self):
        return save_game(self)

    def load_game(self, save_folder_name):
        return load_game(self, save_folder_name)

    def start_new_game(self, player_data, save_dir_name=None):
        return start_new_game(self, player_data, save_dir_name)

    def load_map(self, map_filename):
        result = load_map(self, map_filename)
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

    def capture_pause_screen(self):
        capture_pause_screen(self)

    def _get_scaled_mouse_pos(self):
        return get_scaled_mouse_pos(self)

    def get_player_facing_tile(self):
        return get_player_facing_tile(self)

    def find_interactable_tile(self):
        return find_interactable_tile(self)

    def find_nearby_containers(self):
        return find_nearby_containers(self)

    def screen_to_world(self, screen_pos):
        return screen_to_world(self, screen_pos)

    def _cleanup_modals(self):
        modals_to_remove = []
        if not self.player: return

        def is_item_in_inventory(target, inventory):
            if not inventory: return False
            if target in inventory: return True
            for item in inventory:
                if hasattr(item, 'inventory') and item.inventory:
                    if is_item_in_inventory(target, item.inventory):
                        return True
            return False

        for modal in self.modals:
            MAX_DISTANCE = TILE_SIZE * 2 

            if modal['type'] == 'vehicle':
                vehicle = modal['vehicle']
                dist = math.hypot(self.player.rect.centerx - vehicle.rect.centerx, self.player.rect.centery - vehicle.rect.centery)
                if dist > MAX_DISTANCE: 
                    modals_to_remove.append(modal)

            elif modal['type'] == 'npc_dialog':
                npc = modal['npc']
                dist = math.hypot(self.player.rect.centerx - npc.rect.centerx, self.player.rect.centery - npc.rect.centery)
                if npc.is_dead or dist > MAX_DISTANCE:
                    modals_to_remove.append(modal)

            elif modal['type'] in ('container', 'text', 'big_map', 'mobile'):
                container_item = modal.get('item')
                if container_item:
                    is_equipped = False
                    if is_item_in_inventory(container_item, self.player.inventory):
                        is_equipped = True
                    if not is_equipped:
                        belt_items = [i for i in self.player.belt if i]
                        if is_item_in_inventory(container_item, belt_items):
                            is_equipped = True
                    if not is_equipped:
                        equipped_roots = []
                        if self.player.clothes: 
                            equipped_roots.extend([c for c in self.player.clothes.values() if c])
                        for item in equipped_roots:
                            if item == container_item:
                                is_equipped = True
                                break
                            if hasattr(item, 'inventory') and is_item_in_inventory(container_item, item.inventory):
                                is_equipped = True
                                break

                    if is_equipped: continue 

                    world_root = None
                    if hasattr(container_item, 'rect') and (container_item in self.items_on_ground or container_item in self.containers):
                        world_root = container_item
                    
                    if not world_root:
                        potential_roots = self.items_on_ground + self.containers + self.zombies + self.npcs.sprites()
                        for root in potential_roots:
                            if hasattr(root, 'inventory') and is_item_in_inventory(container_item, root.inventory):
                                world_root = root
                                break
                    
                    if world_root and hasattr(world_root, 'rect'):
                        dist = math.hypot(self.player.rect.centerx - world_root.rect.centerx, 
                                        self.player.rect.centery - world_root.rect.centery)
                        if dist > MAX_DISTANCE:
                            modals_to_remove.append(modal)
                    else:
                        if hasattr(container_item, 'name') and container_item.name != "Ground":
                            modals_to_remove.append(modal)
            
        for modal in modals_to_remove:
            self.modals.remove(modal)

    def run_player_setup(self):
        run_player_setup(self)

    async def run(self):
        self.logger.info("Entering Main Game Loop")
        try:
            while self.running:
                if getattr(self, 'joystick_handler', None):
                    self.joystick_handler.update_cursor(self)

                # The State Machine Dispatcher
                if self.game_state == 'MENU':
                    run_menu(self)
                elif self.game_state == 'LOAD_GAME_MENU':
                    run_load_game_menu(self)
                elif self.game_state == 'PLAYER_SETUP':
                    self.run_player_setup()
                elif self.game_state == 'LOADING':
                    run_loading(self)
                elif self.game_state == 'PLAYING':
                    run_playing(self)
                elif self.game_state == 'PAUSED':
                    run_paused(self)
                elif self.game_state == 'GAME_OVER':
                    run_game_over(self)
                await asyncio.sleep(0)

        except Exception as e:
            self.logger.crash("CRITICAL GAME CRASH DETECTED", e)
            self.running = False
            raise e
        finally:
            self.logger.info("Game Execution Ended safely.")

    def _update_screen(self):
        pygame.display.flip()
        self.dt_ms = self.clock.tick(60)
        if self.dt_ms > 100: 
            self.dt_ms = 100 
        self.dt_mult = (self.dt_ms / 1000.0) * 60.0