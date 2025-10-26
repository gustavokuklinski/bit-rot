import pygame
import random
import time
import math
import uuid
import os
import asyncio

from data.config import *
from core.entities.player import Player
from core.entities.zombie import Zombie
from core.entities.item import Item, Projectile
from core.entities.corpse import Corpse
from core.ui.helpers import draw_menu, draw_game_over, run_player_setup
from core.ui.inventory import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_backpack_slot_rect
from core.ui.container import draw_container_view, get_container_slot_rect
from core.ui.status import draw_status_modal
from core.ui.dropdown import draw_context_menu
from data.player_xml_parser import parse_player_data
from data.professions_xml_parser import get_profession_by_name
from core.ui.assets import load_assets
from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.world import TileManager, parse_layered_map_layout, spawn_initial_items, spawn_initial_zombies, load_map_from_file, MapManager

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
        self.map_manager = MapManager()
        self.tile_manager = TileManager()

        self.player = None
        self.zombies = []
        self.items_on_ground = []
        self.projectiles = []
        self.obstacles = []
        self.renderable_tiles = []
        

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
            'status': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 200),
            'inventory': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 200),
            'container': (VIRTUAL_SCREEN_WIDTH / 2 - 150, VIRTUAL_GAME_HEIGHT / 2 - 150)
        }

        self.status_button_rect = None
        self.inventory_button_rect = None
        self.camera = None
        self.map_states = {}
        self.player_name = ""
        self.name_input_active = False
        self.selected_profession = None
        self.hovered_item = None

    def load_map(self, base_map_filename):
        """Loads map data from base, ground, and spawn CSV layer files."""
        print(f"Loading map layers for: {base_map_filename}")

        # Construct filenames for the layers
        base_filepath = f"{self.map_manager.map_folder}/{base_map_filename}"
        ground_filename = base_map_filename.replace(".csv", "_ground.csv")
        ground_filepath = f"{self.map_manager.map_folder}/{ground_filename}"
        spawn_filename = base_map_filename.replace(".csv", "_spawn.csv")
        spawn_filepath = f"{self.map_manager.map_folder}/{spawn_filename}"

        # Load the data from each layer file
        base_layout = load_map_from_file(base_filepath)
        ground_layout = load_map_from_file(ground_filepath)
        spawn_layout = load_map_from_file(spawn_filepath)

        # Basic validation: Check if base layout loaded successfully
        if not base_layout:
            print(f"Error: Failed to load base map layer: {base_filepath}")
            self.running = False # Or handle error appropriately
            return None # Return None to indicate failure

        # If ground/spawn layers are missing, create empty layouts of the same size
        map_height = len(base_layout)
        map_width = len(base_layout[0]) if map_height > 0 else 0

        if not ground_layout:
            print(f"Warning: Ground layer not found or empty ({ground_filepath}). Creating blank ground layer.")
            ground_layout = [[' ' for _ in range(map_width)] for _ in range(map_height)]
        elif len(ground_layout) != map_height or (map_height > 0 and len(ground_layout[0]) != map_width) :
            print(f"Warning: Ground layer dimensions mismatch base layer. Check {ground_filepath}")
            # Attempt to use it anyway, parser will warn further

        if not spawn_layout:
            print(f"Warning: Spawn layer not found or empty ({spawn_filepath}). Creating blank spawn layer.")
            spawn_layout = [[' ' for _ in range(map_width)] for _ in range(map_height)]
        elif len(spawn_layout) != map_height or (map_height > 0 and len(spawn_layout[0]) != map_width):
            print(f"Warning: Spawn layer dimensions mismatch base layer. Check {spawn_filepath}")
            # Attempt to use it anyway, parser will warn further


        # Update map dimensions (important for camera clamping if you use it)
        self.current_map_width = map_width * TILE_SIZE
        self.current_map_height = map_height * TILE_SIZE

        # Call the new layered parser function
        self.obstacles, self.renderable_tiles, player_spawn, zombie_spawns, item_spawns = \
            parse_layered_map_layout(base_layout, ground_layout, spawn_layout, self.tile_manager)

        # --- Rest of the function (loading state, spawning entities) remains the same ---
        map_filename = base_map_filename # Use base filename as the key for state

        if map_filename in self.map_states:
            map_state = self.map_states[map_filename]
            # Load saved state for items and zombies
            self.items_on_ground = map_state.get('items', [])
            self.zombies = map_state.get('zombies', [])
            # Apply filters for killed/picked up items
            killed_zombie_ids = set(map_state.get('killed_zombies', []))
            self.zombies = [z for z in self.zombies if z.id not in killed_zombie_ids]
            picked_up_item_ids = set(map_state.get('picked_up_items', []))
            self.items_on_ground = [item for item in self.items_on_ground if item.id not in picked_up_item_ids]

        else:
            # First time visiting this map: Spawn initial entities
            self.items_on_ground = spawn_initial_items(self.obstacles, item_spawns)
            self.zombies = spawn_initial_zombies(self.obstacles, zombie_spawns, self.items_on_ground)
            # Initialize map state
            self.map_states[map_filename] = {
                'items': self.items_on_ground[:], # Store copies
                'zombies': self.zombies[:],       # Store copies
                'killed_zombies': [],
                'picked_up_items': []
            }

        # Return the player spawn point found in the spawn layer
        return player_spawn

    def start_new_game(self, profession_name):
        player_data = parse_player_data()
        profession_data = get_profession_by_name(profession_name)
        if profession_data:
            player_data['attributes'] = profession_data['attributes']
            player_data['initial_loot'] = profession_data['initial_loot']
            player_data['visuals'] = profession_data['visuals']
        
        player_data['name'] = self.player_name
        player_data['profession'] = profession_name

        self.player = Player(player_data=player_data)
        self.zoom_level = 1.5
        self.player.inventory = [Item.create_from_name(name) for name in player_data['initial_loot'] if Item.create_from_name(name)]
        self.zombies_killed = 0
        self.modals = []
        self.map_states = {}
        
        player_spawn = self.load_map(self.map_manager.current_map_filename)
        
        if player_spawn:
            self.player.rect.topleft = player_spawn
            self.player.x, self.player.y = player_spawn

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
        start_button, quit_button = draw_menu(self.virtual_screen)

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
        restart_button, quit_button = draw_game_over(self.virtual_screen, self.zombies_killed)

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
        scaled_surf = pygame.transform.scale(self.virtual_screen, (scaled_w, scaled_h))
        blit_x = (current_w - scaled_w) // 2
        blit_y = (current_h - scaled_h) // 2
        self.screen.fill(BLACK)
        self.screen.blit(scaled_surf, (blit_x, blit_y))
        pygame.display.flip()
        self.clock.tick(60)