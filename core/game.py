import pygame
import random
import time
import math
import uuid
import os

from data.config import *
from core.entities.player import Player
from core.entities.zombie import Zombie
from core.entities.item import Item, Projectile
from core.entities.corpse import Corpse
from ui.helpers import draw_menu, draw_game_over, get_belt_slot_rect_in_modal, get_inventory_slot_rect, get_backpack_slot_rect, get_container_slot_rect
from ui.modals import draw_inventory_modal, draw_container_view, draw_status_modal, draw_context_menu
from data.xml_parser import parse_player_data
from assets.assets import load_assets

from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.world import create_obstacles_from_map, spawn_initial_items, spawn_initial_zombies

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

        self.player = None
        self.zombies = []
        self.items_on_ground = []
        self.projectiles = []
        self.obstacles = []
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

    def run(self):
        while self.running:
            if self.game_state == 'MENU':
                self.run_menu()
            elif self.game_state == 'PLAYING':
                self.run_playing()
            elif self.game_state == 'GAME_OVER':
                self.run_game_over()
        pygame.quit()

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
                    self.start_new_game()
                    self.game_state = 'PLAYING'
                elif quit_button.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

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
                    self.start_new_game()
                    self.game_state = 'PLAYING'
                elif quit_button.collidepoint(mouse_pos):
                    self.running = False
                    return
        self._update_screen()

    def run_playing(self):
        handle_input(self)
        update_game_state(self)
        draw_game(self)
        self._update_screen()

    def start_new_game(self):
        player_data = parse_player_data()
        self.player = Player(player_data=player_data)
        self.player.inventory = [Item.create_from_name(name) for name in player_data['initial_loot'] if Item.create_from_name(name)]
        self.zombies_killed = 0
        self.obstacles = create_obstacles_from_map(MAP_LAYOUT)
        self.items_on_ground = spawn_initial_items(self.obstacles)
        self.zombies = spawn_initial_zombies()
        self.projectiles = []
        self.modals = []

    def _get_scaled_mouse_pos(self):
        real_mouse_pos = pygame.mouse.get_pos()
        screen_w, screen_h = self.screen.get_size()
        scale_x = VIRTUAL_SCREEN_WIDTH / screen_w
        scale_y = VIRTUAL_GAME_HEIGHT / screen_h
        return (real_mouse_pos[0] * scale_x, real_mouse_pos[1] * scale_y)

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
