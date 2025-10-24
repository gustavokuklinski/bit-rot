import os
import random
import math
import pygame
import xml.etree.ElementTree as ET
import uuid

from data.config import TILE_SIZE, DARK_GRAY, RED, ZOMBIE_SPEED, ZOMBIE_DROP

ZOMBIE_TEMPLATES = []

class Zombie:
    def __init__(self, x, y, template):
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())
        self.name = template.get('name', 'Zombie')
        self.max_health = template.get('health', 10.0)
        self.health = self.max_health
        self.speed = template.get('speed', 0.0)
        self.loot_table = template.get('loot', [])
        self.xp_value = random.randint(template.get('min_xp', 5), template.get('max_xp', 15))
        self.image = self.load_sprite(template.get('sprite'))
        self.color = RED
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.show_health_bar_timer = 0
        self.last_attack_time = 0
        self.attack_range = TILE_SIZE * 1.5
        self.min_attack = template.get('min_attack', 1)
        self.max_attack = template.get('max_attack', 5)
        self.min_infection = template.get('min_infection', 0)
        self.max_infection = template.get('max_infection', 1)

    @staticmethod
    def load_zombie_templates(zombies_dir='game/zombies'):
        global ZOMBIE_TEMPLATES
        if ZOMBIE_TEMPLATES:
            return
        if not os.path.exists(zombies_dir):
            print(f"Warning: Zombie templates directory not found at '{zombies_dir}'")
            return

        def _safe_float(text, default=0.0):
            if text is None:
                return default
            t = str(text).strip()
            if t == "":
                return default
            try:
                return float(t)
            except Exception:
                return default

        def _safe_int(text, default=0):
            if text is None:
                return default
            t = str(text).strip()
            if t == "":
                return default
            try:
                return int(float(t))
            except Exception:
                return default

        for filename in os.listdir(zombies_dir):
            if not filename.endswith('.xml'):
                continue
            tree = ET.parse(os.path.join(zombies_dir, filename))
            root = tree.getroot()
            # try to read sprite file attribute safely
            sprite_node = root.find('visuals/sprite')
            sprite_file = None
            if sprite_node is not None:
                # prefer explicit 'file' attribute if present
                sprite_file = sprite_node.get('file') or (sprite_node.text or None)
                if isinstance(sprite_file, str):
                    sprite_file = sprite_file.strip() or None

            attack_node = root.find('stats/attack')
            min_attack = _safe_int(attack_node.get('min'), 1) if attack_node is not None else 1
            max_attack = _safe_int(attack_node.get('max'), 5) if attack_node is not None else 5

            infection_node = root.find('stats/infection')
            min_infection = _safe_int(infection_node.get('min'), 0) if infection_node is not None else 0
            max_infection = _safe_int(infection_node.get('max'), 1) if infection_node is not None else 1

            health_node = root.find('stats/health')
            health = _safe_float(health_node.get('value'), 10.0) if health_node is not None else 10.0

            xp_node = root.find('stats/xp')
            min_xp = _safe_int(xp_node.get('min'), 5) if xp_node is not None else 5
            max_xp = _safe_int(xp_node.get('max'), 15) if xp_node is not None else 15

            template = {
                'name': root.attrib.get('name'),
                'health': health,
                'speed': _safe_float(root.findtext('stats/speed'), 1.0) * ZOMBIE_SPEED,
                'sprite': sprite_file,
                'loot': [],
                'min_xp': min_xp,
                'max_xp': max_xp,
                'min_attack': min_attack,
                'max_attack': max_attack,
                'min_infection': min_infection,
                'max_infection': max_infection
            }
            for drop in root.findall('loot/drop'):
                chance_raw = drop.attrib.get('chance', '0')
                chance = _safe_float(chance_raw, 0.0) * ZOMBIE_DROP
                template['loot'].append({
                    'item': drop.attrib.get('item'),
                    'chance': chance
                })
            ZOMBIE_TEMPLATES.append(template)
        # print(f"Loaded {len(ZOMBIE_TEMPLATES)} zombie templates.")

    @staticmethod
    def create_random(x, y):
        if not ZOMBIE_TEMPLATES:
            Zombie.load_zombie_templates()
        if not ZOMBIE_TEMPLATES:
            raise Exception("No zombie templates loaded")
        templ = random.choice(ZOMBIE_TEMPLATES)
        return Zombie(x, y, templ)

    def load_sprite(self, sprite_file):
        if not sprite_file:
            return None
        try:
            path = os.path.join('game', 'zombies', 'sprites', sprite_file)
            return pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            print(f"Warning: Could not load zombie sprite '{sprite_file}': {e}")
            return None

    def draw(self, surface, game_offset_x=0):
        draw_rect = self.rect.move(game_offset_x, 0)
        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)
        if self.show_health_bar_timer > 0:
            bg_bar_rect = pygame.Rect(draw_rect.left, draw_rect.top - 10, TILE_SIZE, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)
            health_percentage = max(0, self.health / self.max_health)
            health_bar_rect = pygame.Rect(draw_rect.left, draw_rect.top - 10, int(health_percentage * TILE_SIZE), 5)
            pygame.draw.rect(surface, (50,200,50), health_bar_rect)
            self.show_health_bar_timer -= 1

    def move_towards(self, target_rect, obstacles, other_zombies):
        dx = target_rect.x - self.x
        dy = target_rect.y - self.y
        dist = math.hypot(dx, dy)
        if dist <= 0:
            return
        # handle overlap push
        if self.rect.colliderect(target_rect):
            overlap_x = min(self.rect.right, target_rect.right) - max(self.rect.left, target_rect.left)
            overlap_y = min(self.rect.bottom, target_rect.bottom) - max(self.rect.top, target_rect.top)
            if overlap_x > 0 and overlap_y > 0:
                if overlap_x < overlap_y:
                    self.x += -overlap_x if self.rect.centerx < target_rect.centerx else overlap_x
                else:
                    self.y += -overlap_y if self.rect.centery < target_rect.centery else overlap_y
                self.rect.topleft = (int(self.x), int(self.y))

        move_x = (dx / dist) * self.speed
        move_y = (dy / dist) * self.speed

        # separation
        separation_x = separation_y = 0
        SEPARATION_RADIUS = TILE_SIZE
        SEPARATION_FORCE = 0.2
        for other in other_zombies:
            if other is self: continue
            dsq = (self.x - other.x)**2 + (self.y - other.y)**2
            if dsq < SEPARATION_RADIUS**2 and dsq > 0:
                d = math.sqrt(dsq)
                repel_x = (self.x - other.x) / d
                repel_y = (self.y - other.y) / d
                separation_x += repel_x * (SEPARATION_RADIUS - d) * SEPARATION_FORCE
                separation_y += repel_y * (SEPARATION_RADIUS - d) * SEPARATION_FORCE

        # separation from player
        dsp = (self.x - target_rect.x)**2 + (self.y - target_rect.y)**2
        if dsp < SEPARATION_RADIUS**2 and dsp > 0:
            d = math.sqrt(dsp)
            separation_x += (self.x - target_rect.x) / d * (SEPARATION_RADIUS - d) * SEPARATION_FORCE
            separation_y += (self.y - target_rect.y) / d * (SEPARATION_RADIUS - d) * SEPARATION_FORCE

        move_x += separation_x
        move_y += separation_y

        old_x, old_y = self.x, self.y
        self.x += move_x
        self.rect.x = int(self.x)
        collided_x = any(self.rect.colliderect(ob) for ob in obstacles) or any(self.rect.colliderect(z.rect) for z in other_zombies if z is not self) or self.rect.colliderect(target_rect)
        if collided_x:
            self.x = old_x
            self.rect.x = int(self.x)

        self.y += move_y
        self.rect.y = int(self.y)
        collided_y = any(self.rect.colliderect(ob) for ob in obstacles) or any(self.rect.colliderect(z.rect) for z in other_zombies if z is not self) or self.rect.colliderect(target_rect)
        if collided_y:
            self.y = old_y
            self.rect.y = int(self.y)

        self.rect.topleft = (int(self.x), int(self.y))

    def attack(self, player):
        damage = random.randint(self.min_attack, self.max_attack)
        infection = random.randint(self.min_infection, self.max_infection)
        player.health -= damage
        player.health = max(0, player.health)
        if infection > 0:
            player.infection = min(100, player.infection + infection)
            print(f"**HIT!** Player took {damage} damage and {infection}% infection!")
        else:
            print(f"Player took {damage} damage (no infection).")

    def take_damage(self, damage):
        self.health -= damage
        self.show_health_bar_timer = 120
        if self.health <= 0:
            print("Zombie eliminated.")
            return True
        return False

