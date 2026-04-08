import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT
import core.data.config

class VirtualAndroidController:
    """
    Duck-types the core.events.joystick.JoystickHandler.
    Translates mobile multi-touch FINGER events into game inputs.
    """
    def __init__(self, logger=None):
        self.logger = logger
        if self.logger:
            self.logger.info("Initializing Virtual Android Controller...")
            
        pygame.font.init() 
        self.font = pygame.font.SysFont(None, 24)
            
        # Virtual Joystick (Left Side - Movement)
        self.joy_base_pos = [150, GAME_HEIGHT - 150]
        self.joy_base_radius = 80
        self.joy_stick_radius = 40
        self.joy_current_pos = list(self.joy_base_pos)
        self.joy_active_finger = None
        
        self.lx = 0.0
        self.ly = 0.0

        # Virtual Joystick (Right Side - Aiming)
        self.rjoy_base_pos = [GAME_WIDTH - 150, GAME_HEIGHT - 150]
        self.rjoy_base_radius = 80
        self.rjoy_stick_radius = 40
        self.rjoy_current_pos = list(self.rjoy_base_pos)
        self.rjoy_active_finger = None
        
        self.rx = 0.0
        self.ry = 0.0
        
        # Virtual Buttons Layout (Aim button 'B' removed)
        self.buttons = {
            'TAB': {'pos': [150, GAME_HEIGHT - 400], 'radius': 35, 'pressed': False, 'color': (100, 100, 200, 150), 'key': pygame.K_TAB, 'text': 'TAB'}, 
            'A':   {'pos': [150, GAME_HEIGHT - 280], 'radius': 35, 'pressed': False, 'color': (50, 200, 50, 150), 'key': pygame.K_SPACE, 'text': 'Shoot'},
            'Y':   {'pos': [GAME_WIDTH - 570, GAME_HEIGHT - 140], 'radius': 35, 'pressed': False, 'color': (200, 200, 50, 150), 'key': pygame.K_e, 'text': 'Intr'},
            'RUN': {'pos': [GAME_WIDTH - 300, GAME_HEIGHT - 110], 'radius': 35, 'pressed': False, 'color': (150, 150, 150, 150), 'key': pygame.K_LSHIFT, 'text': 'Run'},
        }
        
        self.joy_run = False
        self.joy_aim = False
        
        pygame.mouse.set_visible(False)

    def update_layout(self, right_modals_open):
        """Smoothly animates the right-side buttons based on modal visibility."""
        if right_modals_open:
            target_x = {
                'Y': GAME_WIDTH - 570, 
                'RUN': GAME_WIDTH - 300,
                'RJOY': GAME_WIDTH - 430
            }
        else:
            target_x = {
                'Y': GAME_WIDTH - 80,
                'RUN': GAME_WIDTH - 210,
                'RJOY': GAME_WIDTH - 150
            }
            
        for key in ['Y', 'RUN']:
            current_x = self.buttons[key]['pos'][0]
            self.buttons[key]['pos'][0] = current_x + (target_x[key] - current_x) * 0.2

        curr_rjoy_x = self.rjoy_base_pos[0]
        self.rjoy_base_pos[0] = curr_rjoy_x + (target_x['RJOY'] - curr_rjoy_x) * 0.2
        if self.rjoy_active_finger is None:
            self.rjoy_current_pos[0] = self.rjoy_base_pos[0]

    def get_movement_axes(self):
        return self.lx, self.ly

    def get_action_states(self):
        return self.joy_run, self.joy_aim

    def update_cursor(self, game):
        """
        Calculates precise screen centers to snap the crosshair.
        Uses a monkey-patch to ensure native touch events don't hijack the aim!
        """
        if not hasattr(self, '_original_mouse_tracker'):
            self._original_mouse_tracker = game._get_scaled_mouse_pos

        if self.joy_aim:
            # --- ELEGANT FIX: Match the camera's true world offsets and zoom math ---
            if hasattr(game, 'player') and game.player and hasattr(game, 'offset_x'):
                zoom = getattr(game, 'zoom_level', 1.0)
                game_offset_x = getattr(core.data.config, 'GAME_OFFSET_X', 0)
                
                # Find the EXACT screen pixel the player is drawn at
                center_x = (game.player.rect.centerx + game.offset_x) * zoom + game_offset_x
                center_y = (game.player.rect.centery + game.offset_y) * zoom
            else:
                center_x = GAME_WIDTH // 2
                center_y = GAME_HEIGHT // 2
                
                if hasattr(game, 'camera_pan_x'):
                    center_x -= getattr(game, 'camera_pan_x', 0)
                    center_y -= getattr(game, 'camera_pan_y', 0)

            aim_radius = 250 
            target_x = center_x + (self.rx * aim_radius)
            target_y = center_y + (self.ry * aim_radius)
            
            self._locked_crosshair = (int(target_x), int(target_y))
            
            game._get_scaled_mouse_pos = lambda: self._locked_crosshair

        else:
            if hasattr(self, '_original_mouse_tracker') and game._get_scaled_mouse_pos != self._original_mouse_tracker:
                game._get_scaled_mouse_pos = self._original_mouse_tracker

    def process_event(self, event):
        """Intercepts multi-touch events and routes them to sticks/buttons."""
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            x = event.x * GAME_WIDTH
            y = event.y * GAME_HEIGHT
            finger_id = event.finger_id
            
            if event.type == pygame.FINGERDOWN:
                dist_to_joy = math.hypot(x - self.joy_base_pos[0], y - self.joy_base_pos[1])
                if dist_to_joy <= self.joy_base_radius * 1.5 and self.joy_active_finger is None:
                    self.joy_active_finger = finger_id
                    self._update_joystick(x, y)
                    return

                dist_to_rjoy = math.hypot(x - self.rjoy_base_pos[0], y - self.rjoy_base_pos[1])
                if dist_to_rjoy <= self.rjoy_base_radius * 1.5 and self.rjoy_active_finger is None:
                    self.rjoy_active_finger = finger_id
                    self.joy_aim = True 
                    self._update_rjoystick(x, y)
                    return
                
                for btn_name, btn in self.buttons.items():
                    dist = math.hypot(x - btn['pos'][0], y - btn['pos'][1])
                    if dist <= btn['radius']:
                        btn['pressed'] = True
                        if btn_name == 'RUN':
                            self.joy_run = True
                        elif btn_name == 'A':
                            # ELEGANT FIX: Mimic a left mouse click to trigger core.input.py's attack handler
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (x, y)}))
                        else:
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': btn['key'], 'unicode': ''}))
                        return

            elif event.type == pygame.FINGERMOTION:
                if finger_id == self.joy_active_finger:
                    self._update_joystick(x, y)
                elif finger_id == self.rjoy_active_finger:
                    self._update_rjoystick(x, y)

            elif event.type == pygame.FINGERUP:
                if finger_id == self.joy_active_finger:
                    self.joy_active_finger = None
                    self.joy_current_pos = list(self.joy_base_pos)
                    self.lx, self.ly = 0.0, 0.0
                    return

                if finger_id == self.rjoy_active_finger:
                    self.rjoy_active_finger = None
                    self.rjoy_current_pos = list(self.rjoy_base_pos)
                    self.rx, self.ry = 0.0, 0.0
                    self.joy_aim = False 
                    return
                
                for btn_name, btn in self.buttons.items():
                    dist = math.hypot(x - btn['pos'][0], y - btn['pos'][1])
                    if dist <= btn['radius'] or btn['pressed']:
                        btn['pressed'] = False
                        if btn_name == 'RUN':
                            self.joy_run = False
                        elif btn_name == 'A':
                            # Release the left mouse click
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'button': 1, 'pos': (x, y)}))
                        else:
                            pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': btn['key'], 'unicode': ''}))

    def _update_joystick(self, x, y):
        dx = x - self.joy_base_pos[0]
        dy = y - self.joy_base_pos[1]
        dist = math.hypot(dx, dy)
        if dist > self.joy_base_radius:
            dx = (dx / dist) * self.joy_base_radius
            dy = (dy / dist) * self.joy_base_radius
            
        self.joy_current_pos = [self.joy_base_pos[0] + dx, self.joy_base_pos[1] + dy]
        self.lx = dx / self.joy_base_radius
        self.ly = dy / self.joy_base_radius

    def _update_rjoystick(self, x, y):
        dx = x - self.rjoy_base_pos[0]
        dy = y - self.rjoy_base_pos[1]
        dist = math.hypot(dx, dy)
        if dist > self.rjoy_base_radius:
            dx = (dx / dist) * self.rjoy_base_radius
            dy = (dy / dist) * self.rjoy_base_radius
            
        self.rjoy_current_pos = [self.rjoy_base_pos[0] + dx, self.rjoy_base_pos[1] + dy]
        self.rx = dx / self.rjoy_base_radius
        self.ry = dy / self.rjoy_base_radius

    def draw(self, surface):
        """Renders the transparent virtual gamepad and its labels."""
        pygame.draw.circle(surface, (100, 100, 100, 100), (int(self.joy_base_pos[0]), int(self.joy_base_pos[1])), self.joy_base_radius, 2)
        pygame.draw.circle(surface, (200, 200, 200, 180), (int(self.joy_current_pos[0]), int(self.joy_current_pos[1])), self.joy_stick_radius)
        
        pygame.draw.circle(surface, (100, 100, 100, 100), (int(self.rjoy_base_pos[0]), int(self.rjoy_base_pos[1])), self.rjoy_base_radius, 2)
        pygame.draw.circle(surface, (200, 50, 50, 150), (int(self.rjoy_current_pos[0]), int(self.rjoy_current_pos[1])), self.rjoy_stick_radius)
        
        for name, btn in self.buttons.items():
            color = (255, 255, 255, 200) if btn['pressed'] else btn['color']
            pygame.draw.circle(surface, color, btn['pos'], btn['radius'])
            
            if 'text' in btn and self.font:
                text_surface = self.font.render(btn['text'], True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=btn['pos'])
                surface.blit(text_surface, text_rect)