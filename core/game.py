import pygame
import asyncio
import uuid
import glob
import os
import math
import threading
import core.data.config
from core.data.config import *
from core.ui.helpers.main_menu import draw_menu
from core.ui.helpers.game_over import draw_game_over
from core.ui.helpers.player_setup import run_player_setup
from core.ui.dropdown import draw_context_menu
from core.ui.assets import load_assets
from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.map.tile_manager import TileManager
from core.map.map_manager import MapManager
from core.sound_manager import SoundManager
from core.ui.helpers.load_game_screen import draw_load_game_screen, get_save_files, delete_save
from core.messages import init_messages
from core.ui.helpers.start_loading import draw_loading_screen
from core.logger import GameLogger
from core.ui.tooltip import draw_tooltip
from core.map.spawn_manager import spawn_initial_zombies, manage_dynamic_npcs, spawn_l2_population
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.systems.quadtree import Quadtree
from core.systems.save_manager import save_game
from core.systems.load_manager import load_game, start_new_game, load_map
from core.systems.utils import (
    capture_pause_screen, get_scaled_mouse_pos, find_interactable_tile, 
    find_nearby_containers, screen_to_world, get_player_facing_tile
)
from core.entities.animal.animal import Animal
from core.data.localization import load_language, tr

class Game:
    def __init__(self):
        os.environ['SDL_RENDER_SCALE_QUALITY'] = '1'
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        
        initial_w = int(GAME_WIDTH)
        initial_h = int(GAME_HEIGHT)
        
        self.game_screen = pygame.display.set_mode((initial_w, initial_h), pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF, vsync=1)
        
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

        load_language(core.data.config.GAME_LANGUAGE)

        self.clock = pygame.time.Clock()
        self.dt_ms = 16 # Default to 16ms for the very first frame
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

        # [OPTIMIZATION] Spatial Grids & Active Lists
        self.active_zombies = []
        self.active_npcs = []
        self.visible_items = []
        self.visible_containers = []

        self.zombie_grid = {}
        self.item_grid = {}
        self.container_grid = {}
        # [OPTIMIZATION] Dynamic grid cell size based on chunk size
        # Larger chunks = larger grid cells to reduce bucket count
        # Formula: 3x chunk tile size (in pixels), clamped between 512-2048
        self.GRID_CELL_SIZE = max(512, min(2048, c_size * t_size * 3))

        # [OPTIMIZATION] Movement-based grid rebuild tracking
        self.last_zombie_grid_positions = {}  # Track zombie positions for movement detection
        self.last_item_grid_positions = {}
        self.last_container_grid_positions = {}
        self.GRID_REBUILD_THRESHOLD = self.GRID_CELL_SIZE // 4  # Rebuild if entity moves 1/4 cell

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

        self.last_modal_positions = {
            'status': (65, 10),
            'inventory': (970, 10),
            'gear': (650, 10),
            'container': (GAME_WIDTH / 2 - 150, GAME_HEIGHT / 2 - 150),
            'nearby': (970, 360),
            'messages': (10, 390),
            'text': (GAME_WIDTH / 2 - 200, GAME_HEIGHT / 2 - 150),
            'mobile': (GAME_WIDTH / 2 - 125, GAME_HEIGHT / 2 - 200),
            'crafting': (300, 100),
            'help': (GAME_WIDTH / 2 - HELP_MODAL_WIDTH / 2, GAME_HEIGHT / 2 - HELP_MODAL_HEIGHT / 2)
        }

        if UI_SHOW_TUTORIAL_DEFAULT:
            help_pos = self.last_modal_positions['help']
            self.modals.append({
                'type': 'help',
                'rect': pygame.Rect(help_pos[0], help_pos[1], HELP_MODAL_WIDTH, HELP_MODAL_HEIGHT),
                'minimized': False
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
        self.forward_button_rect = None
        self.status_button_rect = None
        self.inventory_button_rect = None
        self.nearby_button_rect = None
        self.messages_button_rect = None
        self.crafting_button_rect = None
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

        self.player_view_radius = BASE_PLAYER_VIEW_RADIUS
        self.sound_manager = SoundManager()
        
        if core.data.config.UI_BACKGROUND_MUSIC:
            self.sound_manager.play_music('game/lib/sfx/ui/music.ogg', volume=1.0)

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
        
        self.is_fast_forwarding = False
        self.fast_forward_speed = 50.0

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
        
        # Reset spatial grids on map load
        self.zombie_grid = {}
        self.item_grid = {}
        self.container_grid = {}
        self.rebuild_zombie_grid()
        self.rebuild_item_grid()
        self.rebuild_container_grid()

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

            elif modal['type'] == 'container':
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
                        if self.player.backpack: equipped_roots.append(self.player.backpack)
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

    def run_paused(self):
        # Create a darker overlay
        overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.game_screen.blit(overlay, (0, 0))

        # --- FIX: Translated Pause Text ---
        text = font_14.render(tr('ui', "GAME PAUSED"), True, WHITE)
        text_rect = text.get_rect(center=(GAME_WIDTH // 2, GAME_HEIGHT // 3))
        self.game_screen.blit(text, text_rect)

        mouse_pos = self._get_scaled_mouse_pos()
        
        btn_w = 200
        btn_h = 50
        btn_continue = pygame.Rect(GAME_WIDTH // 2 - btn_w // 2, GAME_HEIGHT // 2, btn_w, btn_h)
        btn_save = pygame.Rect(GAME_WIDTH // 2 - btn_w // 2, GAME_HEIGHT // 2 + 70, btn_w, btn_h)
        btn_quit = pygame.Rect(GAME_WIDTH // 2 - btn_w // 2, GAME_HEIGHT // 2 + 140, btn_w, btn_h)

        def draw_btn(surface, rect, text, mouse_pos):
            is_hovered = rect.collidepoint(mouse_pos)
            bg_color = (80, 80, 80) if is_hovered else (60, 60, 60)
            pygame.draw.rect(surface, bg_color, rect, border_radius=6)
            txt_surf = font_14.render(text, True, WHITE)
            txt_rect = txt_surf.get_rect(center=rect.center)
            surface.blit(txt_surf, txt_rect)

        # --- FIX: Translated Buttons ---
        draw_btn(self.game_screen, btn_continue, tr('ui', "Continue"), mouse_pos)
        draw_btn(self.game_screen, btn_save, tr('ui', "Save Game"), mouse_pos)
        draw_btn(self.game_screen, btn_quit, tr('ui', "Quit"), mouse_pos)

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
                    # --- NEW: Stop ambient sounds when quitting to menu ---
                    if hasattr(self, 'world_time') and self.world_time:
                        self.world_time.stop_all_sounds()
                    self.game_state = 'MENU'

        self._update_screen()

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
        # 1. Fetch ALL events once at the very beginning of the frame
        events = pygame.event.get()
        
        mouse_pos = self._get_scaled_mouse_pos()
        
        # FIX: Check for QUIT globally so the window can be closed even while loading
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return
        
        # 2. Pass the events into the draw function so it can read the scroll wheel
        start_btn = draw_loading_screen(self.game_screen, self.loading_done, mouse_pos, events)
        self._update_screen()
        
        if not self.loading_done:
            # FIX: Use a background thread to prevent blocking the Pygame Event Loop
            if not hasattr(self, '_loading_thread'):
                
                if self.loading_data:
                    self._loading_thread = threading.Thread(target=self.start_new_game, args=(self.loading_data,), daemon=True)
                    self._loading_thread.start()
                elif self.loading_saved_game_folder:
                    self._loading_thread = threading.Thread(target=self.load_game, args=(self.loading_saved_game_folder,), daemon=True)
                    self._loading_thread.start()
            else:
                # If the thread exists, check if it has finished its job
                if not self._loading_thread.is_alive():
                    self.loading_done = True
                    del self._loading_thread # Cleanup
                    self.loading_data = None 
                    self.loading_saved_game_folder = None
        else:
            # 3. Use the same 'events' list we already fetched! 
            # Do NOT call pygame.event.get() again here.
            for event in events:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if start_btn and start_btn.collidepoint(mouse_pos):
                        self.game_state = 'PLAYING'
                        
    def run_menu(self):
        mouse_pos = self._get_scaled_mouse_pos()
        save_dir = os.path.join("game", "save", "game")
        saves = sorted(glob.glob(os.path.join(save_dir, "save_*"))) if os.path.exists(save_dir) else []
        has_save = len(saves) > 0

        start_btn, load_btn, settings_btn, quit_btn, flag_rects = draw_menu(self.game_screen, mouse_pos, has_save)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()

                flag_clicked = False
                for flag_info in flag_rects:
                    if flag_info['rect'].collidepoint(mouse_pos):
                        lang_code = flag_info['name']
                        
                        # Save it using your existing config tool
                        core.data.config.save_language_to_config(lang_code)
                        
                        # Hot-reload the texts immediately
                        core.data.localization.load_language(lang_code)
                        
                        flag_clicked = True
                        break
                
                if flag_clicked:
                    continue
                
                if start_btn.collidepoint(mouse_pos):
                    self.player_setup_state = {} 
                    self.game_state = 'PLAYER_SETUP'
                    self.player_setup_state['current_tab'] = 'Player' 
                    
                elif has_save and load_btn.collidepoint(mouse_pos):
                    self.game_state = 'LOAD_GAME_MENU'
                    if 'save_list' in self.load_game_state:
                         del self.load_game_state['save_list']
                         
                elif settings_btn.collidepoint(mouse_pos):
                    self.game_state = 'PLAYER_SETUP'
                    self.player_setup_state['current_tab'] = 'Settings'
                    
                elif quit_btn.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

    def run_load_game_menu(self):
        mouse_pos = self._get_scaled_mouse_pos()
        clickable_rects = draw_load_game_screen(self, self.load_game_state, mouse_pos)
        
        if 'is_dragging_scrollbar' not in self.load_game_state:
            self.load_game_state['is_dragging_scrollbar'] = False
            self.load_game_state['scroll_drag_start_y'] = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            
            if event.type == pygame.MOUSEWHEEL:
                 scroll_amount = event.y * 35 
                 current_scroll = self.load_game_state.get('scroll_y', 0)
                 max_scroll = self.load_game_state.get('max_scroll', 0)
                 self.load_game_state['scroll_y'] = max(0, min(current_scroll - scroll_amount, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
                if clickable_rects.get('scrollbar_handle') and clickable_rects['scrollbar_handle'].collidepoint(mouse_pos):
                    self.load_game_state['is_dragging_scrollbar'] = True
                    self.load_game_state['scroll_drag_start_y'] = mouse_pos[1]
                    continue 

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
        # --- NEW: Stop ambient sounds when on Game Over screen ---
        if hasattr(self, 'world_time') and self.world_time:
            self.world_time.stop_all_sounds()
        
        if getattr(self, 'current_save_folder_name', None):
            try:
                delete_save(self.current_save_folder_name)
                self.logger.info(f"Permadeath: Deleted save folder '{self.current_save_folder_name}' due to player death.")
            except Exception as e:
                self.logger.info(f"Permadeath deletion failed: {e}")
            
            # Set to None so it only triggers once while the Game Over screen is running
            self.current_save_folder_name = None
            
        pygame.mouse.set_visible(True)
        mouse_pos = self._get_scaled_mouse_pos()
        menu_button = draw_game_over(self.game_screen, self.zombies_killed, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
                if menu_button.collidepoint(mouse_pos):
                    self.game_state = 'MENU'
                    return
        self._update_screen()

    # [NEW] Grid Rebuild Methods with Movement Detection
    def _check_significant_movement(self, entity, tracked_dict, entity_id):
        """Check if an entity has moved significantly since last grid rebuild."""
        current_pos = (entity.rect.centerx, entity.rect.centery)
        if entity_id not in tracked_dict:
            tracked_dict[entity_id] = current_pos
            return True
        
        last_pos = tracked_dict[entity_id]
        dx = current_pos[0] - last_pos[0]
        dy = current_pos[1] - last_pos[1]
        dist_sq = dx*dx + dy*dy
        
        if dist_sq > self.GRID_REBUILD_THRESHOLD ** 2:
            tracked_dict[entity_id] = current_pos
            return True
        return False

    def rebuild_zombie_grid(self):
        """Rebuild zombie grid only if significant movement detected."""
        

        # Count current zombies and animals
        current_zombie_count = len(self.zombies)
        current_animal_count = sum(1 for item in self.items_on_ground if isinstance(item, Animal))
        current_total = current_zombie_count + current_animal_count

        # Check if count changed (new spawns or deaths)
        tracked_total = len(self.last_zombie_grid_positions)
        if current_total != tracked_total:
            # Count changed - force rebuild
            pass
        else:
            # Count same - check for significant movement
            needs_rebuild = False

            # Check if any zombie moved significantly
            for z in self.zombies:
                z_id = id(z)
                if self._check_significant_movement(z, self.last_zombie_grid_positions, z_id):
                    needs_rebuild = True
                    break

            # Also check animals (they're in items_on_ground but tracked as zombies for AI)
            if not needs_rebuild:
                for item in self.items_on_ground:
                    if isinstance(item, Animal):
                        a_id = id(item)
                        if self._check_significant_movement(item, self.last_zombie_grid_positions, a_id):
                            needs_rebuild = True
                            break

            if not needs_rebuild:
                return  # Skip rebuild - no significant movement

        # Cleanup removed zombies and animals from tracking
        zombie_ids = {id(z) for z in self.zombies}
        animal_ids = {id(item) for item in self.items_on_ground if isinstance(item, Animal)}
        valid_ids = zombie_ids | animal_ids
        for z_id in list(self.last_zombie_grid_positions.keys()):
            if z_id not in valid_ids:
                del self.last_zombie_grid_positions[z_id]

        self.zombie_grid.clear()
        # Add zombies
        for z in self.zombies:
            key = (int(z.rect.centerx // self.GRID_CELL_SIZE), int(z.rect.centery // self.GRID_CELL_SIZE))
            if key not in self.zombie_grid: self.zombie_grid[key] = []
            self.zombie_grid[key].append(z)

        # Add animals (they use zombie AI for wandering)
        for item in self.items_on_ground:
            if isinstance(item, Animal):
                key = (int(item.rect.centerx // self.GRID_CELL_SIZE), int(item.rect.centery // self.GRID_CELL_SIZE))
                if key not in self.zombie_grid: self.zombie_grid[key] = []
                self.zombie_grid[key].append(item)

    def rebuild_item_grid(self, force=False):
        """Rebuild item grid only if items changed or moved significantly."""
        # Items on ground are mostly static, rebuild only on count change or periodic check
        if not hasattr(self, '_last_item_count'):
            self._last_item_count = 0
        
        # Force rebuild if count changed or every 60 frames
        if len(self.items_on_ground) != self._last_item_count:
            self._last_item_count = len(self.items_on_ground)
            force = True
        
        if not force and self.frame_count % 60 != 0:
            return  # Skip rebuild - no new items
        
        self.item_grid.clear()
        for i in self.items_on_ground:
            key = (int(i.rect.centerx // self.GRID_CELL_SIZE), int(i.rect.centery // self.GRID_CELL_SIZE))
            if key not in self.item_grid: self.item_grid[key] = []
            self.item_grid[key].append(i)

    def rebuild_container_grid(self):
        """Rebuild container grid only if containers changed or moved significantly."""
        if not hasattr(self, '_last_container_count'):
            self._last_container_count = 0
        
        if len(self.containers) == self._last_container_count and self.frame_count % 60 != 0:
            return  # Skip rebuild
        
        self._last_container_count = len(self.containers)
        self.container_grid.clear()
        for c in self.containers:
            key = (int(c.rect.centerx // self.GRID_CELL_SIZE), int(c.rect.centery // self.GRID_CELL_SIZE))
            if key not in self.container_grid: self.container_grid[key] = []
            self.container_grid[key].append(c)

    def run_playing(self):
        self.world_time.update()
        handle_input(self)
        self.frame_count += 1

        # [OPTIMIZATION] Movement-based Grid Updates (no fixed intervals)
        # Grids rebuild only when entities move significantly
        self.rebuild_zombie_grid()
        
        # Static grids rebuild less frequently (items/containers are mostly static)
        if self.frame_count % 60 == 0:
            self.rebuild_item_grid()
            self.rebuild_container_grid()

        # [OPTIMIZATION] Dynamic simulation distance based on performance
        # Scale distance down if too many entities, up if few
        px, py = self.player.rect.center
        
        # Base simulation distances (in pixels)
        BASE_SIMULATION_DISTANCE = 800
        MAX_ACTIVE_ENTITIES_TARGET = 150
        
        # Count current entities to adjust simulation distance dynamically
        total_nearby_entities = len(getattr(self, 'active_zombies', []))
        
        # Adjust simulation distance based on entity count
        if total_nearby_entities > MAX_ACTIVE_ENTITIES_TARGET:
            SIMULATION_DISTANCE = BASE_SIMULATION_DISTANCE * 0.75  # Reduce by 25%
        elif total_nearby_entities < MAX_ACTIVE_ENTITIES_TARGET * 0.5:
            SIMULATION_DISTANCE = min(1200, BASE_SIMULATION_DISTANCE * 1.25)  # Increase by 25%, max 1200
        else:
            SIMULATION_DISTANCE = BASE_SIMULATION_DISTANCE
        
        # [OPTIMIZATION] Calculate Active Sets using Spatial Grid
        start_grid_x = int((px - SIMULATION_DISTANCE) // self.GRID_CELL_SIZE)
        end_grid_x = int((px + SIMULATION_DISTANCE) // self.GRID_CELL_SIZE) + 1
        start_grid_y = int((py - SIMULATION_DISTANCE) // self.GRID_CELL_SIZE)
        end_grid_y = int((py + SIMULATION_DISTANCE) // self.GRID_CELL_SIZE) + 1

        self.active_zombies = []
        self.visible_items = []
        self.visible_containers = []
        self.active_animals = []

        for gy in range(start_grid_y, end_grid_y):
            for gx in range(start_grid_x, end_grid_x):
                key = (gx, gy)
                if key in self.zombie_grid:
                    self.active_zombies.extend(self.zombie_grid[key])
                if key in self.item_grid:
                    self.visible_items.extend(self.item_grid[key])
                if key in self.container_grid:
                    self.visible_containers.extend(self.container_grid[key])

        # Filter out animals from active_zombies and collect them separately
        
        self.active_animals = [z for z in self.active_zombies if isinstance(z, Animal)]
        self.active_zombies = [z for z in self.active_zombies if not isinstance(z, Animal)]

        # Also get animals from visible_items (for loaded games)
        for item in self.visible_items:
            if isinstance(item, Animal) and item not in self.active_animals:
                self.active_animals.append(item)

        # [OPTIMIZATION] Hard caps on active entities to maintain FPS on large maps
        MAX_ACTIVE_ZOMBIES = 100
        MAX_ACTIVE_ANIMALS = 30
        
        if len(self.active_zombies) > MAX_ACTIVE_ZOMBIES:
            # Sort by distance and keep closest
            self.active_zombies.sort(key=lambda z: (z.rect.centerx - px)**2 + (z.rect.centery - py)**2)
            self.active_zombies = self.active_zombies[:MAX_ACTIVE_ZOMBIES]
        
        if len(self.active_animals) > MAX_ACTIVE_ANIMALS:
            self.active_animals.sort(key=lambda a: (a.rect.centerx - px)**2 + (a.rect.centery - py)**2)
            self.active_animals = self.active_animals[:MAX_ACTIVE_ANIMALS]

        # Active NPCs (small count, can iterate)
        self.active_npcs = [n for n in self.npcs if abs(n.rect.centerx - px) < SIMULATION_DISTANCE and abs(n.rect.centery - py) < SIMULATION_DISTANCE]
        
        # [OPTIMIZATION] Cap active NPCs
        MAX_ACTIVE_NPCS = 10
        if len(self.active_npcs) > MAX_ACTIVE_NPCS:
            self.active_npcs.sort(key=lambda n: (n.rect.centerx - px)**2 + (n.rect.centery - py)**2)
            self.active_npcs = self.active_npcs[:MAX_ACTIVE_NPCS]

        # [OPTIMIZATION] Quadtree Dirty Flag - Only rebuild if entities moved significantly
        quadtree_needs_rebuild = False

        # Check if player moved significantly (more than 64 pixels)
        if hasattr(self, 'last_quadtree_player_pos'):
            dx = px - self.last_quadtree_player_pos[0]
            dy = py - self.last_quadtree_player_pos[1]
            if dx*dx + dy*dy > 4096:  # 64^2 (increased threshold)
                quadtree_needs_rebuild = True
        else:
            quadtree_needs_rebuild = True

        # Check if projectiles changed
        if hasattr(self, 'last_quadtree_projectile_count'):
            if len(self.projectiles) != self.last_quadtree_projectile_count:
                quadtree_needs_rebuild = True
        else:
            quadtree_needs_rebuild = True

        # Check frame count for periodic rebuild (every 30 frames - reduced frequency)
        if self.frame_count % 30 == 0:
            quadtree_needs_rebuild = True
        
        if quadtree_needs_rebuild:
            # Store state for next frame comparison
            self.last_quadtree_player_pos = (px, py)
            self.last_quadtree_projectile_count = len(self.projectiles)
            
            # Populate Quadtree with ONLY active entities
            self.quadtree.clear()
            for z in self.active_zombies: self.quadtree.insert(z)
            # Add animals to quadtree
            for a in self.active_animals:
                self.quadtree.insert(a)
            for n in self.active_npcs: self.quadtree.insert(n)
            for p in self.projectiles: self.quadtree.insert(p)

            if self.map_manager and hasattr(self.map_manager, 'vehicles'):
                 for v in self.map_manager.vehicles:
                     if abs(v.rect.centerx - px) < SIMULATION_DISTANCE and abs(v.rect.centery - py) < SIMULATION_DISTANCE:
                        self.quadtree.insert(v)

        update_game_state(self)
        
        if self.player:
            base_radius = core.data.config.BASE_PLAYER_VIEW_RADIUS
            radius_mult = 1.0

            for trait_id in self.player.traits:
                t_def = TRAIT_DEFINITIONS.get(trait_id)
                if t_def and 'config_modifiers' in t_def:
                    mod = t_def['config_modifiers'].get('BASE_PLAYER_VIEW_RADIUS')
                    if mod is not None:
                        radius_mult *= mod

            self.player_view_radius = base_radius * radius_mult
        
        self.npc_spawn_timer += 1
        if self.npc_spawn_timer >= 30:
            manage_dynamic_npcs(self)
            self.npc_spawn_timer = 0

        # [OPTIMIZATION] Only update NPCs within reasonable distance with LOD
        player_pos = self.player.rect.center if self.player else None
        NPC_UPDATE_RADIUS_SQ = (NPC_DETECTION_RADIUS + 300) ** 2
        npcs_updated = 0
        MAX_NPCS_PER_FRAME = 8
        
        for npc in self.active_npcs:
            if player_pos:
                dx = npc.rect.centerx - player_pos[0]
                dy = npc.rect.centery - player_pos[1]
                dist_sq = dx*dx + dy*dy
                
                # Skip distant NPCs unless they're chasing
                if dist_sq > NPC_UPDATE_RADIUS_SQ and npc.state != 'chasing':
                    continue
                
                # [OPTIMIZATION] LOD-based update frequency for NPCs
                if dist_sq > 400**2 and npc.state != 'chasing':
                    # Update every 2nd frame for medium distance
                    if dist_sq <= 800**2 and self.frame_count % 2 != 0:
                        continue
                    # Update every 4th frame for far distance
                    elif dist_sq > 800**2 and self.frame_count % 4 != 0:
                        continue
            
            # [OPTIMIZATION] Limit NPCs updated per frame
            npcs_updated += 1
            if npcs_updated > MAX_NPCS_PER_FRAME:
                break
                
            npc.update(self)

        self._cleanup_modals()
        
        self.map_manager.reset_frame_metrics()
        if self.player:
             self.map_manager.update_chunks(self.player.rect.center)
        
        draw_game(self)

        if self.hovered_item:
            mouse_pos = self._get_scaled_mouse_pos()
            draw_tooltip(self.game_screen, self.hovered_item, mouse_pos)

        if self.context_menu['active']:
            draw_context_menu(self.game_screen, self.context_menu, self._get_scaled_mouse_pos())

        self._update_screen()

    def _update_screen(self):
        pygame.display.flip()
        self.dt_ms = self.clock.tick(0) 
        
        # Calculate the multiplier based on your 60 FPS tuning
        # Limits the multiplier to prevent huge physics jumps during lag spikes
        if self.dt_ms > 100: 
            self.dt_ms = 100 
            
        self.dt_mult = (self.dt_ms / 1000.0) * 60.0

    def update_messages(self):
        pass