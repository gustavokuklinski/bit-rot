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
BTN_LB = 4  # Used for Zoom Out (-)
BTN_RB = 5  # Used for Zoom In (+)
BTN_SELECT = 6 # Fast Forward
BTN_START = 7  # Pause
BTN_L3 = 8
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
        self.cursor_speed = 24.0 
        self.deadzone = 0.2
        self.last_snap_time = 0
        
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
        """Dynamically fetches all active slot rects from HUD and Modals for cursor snapping"""
        
        # ---> NEW: Context Menu (Highest Z-Index Priority) <---
        # If the context menu is active, ONLY return its rects. 
        # This isolates the cursor, preventing it from snapping to background UI slots.
        if getattr(game, 'context_menu', {}).get('active', False):
            return game.context_menu.get('rects', [])
            
            
        rects = []
        # Always add the persistent bottom HUD belt
        #for i in range(5):
        #    rects.append(get_belt_hud_slot_rect(i))
            
        for modal in game.modals:
            if modal.get('minimized'): continue
            
            # Include Tabs as Snap Targets so player can click/drop on them
            if 'tab_rects' in modal:
                rects.extend(modal['tab_rects'])
            
            m_type = modal.get('type')
            m_pos = modal.get('position', (0,0))
            
            if m_type == 'inventory':
                if modal.get('active_tab', 'Inventory') == 'Inventory':
                    for i in range(10): rects.append(get_inventory_slot_rect(i, m_pos))
                    for i in range(5): rects.append(get_belt_slot_rect_in_modal(i, m_pos))
                elif modal.get('active_tab') in modal.get('container_mapping', {}):
                    container = modal['container_mapping'][modal['active_tab']]
                    p_calc = (modal.get('rect', pygame.Rect(m_pos,(0,0))).x, modal.get('rect', pygame.Rect(m_pos,(0,0))).y + 40)
                    for i in range(container.capacity or 0): rects.append(get_container_slot_rect(p_calc, i))
            
            elif m_type == 'container':
                container = modal.get('item')
                if container:
                    for i in range(container.capacity or 0): rects.append(get_container_slot_rect(m_pos, i))
                    
            elif m_type == 'nearby':
                active_tab_label = modal.get('active_tab')
                active_container = None
                for tab_data in modal.get('tabs_data', []):
                    if tab_data['label'] == active_tab_label:
                        active_container = tab_data['container']
                        break
                if active_container and modal.get('content_rect'):
                    for i in range(active_container.capacity or 0):
                        rects.append(get_container_slot_rect(modal['content_rect'].topleft, i))
                        
            elif m_type == 'gear':
                active_tab = modal.get('active_tab', 'Gear')
                if active_tab == 'Gear' and 'gear_slot_rects' in modal:
                    rects.extend(modal['gear_slot_rects'].values())
                elif active_tab in modal.get('container_mapping', {}):
                    container = modal['container_mapping'][active_tab]
                    p_calc = (modal.get('rect', pygame.Rect(m_pos,(0,0))).x, modal.get('rect', pygame.Rect(m_pos,(0,0))).y + 40)
                    for i in range(container.capacity or 0): rects.append(get_container_slot_rect(p_calc, i))
                    
            elif m_type == 'vehicle' and modal.get('active_tab') == 'Mechanics':
                if 'equipment_rects' in modal:
                    rects.extend(modal['equipment_rects'].values())
                    
            elif m_type == 'slots':
                for slot_data in modal.get('slot_rects', []):
                    rects.append(slot_data['rect'])
                    
        return rects

    def update_cursor(self, game):
        """Updates mouse position using Free Cursor or UI Snap Logic"""
        if not self.active_controller:
            return

        self.last_game_ref = game # Save reference for process_event mapping
        joy = self.active_controller
        
        if joy.get_numaxes() >= 4:
            rx = joy.get_axis(AXIS_RX)
            ry = joy.get_axis(AXIS_RY)

            if abs(rx) < self.deadzone: rx = 0
            if abs(ry) < self.deadzone: ry = 0

            if rx != 0 or ry != 0:
                mx, my = pygame.mouse.get_pos()
                ui_rects = self.get_all_ui_slots(game)
                
                # Check if cursor is currently locked to a UI Slot
                current_slot = None
                for r in ui_rects:
                    if r.collidepoint((mx, my)):
                        current_slot = r
                        break
                
                current_time = time.time()
                is_snapping = False
                
                if current_slot:
                    # SNAP GRID NAVIGATION
                    if current_time - self.last_snap_time > 0.2: # 200ms jump cooldown
                        # Establish primary direction vector
                        dx = 1 if rx > 0 else -1 if rx < 0 else 0
                        dy = 1 if ry > 0 else -1 if ry < 0 else 0
                        if abs(rx) > abs(ry): dy = 0
                        else: dx = 0
                        
                        best_rect = None
                        best_dist = float('inf')
                        cx, cy = current_slot.center
                        target_angle = math.atan2(dy, dx)
                        
                        # Find the closest adjacent slot in the pushed direction
                        for r in ui_rects:
                            if r == current_slot: continue
                            tx, ty = r.center
                            angle = math.atan2(ty - cy, tx - cx)
                            
                            diff = abs(angle - target_angle)
                            if diff > math.pi: diff = 2 * math.pi - diff
                            
                            if diff < math.pi / 4: # Fall within a 45 degree cone
                                dist = math.hypot(tx - cx, ty - cy)
                                if dist < best_dist:
                                    best_dist = dist
                                    best_rect = r
                        
                        # Snap!
                        if best_rect:
                            pygame.mouse.set_pos(best_rect.center)
                            self.last_snap_time = current_time
                            
                            motion_event = pygame.event.Event(
                                pygame.MOUSEMOTION, 
                                {'pos': best_rect.center, 'rel': (best_rect.centerx - cx, best_rect.centery - cy), 'buttons': pygame.mouse.get_pressed()}
                            )
                            pygame.event.post(motion_event)
                        else:
                            # ---> NEW: EXIT PLAN <---
                            # We pushed the stick, but no adjacent slot was found. 
                            # Break the lock by throwing the cursor outside the slot's bounds!
                            escape_x, escape_y = mx, my
                            if dx > 0: escape_x = current_slot.right + 15
                            elif dx < 0: escape_x = current_slot.left - 15
                            
                            if dy > 0: escape_y = current_slot.bottom + 15
                            elif dy < 0: escape_y = current_slot.top - 15
                            
                            # Constrain to screen bounds so we don't trap the cursor off-screen
                            screen_w, screen_h = pygame.display.get_surface().get_size()
                            escape_x = max(0, min(escape_x, screen_w))
                            escape_y = max(0, min(escape_y, screen_h))
                            
                            pygame.mouse.set_pos((escape_x, escape_y))
                            self.last_snap_time = current_time
                    is_snapping = True # Suppress free moving while locked in a slot
                
                if not is_snapping:
                    # FREE CURSOR NAVIGATION
                    screen_w, screen_h = pygame.display.get_surface().get_size()
                    new_x = max(0, min(mx + int(rx * self.cursor_speed), screen_w))
                    new_y = max(0, min(my + int(ry * self.cursor_speed), screen_h))
                    
                    # Check if free cursor collided with a slot to instantly snap/lock into it
                    entered_slot = None
                    for r in ui_rects:
                        if r.collidepoint((new_x, new_y)):
                            entered_slot = r
                            break
                    
                    if entered_slot:
                        pygame.mouse.set_pos(entered_slot.center)
                        new_x, new_y = entered_slot.center
                    else:
                        pygame.mouse.set_pos((new_x, new_y))

                    motion_event = pygame.event.Event(
                        pygame.MOUSEMOTION, 
                        {'pos': (new_x, new_y), 'rel': (rx * self.cursor_speed, ry * self.cursor_speed), 'buttons': pygame.mouse.get_pressed()}
                    )
                    pygame.event.post(motion_event)

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
        """Returns boolean states for running (A) and aiming (LT)"""
        if not self.active_controller:
            return False, False
        
        joy = self.active_controller
        
        # A Pressed to Run (Button 0)
        is_running = joy.get_button(BTN_A)
            
        # LT Pressed to Aim
        is_aiming = False
        if joy.get_numaxes() > AXIS_LT:
            is_aiming = joy.get_axis(AXIS_LT) > 0.0
            
        return is_running, is_aiming

    def process_event(self, event):
        """Translates joystick hardware events into standard keyboard/mouse events"""
        
        # ---> Handle Triggers (Axes) for Shooting (RT) and UI Drag Drop Toggle <---
        if event.type == pygame.JOYAXISMOTION:
            if event.axis == AXIS_RT:
                mouse_pos = pygame.mouse.get_pos()
                game = getattr(self, 'last_game_ref', None)
                
                is_holding_item = False
                in_ui_slot = False
                
                if game:
                    is_holding_item = getattr(game, 'is_dragging', False) or getattr(game, 'drag_candidate', None) is not None
                    
                    # Auto-sync out-of-bounds drops
                    if not is_holding_item:
                        self.ui_drag_held = False 
                    
                    ui_rects = self.get_all_ui_slots(game)
                    in_ui_slot = any(r.collidepoint(mouse_pos) for r in ui_rects)

                # Trigger Pulled
                if event.value > 0.5 and not getattr(self, 'rt_pressed', False):
                    self.rt_pressed = True
                    
                    if in_ui_slot or is_holding_item:
                        # UI TOGGLE MODE: Click to Grab, Click to Drop
                        if not getattr(self, 'ui_drag_held', False):
                            self.ui_drag_held = True
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 1}))
                        else:
                            self.ui_drag_held = False
                            pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))
                    else:
                        # WORLD SHOOTING (Standard press and hold)
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 1}))

                # Trigger Released
                elif event.value <= 0.5 and getattr(self, 'rt_pressed', False):
                    self.rt_pressed = False
                    # Only release the mouse click if we are NOT using the UI Toggle functionality
                    if not getattr(self, 'ui_drag_held', False):
                        pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 1}))

        elif event.type == pygame.JOYBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # ---> Y: Interact (Sends K_e to trigger native interaction logic)
            if event.button == BTN_Y: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_e, 'unicode': 'e'}))
            
            # ---> B: Context Menu (Right Click)
            elif event.button == BTN_B: 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 3}))

            # ---> X: Reload (Sends K_r)
            elif event.button == BTN_X: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_r, 'unicode': 'r'}))
            
            # ---> Start: Pause Game (F2)
            elif event.button == BTN_START: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_F2, 'unicode': ''}))
                
            # ---> Select: Fast Forward (Tab / f)
            elif event.button == BTN_SELECT: 
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_TAB, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_f, 'unicode': 'f'}))
                
            # ---> LB (-): Zoom Out
            elif event.button == BTN_LB: 
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': -1, 'x': 0}))
                
            # ---> RB (+): Zoom In
            elif event.button == BTN_RB: 
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': 1, 'x': 0}))

        elif event.type == pygame.JOYBUTTONUP:
            mouse_pos = pygame.mouse.get_pos()
            
            # Release Context Menu
            if event.button == BTN_B: 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {'pos': mouse_pos, 'button': 3}))
            # Release Interact
            elif event.button == BTN_Y: 
                pygame.event.post(pygame.event.Event(pygame.KEYUP, {'key': pygame.K_e, 'unicode': 'e'}))
                
        elif event.type == pygame.JOYHATMOTION:
            x, y = event.value
            mouse_pos = pygame.mouse.get_pos()
            
            # Up / Down for scrolling or moving vertically in Context Menus
            if y == 1: # Up
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_UP, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': 1, 'x': 0, 'from_dpad': True})) 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 4}))
            elif y == -1: # Down
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {'key': pygame.K_DOWN, 'unicode': ''}))
                pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL, {'y': -1, 'x': 0, 'from_dpad': True})) 
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {'pos': mouse_pos, 'button': 5}))
                
            # ---> Left / Right for Belt Selection (Slots 1 to 5)
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