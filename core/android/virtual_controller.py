import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT

class VirtualAndroidController:
    """
    Duck-types the core.events.joystick.JoystickHandler.
    Translates mobile multi-touch FINGER events into game inputs.
    """
    def __init__(self, logger=None):
        self.logger = logger
        if self.logger:
            self.logger.info("Initializing Virtual Android Controller...")
            
        # Virtual Joystick (Left Side)
        self.joy_base_pos = (150, GAME_HEIGHT - 150)
        self.joy_base_radius = 80
        self.joy_stick_radius = 40
        self.joy_current_pos = list(self.joy_base_pos)
        self.joy_active_finger = None
        
        self.lx = 0.0
        self.ly = 0.0
        
        # Virtual Buttons (Right Side)
        self.buttons = {
            'A': {'pos': (GAME_WIDTH - 150, GAME_HEIGHT - 100), 'radius': 40, 'pressed': False, 'color': (50, 200, 50, 150), 'key': pygame.K_SPACE}, # Action/Shoot
            'B': {'pos': (GAME_WIDTH - 80, GAME_HEIGHT - 150), 'radius': 40, 'pressed': False, 'color': (200, 50, 50, 150), 'key': pygame.K_RALT},  # Cancel/Alt
            'Y': {'pos': (GAME_WIDTH - 150, GAME_HEIGHT - 200), 'radius': 40, 'pressed': False, 'color': (200, 200, 50, 150), 'key': pygame.K_e},     # Interact
            'RUN': {'pos': (GAME_WIDTH - 240, GAME_HEIGHT - 80), 'radius': 30, 'pressed': False, 'color': (150, 150, 150, 150), 'key': pygame.K_LSHIFT},
            'TAB': {'pos': (GAME_WIDTH - 50, 50), 'radius': 30, 'pressed': False, 'color': (100, 100, 200, 150), 'key': pygame.K_TAB} # Modals
        }
        
        self.joy_run = False
        self.joy_aim = False
        
        # We don't use a cursor on mobile, so we hide it
        pygame.mouse.set_visible(False)

    def get_movement_axes(self):
        """Matches JoystickHandler signature"""
        return self.lx, self.ly

    def get_action_states(self):
        """Matches JoystickHandler signature"""
        return self.joy_run, self.joy_aim

    def update_cursor(self, game):
        """Matches JoystickHandler signature. On mobile, we bypass cursor snapping."""
        pass 

    def process_event(self, event):
        """
        Intercepts multi-touch events and posts native Pygame keyboard/mouse events,
        allowing the rest of the game to work untouched.
        """
        # Pygame 2 normalized touch coordinates (0.0 to 1.0)
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            x = event.x * GAME_WIDTH
            y = event.y * GAME_HEIGHT
            finger_id = event.finger_id
            
            if event.type == pygame.FINGERDOWN:
                # Check Joystick
                dist_to_joy = math.hypot(x - self.joy_base_pos[0], y - self.joy_base_pos[1])
                if dist_to_joy <= self.joy_base_radius * 1.5 and self.joy_active_finger is None:
                    self.joy_active_finger = finger_id
                    self._update_joystick(x, y)
                    return
                
                # Check Buttons
                for btn_name, btn in self.buttons.items():
                    dist = math.hypot(x - btn['pos'][0], y - btn['pos'][1])
                    if dist <= btn['radius']:
                        btn['pressed'] = True
                        if btn_name == 'RUN':
                            self.joy_run = True
                        else:
                            # Simulate physical key press for existing core.input to pick up
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': btn['key']}))
                        return

                # If touching elsewhere, simulate a left mouse click (for UI interaction)
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (x, y), 'button': 1}))

            elif event.type == pygame.FINGERMOTION:
                if finger_id == self.joy_active_finger:
                    self._update_joystick(x, y)
                else:
                    # Simulate mouse drag
                    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (x, y), 'rel': (event.dx * GAME_WIDTH, event.dy * GAME_HEIGHT)}))

            elif event.type == pygame.FINGERUP:
                if finger_id == self.joy_active_finger:
                    self.joy_active_finger = None
                    self.joy_current_pos = list(self.joy_base_pos)
                    self.lx, self.ly = 0.0, 0.0
                    return
                
                for btn_name, btn in self.buttons.items():
                    # Release all buttons tied to this area roughly
                    dist = math.hypot(x - btn['pos'][0], y - btn['pos'][1])
                    if dist <= btn['radius'] or btn['pressed']:
                        btn['pressed'] = False
                        if btn_name == 'RUN':
                            self.joy_run = False
                        else:
                            pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': btn['key']}))
                
                # Simulate mouse release
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (x, y), 'button': 1}))

    def _update_joystick(self, x, y):
        dx = x - self.joy_base_pos[0]
        dy = y - self.joy_base_pos[1]
        dist = math.hypot(dx, dy)
        
        if dist > self.joy_base_radius:
            dx = (dx / dist) * self.joy_base_radius
            dy = (dy / dist) * self.joy_base_radius
            
        self.joy_current_pos = [self.joy_base_pos[0] + dx, self.joy_base_pos[1] + dy]
        
        # Normalize for movement math (-1.0 to 1.0)
        self.lx = dx / self.joy_base_radius
        self.ly = dy / self.joy_base_radius

    def draw(self, surface):
        """Renders the transparent virtual gamepad. Call this last in your draw loop."""
        # Draw Joystick Base
        pygame.draw.circle(surface, (100, 100, 100, 100), self.joy_base_pos, self.joy_base_radius, 2)
        # Draw Joystick Stick
        pygame.draw.circle(surface, (200, 200, 200, 180), (int(self.joy_current_pos[0]), int(self.joy_current_pos[1])), self.joy_stick_radius)
        
        # Draw Buttons
        for name, btn in self.buttons.items():
            color = (255, 255, 255, 200) if btn['pressed'] else btn['color']
            pygame.draw.circle(surface, color, btn['pos'], btn['radius'])
            # Optional: Draw text using a system font or passed-in font to label buttons here