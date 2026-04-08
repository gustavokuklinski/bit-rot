import pygame
import math
import core.data.config 

class VirtualController:
    def __init__(self):
        self.enabled = False 
        self.injected_events = [] # --- FIX: Store events here instead of SDL C-Queue ---
        
        self.v_mouse_x = core.data.config.GAME_WIDTH / 2
        self.v_mouse_y = core.data.config.GAME_HEIGHT / 2
        
        self.joy_base_radius = 80
        self.joy_stick_radius = 35
        
        self.l_cx = 180
        self.l_cy = core.data.config.GAME_HEIGHT - 180
        
        self.r_cx = core.data.config.GAME_WIDTH - 180
        self.r_cy = core.data.config.GAME_HEIGHT - 180
        
        self.left_stick_pos = [self.l_cx, self.l_cy]
        self.left_touch_id = None
        self.dx = 0.0
        self.dy = 0.0
        
        self.idle_alpha = 90    
        self.active_alpha = 220 
        
        btn_r = 40 
        
        self.btn_click = {'rect': pygame.Rect(self.l_cx + 130 - btn_r, self.l_cy - 70 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (150, 50, 50, self.idle_alpha), 'label': 'FIRE'}
        self.btn_interact = {'rect': pygame.Rect(self.l_cx + 130 - btn_r, self.l_cy + 50 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'touch_id': None, 'color': (50, 150, 50, self.idle_alpha), 'label': 'INT', 'last_press': 0}

        self.btn_aim = {'rect': pygame.Rect(self.r_cx - btn_r - 130, self.r_cy - 70 - btn_r, btn_r*2, btn_r*2), 'pressed': False, 'state': False, 'touch_id': None, 'color': (200, 100, 50, self.idle_alpha), 'label': 'AIM'}
        self.btn_run = {'rect': pygame.Rect(self.r_cx - btn_r - 130, self.r_cy + 50 - btn_r, btn_r*2, btn_r*2), 'state': False, 'touch_id': None, 'color': (100, 100, 100, self.idle_alpha), 'label': 'RUN'}

        self.cursor_img = None
        self.is_playing = False 
        
        self.ui_touches = {}
        self.ui_pressed = False

    def _do_auto_aim(self, game):
        if not game.player: return
            
        closest_target = None
        closest_dist = float('inf')
        px, py = game.player.rect.center
        
        potential_targets = []
        potential_targets.extend(getattr(game, 'active_zombies', []))
        potential_targets.extend(getattr(game, 'active_animals', []))
        potential_targets.extend(getattr(game, 'active_npcs', []))
        
        for target in potential_targets:
            if getattr(target, 'is_dead', False): continue
            if getattr(target, 'is_friendly', False) and getattr(target, 'aggro_timer', 0) <= 0: continue

            dx = target.rect.centerx - px
            dy = target.rect.centery - py
            dist = math.hypot(dx, dy)
            
            if dist < (core.data.config.TILE_SIZE * 5) and dist < closest_dist: 
                closest_dist = dist
                closest_target = target
                
        if closest_target:
            zoom = getattr(game, 'zoom_level', 1.0)
            offset_x = getattr(game, 'offset_x', 0)
            offset_y = getattr(game, 'offset_y', 0)
            
            self.v_mouse_x = (closest_target.rect.centerx + offset_x) * zoom + core.data.config.GAME_OFFSET_X
            self.v_mouse_y = (closest_target.rect.centery + offset_y) * zoom
            self.v_mouse_x = max(0, min(core.data.config.GAME_WIDTH, self.v_mouse_x))
            self.v_mouse_y = max(0, min(core.data.config.GAME_HEIGHT, self.v_mouse_y))

    def process_event(self, event, game):
        if not self.enabled: return
        self.is_playing = (getattr(game, 'game_state', 'PLAYING') == 'PLAYING')

        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            try:
                window_w, window_h = pygame.display.get_window_size()
                scale = min(window_w / core.data.config.GAME_WIDTH, window_h / core.data.config.GAME_HEIGHT)
                offset_x = (window_w - core.data.config.GAME_WIDTH * scale) / 2
                offset_y = (window_h - core.data.config.GAME_HEIGHT * scale) / 2
                x = ((event.x * window_w) - offset_x) / scale
                y = ((event.y * window_h) - offset_y) / scale
            except Exception:
                x = event.x * core.data.config.GAME_WIDTH
                y = event.y * core.data.config.GAME_HEIGHT

            touch_id = event.finger_id

            if event.type == pygame.FINGERDOWN:
                is_controller = False
                if self.is_playing:
                    if self.btn_run['rect'].collidepoint(x, y):
                        self.btn_run['state'] = True; self.btn_run['touch_id'] = touch_id; self.btn_run['color'] = (100, 200, 100, self.active_alpha) 
                        is_controller = True
                    elif self.btn_click['rect'].collidepoint(x, y):
                        self.btn_click['pressed'] = True; self.btn_click['touch_id'] = touch_id; self.btn_click['color'] = (255, 50, 50, self.active_alpha)
                        if game.context_menu.get('active') and game.context_menu.get('use_nav'):
                            flat_idx = game.context_menu.get('nav_main_idx', 0)
                            if game.context_menu.get('nav_sub_idx', -1) != -1:
                                flat_idx += 1 + game.context_menu.get('nav_sub_idx', -1)
                            
                            rects = game.context_menu.get('rects', [])
                            if rects and flat_idx < len(rects):
                                self.v_mouse_x, self.v_mouse_y = rects[flat_idx].center
                            
                            self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 1, 'injected': True}))
                            game.context_menu['use_nav'] = False
                        else:
                            self._do_auto_aim(game)
                            self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 1, 'injected': True}))
                        is_controller = True
                    elif self.btn_interact['rect'].collidepoint(x, y):
                        now = pygame.time.get_ticks()
                        if now - self.btn_interact.get('last_press', 0) > 300:
                            self.btn_interact['pressed'] = True; self.btn_interact['touch_id'] = touch_id; self.btn_interact['color'] = (100, 255, 100, self.active_alpha)
                            self.injected_events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e, unicode='e'))
                            self.btn_interact['last_press'] = now
                        is_controller = True
                    elif self.btn_aim['rect'].collidepoint(x, y):
                        self.btn_aim['pressed'] = True; self.btn_aim['touch_id'] = touch_id; self.btn_aim['color'] = (255, 150, 50, self.active_alpha); self.btn_aim['state'] = True 
                        self._do_auto_aim(game)
                        self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 3, 'injected': True}))
                        is_controller = True
                    elif math.hypot(x - self.l_cx, y - self.l_cy) <= self.joy_base_radius:
                        self.left_touch_id = touch_id
                        self._update_stick('left', x, y)
                        is_controller = True

                if not is_controller:
                    self.ui_touches[touch_id] = {'start_time': pygame.time.get_ticks(), 'moved': False, 'start_pos': (x, y)}
                    self.v_mouse_x = x; self.v_mouse_y = y; self.ui_pressed = True
                    
                    self.injected_events.append(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (int(x), int(y)), 'rel': (0, 0), 'buttons': (0,0,0), 'injected': True}))
                    self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(x), int(y)), 'button': 1, 'injected': True}))

            elif event.type == pygame.FINGERMOTION:
                if self.is_playing and touch_id == self.left_touch_id:
                    self._update_stick('left', x, y)
                elif touch_id in self.ui_touches:
                    self.v_mouse_x = x; self.v_mouse_y = y
                    sx, sy = self.ui_touches[touch_id]['start_pos']
                    
                    if not self.ui_touches[touch_id]['moved']:
                        if math.hypot(x - sx, y - sy) > 15:
                            self.ui_touches[touch_id]['moved'] = True
                    
                    if self.ui_touches[touch_id]['moved']:
                        self.injected_events.append(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (int(x), int(y)), 'rel': (event.dx * core.data.config.GAME_WIDTH, event.dy * core.data.config.GAME_HEIGHT), 'buttons': (1,0,0), 'injected': True}))

            elif event.type == pygame.FINGERUP:
                if self.is_playing:
                    if touch_id == self.btn_run.get('touch_id'):
                        self.btn_run['state'] = False; self.btn_run['touch_id'] = None; self.btn_run['color'] = (100, 100, 100, self.idle_alpha)
                    if touch_id == self.btn_click.get('touch_id'):
                        self.btn_click['pressed'] = False; self.btn_click['touch_id'] = None; self.btn_click['color'] = (150, 50, 50, self.idle_alpha)
                        self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 1, 'injected': True}))
                    if touch_id == self.btn_interact.get('touch_id'):
                        self.btn_interact['pressed'] = False; self.btn_interact['touch_id'] = None; self.btn_interact['color'] = (50, 150, 50, self.idle_alpha)
                        self.injected_events.append(pygame.event.Event(pygame.KEYUP, key=pygame.K_e, unicode='e'))
                    if touch_id == self.btn_aim.get('touch_id'):
                        self.btn_aim['pressed'] = False; self.btn_aim['touch_id'] = None; self.btn_aim['color'] = (200, 100, 50, self.idle_alpha); self.btn_aim['state'] = False 
                        self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'button': 3, 'injected': True}))
                    if touch_id == self.left_touch_id:
                        self.left_touch_id = None; self.left_stick_pos = [self.l_cx, self.l_cy]; self.dx, self.dy = 0.0, 0.0

                if touch_id in self.ui_touches:
                    self.v_mouse_x = x; self.v_mouse_y = y; self.ui_pressed = False
                    self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(x), int(y)), 'button': 1, 'injected': True}))
                    
                    if not self.ui_touches[touch_id]['moved']:
                        time_pressed = pygame.time.get_ticks() - self.ui_touches[touch_id]['start_time']
                        if time_pressed >= 500:
                            self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': (int(x), int(y)), 'button': 3, 'injected': True}))
                            self.injected_events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': (int(x), int(y)), 'button': 3, 'injected': True}))
                            
                    del self.ui_touches[touch_id]

    def _update_stick(self, side, x, y):
        if side == 'left':
            center = (self.l_cx, self.l_cy)
            stick = self.left_stick_pos
            dist = math.hypot(x - center[0], y - center[1])
            angle = math.atan2(y - center[1], x - center[0])
            if dist > self.joy_base_radius: dist = self.joy_base_radius
            stick[0] = center[0] + math.cos(angle) * dist
            stick[1] = center[1] + math.sin(angle) * dist
            self.dx = (stick[0] - center[0]) / self.joy_base_radius
            self.dy = (stick[1] - center[1]) / self.joy_base_radius

    def update_cursor(self, game):
        if not self.enabled: return
        self.is_playing = (getattr(game, 'game_state', 'PLAYING') == 'PLAYING')
        
        if self.is_playing and getattr(game, 'player', None):
            self.p_hp = getattr(game.player, 'health', 0); self.p_max_hp = getattr(game.player, 'max_health', 100)
            self.p_sp = getattr(game.player, 'stamina', 0); self.p_max_sp = getattr(game.player, 'max_stamina', 100)
            
        if game.context_menu.get('active'):
            now = pygame.time.get_ticks()
            if 'nav_main_idx' not in game.context_menu:
                game.context_menu['nav_main_idx'] = 0; game.context_menu['nav_sub_idx'] = -1; game.context_menu['use_nav'] = False
            if self.left_touch_id is not None and (abs(self.dx) > 0.5 or abs(self.dy) > 0.5):
                game.context_menu['use_nav'] = True
                if now - getattr(self, 'last_menu_nav', 0) > 200:
                    options = game.context_menu.get('options', [])
                    if options:
                        nav_main = game.context_menu.get('nav_main_idx', 0)
                        nav_sub = game.context_menu.get('nav_sub_idx', -1)
                        if self.dy < -0.5: 
                            if nav_sub != -1: nav_sub = max(0, nav_sub - 1)
                            else: nav_main = max(0, nav_main - 1)
                            self.last_menu_nav = now
                        elif self.dy > 0.5: 
                            if nav_sub != -1: nav_sub = min(len(options[nav_main].get('sub', [])) - 1, nav_sub + 1)
                            else: nav_main = min(len(options) - 1, nav_main + 1)
                            self.last_menu_nav = now
                        elif abs(self.dx) > 0.5: 
                            if nav_sub == -1 and isinstance(options[nav_main], dict) and 'sub' in options[nav_main]: nav_sub = 0
                            elif nav_sub != -1: nav_sub = -1
                            self.last_menu_nav = now
                        game.context_menu['nav_main_idx'] = nav_main
                        game.context_menu['nav_sub_idx'] = nav_sub
            
            if game.context_menu.get('use_nav'):
                flat_idx = game.context_menu.get('nav_main_idx', 0)
                nav_sub = game.context_menu.get('nav_sub_idx', -1)
                if nav_sub != -1:
                    flat_idx += 1 + nav_sub
                
                rects = game.context_menu.get('rects', [])
                if rects and flat_idx < len(rects):
                    self.v_mouse_x, self.v_mouse_y = rects[flat_idx].center

        else:
            game.context_menu['use_nav'] = False; game.context_menu['nav_main_idx'] = 0; game.context_menu['nav_sub_idx'] = -1

        if self.is_playing and self.btn_aim.get('pressed') and not game.context_menu.get('active'):
            self._do_auto_aim(game)
            self.injected_events.append(pygame.event.Event(pygame.MOUSEMOTION, {'pos': (int(self.v_mouse_x), int(self.v_mouse_y)), 'rel': (0, 0), 'buttons': (0,0,0), 'injected': True}))

        if not self.ui_touches and not self.ui_pressed:
            if hasattr(game, 'click_handled') and getattr(game, 'click_handled', False): game.click_handled = False
            if hasattr(game, 'ui_click_handled') and getattr(game, 'ui_click_handled', False): game.ui_click_handled = False

    def draw(self, surface):
        if not self.enabled: return
        pygame.mouse.set_visible(False)
        overlay_surf = pygame.Surface((core.data.config.GAME_WIDTH, core.data.config.GAME_HEIGHT), pygame.SRCALPHA)

        if self.is_playing:
            if hasattr(self, 'p_hp'):
                bar_w, bar_h, base_x, base_y = 120, 10, self.l_cx - 60, self.l_cy - self.joy_base_radius - 50
                font_small = pygame.font.SysFont(None, 16)
                hp_pct = max(0, min(1, self.p_hp / max(1, self.p_max_hp)))
                pygame.draw.rect(overlay_surf, (50, 50, 50, self.active_alpha), (base_x, base_y, bar_w, bar_h))
                pygame.draw.rect(overlay_surf, (200, 50, 50, self.active_alpha), (base_x, base_y, int(bar_w * hp_pct), bar_h))
                pygame.draw.rect(overlay_surf, (255, 255, 255, self.active_alpha), (base_x, base_y, bar_w, bar_h), 1)
                
                hp_lbl = font_small.render("HP", True, (255, 50, 50)); hp_lbl.set_alpha(self.active_alpha)
                overlay_surf.blit(hp_lbl, (base_x - 25, base_y - 1))
                
                st_y = base_y + 15
                st_pct = max(0, min(1, self.p_sp / max(1, self.p_max_sp)))
                pygame.draw.rect(overlay_surf, (50, 50, 50, self.active_alpha), (base_x, st_y, bar_w, bar_h))
                pygame.draw.rect(overlay_surf, (50, 200, 50, self.active_alpha), (base_x, st_y, int(bar_w * st_pct), bar_h))
                pygame.draw.rect(overlay_surf, (255, 255, 255, self.active_alpha), (base_x, st_y, bar_w, bar_h), 1)
                
                st_lbl = font_small.render("SP", True, (50, 255, 50)); st_lbl.set_alpha(self.active_alpha)
                overlay_surf.blit(st_lbl, (base_x - 25, st_y - 1))

            pygame.draw.circle(overlay_surf, (30, 30, 30, 80), (self.l_cx, self.l_cy), self.joy_base_radius)
            pygame.draw.circle(overlay_surf, (200, 200, 200, 50), (self.l_cx, self.l_cy), self.joy_base_radius, 2)
            l_color = (220, 220, 220, self.active_alpha) if self.left_touch_id else (150, 150, 150, self.idle_alpha)
            pygame.draw.circle(overlay_surf, l_color, (int(self.left_stick_pos[0]), int(self.left_stick_pos[1])), self.joy_stick_radius)
            
            font = pygame.font.SysFont(None, 24)
            for btn in [self.btn_run, self.btn_click, self.btn_interact, self.btn_aim]:
                pygame.draw.ellipse(overlay_surf, btn['color'], btn['rect'])
                is_active = btn.get('pressed') or btn.get('state') or btn.get('auto_active')
                pygame.draw.ellipse(overlay_surf, (255, 255, 255, 255 if is_active else 100), btn['rect'], 2)
                
                text_surf = font.render(btn['label'], True, (255, 255, 255))
                text_surf.set_alpha(255 if is_active else self.idle_alpha + 50)
                overlay_surf.blit(text_surf, text_surf.get_rect(center=btn['rect'].center))

        surface.blit(overlay_surf, (0, 0))