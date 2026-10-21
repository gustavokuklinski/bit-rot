# core/events/joystick.py

import pygame
import sys
import math
import time
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_hud_slot_rect
from core.ui.container_modal import get_container_slot_rect
from core.ui.helpers.keybinds import keybind_manager

# XBOX Controller mapping for Pygame 2 (SDL2 standard)
BTN_A = 0
BTN_B = 1
BTN_X = 2
BTN_Y = 3
BTN_LB = 4  # Prev Tab
BTN_RB = 5  # Next Tab
BTN_SELECT = 6
BTN_START = 7  # Toggle Modals
BTN_L3 = 8     # Pause Game
BTN_R3 = 9

# Dynamic Axis Mapping (Cross-Platform)
if sys.platform.startswith('linux'):
    AXIS_LX = 0
    AXIS_LY = 1
    AXIS_LT = 2
    AXIS_RX = 3
    AXIS_RY = 4
    AXIS_RT = 5
else:
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
        
        self.cursor_speed = 12.0 
        self.deadzone = 0.2
        
        # Logical Navigation Memory for Context Menus
        self.c_main_idx = None 
        self.c_sub_idx = -1

        # Slot Navigation State (Exclusively driven by D-Pad)
        self.in_slot_mode = False
        self.cursor_hidden = False
        self.current_slot_rect = None
        
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

    def get_all_interactive_slots(self, game):
        """Gathers all currently visible and clickable item slot rectangles."""
        if getattr(game, 'context_menu', {}).get('active', False):
            return game.context_menu.get('rects', [])

        slots = []

        # 1. Topmost Modal Slots
        top_modal = None
        for modal in reversed(getattr(game, 'modals', [])):
            if modal.get('rect'):
                top_modal = modal
                break

        if top_modal:
            m_type = top_modal.get('type')
            pos = top_modal.get('position', (0, 0))

            if m_type == 'inventory':
                active_tab = top_modal.get('active_tab', 'Inventory')
                if active_tab == 'Inventory':
                    slots.extend([get_inventory_slot_rect(i, pos) for i in range(15)])
                elif active_tab in top_modal.get('container_mapping', {}):
                    c = top_modal['container_mapping'][active_tab]
                    if c and hasattr(c, 'capacity'):
                        c_pos = (top_modal['rect'].x, top_modal['rect'].y + 40)
                        slots.extend([get_container_slot_rect(c_pos, i) for i in range(c.capacity or 0)])

            elif m_type == 'gear':
                active_tab = top_modal.get('active_tab', 'Gear')
                if active_tab == 'Gear':
                    slots.extend(list(top_modal.get('gear_slot_rects', {}).values()))
                elif active_tab in top_modal.get('container_mapping', {}):
                    c = top_modal['container_mapping'][active_tab]
                    if c and hasattr(c, 'capacity'):
                        c_pos = (top_modal['rect'].x, top_modal['rect'].y + 40)
                        slots.extend([get_container_slot_rect(c_pos, i) for i in range(c.capacity or 0)])

            elif m_type == 'container':
                c = top_modal.get('item')
                if c and hasattr(c, 'capacity'):
                    slots.extend([get_container_slot_rect(pos, i) for i in range(c.capacity or 0)])

            elif m_type == 'nearby':
                content_rect = top_modal.get('content_rect')
                active_tab = top_modal.get('active_tab')
                target_container = None
                for t in top_modal.get('tabs_data', []):
                    if t.get('label') == active_tab:
                        target_container = t.get('container')
                        break
                if target_container and content_rect:
                    slots.extend([get_container_slot_rect(content_rect.topleft, i) for i in range(target_container.capacity or 0)])

            elif m_type == 'slots':
                slots.extend([s['rect'] for s in top_modal.get('slot_rects', [])])

            elif m_type == 'vehicle':
                if top_modal.get('active_tab') == 'Mechanics':
                    slots.extend(list(top_modal.get('equipment_rects', {}).values()))

            elif m_type == 'mobile':
                if top_modal.get('active_tab') == 'Apps':
                    slots.extend([s['rect'] for s in top_modal.get('app_slot_rects', [])])

            elif m_type == 'npc_dialog':
                if top_modal.get('active_tab_index') == 2:
                    slots.extend([s['rect'] for s in top_modal.get('trade_slot_rects', [])])

        # 2. Belt HUD Slots
        if getattr(game, 'player', None) and getattr(game.player, 'belt', None):
            slots.extend([get_belt_hud_slot_rect(i, game=game) for i in range(len(game.player.belt))])

        return slots

    def _set_mouse_pos_scaled(self, game, logic_x, logic_y):
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

    def _find_neighbor_slot(self, current_slot, all_slots, dir_x, dir_y):
        """Finds the geometrically closest slot in the specified D-Pad direction."""
        cx, cy = current_slot.center
        best_slot = None
        best_score = float('inf')

        for s in all_slots:
            if s == current_slot:
                continue
            sx, sy = s.center
            dx = sx - cx
            dy = sy - cy

            valid = False
            score = float('inf')

            # Horizontal Navigation (Right / Left)
            if dir_x > 0 and dx > 8:
                valid = True
                score = dx + abs(dy) * 2.2
            elif dir_x < 0 and dx < -8:
                valid = True
                score = -dx + abs(dy) * 2.2

            # Vertical Navigation (Down / Up)
            elif dir_y > 0 and dy > 8:
                valid = True
                score = dy + abs(dx) * 2.2
            elif dir_y < 0 and dy < -8:
                valid = True
                score = -dy + abs(dx) * 2.2

            if valid and score < best_score:
                best_score = score
                best_slot = s

        return best_slot

    def update_cursor(self, game):
        self.last_game_ref = game 
        
        if not getattr(game, 'context_menu', {}).get('active', False):
            self.c_main_idx = None 

        if not self.active_controller:
            self.cursor_hidden = False
            self.in_slot_mode = False
            return

        # 1. Read Analog Stick Input (Right Stick)
        rx, ry = 0.0, 0.0
        if self.active_controller.get_numaxes() >= 4:
            j_rx = self.active_controller.get_axis(AXIS_RX)
            j_ry = self.active_controller.get_axis(AXIS_RY)
            if abs(j_rx) >= self.deadzone: rx = j_rx
            if abs(j_ry) >= self.deadzone: ry = j_ry

        # 2. IF ANALOG STICK MOVES: IMMEDIATELY LOSE FOCUS, SHOW CURSOR, AND MOVE FREELY!
        if rx != 0.0 or ry != 0.0:
            self.in_slot_mode = False
            self.cursor_hidden = False
            self.current_slot_rect = None

            mx, my = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
            screen_w, screen_h = game.game_screen.get_size() if hasattr(game, 'game_screen') else pygame.display.get_surface().get_size()

            new_x = max(0, min(mx + int(rx * self.cursor_speed), screen_w))
            new_y = max(0, min(my + int(ry * self.cursor_speed), screen_h))

            # Free movement — never magnetic, never stuck!
            self._set_mouse_pos_scaled(game, new_x, new_y)

    def get_movement_axes(self):
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

    def is_rt_pressed(self):
        """Checks if the Right Trigger is being pulled for Aiming"""
        if self.active_controller and self.active_controller.get_numaxes() > AXIS_RT:
            return self.active_controller.get_axis(AXIS_RT) > 0.2
        return False

    def process_event(self, event):
        """Translates joystick hardware events into standard keyboard/mouse events"""

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
            
            # ---> X Button (2): Open Context Menu (Simulates Right Click) <---
            if event.button == BTN_X:
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 3}))
            
            # Modal Tab Navigation (LB/RB)
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
            if event.button == BTN_X:
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 3}))
                
        elif event.type == pygame.JOYHATMOTION:
            x, y = event.value
            mouse_pos = pygame.mouse.get_pos()
            game = getattr(self, 'last_game_ref', None)
            
            # 1. Context Menu D-Pad Navigation
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

            # 2. D-PAD EXCLUSIVE SLOT NAVIGATION
            if game and (x != 0 or y != 0):
                interactive_slots = self.get_all_interactive_slots(game)
                if interactive_slots:
                    logic_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else mouse_pos
                    
                    # If not yet in slot mode, lock to the slot under or nearest to the cursor
                    if not self.in_slot_mode or not self.current_slot_rect:
                        current_slot = next((s for s in interactive_slots if s.collidepoint(logic_pos)), None)
                        if not current_slot:
                            current_slot = min(interactive_slots, key=lambda s: (s.centerx - logic_pos[0])**2 + (s.centery - logic_pos[1])**2)

                        self.current_slot_rect = current_slot
                        self.in_slot_mode = True
                        self.cursor_hidden = True
                        self._set_mouse_pos_scaled(game, current_slot.centerx, current_slot.centery)
                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_ui_hover()

                    # Navigate to neighbor in D-pad direction
                    dir_x = x
                    dir_y = -y  # Invert D-pad Y so Up (y=1) moves to negative y
                    neighbor = self._find_neighbor_slot(self.current_slot_rect, interactive_slots, dir_x, dir_y)
                    if neighbor:
                        self.current_slot_rect = neighbor
                        self.in_slot_mode = True
                        self.cursor_hidden = True
                        self._set_mouse_pos_scaled(game, neighbor.centerx, neighbor.centery)
                        if hasattr(game, 'sound_manager'):
                            game.sound_manager.play_ui_hover()
                    return

            # 3. Fallback when no slots exist
            if y == 1:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': 1, 'x': 0, 'from_dpad': True})) 
            elif y == -1:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': -1, 'x': 0, 'from_dpad': True})) 
                
            if x != 0 and not getattr(game, 'modals', []):
                current_index = getattr(self, 'belt_index', -1)
                max_idx = (len(game.player.belt) - 1) if (game and getattr(game, 'player', None)) else 1
                if x == -1:
                    current_index = max_idx if current_index <= 0 else current_index - 1
                elif x == 1:
                    current_index = 0 if current_index >= max_idx else current_index + 1
                    
                self.belt_index = current_index
                key_to_send = pygame.K_1 + current_index
                pygame.event.post(pygame.event.Event(
                    pygame.KEYDOWN, 
                    {'key': key_to_send, 'unicode': str(current_index + 1)}
                ))