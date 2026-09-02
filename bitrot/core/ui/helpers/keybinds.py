import pygame
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
import core.data.config as config
from core.ui.helpers.main_menu import draw_btn
from core.ui.modals import draw_scrollbar

# Keyboard / Mouse uses positive integers for keys, negative for mouse buttons.
DEFAULT_KB_MOUSE_BINDS = {
    'move_up': {'val': pygame.K_w, 'name': 'Move Up'},
    'move_down': {'val': pygame.K_s, 'name': 'Move Down'},
    'move_left': {'val': pygame.K_a, 'name': 'Move Left'},
    'move_right': {'val': pygame.K_d, 'name': 'Move Right'},
    'run': {'val': pygame.K_LSHIFT, 'name': 'Run'},
    'aim': {'val': pygame.K_LCTRL, 'name': 'Aim'},
    'interact': {'val': pygame.K_e, 'name': 'Interact'},
    'chat': {'val': pygame.K_t, 'name': 'Chat'},
    'toggle_inventory': {'val': pygame.K_i, 'name': 'Toggle Inventory'},
    'toggle_crafting': {'val': pygame.K_c, 'name': 'Toggle Crafting'},
    'toggle_status': {'val': pygame.K_h, 'name': 'Toggle Status'},
    'toggle_gear': {'val': pygame.K_g, 'name': 'Toggle Gear'},
    'toggle_nearby': {'val': pygame.K_n, 'name': 'Toggle Nearby'},
    'toggle_messages': {'val': pygame.K_m, 'name': 'Toggle Messages'},
    'toggle_slots': {'val': pygame.K_y, 'name': 'Toggle Slots'},
    'reload': {'val': pygame.K_r, 'name': 'Reload Weapon'},
    'vehicle_engine': {'val': pygame.K_q, 'name': 'Toggle Engine'},
    'action_shove': {'val': pygame.K_SPACE, 'name': 'Shove / Brake'},
    
    # ---> ADDED: System Controls for Keyboard <---
    'toggle_modals': {'val': pygame.K_TAB, 'name': 'Toggle Modals'},
    'pause': {'val': pygame.K_F2, 'name': 'Pause Game'},
    
    # Fake Keyboard keys just so the UI has something to show for triggers
    'shoot': {'val': -1, 'name': 'Shoot / Attack'}, # -1 is Left Click
    'aim_trigger': {'val': -3, 'name': 'Aim Weapon'} # -3 is Right Click
}

# Joystick uses button integers directly (0, 1, 2, 3...)
# Note: LT (Shoot), RT (Aim), and X (Context Menu) are handled natively via hardware axes/overrides
DEFAULT_JOYSTICK_BINDS = {
    'move_up': {'val': 11, 'name': 'Move Up (D-Pad)'},
    'move_down': {'val': 12, 'name': 'Move Down (D-Pad)'},
    'move_left': {'val': 13, 'name': 'Move Left (D-Pad)'},
    'move_right': {'val': 14, 'name': 'Move Right (D-Pad)'},
    'interact': {'val': 0, 'name': 'Interact (A)'},
    'run': {'val': 1, 'name': 'Run (B)'},
    'reload': {'val': 3, 'name': 'Reload Weapon (Y)'},
    'vehicle_engine': {'val': 4, 'name': 'Toggle Engine (LB)'},
    'action_shove': {'val': 5, 'name': 'Shove / Brake (RB)'},
    
    # ---> ADDED: System Controls for Joystick <---
    'toggle_modals': {'val': 7, 'name': 'Toggle Modals'},
    'pause': {'val': 8, 'name': 'Pause Game'},
    
    # Fake IDs for Triggers so they display in UI
    'shoot': {'val': 15, 'name': 'Shoot / Attack'},
    'aim_trigger': {'val': 16, 'name': 'Aim Weapon'}
}

JOYSTICK_BTN_NAMES = {
    0: 'A',
    1: 'B',
    2: 'X',
    3: 'Y',
    4: 'LB',
    5: 'RB',
    6: 'SELECT',
    7: 'START',
    8: 'L3',
    9: 'R3',
    11: 'D-PAD UP',
    12: 'D-PAD DOWN',
    13: 'D-PAD LEFT',
    14: 'D-PAD RIGHT',
    15: 'LT',
    16: 'RT'
}

