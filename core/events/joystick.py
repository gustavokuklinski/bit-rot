import pygame
import sys
import math
import time
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_slot_rect_in_modal, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect

# XBOX Controller mapping for Pygame 2 (SDL2 standard)
BTN_A = 0
BTN_B = 1
BTN_X = 2
BTN_Y = 3
BTN_LB = 4  # Used for Zoom Out (-) / Prev Tab
BTN_RB = 5  # Used for Zoom In (+) / Next Tab
BTN_SELECT = 6 # Fast Forward Time
BTN_START = 7  # Toggle Modals (TAB behavior)
BTN_L3 = 8     # Pause Game
BTN_R3 = 9

# ---------------------------------------------------------
# Dynamic Axis Mapping (Cross-Platform)
# ---------------------------------------------------------
if sys.platform.startswith('linux'):
    # Linux / 8BitDo quirk mapping
    AXIS_LX = 0
    AXIS_LY = 1
    AXIS_LT = 2  # Linux slides LT into Axis 2
    AXIS_RX = 3  # Shifted down
    AXIS_RY = 4  # Shifted down
    AXIS_RT = 5
else:
    # Standard Windows / macOS XInput mapping
    AXIS_LX = 0
    AXIS_LY = 1
    AXIS_RX = 2
    AXIS_RY = 3
    AXIS_LT = 4
    AXIS_RT = 5

