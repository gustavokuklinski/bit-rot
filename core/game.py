import pygame
import random
import time
import math
import uuid
import os
import asyncio

from data.config import *
from core.entities.player.player import Player
from core.entities.zombie.zombie import Zombie
from core.entities.item.item import Item, Projectile
from core.entities.zombie.corpse import Corpse
from core.ui.helpers import draw_menu, draw_game_over, run_player_setup
from core.ui.inventory import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect, get_invcontainer_slot_rect
from core.ui.container import draw_container_view, get_container_slot_rect
from core.ui.status import draw_status_modal
from core.ui.dropdown import draw_context_menu
from data.player_xml_parser import parse_player_data
from core.ui.assets import load_assets
from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.map.tile_manager import TileManager
from core.map.map_manager import MapManager
from core.map.map_loader import load_map_from_file, parse_layered_map_layout
from core.map.spawn_manager import spawn_initial_items, spawn_initial_zombies
from core.map.world_layers import load_all_map_layers, set_active_layer
from core.map.world_time import WorldTime
from core.ui.mobile_modal import draw_mobile_modal

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT), pygame.RESIZABLE)
        self.virtual_screen = pygame.Surface((VIRTUAL_SCREEN_WIDTH, VIRTUAL_GAME_HEIGHT))
        pygame.display.set_caption("Bit Rot")
        self.clock = pygame.time.Clock()
        self.assets = load_assets()
        self.game_state = 'MENU'
        self.running = True

        self.map_manager = MapManager(self)
        #self.map_manager = MapManager()
        self.tile_manager = TileManager()

        self.player = None
        self.zombies = []
        self.items_on_ground = []
        self.projectiles = []
        self.obstacles = []
        self.renderable_tiles = []
        self.containers = []
        self.corpses = []
        

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
            'inventory': (970, 10),
            'container': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150),
            'nearby': (970, 360),
            'messages': (10, 560)
        }

        self.last_modal_positions = {
            'status': (65, 10),
            'inventory': (970, 10),
            'container': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150),
            'nearby': (970, 360),
            'messages': (10, 560),
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

        self.hovered_interactable_tile_rect = None

        self.message_log = []

        self.current_layer_index = 1
        self.all_map_layers = {} # Will store {1: data, 2: data, ...}
        self.all_ground_layers = {}
        self.all_spawn_layers = {}
        self.layer_spawn_triggers = {} # Stores triggered spawns for each layer
        self.triggered_spawns = set()
        
        self.current_zombie_spawns = []

        self.spawn_point_grid = {}
        self.SPAWN_GRID_SIZE = 512

        self.player_setup_state = {}
        
        self.player_view_radius = BASE_PLAYER_VIEW_RADIUS
        self.world_time = WorldTime(self)


    def load_map(self, map_filename):
        # Clear all game state
        self.obstacles.clear()
        self.containers.clear()
        self.items_on_ground.clear()
        self.zombies.clear()
        #self.corpses.clear()

        # Clear all layer data dictionaries
        self.all_map_layers.clear()
        self.all_ground_layers.clear()
        self.all_spawn_layers.clear()
        self.layer_items.clear()
        self.layer_zombies.clear()

        self.map_manager.current_map_filename = map_filename


        self.all_map_layers, self.all_ground_layers, self.all_spawn_layers = \
            load_all_map_layers(map_filename)

        if 1 not in self.all_map_layers:
            raise FileNotFoundError(f"Base map file {map_filename} (Layer 1) could not be loaded.")


        set_active_layer(self, 1)

        # --- Find Player Spawn ('P') *only on Layer 1* ---
        player_spawn_pos = None
        # Note: self.spawn_data is already set to layer 1's spawn data by set_active_layer(1)
        for y, row in enumerate(self.spawn_data):
            for x, tile in enumerate(row):
                if tile == 'P':
                    player_spawn_pos = (x * TILE_SIZE, y * TILE_SIZE)
                    print(f"Player spawn 'P' found at {player_spawn_pos} on layer 1.")
                    break
            if player_spawn_pos:
                break

        if not player_spawn_pos:
            print("Warning: No player spawn 'P' found on Layer 1. Defaulting position.")
            player_spawn_pos = (GAME_WIDTH // 2, GAME_HEIGHT // 2)

        return player_spawn_pos

    def start_new_game(self, player_data):
        
        # The player_data dict is now fully constructed by the setup screen.
        self.player_name = player_data.get('name', "Player") # Ensure game obj has name
        
        self.player = Player(player_data=player_data)
        self.zoom_level = START_ZOOM
        
        # The setup screen should have put initial_loot in the dict.
        initial_loot = player_data.get('initial_loot', [])
        self.player.inventory = [Item.create_from_name(name) for name in initial_loot if Item.create_from_name(name)]

        try:
            # Assumes your item name in the XML is "ID"
            # If your item is named "Wallet", change "ID" to "Wallet"
            wallet_item = Item.create_from_name("Wallet") 
            if wallet_item:
                # Check if there's space
                if len(self.player.inventory) < self.player.get_total_inventory_slots():
                    self.player.inventory.append(wallet_item)
                else:
                    print("Could not add wallet; inventory is full!")
            else:
                print("Warning: Could not create 'ID' item. Check item XML.")
        except Exception as e:
            print(f"Error creating starting wallet: {e}")
        
        try:
            # Assumes your item name in the XML is "ID"
            # If your item is named "Wallet", change "ID" to "Wallet"
            wallet_item = Item.create_from_name("Powerbank") 
            if wallet_item:
                # Check if there's space
                if len(self.player.inventory) < self.player.get_total_inventory_slots():
                    self.player.inventory.append(wallet_item)
                else:
                    print("Could not add wallet; inventory is full!")
            else:
                print("Warning: Could not create 'ID' item. Check item XML.")
        except Exception as e:
            print(f"Error creating starting wallet: {e}")
        

        self.zombies_killed = 0
        self.modals = []
        self.map_states = {}
        
        player_spawn = self.load_map(self.map_manager.current_map_filename)
        
        if player_spawn:
            self.player.rect.topleft = player_spawn
            self.player.x, self.player.y = player_spawn

        self.world_time = WorldTime(self)
        self.game_start_time = pygame.time.get_ticks()

        inventory_modal = {
            'id': uuid.uuid4(),
            'type': 'inventory',
            'item': None,
            'position': self.last_modal_positions['inventory'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(self.last_modal_positions['inventory'][0], self.last_modal_positions['inventory'][1], INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT),
            'minimized': False
        }
        self.modals.append(inventory_modal)

        nearby_modal = {
            'id': uuid.uuid4(),
            'type': 'nearby',
            'item': None,
            'position': self.last_modal_positions['nearby'],
            'is_dragging': False,
            'drag_offset': (0, 0),
            'rect': pygame.Rect(self.last_modal_positions['nearby'][0], self.last_modal_positions['nearby'][1], NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT),
            'minimized': False
        }
        self.modals.append(nearby_modal)

    def check_map_transition(self):
        new_map = None
        new_player_pos = None
        if self.player.rect.top <= 0:
            new_map = self.map_manager.transition('top')
            if new_map:
                new_player_pos = (self.player.rect.x, GAME_HEIGHT - self.player.rect.height)
        elif self.player.rect.bottom >= GAME_HEIGHT:
            new_map = self.map_manager.transition('bottom')
            if new_map:
                new_player_pos = (self.player.rect.x, 0)
        elif self.player.rect.left <= 0:
            new_map = self.map_manager.transition('left')
            if new_map:
                new_player_pos = (GAME_WIDTH - self.player.rect.width, self.player.rect.y)
            elif self.player.rect.right >= GAME_WIDTH:
                new_map = self.map_manager.transition('right')
            if new_map:
                new_player_pos = (0, self.player.rect.y)
            if new_map and new_player_pos:
                current_map_filename = self.map_manager.current_map_filename

            if current_map_filename not in self.map_states:
                self.map_states[current_map_filename] = {}

                self.map_states[current_map_filename]['items'] = self.items_on_ground
                self.map_states[current_map_filename]['zombies'] = self.zombies
                self.map_states[current_map_filename]['containers'] = self.containers

                self.load_map(new_map)
                    
                self.player.rect.topleft = new_player_pos
                self.player.x, self.player.y = new_player_pos
                self.player.vx = 0
                self.player.vy = 0

    async def run(self):
        while self.running:
            if self.game_state == 'MENU':
                self.run_menu()
            elif self.game_state == 'PLAYER_SETUP':
                self.run_player_setup()
            elif self.game_state == 'PLAYING':
                self.run_playing()
            elif self.game_state == 'PAUSED':
                self.run_paused()
            elif self.game_state == 'GAME_OVER':
                self.run_game_over()
            
            await asyncio.sleep(0)

        # pygame.quit()

    def run_menu(self):
        mouse_pos = self._get_scaled_mouse_pos()
        start_button, quit_button = draw_menu(self.virtual_screen, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                if start_button.collidepoint(mouse_pos):
                    self.game_state = 'PLAYER_SETUP'
                elif quit_button.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

    def run_player_setup(self):
        run_player_setup(self)

    def run_game_over(self):
        mouse_pos = self._get_scaled_mouse_pos()
        restart_button, quit_button = draw_game_over(self.virtual_screen, self.zombies_killed, mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = self._get_scaled_mouse_pos()
                if restart_button.collidepoint(mouse_pos):
                    self.game_state = 'PLAYER_SETUP'
                elif quit_button.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

    def run_playing(self):
        self.world_time.update()

        handle_input(self)
        update_game_state(self)
        self.check_map_transition()
        draw_game(self)
        self._update_screen()

    def run_paused(self):
        handle_input(self)
        draw_game(self)
        font = pygame.font.Font(None, 50)
        text = font.render("PAUSED", True, WHITE)
        text_rect = text.get_rect(center=(VIRTUAL_SCREEN_WIDTH / 2, VIRTUAL_GAME_HEIGHT / 2))
        self.virtual_screen.blit(text, text_rect)
        self._update_screen()

    def _get_scaled_mouse_pos(self):
        real_mouse_pos = pygame.mouse.get_pos()
        current_w, current_h = self.screen.get_size()

        scale = min(current_w / VIRTUAL_SCREEN_WIDTH, current_h / VIRTUAL_GAME_HEIGHT)
        
        scaled_w, scaled_h = int(VIRTUAL_SCREEN_WIDTH * scale), int(VIRTUAL_GAME_HEIGHT * scale)
        blit_x = (current_w - scaled_w) // 2
        blit_y = (current_h - scaled_h) // 2

        mouse_on_surf_x = real_mouse_pos[0] - blit_x
        mouse_on_surf_y = real_mouse_pos[1] - blit_y

        scaled_x = mouse_on_surf_x / scale
        scaled_y = mouse_on_surf_y / scale

        return (scaled_x, scaled_y)

    def get_player_facing_tile(self):
        if not self.player:
            return None, None
        
        # Get player's center grid position
        player_grid_x = self.player.rect.centerx // TILE_SIZE
        player_grid_y = self.player.rect.centery // TILE_SIZE
        
        # Get facing direction (default to down if not set)
        facing_x, facing_y = getattr(self.player, 'facing_direction', (0, 1))
        
        # Calculate the tile in front
        target_grid_x = player_grid_x + facing_x
        target_grid_y = player_grid_y + facing_y
        
        return target_grid_x, target_grid_y


    def find_nearby_containers(self):
        nearby_containers = []
        for item in self.items_on_ground + self.containers:
            if hasattr(item, 'inventory'):
                dist = math.hypot(self.player.rect.centerx - item.rect.centerx, self.player.rect.centery - item.rect.centery)
                if dist <= TILE_SIZE * 1.5:
                    nearby_containers.append(item)
        return nearby_containers

    def screen_to_world(self, screen_pos):
        """Converts screen coordinates to world coordinates."""
        screen_x, screen_y = screen_pos
        
        # Adjust for the game area's offset on the virtual screen
        screen_x -= GAME_OFFSET_X
        
        # Calculate mouse position relative to the screen center (where the player is)
        relative_screen_x = screen_x - (GAME_WIDTH / 2)
        relative_screen_y = screen_y - (GAME_HEIGHT / 2)
        
        # Scale this relative position down by the zoom level to get world offset
        relative_world_x = relative_screen_x / self.zoom_level
        relative_world_y = relative_screen_y / self.zoom_level
        
        # Add to the player's world position to get the final world coordinate
        world_x = self.player.rect.centerx + relative_world_x
        world_y = self.player.rect.centery + relative_world_y
        
        return (world_x, world_y)


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
        self.active_messages = [msg for msg in self.active_messages if msg.duration > 0]
        for msg in self.active_messages:
            msg.update()