class KeybindManager:
    def __init__(self):
        self.kb_binds = {k: v['val'] for k, v in DEFAULT_KB_MOUSE_BINDS.items()}
        self.joy_binds = {k: v['val'] for k, v in DEFAULT_JOYSTICK_BINDS.items()}
        self.filepath = os.path.join(config.get_writable_dir(), "data.rot", "save", "config", "keybinds.xml")
        self.load()

    def load(self):
        if not os.path.exists(self.filepath):
            self.save()
            return
        try:
            tree = ET.parse(self.filepath)
            root = tree.getroot()

            kb_node = root.find('keyboard_mouse')
            if kb_node is not None:
                for bind_node in kb_node.findall('bind'):
                    action = bind_node.get('action')
                    key_val = bind_node.get('key')
                    if action in self.kb_binds and key_val is not None:
                        self.kb_binds[action] = int(key_val)

            joy_node = root.find('joystick')
            if joy_node is not None:
                for bind_node in joy_node.findall('bind'):
                    action = bind_node.get('action')
                    key_val = bind_node.get('key')
                    if action in self.joy_binds and key_val is not None:
                        self.joy_binds[action] = int(key_val)
        except Exception as e:
            print(f"Error loading keybinds: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            root = ET.Element('keybinds')

            kb_node = ET.SubElement(root, 'keyboard_mouse')
            for action, key in self.kb_binds.items():
                node = ET.SubElement(kb_node, 'bind')
                node.set('action', action)
                node.set('key', str(key))
                # Add default attribute when rewriting
                if action in DEFAULT_KB_MOUSE_BINDS:
                    node.set('default', str(DEFAULT_KB_MOUSE_BINDS[action]['val']))

            joy_node = ET.SubElement(root, 'joystick')
            for action, key in self.joy_binds.items():
                node = ET.SubElement(joy_node, 'bind')
                node.set('action', action)
                node.set('key', str(key))
                # Add default attribute when rewriting
                if action in DEFAULT_JOYSTICK_BINDS:
                    node.set('default', str(DEFAULT_JOYSTICK_BINDS[action]['val']))

            raw_xml = ET.tostring(root, 'utf-8')
            pretty_xml = xml.dom.minidom.parseString(raw_xml).toprettyxml(indent="    ")
            pretty_xml = os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])
            with open(self.filepath, "w") as f:
                f.write(pretty_xml)
        except Exception as e:
            print(f"Error saving keybinds: {e}")

    def get_kb_action_for_key(self, key):
        for action, bound_key in self.kb_binds.items():
            if bound_key == key: return action
        return None

    def get_joy_action_for_key(self, key):
        for action, bound_key in self.joy_binds.items():
            if bound_key == key: return action
        return None

keybind_manager = KeybindManager()

