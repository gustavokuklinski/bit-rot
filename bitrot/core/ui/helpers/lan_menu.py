# core/ui/helpers/lan_menu.py

import os
import pygame
import core.data.config as config
from core.data.config import (
    GAME_WIDTH, GAME_HEIGHT, UI_SCALE, WHITE, GRAY, DARK_GRAY,
    GRAY_60, GRAY_80, RED, YELLOW, font_16, font_14, font_12,
    SPRITE_PATH, BASE_DIR
)
from core.data.localization import tr

def _draw_btn(surface, rect, text, mouse_pos, enabled=True, base_color=(80, 80, 80)):
    is_hovered = rect.collidepoint(mouse_pos)
    if not enabled:
        bg_color = (40, 40, 40)
        text_color = (100, 100, 100)
    else:
        bg_color = (min(255, base_color[0] + 30), min(255, base_color[1] + 30), min(255, base_color[2] + 30)) if is_hovered else base_color
        text_color = WHITE

    pygame.draw.rect(surface, bg_color, rect, border_radius=4)
    txt_surf = font_16.render(tr('ui', text), False, text_color)
    surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))

class LanMenuUI:
    def __init__(self):
        self.active = False
        self.server_address = "192.168.0.6:7777"
        self.input_active = True
        self.error_message = ""
        self.error_timer = 0
        self._last_hovered_id = None
        self._lan_icon = None

    def toggle(self):
        self.active = not self.active
        self.error_message = ""
        self.input_active = True
        if self.active and self._lan_icon is None:
            self._load_icon()

    def _load_icon(self):
        scale = UI_SCALE
        def S(val): return int(val * scale)
        candidates = [
            os.path.join(BASE_DIR, 'data.rot', 'lib', 'sprites', 'ui', 'lan.png'),
            os.path.join(SPRITE_PATH, 'ui', 'lan.png')
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self._lan_icon = pygame.transform.scale(img, (S(48), S(48)))
                    return
                except Exception:
                    pass
        self._lan_icon = None

    def get_rects(self):
        scale = UI_SCALE
        def S(val): return int(val * scale)

        center_x = GAME_WIDTH // 2
        center_y = GAME_HEIGHT // 2

        w = S(900)
        h = S(480)

        bg_rect = pygame.Rect(center_x - w // 2, center_y - h // 2, w, h)
        header_rect = pygame.Rect(bg_rect.x, bg_rect.y, bg_rect.width, S(50))

        # Bottom buttons (Connect and Back)
        btn_width = S(200)
        btn_height = S(45)
        spacing = S(20)

        total_btn_width = (btn_width * 2) + spacing
        start_btn_x = center_x - (total_btn_width // 2)

        connect_btn_rect = pygame.Rect(start_btn_x, bg_rect.bottom + S(20), btn_width, btn_height)
        back_btn_rect = pygame.Rect(connect_btn_rect.right + spacing, bg_rect.bottom + S(20), btn_width, btn_height)

        # Input box inside the panel
        input_w = S(460)
        input_h = S(44)
        input_rect = pygame.Rect(center_x - input_w // 2, bg_rect.centery - S(10), input_w, input_h)

        return center_x, center_y, bg_rect, header_rect, input_rect, connect_btn_rect, back_btn_rect

    def _attempt_connect(self, game):
        import socket
        raw = self.server_address.strip()
        if not raw:
            self.error_message = tr('ui', "Please enter server address.")
            self.error_timer = pygame.time.get_ticks()
            return

        if ":" not in raw:
            self.error_message = tr('ui', "Missing port. Format: <IP>:<PORT> (e.g. 0.0.0.0:00000)")
            self.error_timer = pygame.time.get_ticks()
            return

        parts = raw.split(":", 1)
        ip_str = parts[0].strip()
        port_str = parts[1].strip()

        try:
            port_num = int(port_str)
            if not (1 <= port_num <= 65535):
                raise ValueError
        except ValueError:
            self.error_message = tr('ui', "Invalid port. Must be between 1 and 65535.")
            self.error_timer = pygame.time.get_ticks()
            return

        if not ip_str:
            ip_str = "127.0.0.1"

        # Immediate visual feedback on screen before blocking network call
        if hasattr(game, 'game_screen') and hasattr(game, '_update_screen'):
            scale = UI_SCALE
            def S(val): return int(val * scale)
            _, _, _, _, input_rect, _, _ = self.get_rects()
            feedback_surf = font_12.render(tr('ui', "Checking server connection..."), False, YELLOW)
            game.game_screen.blit(feedback_surf, feedback_surf.get_rect(center=(GAME_WIDTH // 2, input_rect.bottom + S(42))))
            game._update_screen()

        # Perform actual TCP ping check to verify the server is reachable and open
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2.5)
        try:
            test_sock.connect((ip_str, port_num))
            test_sock.close()
        except socket.timeout:
            self.error_message = f"{tr('ui', 'Connection timed out')}: {ip_str}:{port_num}"
            self.error_timer = pygame.time.get_ticks()
            return
        except ConnectionRefusedError:
            self.error_message = f"{tr('ui', 'Connection refused')}: {ip_str}:{port_num}"
            self.error_timer = pygame.time.get_ticks()
            return
        except OSError as e:
            err_detail = e.strerror or str(e)
            self.error_message = f"{tr('ui', 'Cannot reach server')} ({err_detail})"
            self.error_timer = pygame.time.get_ticks()
            return
        except Exception as e:
            self.error_message = f"{tr('ui', 'Network error')}: {e}"
            self.error_timer = pygame.time.get_ticks()
            return

        # Server reached and verified successfully: proceed to character selection
        game.is_client = True
        game.is_server = False
        game.cli_connect_address = (ip_str, port_num)
        game.player_setup_state = {}
        game.world_setup_state = {}
        self.active = False
        game.game_state = 'PLAYER_SETUP'
        game.player_setup_state['current_tab'] = 'SelectCharacter'

    def handle_events(self, game, events):
        if not self.active:
            return False

        for event in events:
            mouse_pos = game._get_scaled_mouse_pos() if hasattr(game, '_get_scaled_mouse_pos') else pygame.mouse.get_pos()
            _, _, _, _, input_rect, connect_btn, back_btn = self.get_rects()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.active = False
                    continue

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._attempt_connect(game)
                    continue

                if self.input_active:
                    # Handle clipboard paste
                    mods = pygame.key.get_mods()
                    if (event.key == pygame.K_v and (mods & pygame.KMOD_CTRL or mods & pygame.KMOD_GUI)):
                        try:
                            if pygame.scrap.get_init():
                                clip_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                                if clip_text:
                                    clean_txt = clip_text.decode('utf-8', errors='ignore').replace('\x00', '').strip()
                                    self.server_address += clean_txt
                        except Exception:
                            pass
                        continue

                    if event.key == pygame.K_BACKSPACE:
                        self.server_address = self.server_address[:-1]
                    elif len(self.server_address) < 45 and event.unicode.isprintable():
                        self.server_address += event.unicode
                    continue

            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
                if back_btn.collidepoint(mouse_pos):
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    self.active = False
                    continue

                if connect_btn.collidepoint(mouse_pos):
                    if hasattr(game, 'sound_manager'):
                        game.sound_manager.play_ui_hover()
                    self._attempt_connect(game)
                    continue

                if input_rect.collidepoint(mouse_pos):
                    self.input_active = True
                else:
                    self.input_active = False

        return True

    def draw(self, screen, mouse_pos, game=None):
        if not self.active:
            return

        scale = UI_SCALE
        def S(val): return int(val * scale)

        center_x, center_y, bg_rect, header_rect, input_rect, connect_btn, back_btn = self.get_rects()

        # 1. Background Panel
        screen.fill(DARK_GRAY)
        pygame.draw.rect(screen, (35, 35, 35), bg_rect, border_radius=10)
        pygame.draw.rect(screen, GRAY_80, bg_rect, width=2, border_radius=10)

        # 2. Header Bar
        pygame.draw.rect(screen, (45, 45, 45), header_rect, border_top_left_radius=10, border_top_right_radius=10)
        pygame.draw.line(screen, GRAY_80, header_rect.bottomleft, header_rect.bottomright, 2)

        title_surf = font_16.render(tr('ui', "LAN Multiplayer"), False, WHITE)
        screen.blit(title_surf, (header_rect.x + S(20), header_rect.centery - title_surf.get_height() // 2))

        # 3. Content Body
        if self._lan_icon:
            icon_rect = self._lan_icon.get_rect(center=(center_x, bg_rect.top + S(110)))
            screen.blit(self._lan_icon, icon_rect)
            sub_y = icon_rect.bottom + S(12)
        else:
            sub_y = bg_rect.top + S(90)

        sub_surf = font_16.render(tr('ui', "Connect to Dedicated Server"), False, WHITE)
        screen.blit(sub_surf, sub_surf.get_rect(center=(center_x, sub_y)))

        desc_surf = font_12.render(tr('ui', "Enter the host server address and port to join an existing session:"), False, (180, 180, 180))
        screen.blit(desc_surf, desc_surf.get_rect(center=(center_x, sub_y + S(26))))

        # 4. Text Input Field
        is_hovered_input = input_rect.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (45, 45, 45), input_rect, border_radius=4)
        border_col = YELLOW if self.input_active else (WHITE if is_hovered_input else GRAY)
        pygame.draw.rect(screen, border_col, input_rect, 1, border_radius=4)

        disp_text = self.server_address if self.server_address else "127.0.0.1:00000"
        text_col = WHITE if self.server_address else (130, 130, 130)
        txt_surf = font_16.render(disp_text, False, text_col)

        # Keep text inside input field with clipping
        old_clip = screen.get_clip()
        screen.set_clip(input_rect.inflate(-S(16), -S(6)))
        txt_y = input_rect.centery - txt_surf.get_height() // 2
        screen.blit(txt_surf, (input_rect.x + S(12), txt_y))

        # Blinking cursor
        if self.input_active and (pygame.time.get_ticks() // 450) % 2 == 0:
            cursor_x = input_rect.x + S(12) + (font_16.size(self.server_address)[0] if self.server_address else 0)
            cursor_x = min(input_rect.right - S(8), cursor_x + S(2))
            pygame.draw.line(screen, WHITE, (cursor_x, input_rect.y + S(8)), (cursor_x, input_rect.bottom - S(8)), 2)
        screen.set_clip(old_clip)

        # 5. Hints & Error messages
        hint_surf = font_12.render(tr('ui', "Type the IP and Port"), False, (140, 140, 140))
        screen.blit(hint_surf, hint_surf.get_rect(center=(center_x, input_rect.bottom + S(18))))

        if self.error_message and (pygame.time.get_ticks() - self.error_timer < 4000):
            err_surf = font_12.render(self.error_message, False, RED)
            screen.blit(err_surf, err_surf.get_rect(center=(center_x, input_rect.bottom + S(42))))
        elif self.error_message:
            self.error_message = ""

        # 6. Bottom Buttons
        _draw_btn(screen, connect_btn, "Connect", mouse_pos, base_color=(80, 80, 80))
        _draw_btn(screen, back_btn, "Back", mouse_pos, base_color=(80, 80, 80))

        # Audio feedback tracker
        hovered_btn_id = None
        if connect_btn.collidepoint(mouse_pos):
            hovered_btn_id = "btn_connect"
        elif back_btn.collidepoint(mouse_pos):
            hovered_btn_id = "btn_back"

        if hovered_btn_id is not None and hovered_btn_id != self._last_hovered_id:
            if game and hasattr(game, 'sound_manager'):
                game.sound_manager.play_ui_hover()
        self._last_hovered_id = hovered_btn_id

lan_ui = LanMenuUI()