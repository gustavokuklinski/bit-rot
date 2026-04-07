import pygame
import math
from core.data.config import GAME_WIDTH, GAME_HEIGHT, SPRITE_PATH

class VirtualController:
    def __init__(self):
        self.enabled = False 
        
        self.v_mouse_x = GAME_WIDTH / 2
        self.v_mouse_y = GAME_HEIGHT / 2
        
        self.joy_base_radius = 80
        self.joy_stick_radius = 35
        
        self.l_cx = 180
        self.l_cy = GAME_HEIGHT - 180
        
        self.r_cx = GAME_WIDTH - 180
        self.r_cy = GAME_HEIGHT - 180
        
        self.left_stick_pos = [self.l_cx, self.l_cy]
        self.left_touch_id = None
        self.dx = 0.0
        self.dy = 0.0
        
        self.right_stick_pos = [self.r_cx, self.r_cy]
        self.right_touch_id = None
        self.right_dx = 0.0
        self.right_dy = 0.0
        
        self.idle_alpha = 90    
        self.active_alpha = 220 
        
        btn_r = 30 
        
        # --- ERGONOMIC MOBILE REORGANIZATION (LEFT SIDE) ---
        self.btn_click = {'rect': pygame.Rect(self.l_cx + 110, self.l_cy - 70 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (150, 50, 50, self.idle_alpha), 'label': 'SHOT'}
        self.btn_interact = {'rect': pygame.Rect(self.l_cx + 110, self.l_cy + 10 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (50, 150, 50, self.idle_alpha), 'label': 'INT'}
        self.btn_run = {'rect': pygame.Rect(self.r_cx - 130 - btn_r, self.r_cy - btn_r, btn_r*2, btn_r*2), 'state': False, 'previous_state': False, 'auto_active': False, 'color': (100, 100, 100, self.idle_alpha), 'label': 'RUN'}

        # --- HIDDEN STATE: Prevents crash in core/game.py patched_mouse_get_pressed ---
        self.btn_aim = {'state': False} 

        self.cursor_img = None
        self.is_playing = False 
        
        # --- NATIVE UI TOUCH TRACKING ---
        self.ui_touches = {}
        self.ui_pressed = False

    def _do_auto_aim(self, game):
        """Finds the closest zombie and snaps the virtual cursor to it."""
        if not hasattr(game, 'active_zombies') or not game.player:
            return
            
        closest_zombie = None
        closest_dist = float('inf')
        px, py = game.player.rect.center
        
        for z in game.active_zombies:
            if getattr(z, 'is_dead', False): continue
            dx = z.rect.centerx - px
            dy = z.rect.centery - py
            dist = math.hypot(dx, dy)
            if dist < 600 and dist < closest_dist: 
                closest_dist = dist
                closest_zombie = z
                
        if closest_zombie:
            screen_cx, screen_cy = GAME_WIDTH // 2, GAME_HEIGHT // 2
            self.v_mouse_x = screen_cx + (closest_zombie.rect.centerx - px)
            self.v_mouse_y = screen_cy + (closest_zombie.rect.centery - py)
            
            self.v_mouse_x = max(0, min(GAME_WIDTH, self.v_mouse_x))
            self.v_mouse_y = max(0, min(GAME_HEIGHT, self.v_mouse_y))

    def process_event(self, event, game):
        if not self.enabled: return
        
        self.is_playing = (getattr(game, 'game_state', 'PLAYING') == 'PLAYING')

        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            
            try:
                window_w, window_h = pygame.display.get_window_size()
                scale = min(window_w / GAME_WIDTH, window_h / GAME_HEIGHT)
                offset_x = (window_w - GAME_WIDTH * scale) / 2
                offset_y = (window_h - GAME_HEIGHT * scale) / 2
                x = ((event.x * window_w) - offset_x) / scale
                y = ((event.y * window_h) - offset_y) / scale
            except Exception:
                x = event.x * GAME_WIDTH
                y = event.y * GAME_HEIGHT

            touch_id = event.finger_id

            if event.type == pygame.FINGERDOWN:
                is_controller = False
                
                if self.is_playing:
                    if self.btn_run['rect'].collidepoint(x, y):
                        self.btn_run['state'] = not self.btn_run['state'] 
                        self.btn_run['color'] = (100, 200, 100, self.active_alpha) if self.btn_run['state'] else (100, 100, 100, self.idle_alpha)
                        is_controller = True
                    
                    elif self.btn_click['rect'].collidepoint(x, y):
                        self.btn_click['pressed'] = True
                        self.btn_click['touch_id'] = touch_id
                        self.btn_click['color'] = (255, 50, 50, self.active_alpha)
                        
                        self._do_auto_aim(game)
                        
                        pos = (int(self.v_mouse_x), int(self.v_mouse_y))
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': pos, 'button': 1, 'injected': True}))
                        is_controller = True
                        
                    elif self.btn_interact['rect'].collidepoint(x, y):
                        self.btn_interact['pressed'] = True
                        self.btn_interact['touch_id'] = touch_id
                        self.btn_interact['color'] = (100, 255, 100, self.active_alpha)
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode='e'))
                        is_controller = True
                    
                    elif math.hypot(x - self.l_cx, y - self.l_cy) < self.joy_base_radius * 2.5:
                        self.left_touch_id = touch_id
                        self._update_stick('left', x, y)
                        is_controller = True
                        
                    elif math.hypot(x - self.r_cx, y - self.r_cy) < self.joy_base_radius * 2.5:
                        self.right_touch_id = touch_id
                        self._update_stick('right', x, y)
                        
                        self.btn_aim['state'] = True # Feed the hook in game.py!
                        
                        self._do_auto_aim(game)
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 3, 'injected': True}))
                        is_controller = True

                if not is_controller:
                    self.ui_touches[touch_id] = {'start_time': pygame.time.get_ticks(), 'moved': False, 'start_pos': (x, y)}
                    self.v_mouse_x = x
                    self.v_mouse_y = y
                    self.ui_pressed = True
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(x), int(y)), 'button': 1, 'injected': True}))

            elif event.type == pygame.FINGERMOTION:
                if self.is_playing and touch_id == self.left_touch_id:
                    self._update_stick('left', x, y)
                elif self.is_playing and touch_id == self.right_touch_id:
                    self._update_stick('right', x, y)
                elif touch_id in self.ui_touches:
                    self.v_mouse_x = x
                    self.v_mouse_y = y
                    sx, sy = self.ui_touches[touch_id]['start_pos']
                    if math.hypot(x - sx, y - sy) > 15:
                        self.ui_touches[touch_id]['moved'] = True
                    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (int(x), int(y)), 'rel': (event.dx * GAME_WIDTH, event.dy * GAME_HEIGHT), 'buttons': (1,0,0), 'injected': True}))

            elif event.type == pygame.FINGERUP:
                if self.is_playing:
                    if touch_id == self.btn_click.get('touch_id'):
                        self.btn_click['pressed'] = False
                        self.btn_click['touch_id'] = None
                        self.btn_click['color'] = (150, 50, 50, self.idle_alpha)
                        pos = (int(self.v_mouse_x), int(self.v_mouse_y))
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': pos, 'button': 1, 'injected': True}))

                    if touch_id == self.btn_interact.get('touch_id'):
                        self.btn_interact['pressed'] = False
                        self.btn_interact['touch_id'] = None
                        self.btn_interact['color'] = (50, 150, 50, self.idle_alpha)
                        pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_e, unicode='e'))

                    if touch_id == self.left_touch_id:
                        self.left_touch_id = None
                        self.left_stick_pos = [self.l_cx, self.l_cy]
                        self.dx, self.dy = 0.0, 0.0
                        
                        if self.btn_run.get('auto_active', False):
                            self.btn_run['auto_active'] = False
                            self.btn_run['state'] = self.btn_run.get('previous_state', False)
                            self.btn_run['color'] = (100, 200, 100, self.active_alpha) if self.btn_run['state'] else (100, 100, 100, self.idle_alpha)
                    
                    if touch_id == self.right_touch_id:
                        self.right_touch_id = None
                        self.right_stick_pos = [self.r_cx, self.r_cy]
                        self.right_dx, self.right_dy = 0.0, 0.0
                        
                        self.btn_aim['state'] = False # Reset the hook!
                        
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 3, 'injected': True}))

                if touch_id in self.ui_touches:
                    self.v_mouse_x = x
                    self.v_mouse_y = y
                    self.ui_pressed = False
                    
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(x), int(y)), 'button': 1, 'injected': True}))
                    
                    if not self.ui_touches[touch_id]['moved']:
                        time_pressed = pygame.time.get_ticks() - self.ui_touches[touch_id]['start_time']
                        
                        is_interactable = False
                        if game and self.is_playing:
                            if getattr(game, 'hovered_npc', None) or \
                               getattr(game, 'hovered_item', None) or \
                               getattr(game, 'hovered_container', None) or \
                               getattr(game, 'hovered_interactable_tile_rect', None):
                                is_interactable = True

                        if time_pressed >= 500 or is_interactable:
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(x), int(y)), 'button': 3, 'injected': True}))
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(x), int(y)), 'button': 3, 'injected': True}))
                            
                    del self.ui_touches[touch_id]

    def _update_stick(self, side, x, y):
        if side == 'left':
            center = (self.l_cx, self.l_cy)
            stick = self.left_stick_pos
        else:
            center = (self.r_cx, self.r_cy)
            stick = self.right_stick_pos
            
        dist = math.hypot(x - center[0], y - center[1])
        angle = math.atan2(y - center[1], x - center[0])
        
        if dist > self.joy_base_radius:
            dist = self.joy_base_radius
            
        stick[0] = center[0] + math.cos(angle) * dist
        stick[1] = center[1] + math.sin(angle) * dist
        
        norm_dx = (stick[0] - center[0]) / self.joy_base_radius
        norm_dy = (stick[1] - center[1]) / self.joy_base_radius
        
        if side == 'left':
            self.dx = norm_dx
            self.dy = norm_dy
            
            if dist > self.joy_base_radius * 0.85:
                if not self.btn_run.get('auto_active', False):
                    self.btn_run['auto_active'] = True
                    self.btn_run['previous_state'] = self.btn_run.get('state', False)
                    self.btn_run['state'] = True
                    self.btn_run['color'] = (100, 200, 100, self.active_alpha)
            else:
                if self.btn_run.get('auto_active', False):
                    self.btn_run['auto_active'] = False
                    self.btn_run['state'] = self.btn_run.get('previous_state', False)
                    self.btn_run['color'] = (100, 200, 100, self.active_alpha) if self.btn_run['state'] else (100, 100, 100, self.idle_alpha)

        else:
            self.right_dx = norm_dx
            self.right_dy = norm_dy

    def update_cursor(self, game):
        if not self.enabled: return
        self.is_playing = (getattr(game, 'game_state', 'PLAYING') == 'PLAYING')
        
        if self.is_playing and self.right_touch_id is not None:
            self.v_mouse_x += self.right_dx * 15.0
            self.v_mouse_y += self.right_dy * 15.0
            
            self.v_mouse_x = max(0, min(GAME_WIDTH, self.v_mouse_x))
            self.v_mouse_y = max(0, min(GAME_HEIGHT, self.v_mouse_y))
            
            pygame.event.post(pygame.event.Event(
                pygame.MOUSEMOTION, 
                {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'rel': (0, 0), 'buttons': (0,0,0), 'injected': True}
            ))

    def draw(self, surface):
        if not self.enabled: return
        
        overlay_surf = pygame.Surface((GAME_WIDTH, GAME_HEIGHT), pygame.SRCALPHA)
        
        if self.cursor_img is None:
            try:
                self.cursor_img = pygame.image.load(SPRITE_PATH + 'ui/cursor.png').convert_alpha()
            except Exception:
                self.cursor_img = False 
        
        mx, my = int(self.v_mouse_x), int(self.v_mouse_y)
        
        if self.cursor_img:
            surface.blit(self.cursor_img, (mx, my))
        else:
            pygame.draw.line(surface, (0, 0, 0), (mx - 12, my), (mx + 12, my), 3)
            pygame.draw.line(surface, (0, 0, 0), (mx, my - 12), (mx, my + 12), 3)
            pygame.draw.line(surface, (255, 255, 255), (mx - 11, my), (mx + 11, my), 1)
            pygame.draw.line(surface, (255, 255, 255), (mx, my - 11), (mx, my + 11), 1)
            pygame.draw.circle(surface, (255, 50, 50), (mx, my), 3)
            pygame.draw.circle(surface, (0, 0, 0), (mx, my), 3, 1)

        if self.is_playing:
            pygame.draw.circle(overlay_surf, (30, 30, 30, 80), (self.l_cx, self.l_cy), self.joy_base_radius)
            pygame.draw.circle(overlay_surf, (200, 200, 200, 50), (self.l_cx, self.l_cy), self.joy_base_radius, 2)
            l_color = (220, 220, 220, self.active_alpha) if self.left_touch_id else (150, 150, 150, self.idle_alpha)
            pygame.draw.circle(overlay_surf, l_color, (int(self.left_stick_pos[0]), int(self.left_stick_pos[1])), self.joy_stick_radius)
                
            pygame.draw.circle(overlay_surf, (30, 30, 30, 80), (self.r_cx, self.r_cy), self.joy_base_radius)
            pygame.draw.circle(overlay_surf, (200, 200, 200, 50), (self.r_cx, self.r_cy), self.joy_base_radius, 2)
            r_color = (220, 120, 120, self.active_alpha) if self.right_touch_id else (150, 100, 100, self.idle_alpha)
            pygame.draw.circle(overlay_surf, r_color, (int(self.right_stick_pos[0]), int(self.right_stick_pos[1])), self.joy_stick_radius)
            
            font = pygame.font.SysFont(None, 24)
            for btn in [self.btn_run, self.btn_click, self.btn_interact]:
                pygame.draw.ellipse(overlay_surf, btn['color'], btn['rect'])
                
                is_active = btn.get('pressed') or btn.get('state') or btn.get('auto_active')
                border_alpha = 255 if is_active else 100
                pygame.draw.ellipse(overlay_surf, (255, 255, 255, border_alpha), btn['rect'], 2)
                
                text_surf = font.render(btn['label'], True, (255, 255, 255))
                text_alpha = 255 if is_active else self.idle_alpha + 50
                text_surf.set_alpha(text_alpha)
                overlay_surf.blit(text_surf, text_surf.get_rect(center=btn['rect'].center))

        surface.blit(overlay_surf, (0, 0))