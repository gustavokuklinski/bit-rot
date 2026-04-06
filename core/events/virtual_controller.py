import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT

class VirtualController:
    def __init__(self):
        self.enabled = False 
        
        # --- Analog Stick (Bottom Left) ---
        self.joy_base_radius = 80
        self.joy_stick_radius = 35
        self.joy_center = (120, GAME_HEIGHT - 120)
        self.stick_pos = list(self.joy_center)
        self.joy_touch_id = None
        self.dx = 0.0
        self.dy = 0.0
        
        # --- Buttons (Bottom Right Layout) ---
        btn_r = 35
        gap = 15
        bx2 = GAME_WIDTH - btn_r - gap        # Right-most column
        bx1 = bx2 - (btn_r * 2) - gap         # Inner column
        by2 = GAME_HEIGHT - btn_r - gap       # Bottom row
        by1 = by2 - (btn_r * 2) - gap         # Top row
        
        # Action Buttons (Press)
        self.btn_shoot = {'rect': pygame.Rect(bx2 - btn_r, by2 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (150, 50, 50), 'label': 'FIRE'}
        self.btn_interact = {'rect': pygame.Rect(bx2 - btn_r, by1 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (50, 50, 150), 'label': 'INT'}
        
        # Stance Buttons (Toggle)
        self.btn_aim = {'rect': pygame.Rect(bx1 - btn_r, by2 - btn_r, btn_r*2, btn_r*2), 'state': False, 'touch_id': None, 'color': (100, 100, 100), 'label': 'AIM'}
        self.btn_run = {'rect': pygame.Rect(bx1 - btn_r, by1 - btn_r, btn_r*2, btn_r*2), 'state': False, 'touch_id': None, 'color': (100, 100, 100), 'label': 'RUN'}

        # --- Long Press Tracking ---
        self.touch_start_time = {}
        self.touch_start_pos = {}

    def process_event(self, event, game):
        if not self.enabled: return

        # Multi-touch Events (x and y are normalized 0.0 to 1.0)
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            x = event.x * GAME_WIDTH
            y = event.y * GAME_HEIGHT
            touch_id = event.finger_id

            if event.type == pygame.FINGERDOWN:
                # 1. Check Joystick
                if math.hypot(x - self.joy_center[0], y - self.joy_center[1]) <= self.joy_base_radius:
                    self.joy_touch_id = touch_id
                    self._update_stick(x, y)
                
                # 2. Check Run Toggle
                elif self.btn_run['rect'].collidepoint(x, y):
                    self.btn_run['state'] = not self.btn_run['state'] 
                    self.btn_run['color'] = (50, 150, 50) if self.btn_run['state'] else (100, 100, 100)
                
                # 3. Check Aim Toggle
                elif self.btn_aim['rect'].collidepoint(x, y):
                    self.btn_aim['state'] = not self.btn_aim['state'] 
                    self.btn_aim['color'] = (200, 100, 50) if self.btn_aim['state'] else (100, 100, 100)
                
                # 4. Check Shoot Action (Only works if Aim is ON)
                elif self.btn_shoot['rect'].collidepoint(x, y):
                    self.btn_shoot['pressed'] = True
                    self.btn_shoot['touch_id'] = touch_id
                    self.btn_shoot['color'] = (255, 50, 50)
                    if self.btn_aim['state']:
                        # Dispatch a Left Click so the game shoots natively
                        pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos, 'button': 1}))
                
                # 5. Check Interact Action ('E' key equivalent)
                elif self.btn_interact['rect'].collidepoint(x, y):
                    self.btn_interact['pressed'] = True
                    self.btn_interact['touch_id'] = touch_id
                    self.btn_interact['color'] = (100, 100, 255)
                    # Dispatch 'e' key so vehicle/door/NPC interaction triggers
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_e, 'unicode': 'e'}))
                
                # 6. Unassigned screen space (Start timer for long-press Context Menu)
                else:
                    self.touch_start_time[touch_id] = pygame.time.get_ticks()
                    self.touch_start_pos[touch_id] = (x, y)

            elif event.type == pygame.FINGERMOTION:
                if touch_id == self.joy_touch_id:
                    self._update_stick(x, y)
                
                # Cancel long-press if the finger drags too far across the screen
                if touch_id in self.touch_start_pos:
                    sx, sy = self.touch_start_pos[touch_id]
                    if math.hypot(x - sx, y - sy) > 20:
                        del self.touch_start_pos[touch_id]
                        if touch_id in self.touch_start_time:
                            del self.touch_start_time[touch_id]

            elif event.type == pygame.FINGERUP:
                # Release Joystick
                if touch_id == self.joy_touch_id:
                    self.joy_touch_id = None
                    self.stick_pos = list(self.joy_center)
                    self.dx, self.dy = 0.0, 0.0
                
                # Release Shoot
                if touch_id == self.btn_shoot.get('touch_id'):
                    self.btn_shoot['pressed'] = False
                    self.btn_shoot['touch_id'] = None
                    self.btn_shoot['color'] = (150, 50, 50)
                    pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': pos, 'button': 1}))
                
                # Release Interact
                if touch_id == self.btn_interact.get('touch_id'):
                    self.btn_interact['pressed'] = False
                    self.btn_interact['touch_id'] = None
                    self.btn_interact['color'] = (50, 50, 150)
                    pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': pygame.K_e, 'unicode': 'e'}))

                # Handle Screen Tap vs Screen Hold
                if touch_id in self.touch_start_time:
                    if pygame.time.get_ticks() - self.touch_start_time[touch_id] >= 500:
                        # LONG PRESS (500ms): Open Context Menu
                        self.trigger_context_menu(game, x, y)
                    else:
                        # SHORT TAP: Emulate a standard Left Click (allows pressing UI, walking to point)
                        pos = (int(x), int(y))
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos, 'button': 1}))
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': pos, 'button': 1}))
                        
                    del self.touch_start_time[touch_id]
                    if touch_id in self.touch_start_pos:
                        del self.touch_start_pos[touch_id]

    def _update_stick(self, x, y):
        dist = math.hypot(x - self.joy_center[0], y - self.joy_center[1])
        angle = math.atan2(y - self.joy_center[1], x - self.joy_center[0])
        
        if dist > self.joy_base_radius:
            dist = self.joy_base_radius
            
        self.stick_pos[0] = self.joy_center[0] + math.cos(angle) * dist
        self.stick_pos[1] = self.joy_center[1] + math.sin(angle) * dist
        
        # Normalize to -1.0 to 1.0 for player movement
        self.dx = (self.stick_pos[0] - self.joy_center[0]) / self.joy_base_radius
        self.dy = (self.stick_pos[1] - self.joy_center[1]) / self.joy_base_radius

    def trigger_context_menu(self, game, screen_x, screen_y):
        from core.events.mouse_context import handle_right_click
        # handle_right_click naturally takes screen coordinates and does the world conversion internally
        handle_right_click(game, (screen_x, screen_y))

    def draw(self, surface):
        if not self.enabled: return
        
        # Draw Joypad Base and Stick
        pygame.draw.circle(surface, (50, 50, 50, 150), self.joy_center, self.joy_base_radius)
        pygame.draw.circle(surface, (200, 200, 200, 200), (int(self.stick_pos[0]), int(self.stick_pos[1])), self.joy_stick_radius)
        
        # Draw all Action/Stance Buttons
        font = pygame.font.SysFont(None, 24)
        for btn in [self.btn_run, self.btn_aim, self.btn_shoot, self.btn_interact]:
            pygame.draw.ellipse(surface, btn['color'], btn['rect'])
            pygame.draw.ellipse(surface, (255, 255, 255), btn['rect'], 2) # Adding a white outline for visibility
            
            text = font.render(btn['label'], True, (255, 255, 255))
            surface.blit(text, text.get_rect(center=btn['rect'].center))