class KeybindsMenuUI:
    def __init__(self):
        self.active = False
        self.active_tab = 'keyboard_mouse' 
        self.waiting_for_key = None
        self.error_message = ""
        self.error_timer = 0
        self.scroll_offset_y = 0
        self.is_dragging_scrollbar = False
        
        self.is_scrolling_content = False
        self.content_drag_last_y = 0

        self.item_height = int(45 * config.UI_SCALE)
        self.modal_state = {}

    def toggle(self):
        self.active = not self.active
        self.waiting_for_key = None
        self.error_message = ""
        self.scroll_offset_y = 0
        self.is_dragging_scrollbar = False

    def _clamp_scroll(self):
        _, _, _, _, _, list_rect, _, _, _ = self.get_rects()
        binds = DEFAULT_KB_MOUSE_BINDS if self.active_tab == 'keyboard_mouse' else DEFAULT_JOYSTICK_BINDS
        total_h = len(binds) * self.item_height
        max_scroll = max(0, total_h - list_rect.height)
        self.scroll_offset_y = max(0, min(self.scroll_offset_y, max_scroll))

    def _handle_scroll_drag(self, my):
        _, _, _, _, _, list_rect, bar_rect, _, _ = self.get_rects()
        binds = DEFAULT_KB_MOUSE_BINDS if self.active_tab == 'keyboard_mouse' else DEFAULT_JOYSTICK_BINDS
        total_h = len(binds) * self.item_height
        visible_h = list_rect.height
        
        if total_h <= visible_h:
            self.scroll_offset_y = 0
            return
            
        thumb_h = max(20, (visible_h / total_h) * bar_rect.height)
        track_h = bar_rect.height - thumb_h
        
        rel_y = my - bar_rect.y - thumb_h / 2
        ratio = max(0.0, min(1.0, rel_y / track_h))
        self.scroll_offset_y = int(ratio * (total_h - visible_h))

    def handle_events(self, events):
        if not self.active: return False

        for event in events:
            if self.waiting_for_key:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.waiting_for_key = None
                        continue

                    if self.active_tab == 'keyboard_mouse':
                        conflict = keybind_manager.get_kb_action_for_key(event.key)
                        self._attempt_bind(event.key, conflict)
                    continue

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.active_tab == 'keyboard_mouse':
                        mouse_val = -event.button
                        conflict = keybind_manager.get_kb_action_for_key(mouse_val)
                        self._attempt_bind(mouse_val, conflict)
                    continue

                elif event.type == pygame.JOYBUTTONDOWN:
                    if self.active_tab == 'joystick':
                        conflict = keybind_manager.get_joy_action_for_key(event.button)
                        self._attempt_bind(event.button, conflict)
                    continue

                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.active = False
                continue

            if event.type == pygame.MOUSEWHEEL:
                self.scroll_offset_y -= event.y * int(30 * config.UI_SCALE)
                self._clamp_scroll()
                continue
                
            if event.type == pygame.MOUSEMOTION:
                if self.is_dragging_scrollbar:
                    self._handle_scroll_drag(event.pos[1])
                    continue 

                elif self.is_scrolling_content:
                    delta_y = event.pos[1] - self.content_drag_last_y
                    self.content_drag_last_y = event.pos[1]
                    self.scroll_offset_y -= delta_y 
                    self._clamp_scroll()
                    continue 

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.is_dragging_scrollbar = False
                self.is_scrolling_content = False
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _, _, _, tab_kb_rect, tab_joy_rect, list_rect, bar_rect, back_btn_rect, reset_btn_rect = self.get_rects()
                mouse_pos = event.pos

                if back_btn_rect.collidepoint(mouse_pos):
                    self.active = False
                    continue

                if reset_btn_rect.collidepoint(mouse_pos):
                    if self.active_tab == 'keyboard_mouse':
                        for action, data in DEFAULT_KB_MOUSE_BINDS.items():
                            keybind_manager.kb_binds[action] = data['val']
                    else:
                        for action, data in DEFAULT_JOYSTICK_BINDS.items():
                            keybind_manager.joy_binds[action] = data['val']
                    keybind_manager.save()
                    continue

                if bar_rect.collidepoint(mouse_pos):
                    self.is_dragging_scrollbar = True
                    self._handle_scroll_drag(mouse_pos[1])
                    continue
                
                if tab_kb_rect.collidepoint(mouse_pos):
                    self.active_tab = 'keyboard_mouse'
                    self.scroll_offset_y = 0
                    continue

                if tab_joy_rect.collidepoint(mouse_pos):
                    self.active_tab = 'joystick'
                    self.scroll_offset_y = 0
                    continue

                clicked_button = False
                if list_rect.collidepoint(mouse_pos):
                    y_offset = list_rect.y - self.scroll_offset_y
                    binds = DEFAULT_KB_MOUSE_BINDS if self.active_tab == 'keyboard_mouse' else DEFAULT_JOYSTICK_BINDS

                    for action in binds:
                        row_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, self.item_height)
                        if row_rect.collidepoint(mouse_pos) and row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                            btn_w = int(250 * config.UI_SCALE)
                            btn_h = int(35 * config.UI_SCALE)
                            key_btn_rect = pygame.Rect(row_rect.right - btn_w, row_rect.centery - btn_h//2, btn_w, btn_h)
                            
                            if key_btn_rect.collidepoint(mouse_pos):
                                self.waiting_for_key = action
                                clicked_button = True
                                break
                        y_offset += self.item_height

                if list_rect.collidepoint(mouse_pos) and not clicked_button:
                    self.is_scrolling_content = True
                    self.content_drag_last_y = mouse_pos[1]

        return True

    def _attempt_bind(self, new_val, conflict_action):
        binds_ref = DEFAULT_KB_MOUSE_BINDS if self.active_tab == 'keyboard_mouse' else DEFAULT_JOYSTICK_BINDS
        manager_binds = keybind_manager.kb_binds if self.active_tab == 'keyboard_mouse' else keybind_manager.joy_binds

        if conflict_action and conflict_action != self.waiting_for_key:
            conflict_name = binds_ref[conflict_action]['name']
            self.error_message = f"Key in use for: {conflict_name}"
            self.error_timer = pygame.time.get_ticks()
        else:
            manager_binds[self.waiting_for_key] = new_val
            keybind_manager.save()
            self.error_message = ""

        self.waiting_for_key = None

    def get_rects(self):
        scale = config.UI_SCALE
        def S(val): return int(val * scale)
        
        center_x = config.GAME_WIDTH // 2
        center_y = config.GAME_HEIGHT // 2
        
        w = S(900)
        h = S(480)
        
        bg_rect = pygame.Rect(center_x - w//2, center_y - h//2, w, h)
        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, S(50))
        
        tab_h = S(38)
        tab_y = header_rect.bottom
        tab_w = bg_rect.width // 2
        tab_kb_rect = pygame.Rect(bg_rect.x, tab_y, tab_w, tab_h)
        tab_joy_rect = pygame.Rect(tab_kb_rect.right, tab_y, tab_w, tab_h)
        
        padding = S(20)
        list_y = tab_kb_rect.bottom + padding
        list_height = bg_rect.bottom - list_y - padding
        
        scrollbar_width = S(12)
        list_rect = pygame.Rect(bg_rect.x + padding, list_y, bg_rect.width - (padding * 2) - scrollbar_width - S(10), list_height)
        bar_rect = pygame.Rect(list_rect.right + S(10), list_y, scrollbar_width, list_height)

        btn_width = S(200)
        btn_height = S(45)
        spacing = S(20)
        back_btn_rect = pygame.Rect(center_x - btn_width - spacing//2, bg_rect.bottom + S(20), btn_width, btn_height)
        reset_btn_rect = pygame.Rect(center_x + spacing//2, bg_rect.bottom + S(20), btn_width, btn_height)
        
        return center_x, center_y, bg_rect, tab_kb_rect, tab_joy_rect, list_rect, bar_rect, back_btn_rect, reset_btn_rect

    def draw(self, screen, mouse_pos):
        if not self.active: return

        center_x, center_y, bg_rect, tab_kb_rect, tab_joy_rect, list_rect, bar_rect, back_btn_rect, reset_btn_rect = self.get_rects()

        screen.fill(config.DARK_GRAY)

        pygame.draw.rect(screen, (35, 35, 35), bg_rect, border_radius=10)
        pygame.draw.rect(screen, config.GRAY_80, bg_rect, width=2, border_radius=10)

        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, int(50 * config.UI_SCALE))
        pygame.draw.rect(screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, config.GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)
        
        title_surf = config.font_16.render("Controls Configuration", False, config.WHITE)
        screen.blit(title_surf, (header_rect.x + 20, header_rect.centery - title_surf.get_height() // 2))

        kb_is_active = self.active_tab == 'keyboard_mouse'
        joy_is_active = self.active_tab == 'joystick'

        kb_color = (35, 35, 35) if kb_is_active else (25, 25, 25)
        joy_color = (35, 35, 35) if joy_is_active else (25, 25, 25)

        if not kb_is_active and tab_kb_rect.collidepoint(mouse_pos): kb_color = (45, 45, 45)
        if not joy_is_active and tab_joy_rect.collidepoint(mouse_pos): joy_color = (45, 45, 45)

        pygame.draw.rect(screen, kb_color, tab_kb_rect)
        pygame.draw.rect(screen, joy_color, tab_joy_rect)

        pygame.draw.rect(screen, config.WHITE, tab_kb_rect, width=1)
        pygame.draw.rect(screen, config.WHITE, tab_joy_rect, width=1)

        kb_surf = config.font_16.render("Keyboard & Mouse", False, config.WHITE)
        joy_surf = config.font_16.render("Controller Joystick", False, config.WHITE)
        screen.blit(kb_surf, kb_surf.get_rect(center=tab_kb_rect.center))
        screen.blit(joy_surf, joy_surf.get_rect(center=tab_joy_rect.center))

        old_clip = screen.get_clip()
        screen.set_clip(list_rect)

        self._clamp_scroll()
        y_offset = list_rect.y - self.scroll_offset_y

        binds_ref = DEFAULT_KB_MOUSE_BINDS if self.active_tab == 'keyboard_mouse' else DEFAULT_JOYSTICK_BINDS
        manager_binds = keybind_manager.kb_binds if self.active_tab == 'keyboard_mouse' else keybind_manager.joy_binds

        for action, data in binds_ref.items():
            name = data['name']
            current_key = manager_binds[action]

            if self.active_tab == 'keyboard_mouse':
                if current_key < 0:
                    btn_num = -current_key
                    if btn_num == 1: key_name = "LEFT CLICK"
                    elif btn_num == 2: key_name = "MIDDLE CLICK"
                    elif btn_num == 3: key_name = "RIGHT CLICK"
                    else: key_name = f"MOUSE BTN {btn_num}"
                else:
                    key_name = pygame.key.name(current_key).upper()
            else:
                # Use the lookup dictionary, or fallback to the raw number if it's an unknown button
                key_name = JOYSTICK_BTN_NAMES.get(current_key, f"JOY BUTTON {current_key}")

            row_rect = pygame.Rect(list_rect.x, y_offset, list_rect.width, self.item_height)
            
            if row_rect.bottom > list_rect.top and row_rect.top < list_rect.bottom:
                
                pygame.draw.line(screen, (55, 55, 55), (row_rect.left, row_rect.bottom - 1), (row_rect.right, row_rect.bottom - 1), 1)

                name_surf = config.font_16.render(name, False, config.WHITE)
                screen.blit(name_surf, (row_rect.x + int(10 * config.UI_SCALE), row_rect.centery - name_surf.get_height() // 2))
                
                btn_w = int(250 * config.UI_SCALE)
                btn_h = int(35 * config.UI_SCALE)
                key_btn_rect = pygame.Rect(row_rect.right - btn_w, row_rect.centery - btn_h//2, btn_w, btn_h)
                
                display_text = "PRESS ANY KEY..." if self.waiting_for_key == action else key_name
                
                draw_btn(screen, key_btn_rect, display_text, mouse_pos, enabled=True)
                
                if self.waiting_for_key == action:
                    pygame.draw.rect(screen, config.BLUE, key_btn_rect, border_radius=6)
                    pygame.draw.rect(screen, config.WHITE, key_btn_rect, width=2, border_radius=6)
                    active_surf = config.font_16.render(display_text, False, config.WHITE)
                    screen.blit(active_surf, active_surf.get_rect(center=key_btn_rect.center))

            y_offset += self.item_height

        screen.set_clip(old_clip)

        total_h = len(binds_ref) * self.item_height
        draw_scrollbar(screen, self.modal_state, bar_rect, list_rect.height, total_h, self.scroll_offset_y)

        draw_btn(screen, back_btn_rect, "Back", mouse_pos, enabled=True)

        hovered = reset_btn_rect.collidepoint(mouse_pos)
        reset_color = (220, 70, 70) if hovered else (200, 50, 50)
        pygame.draw.rect(screen, reset_color, reset_btn_rect, border_radius=4)
        pygame.draw.rect(screen, config.WHITE, reset_btn_rect, width=1, border_radius=4)
        reset_txt = config.font_16.render("Reset Default", False, config.WHITE)
        screen.blit(reset_txt, (reset_btn_rect.centerx - reset_txt.get_width()//2, reset_btn_rect.centery - reset_txt.get_height()//2))

        if self.error_message:
            if pygame.time.get_ticks() - self.error_timer < 3000:
                err_surf = config.font_16.render(self.error_message, False, config.RED)
                err_bg = pygame.Rect(0, 0, err_surf.get_width() + 40, err_surf.get_height() + 20)
                err_bg.center = (center_x, back_btn_rect.bottom + int(30 * config.UI_SCALE)) 
                
                pygame.draw.rect(screen, config.DARK_GRAY, err_bg, border_radius=6)
                pygame.draw.rect(screen, config.WHITE, err_bg, width=1, border_radius=6)
                screen.blit(err_surf, err_surf.get_rect(center=err_bg.center))
            else:
                self.error_message = ""

keybinds_ui = KeybindsMenuUI()