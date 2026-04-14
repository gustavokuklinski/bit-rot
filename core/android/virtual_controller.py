import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT, SPRITE_PATH
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
        self.font = pygame.font.Font(None, 24)

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

        self.current_belt_slot = -1

        # Load the custom UI Icons
        self.icons = {}
        icon_files = {
            'TAB': 'android_tab.png',
            'A': 'android_shoot.png',
            'Y': 'android_interaction.png',
            'RUN': 'android_run.png',
            'MOVE': 'android_movement.png',
            'AIM': 'android_aim.png',
            'BELT': 'android_belt.png'
        }
        
        base_path = SPRITE_PATH + 'ui/'
        for key, filename in icon_files.items():
            try:
                img = pygame.image.load(base_path + filename).convert_alpha()
                # Scale appropriately for sticks (larger) and buttons (smaller)
                size = (48, 48) if key in ['MOVE', 'AIM'] else (36, 36)
                self.icons[key] = pygame.transform.smoothscale(img, size)
            except Exception as e:
                if self.logger:
                    self.logger.warning(f"Could not load icon {filename}: {e}")
                self.icons[key] = None
        light_gray = (160, 160, 160, 120)
        # Virtual Buttons Layout (Left Shoot, Right Cluster)
        self.buttons = {
            # Top-Center
            'BELT': {'pos': [150, GAME_HEIGHT - 280], 'radius': 35, 'pressed': False, 'color': light_gray, 'key': None, 'text': 'Belt'},
            
            # Top-Right
            'A':   {'pos': [240, GAME_HEIGHT - 240], 'radius': 35, 'pressed': False, 'color': light_gray, 'key': pygame.K_SPACE, 'text': 'Shoot'},
            
            # Direct-Right
            'Y':   {'pos': [280, GAME_HEIGHT - 150], 'radius': 35, 'pressed': False, 'color': light_gray, 'key': pygame.K_e, 'text': 'Intr'},
            
            # Bottom-Right (Directly below Y, completing the curve)
            'TAB': {'pos': [240, GAME_HEIGHT - 60], 'radius': 35, 'pressed': False, 'color': light_gray, 'key': pygame.K_TAB, 'text': 'TAB'}, 
            
            # --- RIGHT SIDE ---
            # RUN perfectly mirrored to match TAB's height and inset on the right side
            'RUN': {'pos': [GAME_WIDTH - 240, GAME_HEIGHT - 60], 'radius': 35, 'pressed': False, 'color': light_gray, 'key': pygame.K_LSHIFT, 'text': 'Run'},
        }
        
        self.joy_run = False
        self.joy_aim = False
        
        pygame.mouse.set_visible(False)

    def update_layout(self, right_modals_open):
        """Keep the right-side buttons static. No longer shifts when modals open."""
        # Both RJOY and RUN are safely anchored to the right side
        target_x = {
            'RJOY': GAME_WIDTH - 145,
            'RUN': GAME_WIDTH - 240
        }

        # Smoothly anchor RUN
        if 'RUN' in self.buttons:
            current_x = self.buttons['RUN']['pos'][0]
            self.buttons['RUN']['pos'][0] = current_x + (target_x['RUN'] - current_x) * 0.2

        # Smoothly lock the Right Joystick to its position
        curr_rjoy_x = self.rjoy_base_pos[0]
        self.rjoy_base_pos[0] = curr_rjoy_x + (target_x['RJOY'] - curr_rjoy_x) * 0.2
        
        if self.rjoy_active_finger is None:
            self.rjoy_current_pos[0] = self.rjoy_base_pos[0]

    def get_movement_axes(self):
        return self.lx, self.ly

    def get_action_states(self):
        return self.joy_run, self.joy_aim

    def is_over_controller(self, pos):
        """Helper to block native Pygame touch-to-mouse events over the UI"""
        x, y = pos
        
        # --- FIX: ALLOW NATIVE CLICKS ON MODALS AND TABS ---
        if hasattr(self, 'game') and self.game and hasattr(self.game, 'modals'):
            for modal in self.game.modals:
                if 'rect' in modal:
                    # Tabs sit above the rect, so expand the hit zone upwards by 40px
                    hit_rect = pygame.Rect(
                        modal['rect'].x, 
                        modal['rect'].y - 40, 
                        modal['rect'].width, 
                        modal['rect'].height + 40
                    )
                    if hit_rect.collidepoint(x, y):
                        return False # Touch is over a modal, allow mouse clicks!

        if math.hypot(x - self.joy_base_pos[0], y - self.joy_base_pos[1]) <= self.joy_base_radius * 1.5: 
            return True
        if math.hypot(x - self.rjoy_base_pos[0], y - self.rjoy_base_pos[1]) <= self.rjoy_base_radius * 1.5: 
            return True
        for btn in self.buttons.values():
            if math.hypot(x - btn['pos'][0], y - btn['pos'][1]) <= btn['radius'] * 1.5: 
                return True
        return False

    def update_cursor(self, game):
        """
        Calculates precise screen centers to snap the crosshair.
        Uses a monkey-patch to ensure native touch events don't hijack the aim!
        """
        self.game = game

        if not hasattr(self, '_original_mouse_tracker'):
            self._original_mouse_tracker = game._get_scaled_mouse_pos
            self._original_mouse_pressed = pygame.mouse.get_pressed
            
            # --- NEW: Monkey patch get_pressed to prevent auto-firing when using joysticks ---
            def mock_mouse_pressed():
                pressed = list(self._original_mouse_pressed())
                
                touching_joystick = (self.joy_active_finger is not None or 
                                     self.rjoy_active_finger is not None)
                
                # Suppress the native touch-click if interacting with joysticks
                if touching_joystick and not self.buttons['A']['pressed']:
                    pressed[0] = False
                    
                # Force the left click state if our virtual 'Shoot' is explicitly pressed
                if self.buttons['A']['pressed']:
                    pressed[0] = True
                    
                return tuple(pressed)
                
            pygame.mouse.get_pressed = mock_mouse_pressed

        if self.joy_aim:
            # Match the camera's true world offsets and zoom math
            if hasattr(game, 'player') and game.player and hasattr(game, 'offset_x'):
                zoom = getattr(game, 'zoom_level', 1.0)
                game_offset_x = getattr(core.data.config, 'GAME_OFFSET_X', 0)
                
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
                # --- FIX: INTERACTION Z-INDEX INCLUDING TABS ---
                if hasattr(self, 'game') and self.game and hasattr(self.game, 'modals'):
                    for modal in self.game.modals:
                        if 'rect' in modal:
                            # Match the tab-inclusive hit zone
                            hit_rect = pygame.Rect(
                                modal['rect'].x, 
                                modal['rect'].y - 40, 
                                modal['rect'].width, 
                                modal['rect'].height + 40
                            )
                            if hit_rect.collidepoint(x, y):
                                return 

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
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'button': 1, 'pos': (x, y), 'v_btn': True}))
                        elif btn_name == 'BELT':
                            # Cycle through 0 to 4 (Keys 1 to 5)
                            self.current_belt_slot = (self.current_belt_slot + 1) % 5
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_1 + self.current_belt_slot, 'unicode': str(self.current_belt_slot + 1)}))
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
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'button': 1, 'pos': (x, y), 'v_btn': True}))
                        elif btn_name == 'BELT':
                            pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': pygame.K_1 + self.current_belt_slot, 'unicode': str(self.current_belt_slot + 1)}))
                       
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
        # 1. Draw Left Joystick
        pygame.draw.circle(surface, (150, 150, 150, 80), (int(self.joy_base_pos[0]), int(self.joy_base_pos[1])), self.joy_base_radius, 2)
        pygame.draw.circle(surface, (180, 180, 180, 150), (int(self.joy_current_pos[0]), int(self.joy_current_pos[1])), self.joy_stick_radius)
        
        move_icon = self.icons.get('MOVE')
        if move_icon:
            move_rect = move_icon.get_rect(center=(int(self.joy_current_pos[0]), int(self.joy_current_pos[1])))
            surface.blit(move_icon, move_rect)
        
        # 2. Draw Right Joystick
        pygame.draw.circle(surface, (150, 150, 150, 80), (int(self.rjoy_base_pos[0]), int(self.rjoy_base_pos[1])), self.rjoy_base_radius, 2)
        pygame.draw.circle(surface, (180, 180, 180, 150), (int(self.rjoy_current_pos[0]), int(self.rjoy_current_pos[1])), self.rjoy_stick_radius)
        
        aim_icon = self.icons.get('AIM')
        if aim_icon:
            aim_rect = aim_icon.get_rect(center=(int(self.rjoy_current_pos[0]), int(self.rjoy_current_pos[1])))
            surface.blit(aim_icon, aim_rect)
        
        # 3. Draw Virtual Action Buttons
        for name, btn in self.buttons.items():
            # Brighter if pressed
            color = (220, 220, 220, 180) if btn['pressed'] else btn['color']
            btn_center = (int(btn['pos'][0]), int(btn['pos'][1]))
            
            pygame.draw.circle(surface, color, btn_center, btn['radius'])
            
            icon = self.icons.get(name)
            if icon:
                icon_rect = icon.get_rect(center=btn_center)
                surface.blit(icon, icon_rect)
            elif 'text' in btn and self.font:
                # Fallback to Text if the icon fails to load
                text_surface = self.font.render(btn['text'], True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=btn_center)
                surface.blit(text_surface, text_rect)