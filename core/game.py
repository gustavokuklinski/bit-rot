import pygame
import asyncio
import uuid
import glob
import os
import math
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
# [NEW] Import traits definitions
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS

# Imported Systems
from core.systems.save_manager import save_game
from core.systems.load_manager import load_game, start_new_game, load_map
from core.systems.utils import (
    capture_pause_screen, get_scaled_mouse_pos, find_interactable_tile, 
    find_nearby_containers, screen_to_world, get_player_facing_tile
)

# ... (Game class definition remains the same until run_playing) ...
class Game:
    # ... (init and other methods unchanged) ...
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        
        initial_w = int(GAME_WIDTH)
        initial_h = int(GAME_HEIGHT)
        
        self.game_screen = pygame.display.set_mode((initial_w, initial_h), pygame.SCALED | pygame.RESIZABLE)
        
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
        self.saved_modals = [] 
        
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
            'inventory': (970, 10),
            'gear': (650, 10),
            'container': (GAME_WIDTH / 2 - 150, GAME_HEIGHT / 2 - 150),
            'nearby': (970, 360),
            'messages': (10, 360),
            'text': (GAME_WIDTH / 2 - 200, GAME_HEIGHT / 2 - 150),
            'mobile': (GAME_WIDTH / 2 - 125, GAME_HEIGHT / 2 - 200),
            'crafting': (300, 100)
        }
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
            self.sound_manager.play_music('game/lib/sfx/ui/music.ogg', volume=0.2)

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

    # --- Delegated Methods ---
    def save_game(self):
        return save_game(self)

    def load_game(self, save_folder_name):
        return load_game(self, save_folder_name)

    def start_new_game(self, player_data, save_dir_name=None):
        return start_new_game(self, player_data, save_dir_name)

    def load_map(self, map_filename):
        return load_map(self, map_filename)

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

    # --- Game Loop Methods ---
    
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
        if self.paused_surface:
            self.game_screen.blit(self.paused_surface, (0, 0))
        else:
            self.game_screen.fill((50, 50, 50))

        overlay = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.game_screen.blit(overlay, (0, 0))

        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2
        btn_w, btn_h = 220, 50
        spacing = 20
        
        btn_continue = pygame.Rect(center_x - btn_w//2, center_y - btn_h - spacing, btn_w, btn_h)
        btn_save     = pygame.Rect(center_x - btn_w//2, center_y, btn_w, btn_h)
        btn_quit     = pygame.Rect(center_x - btn_w//2, center_y + btn_h + spacing, btn_w, btn_h)

        mouse_pos = self._get_scaled_mouse_pos()

        def draw_btn(rect, text, color_base, color_hover):
            color = color_hover if rect.collidepoint(mouse_pos) else color_base
            pygame.draw.rect(self.game_screen, color, rect, border_radius=5)
            pygame.draw.rect(self.game_screen, WHITE, rect, 1, border_radius=5)
            txt_surf = font_notification.render(text, True, WHITE)
            self.game_screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

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
        mouse_pos = self._get_scaled_mouse_pos()
        start_btn = draw_loading_screen(self.game_screen, self.loading_done, mouse_pos)
        self._update_screen()
        
        if not self.loading_done:
            if self.loading_data:
                self.start_new_game(self.loading_data)
                self.game_state = 'LOADING'
                self.loading_done = True
                self.loading_data = None 
            elif self.loading_saved_game_folder:
                self.load_game(self.loading_saved_game_folder)
                self.game_state = 'LOADING'
                self.loading_done = True
                self.loading_saved_game_folder = None
        else:
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

        start_btn, load_btn, settings_btn, quit_btn = draw_menu(self.game_screen, mouse_pos, has_save)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                
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

    def run_playing(self):
        self.world_time.update()
        handle_input(self)
        update_game_state(self)
        
        # [NEW] Dynamic Attribute Updates via XML Config
        if self.player:
            base_radius = core.data.config.BASE_PLAYER_VIEW_RADIUS
            radius_mult = 1.0

            # Iterate over traits and apply 'BASE_PLAYER_VIEW_RADIUS' modifiers
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

        for npc in self.npcs:
            npc.update(self)

        self._cleanup_modals()
        draw_game(self)

        if self.hovered_item:
            mouse_pos = self._get_scaled_mouse_pos()
            draw_tooltip(self.game_screen, self.hovered_item, mouse_pos)

        if self.context_menu['active']:
            draw_context_menu(self.game_screen, self.context_menu, self._get_scaled_mouse_pos())

        self._update_screen()

    def _update_screen(self):
        pygame.display.flip()
        self.clock.tick(60)

    def update_messages(self):
        pass