class JoystickHandler:
    def __init__(self, logger=None):
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        self.active_controller = None
        
        # ---> INCREASED SENSITIVITY <---
        self.cursor_speed = 12.0 
        self.deadzone = 0.2
        self.last_snap_time = 0
        
        # Logical Navigation Memory for Context Menus
        self.c_main_idx = None 
        self.c_sub_idx = -1
        
        # Combo state tracking
        self.y_pressed = False
        self.b_pressed = False
        
        self.set_xbox_controller(logger)

    def set_xbox_controller(self, logger):
        """Finds and sets the first connected Xbox-style or 8BitDo controller"""
        for joy in self.joysticks:
            name = joy.get_name().lower()
            if any(x in name for x in ["xbox", "x-box", "controller", "8bitdo", "pad", "wireless"]):
                self.active_controller = joy
                msg = f"[Joystick] Successfully Connected to: {joy.get_name()}"
                if logger: logger.info(msg)
                else: print(msg)
                return
        
        if self.joysticks:
            self.active_controller = self.joysticks[0]
            msg = f"[Joystick] Defaulting to: {self.active_controller.get_name()}"
            if logger: logger.info(msg)
            else: print(msg)
        else:
            msg = "[Joystick] No controllers detected."
            if logger: logger.info(msg)
            else: print(msg)

    def check_connections(self, logger=None):
        if pygame.joystick.get_count() != len(self.joysticks):
            self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            self.set_xbox_controller(logger)

    def get_all_ui_slots(self, game):
        """Dynamically fetches active window control rects for cursor snapping"""
        
        if getattr(game, 'context_menu', {}).get('active', False):
            return game.context_menu.get('rects', [])
            
        rects = []
            
        if hasattr(game, 'modal_buttons'):
            for b in game.modal_buttons:
                if b:
                    if isinstance(b, pygame.Rect): rects.append(b)
                    elif isinstance(b, dict) and 'rect' in b: rects.append(b['rect'])
                    
        return rects

    def _set_mouse_pos_scaled(self, game, logic_x, logic_y):
        """Calculates exact letterbox scaling offsets to permanently prevent Tooltip desynchronization"""
        phys_x, phys_y = logic_x, logic_y
        
        if hasattr(game, 'game_screen') and pygame.display.get_surface():
            display_surf = pygame.display.get_surface()
            
            if game.game_screen is not display_surf:
                phys_w, phys_h = display_surf.get_size()
                log_w, log_h = game.game_screen.get_size()
                
                if log_w > 0 and log_h > 0:
                    scale = min(phys_w / log_w, phys_h / log_h)
                    scaled_w = int(log_w * scale)
                    scaled_h = int(log_h * scale)
                    
                    offset_x = (phys_w - scaled_w) // 2
                    offset_y = (phys_h - scaled_h) // 2
                    
                    phys_x = (logic_x * scale) + offset_x
                    phys_y = (logic_y * scale) + offset_y

        pygame.mouse.set_pos((int(phys_x), int(phys_y)))
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEMOTION, 
            {'pos': (int(logic_x), int(logic_y)), 'rel': (0, 0), 'buttons': pygame.mouse.get_pressed()}
        ))

    def update_cursor(self, game):
        """Updates mouse position using Free Cursor or UI Snap Logic"""
        self.last_game_ref = game 
        
        if not getattr(game, 'context_menu', {}).get('active', False):
            self.c_main_idx = None 

        # ---------------------------------------------------------
        # UNIFIED SNAP CURSOR (Keyboard Arrows & Joystick)
        # ---------------------------------------------------------
        keys = pygame.key.get_pressed()
        rx, ry = 0.0, 0.0
        
        # 1. Read Keyboard Arrows natively into analog values
        if keys[pygame.K_LEFT]:  rx -= 1.0
        if keys[pygame.K_RIGHT]: rx += 1.0
        if keys[pygame.K_UP]:    ry -= 1.0
        if keys[pygame.K_DOWN]:  ry += 1.0
        
        # Normalize diagonal keyboard movement
        if rx != 0 and ry != 0:
            length = math.hypot(rx, ry)
            rx /= length
            ry /= length

        # 2. Read Joystick (Overrides keyboard if actively past deadzone)
        joy_numaxes = 4 if not self.active_controller else self.active_controller.get_numaxes()
        if self.active_controller and joy_numaxes >= 4:
            j_rx = self.active_controller.get_axis(AXIS_RX)
            j_ry = self.active_controller.get_axis(AXIS_RY)
            if abs(j_rx) >= self.deadzone: rx = j_rx
            if abs(j_ry) >= self.deadzone: ry = j_ry

        # 3. Process identical snap physics for both inputs
        if joy_numaxes >= 4:
            if rx != 0 or ry != 0:
                self.c_main_idx = None 
                
                if hasattr(game, '_get_scaled_mouse_pos'):
                    mx, my = game._get_scaled_mouse_pos()
                else:
                    mx, my = pygame.mouse.get_pos()
                    
                is_aiming = False
                joy = self.active_controller
                if joy.get_numaxes() > AXIS_RT and joy.get_axis(AXIS_RT) > 0.0:
                    is_aiming = True
                elif hasattr(game, 'player') and getattr(game.player, 'is_aiming', False):
                    is_aiming = True
                    
                ui_rects = [] if is_aiming else self.get_all_ui_slots(game)
                
                current_slot = None
                for r in ui_rects:
                    if r.collidepoint((mx, my)):
                        current_slot = r
                        break
                
                current_time = time.time()
                is_snapping = False
                
                if current_slot:
                    if current_time - self.last_snap_time > 0.2: 
                        dx = 1 if rx > 0 else -1 if rx < 0 else 0
                        dy = 1 if ry > 0 else -1 if ry < 0 else 0
                        if abs(rx) > abs(ry): dy = 0
                        else: dx = 0
                        
                        best_rect = None
                        best_dist = float('inf')
                        cx, cy = current_slot.center
                        target_angle = math.atan2(dy, dx)
                        
                        for r in ui_rects:
                            if r == current_slot: continue
                            tx, ty = r.center
                            angle = math.atan2(ty - cy, tx - cx)
                            
                            diff = abs(angle - target_angle)
                            if diff > math.pi: diff = 2 * math.pi - diff
                            
                            if diff < math.pi / 4:
                                gap_x = max(0, abs(tx - cx) - (current_slot.width + r.width) / 2)
                                gap_y = max(0, abs(ty - cy) - (current_slot.height + r.height) / 2)
                                gap = math.hypot(gap_x, gap_y)
                                
                                if gap <= 35:
                                    dist = math.hypot(tx - cx, ty - cy)
                                    if dist < best_dist:
                                        best_dist = dist
                                        best_rect = r
                        
                        if best_rect:
                            self._set_mouse_pos_scaled(game, best_rect.centerx, best_rect.centery)
                            self.last_snap_time = current_time
                        else:
                            escape_x, escape_y = mx, my
                            if dx > 0: escape_x = current_slot.right + 15
                            elif dx < 0: escape_x = current_slot.left - 15
                            
                            if dy > 0: escape_y = current_slot.bottom + 15
                            elif dy < 0: escape_y = current_slot.top - 15
                            
                            screen_w, screen_h = game.game_screen.get_size() if hasattr(game, 'game_screen') else pygame.display.get_surface().get_size()
                            escape_x = max(0, min(escape_x, screen_w))
                            escape_y = max(0, min(escape_y, screen_h))
                            
                            self._set_mouse_pos_scaled(game, escape_x, escape_y)
                            self.last_snap_time = current_time
                            
                    is_snapping = True
                
                if not is_snapping:
                    screen_w, screen_h = game.game_screen.get_size() if hasattr(game, 'game_screen') else pygame.display.get_surface().get_size()
                    new_x = max(0, min(mx + int(rx * self.cursor_speed), screen_w))
                    new_y = max(0, min(my + int(ry * self.cursor_speed), screen_h))
                    
                    entered_slot = None
                    for r in ui_rects:
                        if r.inflate(20, 20).collidepoint((new_x, new_y)):
                            entered_slot = r
                            break
                    
                    if entered_slot:
                        self._set_mouse_pos_scaled(game, entered_slot.centerx, entered_slot.centery)
                    else:
                        self._set_mouse_pos_scaled(game, new_x, new_y)

            # Make Hovered Modal Active (Bring to Front)
            if hasattr(game, 'modals') and game.modals:
                if hasattr(game, '_get_scaled_mouse_pos'):
                    logic_x, logic_y = game._get_scaled_mouse_pos()
                else:
                    logic_x, logic_y = pygame.mouse.get_pos()
                    
                hovered_modal = None
                for m in reversed(game.modals):
                    if m.get('rect') and m['rect'].collidepoint((logic_x, logic_y)):
                        hovered_modal = m
                        break
                        
                if hovered_modal and game.modals[-1] != hovered_modal:
                    game.modals.remove(hovered_modal)
                    game.modals.append(hovered_modal)

    def get_movement_axes(self):
        """Returns Left Analog Stick X and Y for free player movement"""
        if not self.active_controller:
            return 0, 0
            
        joy = self.active_controller
        lx, ly = 0, 0
        
        if joy.get_numaxes() >= 2:
            lx = joy.get_axis(AXIS_LX)
            ly = joy.get_axis(AXIS_LY)
        
        if abs(lx) < self.deadzone: lx = 0
        if abs(ly) < self.deadzone: ly = 0
        
        return lx, ly

    def get_action_states(self):
        joy_run = False
        joy_aim = False
        
        if not self.joysticks:
            return joy_run, joy_aim

        try:
            # Ask the joystick how many buttons it actually has before checking them
            num_buttons = self.joysticks.get_numbuttons()
            
            # Replace BTN_RUN / BTN_AIM with whatever your actual button variables are called
            if hasattr(self, 'BTN_RUN') and self.BTN_RUN < num_buttons:
                joy_run = self.joysticks.get_button(self.BTN_RUN)
                
            if hasattr(self, 'BTN_AIM') and self.BTN_AIM < num_buttons:
                joy_aim = self.joysticks.get_button(self.BTN_AIM)
                
        except pygame.error:
            # If the controller drops connection or bugs out, just ignore it
            pass
            
        return joy_run, joy_aim

    def process_event(self, event):
        """Translates joystick hardware events into standard keyboard/mouse events"""
        
        # --- GLOBAL KEYBOARD CLICK INTERCEPTION ---
        # --- GLOBAL KEYBOARD CLICK INTERCEPTION ---
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                game = getattr(self, 'last_game_ref', None)
                mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 1}))
            elif event.key == pygame.K_RALT: # ALT GR for Right Click
                game = getattr(self, 'last_game_ref', None)
                mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 3}))
                
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_SPACE:
                game = getattr(self, 'last_game_ref', None)
                mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))
            elif event.key == pygame.K_RALT:
                game = getattr(self, 'last_game_ref', None)
                mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 3}))

        if event.type == pygame.JOYAXISMOTION:
            if event.axis == AXIS_LT: 
                mouse_pos = pygame.mouse.get_pos()
                game = getattr(self, 'last_game_ref', None)
                
                is_holding_item = False
                in_ui_bounds = False
                
                if game:
                    is_holding_item = getattr(game, 'is_dragging', False) or getattr(game, 'drag_candidate', None) is not None
                    
                    if not is_holding_item:
                        self.is_toggle_dragging = False 
                    
                    for m in getattr(game, 'modals', []):
                        if m.get('rect') and m['rect'].collidepoint(mouse_pos):
                            in_ui_bounds = True
                            break
                            
                    
                                
                    if not in_ui_bounds and getattr(game, 'context_menu', {}).get('active', False):
                        in_ui_bounds = True

                if event.value > 0.5 and not getattr(self, 'lt_pressed', False):
                    self.lt_pressed = True
                    self.lt_press_time = time.time()
                    self.lt_action_was_ui = in_ui_bounds or is_holding_item
                    
                    if self.lt_action_was_ui:
                        if getattr(self, 'is_toggle_dragging', False):
                            self.is_toggle_dragging = False
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))
                            self.lt_handled_drop = True 
                        else:
                            self.lt_handled_drop = False
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 1}))
                    else:
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 1}))

                elif event.value <= 0.5 and getattr(self, 'lt_pressed', False):
                    self.lt_pressed = False
                    held_duration = time.time() - getattr(self, 'lt_press_time', 0)
                    
                    if getattr(self, 'lt_action_was_ui', False):
                        if not getattr(self, 'lt_handled_drop', False):
                            if held_duration < 0.25:
                                self.is_toggle_dragging = True
                            else:
                                self.is_toggle_dragging = False
                                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))
                    else:
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))

        elif event.type == pygame.JOYBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            game = getattr(self, 'last_game_ref', None)
            
            # ---> Y Button: Strictly Interact (No Modal Closing) <---
            if event.button == BTN_Y: 
                self.y_pressed = True
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_e, 'unicode': 'e'}))
                    
            elif event.button == BTN_B: 
                self.b_pressed = True
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 3}))
            elif event.button == BTN_X: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_r, 'unicode': 'r'}))
            
            # ---> BTN 8 (L3): Pause Game (F2) <---
            elif event.button == BTN_L3: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F2, 'unicode': ''}))
            
            # ---> BTN 7 (START): Toggle Modals (TAB) <---
            elif event.button == BTN_START: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_TAB, 'unicode': '\t'}))
                
            # ---> BTN 6 (SELECT): Fast Forward (F) <---
            elif event.button == BTN_SELECT: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_f, 'unicode': 'f'}))
                
            elif event.button in (BTN_LB, BTN_RB):
                handled_tab = False
                
                if game:
                    logic_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else mouse_pos
                    
                    target_modal = None
                    for m in reversed(getattr(game, 'modals', [])):
                        if m.get('rect') and m['rect'].collidepoint(logic_pos):
                            target_modal = m
                            break
                            
                    if target_modal:
                        tabs_data = target_modal.get('tabs_data') or target_modal.get('help_tabs')
                        
                        if tabs_data:
                            active_key = None
                            current_val = None
                            
                            if 'active_tab' in target_modal:
                                active_key = 'active_tab'
                                current_val = target_modal['active_tab']
                            elif 'active_help_tab' in target_modal:
                                active_key = 'active_help_tab'
                                current_val = target_modal['active_help_tab']
                                
                            if active_key is not None:
                                current_idx = 0
                                for i, t in enumerate(tabs_data):
                                    label = t.get('label') or t.get('title')
                                    if current_val == label or current_val == i:
                                        current_idx = i
                                        break
                                        
                                if event.button == BTN_RB:
                                    current_idx = (current_idx + 1) % len(tabs_data)
                                else:
                                    current_idx = (current_idx - 1) % len(tabs_data)
                                    
                                next_tab = tabs_data[current_idx]
                                
                                if isinstance(current_val, str):
                                    target_modal[active_key] = next_tab.get('label') or next_tab.get('title')
                                else:
                                    target_modal[active_key] = current_idx
                                    
                                if 'scroll_offset_y' in target_modal: target_modal['scroll_offset_y'] = 0
                                if 'crafting_scroll_offset' in target_modal: target_modal['crafting_scroll_offset'] = 0
                                if 'inventory_scroll' in target_modal: target_modal['inventory_scroll'] = 0
                                
                                handled_tab = True
                                
                if not handled_tab:
                    if event.button == BTN_LB: 
                        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': -1, 'x': 0}))
                    elif event.button == BTN_RB: 
                        pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': 1, 'x': 0}))

        elif event.type == pygame.JOYBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            
            if event.button == BTN_B: 
                self.b_pressed = False
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 3}))
            elif event.button == BTN_Y: 
                self.y_pressed = False
                pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': pygame.K_e, 'unicode': 'e'}))
                
        elif event.type == pygame.JOYHATMOTION:
            x, y = event.value
            mouse_pos = pygame.mouse.get_pos()
            game = getattr(self, 'last_game_ref', None)
            
            if x != 0 or y != 0:
                if getattr(self, 'y_pressed', False):
                    if y == 1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_h, 'unicode': 'h'})) # Status
                    elif y == -1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_g, 'unicode': 'g'})) # Gear
                    elif x == -1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_i, 'unicode': 'i'})) # Inventory
                    elif x == 1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_n, 'unicode': 'n'})) # Nearby
                    return 
                    
                if getattr(self, 'b_pressed', False):
                    if y == 1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_m, 'unicode': 'm'})) # Messages
                    elif y == -1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_c, 'unicode': 'c'})) # Crafting
                    elif x == -1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_m, 'unicode': 'm'})) # Messages
                    elif x == 1: pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_SLASH, 'unicode': '?'})) # Help
                    return 
            
            if game and getattr(game, 'context_menu', {}).get('active', False):
                options = game.context_menu.get('options', [])
                if options and (x != 0 or y != 0):
                    rects = game.context_menu.get('rects', [])
                    action_map = game.context_menu.get('action_map', [])
                    
                    if self.c_main_idx is None:
                        self.c_main_idx = 0
                        self.c_sub_idx = -1
                        logic_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else mouse_pos
                        
                        for i, r in enumerate(rects):
                            if r.collidepoint(logic_pos):
                                action = action_map[i]
                                if "::" in action:
                                    parent_label, sub_name = action.split("::")
                                    for m_i, opt in enumerate(options):
                                        if isinstance(opt, dict) and opt['label'] == parent_label:
                                            self.c_main_idx = m_i
                                            if sub_name in opt['sub']: self.c_sub_idx = opt['sub'].index(sub_name)
                                            break
                                else:
                                    for m_i, opt in enumerate(options):
                                        if not isinstance(opt, dict) and opt == action:
                                            self.c_main_idx = m_i
                                            break
                                break

                    if self.c_main_idx >= len(options): self.c_main_idx = 0

                    if y == 1: # Up
                        if self.c_sub_idx != -1:
                            self.c_sub_idx -= 1
                            if self.c_sub_idx < 0: self.c_sub_idx = len(options[self.c_main_idx]['sub']) - 1
                        else:
                            self.c_main_idx -= 1
                            if self.c_main_idx < 0: self.c_main_idx = len(options) - 1
                    elif y == -1: # Down
                        if self.c_sub_idx != -1:
                            self.c_sub_idx += 1
                            if self.c_sub_idx >= len(options[self.c_main_idx]['sub']): self.c_sub_idx = 0
                        else:
                            self.c_main_idx += 1
                            if self.c_main_idx >= len(options): self.c_main_idx = 0
                            
                    elif x == 1: # Right
                        if self.c_sub_idx == -1 and isinstance(options[self.c_main_idx], dict):
                            self.c_sub_idx = 0 
                    elif x == -1: # Left
                        if self.c_sub_idx != -1:
                            self.c_sub_idx = -1

                    target_rect = None
                    
                    if self.c_sub_idx != -1:
                        target_action = f"{options[self.c_main_idx]['label']}::{options[self.c_main_idx]['sub'][self.c_sub_idx]}"
                        for i, action in enumerate(action_map):
                            if action == target_action:
                                target_rect = rects[i]
                                break
                    else:
                        target_opt = options[self.c_main_idx]
                        if isinstance(target_opt, dict):
                            main_x, menu_y = None, None
                            for i, action in enumerate(action_map):
                                if "::" not in action:
                                    main_x = rects[i].x
                                    for opt_i, opt in enumerate(options):
                                        if not isinstance(opt, dict) and opt == action:
                                            menu_y = rects[i].y - (opt_i * 25)
                                            break
                                    if main_x is not None and menu_y is not None:
                                        break
                                        
                            if main_x is None or menu_y is None:
                                base_x, base_y = game.context_menu.get('position', (0,0))
                                surf = getattr(game, 'game_screen', pygame.display.get_surface())
                                if surf:
                                    screen_h = surf.get_height()
                                    if base_y + (len(options) * 25) > screen_h:
                                        base_y -= (len(options) * 25)
                                    main_x, menu_y = base_x, base_y
                                    
                            target_rect = pygame.Rect(main_x, menu_y + self.c_main_idx * 25, 100, 25)
                        else:
                            for i, action in enumerate(action_map):
                                if action == target_opt:
                                    target_rect = rects[i]
                                    break

                    if target_rect:
                        self._set_mouse_pos_scaled(game, target_rect.centerx, target_rect.centery)
                return 

            if y == 1: # Up
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': 1, 'x': 0, 'from_dpad': True})) 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 4}))
            elif y == -1: # Down
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': -1, 'x': 0, 'from_dpad': True})) 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 5}))
                
            if x != 0:
                current_index = getattr(self, 'belt_index', -1)
                if x == -1: # Left
                    current_index = 4 if current_index <= 0 else current_index - 1
                elif x == 1: # Right
                    current_index = 0 if current_index >= 4 else current_index + 1
                    
                self.belt_index = current_index
                key_to_send = pygame.K_1 + current_index
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN, 
                    {'key': key_to_send, 'unicode': str(current_index + 1)}
                ))