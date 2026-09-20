# core/server/remote_player.py
import pygame
import math
from core.data.config import TILE_SIZE, WHITE, GREEN, RED, GRAY, font_14
from core.entities.item.item import Item
from core.entities.item.item_factory import get_tinted_sprite

class RemotePlayer(pygame.sprite.Sprite):
    """Represents another connected player in the world."""
    def __init__(self, player_id, name, x, y, sex="Male"):
        super().__init__()
        self.player_id = player_id
        self.name = name
        self.sex = sex
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(int(self.x), int(self.y), TILE_SIZE, TILE_SIZE)

        self.facing_direction = (0, 1)
        self.aim_angle = 0.0
        self.is_moving = False
        self.is_running = False
        self.is_aiming = False
        self.health = 100.0
        self.max_health = 100.0
        self.is_dead = False
        self.walk_anim_angle = 0.0

        self.clothes = {}
        self.clothes_colors = {}
        self.cached_clothes_surfaces = {}
        self.equipped_weapon_name = None
        self.cached_weapon_img = None
        
        self.swing_timer = 0
        self.swing_angle = 0.0
        self.gun_flash_timer = 0  # <--- NEW: Track gun flash for remote players

        self.action_timer = 0.0
        self.action_total_time = 0.0
        self.action_name = ""

        self.base_image = None
        self._load_base_sprite()

    def _load_base_sprite(self):
        try:
            from core.data.config import SPRITE_PATH
            path = SPRITE_PATH + "player/player.png"
            img = pygame.image.load(path).convert_alpha()
            self.base_image = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        except Exception:
            self.base_image = pygame.Surface((TILE_SIZE, TILE_SIZE))
            self.base_image.fill((0, 180, 220))

    def _rebuild_clothes_cache(self):
        self.cached_clothes_surfaces.clear()
        for slot, item_name in self.clothes.items():
            if not item_name or item_name == "None":
                continue
            color = self.clothes_colors.get(slot, (255, 255, 255))
            if isinstance(color, list):
                color = tuple(color)
            item = Item.create_from_name(item_name, force_color=color, spawn_loot=False)
            if item and item.image:
                img = item.image
                if color and color != (255, 255, 255):
                    img = get_tinted_sprite(img, item_name, color)
                self.cached_clothes_surfaces[slot] = img

    def take_damage(self, damage, game, attacker=None, infection=0):
        if hasattr(game, 'server') and game.server:
            for sock, info in game.server.clients.items():
                if info.get('id') == self.player_id:
                    from core.server.network import NetMsg, send_msg
                    send_msg(sock, {
                        'type': NetMsg.ENTITY_DAMAGE,
                        'entity_type': 'player',
                        'damage': damage,
                        'infection': infection
                    })
                    break
        return False

    def update_from_network(self, data):
        self.x = float(data.get('x', self.x))
        self.y = float(data.get('y', self.y))
        self.rect.topleft = (int(self.x), int(self.y))
        self.facing_direction = tuple(data.get('facing', self.facing_direction))
        self.aim_angle = float(data.get('aim_angle', self.aim_angle))
        self.is_moving = bool(data.get('is_moving', False))
        self.is_running = bool(data.get('is_running', False))
        self.is_aiming = bool(data.get('is_aiming', False))
        self.health = float(data.get('health', self.health))
        self.max_health = float(data.get('max_health', self.max_health))
        self.is_dead = bool(data.get('is_dead', False))

        net_swing = int(data.get('swing_timer', 0))
        if net_swing > 0 and self.swing_timer <= 0:
            self.swing_timer = net_swing
        self.swing_angle = float(data.get('swing_angle', self.swing_angle))

        self.action_timer = float(data.get('action_timer', 0))
        self.action_total_time = float(data.get('action_total_time', 0))
        self.action_name = str(data.get('action_name', ''))

        new_weapon = data.get('weapon')
        if new_weapon != self.equipped_weapon_name:
            self.equipped_weapon_name = new_weapon
            if new_weapon:
                w_item = Item.create_from_name(new_weapon, spawn_loot=False)
                self.cached_weapon_img = w_item.image if w_item else None
            else:
                self.cached_weapon_img = None

        new_clothes = data.get('clothes', {})
        new_colors = data.get('clothes_colors', {})
        if new_clothes != self.clothes or new_colors != self.clothes_colors:
            self.clothes = new_clothes
            self.clothes_colors = new_colors
            self._rebuild_clothes_cache()

        if self.is_moving:
            anim_speed = 25 if self.is_running else 15
            self.walk_anim_angle = math.sin(pygame.time.get_ticks() * 0.01 * anim_speed) * 3
        else:
            self.walk_anim_angle = 0.0

    def draw(self, surface, offset_x, offset_y, game=None):
        if self.is_dead:
            return

        draw_x = int(self.x + offset_x)
        draw_y = int(self.y + offset_y)
        draw_rect = pygame.Rect(draw_x, draw_y, TILE_SIZE, TILE_SIZE)

        img = self.base_image
        if self.walk_anim_angle != 0 and img:
            rot_img = pygame.transform.rotate(img, self.walk_anim_angle)
            surface.blit(rot_img, rot_img.get_rect(center=draw_rect.center))
        elif img:
            surface.blit(img, draw_rect)

        # Clothes
        for c_img in self.cached_clothes_surfaces.values():
            if self.walk_anim_angle != 0:
                rot_c = pygame.transform.rotate(c_img, self.walk_anim_angle)
                surface.blit(rot_c, rot_c.get_rect(center=draw_rect.center))
            else:
                surface.blit(c_img, draw_rect)

        # Weapon & Swing Handling
        is_swinging = (self.swing_timer > 0)
        
        # Determine if weapon is ranged for aiming offset
        is_ranged = False
        if self.equipped_weapon_name:
            from core.entities.item.item_data import ITEM_TEMPLATES
            tmpl = ITEM_TEMPLATES.get(self.equipped_weapon_name)
            if tmpl and tmpl.get('type') == 'weapon_ranged':
                is_ranged = True

        if self.cached_weapon_img:
            if is_swinging:
                original_image = self.cached_weapon_img
                swing_progress = (self.swing_timer - 7.5) / 7.5
                dynamic_swing_angle = self.swing_angle + (swing_progress * (math.pi / 4))
                angle_degrees = math.degrees(dynamic_swing_angle)
                rotated_image = pygame.transform.rotate(original_image, angle_degrees)

                offset_radius = TILE_SIZE * 0.8
                offset_x_weapon = math.cos(dynamic_swing_angle) * offset_radius
                offset_y_weapon = -math.sin(dynamic_swing_angle) * offset_radius

                rot_rect = rotated_image.get_rect(center=draw_rect.center)
                rot_rect.centerx += offset_x_weapon
                rot_rect.centery += offset_y_weapon
                surface.blit(rotated_image, rot_rect)
            else:
                angle_deg = math.degrees(self.aim_angle)
                w_img = self.cached_weapon_img
                if math.cos(self.aim_angle) < 0:
                    w_img = pygame.transform.flip(w_img, False, True)
                rot_w = pygame.transform.rotate(w_img, angle_deg)
                
                # --- FIX: Remote Player Aim Offset Animation ---
                offset_dist = TILE_SIZE * (0.8 if (self.is_aiming and is_ranged) else 0.4)
                wx = draw_rect.centerx + math.cos(self.aim_angle) * offset_dist
                wy = draw_rect.centery - math.sin(self.aim_angle) * offset_dist
                surface.blit(rot_w, rot_w.get_rect(center=(wx, wy)))

        # --- FIX: Default Game Melee Arc ---
        if is_swinging:
            self.swing_timer -= 1
            swing_radius = TILE_SIZE * 0.7
            center_x, center_y = draw_rect.center
            start_angle = self.swing_angle - (3.1415 / 4)
            end_angle = self.swing_angle + (3.1415 / 4)
            arc_surf = pygame.Surface((swing_radius * 2, swing_radius * 2), pygame.SRCALPHA)
            arc_rect = arc_surf.get_rect()
            pygame.draw.arc(arc_surf, (0, 0, 0, 80), arc_rect, start_angle, end_angle, 2)
            surface.blit(arc_surf, (center_x - swing_radius, center_y - swing_radius))

        # --- FIX: Default Game Gun Flash ---
        if getattr(self, 'gun_flash_timer', 0) > 0:
            self.gun_flash_timer -= 1
            flash_dist = TILE_SIZE * 1.4
            flash_x = draw_rect.centerx + math.cos(self.aim_angle) * flash_dist
            flash_y = draw_rect.centery - math.sin(self.aim_angle) * flash_dist
            
            light_tex = game.assets.get('light_texture') if game and hasattr(game, 'assets') else None
            if light_tex:
                base_size = 8
                width = int(base_size * 0.8)
                height = int(base_size * 0.8)
                small_flash = pygame.transform.smoothscale(light_tex, (width, height))
                
                color_surf = pygame.Surface((width, height))
                color_surf.fill((255, 180, 50))
                color_surf.blit(small_flash, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                
                opacity = min(153, int((self.gun_flash_timer/5) * 153))
                color_surf.set_alpha(opacity)
                
                rotated_flash = pygame.transform.rotate(color_surf, -math.degrees(self.aim_angle))
                flash_rect = rotated_flash.get_rect(center=(int(flash_x), int(flash_y)))
                surface.blit(rotated_flash, flash_rect, special_flags=pygame.BLEND_RGB_ADD)
            else:
                pygame.draw.circle(surface, (255, 200, 50), (int(flash_x), int(flash_y)), 6)

        # Action / Looting Progress Bar & Label
        if self.action_timer > 0 and self.action_total_time > 0:
            self.action_timer = max(0.0, self.action_timer - 1.0)
            progress = 1.0 - (self.action_timer / self.action_total_time)
            bar_w = TILE_SIZE + 8
            bar_h = 4
            bar_x = draw_rect.centerx - bar_w // 2
            bar_y = draw_rect.top - 18
            pygame.draw.rect(surface, (30, 30, 30), (bar_x, bar_y, bar_w, bar_h))
            fill_w = max(0, int(bar_w * max(0.0, min(1.0, progress))))
            if fill_w > 0:
                pygame.draw.rect(surface, (50, 200, 50), (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(surface, (180, 180, 180), (bar_x, bar_y, bar_w, bar_h), 1)
            if self.action_name:
                act_surf = font_14.render(self.action_name, False, (220, 220, 220))
                surface.blit(act_surf, act_surf.get_rect(center=(draw_rect.centerx, bar_y - 6)))

        # Name Tag
        name_surf = font_14.render(self.name, False, (220, 220, 220))
        surface.blit(name_surf, name_surf.get_rect(center=(draw_rect.centerx, draw_rect.top - 10)))