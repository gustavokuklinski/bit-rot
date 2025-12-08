import pygame
import random
import os
import math
import time
import xml.etree.ElementTree as ET
from core.entities.zombie.zombie import Zombie, ZOMBIE_CLOTHES_POOL
from core.data.config import TILE_SIZE, SPRITE_PATH, RED, DATA_PATH

class NPC(Zombie):
    # --- Class-Level Cache ---
    _base_cache = {} 
    NPC_TEMPLATES = [] # Store loaded NPC templates here

    def __init__(self, x, y, game):
        # 1. Load templates if they haven't been loaded yet
        if not NPC.NPC_TEMPLATES:
            NPC.load_templates()

        # 2. Select a template (Fallback to hardcoded if XML fails)
        if NPC.NPC_TEMPLATES:
            template = random.choice(NPC.NPC_TEMPLATES)
        else:
            # Fallback template
            template = {
                'name': "Survivor", 
                'sex': random.choice(['Male', 'Female']),
                'health': 100,
                'speed': 1.0,
                'min_xp': 10,
                'max_xp': 20,
                'min_attack': 1,
                'max_attack': 5,
                'loot': [],
                'sprites': {},
                'clothes': {} 
            }

        # 3. Initialize parent (Zombie) with the chosen template
        super().__init__(x, y, template)
        
        self.game = game
        
        # Override name if template was random/generic
        if self.name == "Zombie" or self.name == "RANDOM":
             self.name = f"Survivor {random.randint(100, 999)}"

        self.is_friendly = True
        self.state = 'wandering'
        
        # Ensure movement attributes exist
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
        
        if not hasattr(self, 'speed') or self.speed == 0:
            self.speed = 1.1
            
        self.attack_range = TILE_SIZE * 1.2
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        # --- Visual Setup ---
        # Fix: Check if 'center' is missing, not just if the dict is empty
        if not self.images or not self.images.get('center'):
            self._load_base_sprite()
            
        # Only assign random clothes if the XML didn't specify them
        if not self.clothes:
             self._assign_random_clothes()

    def load_sprite(self, sprite_file):
        """Override to prefer player/ folder for NPCs."""
        if not sprite_file: return None
        
        # Paths to check for NPC sprites
        candidates = [
            os.path.join(SPRITE_PATH, "player", sprite_file), # Prefer player/
            os.path.join(SPRITE_PATH, sprite_file),
            os.path.join(SPRITE_PATH, "zombie", sprite_file)  # Fallback
        ]

        for path in candidates:
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                except Exception as e:
                    print(f"Error loading NPC sprite at {path}: {e}")
        return None

    @staticmethod
    def load_templates():
        """Loads NPC templates from game/lib/data/npc/."""
        npc_folder = os.path.join(DATA_PATH, 'npc')
        NPC.NPC_TEMPLATES = []
        
        if not os.path.exists(npc_folder):
            print(f"NPC Warning: Folder not found at {npc_folder}")
            return

        for filename in os.listdir(npc_folder):
            if filename.endswith('.xml'):
                filepath = os.path.join(npc_folder, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    
                    if root.tag == 'zombie':
                        template = {}
                        
                        name_node = root.find('name')
                        template['name'] = name_node.get('value') if name_node is not None else 'Survivor'

                        stats_node = root.find('stats')
                        if stats_node is not None:
                            health_node = stats_node.find('health')
                            template['min_health'] = int(health_node.get('min', 100))
                            template['max_health'] = int(health_node.get('max', 100))
                            template['health'] = template['max_health'] 

                            speed_node = stats_node.find('speed')
                            template['min_speed'] = float(speed_node.get('min', 1.0))
                            template['max_speed'] = float(speed_node.get('max', 1.0))
                            template['speed'] = template['max_speed']

                            attack_node = stats_node.find('attack')
                            template['min_attack'] = int(attack_node.get('min', 5))
                            template['max_attack'] = int(attack_node.get('max', 10))

                            infection_node = stats_node.find('infection')
                            template['min_infection'] = int(infection_node.get('min', 0))
                            template['max_infection'] = int(infection_node.get('max', 0))

                        xp_node = root.find('xp')
                        if xp_node is not None:
                            template['min_xp'] = float(xp_node.get('min', 10))
                            template['max_xp'] = float(xp_node.get('max', 20))
                        else:
                            template['min_xp'], template['max_xp'] = 10, 20

                        visuals_node = root.find('visuals')
                        template['sprites'] = {}
                        if visuals_node is not None:
                            for sprite_node in visuals_node.findall('sprite'):
                                s_id = sprite_node.get('id')
                                s_file = sprite_node.get('file')
                                if s_id and s_file:
                                    template['sprites'][s_id] = s_file

                        clothes_node = root.find('clothes')
                        template['clothes_slots'] = []
                        if clothes_node is not None:
                            for slot_node in clothes_node:
                                template['clothes_slots'].append(slot_node.tag)

                        sound_node = root.find('sound')
                        template['sounds'] = {}
                        if sound_node is not None:
                            for sound_type in ['hit', 'wander', 'dead', 'attack', 'steps']:
                                node = sound_node.find(sound_type)
                                if node is not None:
                                    template['sounds'][sound_type] = node.get('src')
                        
                        template['sex'] = root.find('sex').get('value') if root.find('sex') is not None else 'Random'
                        template['profession'] = root.find('profession').get('value') if root.find('profession') is not None else 'Survivor'

                        NPC.NPC_TEMPLATES.append(template)

                except Exception as e:
                    print(f"NPC Error: Could not load {filename}: {e}")

    def _load_base_sprite(self):
        """Robustly loads a base sprite (Fallback if XML has no visuals)."""
        candidates = ["player/base.png", "player/player.png", "player/idle.png", "zombie/zombie.png"]
        found_img = None

        for filename in candidates:
            if filename in NPC._base_cache:
                found_img = NPC._base_cache[filename]; break
            
            # Check multiple path styles (exact path vs sprite root)
            full_path_A = os.path.join(SPRITE_PATH, *filename.split('/'))
            full_path_B = os.path.join(SPRITE_PATH, filename)
            
            if os.path.exists(full_path_A):
                try:
                    img = pygame.image.load(full_path_A).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPC._base_cache[filename] = found_img
                    break
                except: pass
            elif os.path.exists(full_path_B):
                 try:
                    img = pygame.image.load(full_path_B).convert_alpha()
                    found_img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
                    NPC._base_cache[filename] = found_img
                    break
                 except: pass

        if found_img:
            self.images['center'] = found_img
            self.images['left'] = found_img
            self.images['right'] = found_img
            self.image = found_img
        else:
             print("NPC Error: No valid sprite found! Rendering as Red Square.")

    def _assign_random_clothes(self):
        """Fallback clothes assignment."""
        self.clothes = {}
        slots = ['legs', 'body', 'head']
        for slot in slots:
            if slot == 'head' and random.random() < 0.3: continue 
            available = ZOMBIE_CLOTHES_POOL.get(slot, [])
            if available:
                self.clothes[slot] = random.choice(available)

    def update(self, game):
        """Updates the NPC: AI, Physics, Animation."""
        obstacles = game.obstacles
        current_time = pygame.time.get_ticks()

        # --- AI: Find and Attack Zombies ---
        target_zombie = None
        min_dist = 400 
        
        for zombie in game.zombies:
            dist = math.hypot(zombie.rect.centerx - self.rect.centerx, zombie.rect.centery - self.rect.centery)
            if dist < min_dist:
                min_dist = dist
                target_zombie = zombie

        if target_zombie:
            self.state = 'chasing'
            dx = target_zombie.rect.centerx - self.rect.centerx
            dy = target_zombie.rect.centery - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if dist > TILE_SIZE * 0.8:
                self.angle = math.degrees(math.atan2(-dy, dx))
                scale = self.speed / dist
                self.dx = dx * scale
                self.dy = dy * scale
            else:
                self.dx, self.dy = 0, 0
                
            # Attack logic
            if dist <= self.attack_range and (current_time - self.last_attack_time > self.attack_cooldown):
                self.last_attack_time = current_time
                self.melee_swing_timer = 15
                self.melee_swing_angle = math.atan2(-dy, dx)
                
                # Deal damage
                damage = random.randint(self.min_attack, self.max_attack)
                is_dead = target_zombie.take_damage(damage, game)
                
                if is_dead:
                    if target_zombie in game.zombies:
                        game.zombies.remove(target_zombie)
                        game.sound_manager.play_sound('zombie_death', subdir='zombie', game=game)
                    self._trigger_respawn(game)
        
        else:
            self.state = 'wandering'
            if random.random() < 0.02:
                self.angle += random.randint(-45, 45)
            rad = math.radians(self.angle)
            self.dx = math.cos(rad) * self.speed * 0.5
            self.dy = -math.sin(rad) * self.speed * 0.5

        # Optimization & Animation
        is_moving = self.dx != 0 or self.dy != 0

        if is_moving:
            self.walk_anim_angle = math.sin(time.time() * 15) * 2
            self.vx = self.dx
        else:
            self.walk_anim_angle = 0
            self.vx = 0

        if not is_moving: return

        # --- Apply Physics ---
        self.x += self.dx
        self.rect.x = int(self.x)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.dx > 0: self.rect.right = obstacle.left
                elif self.dx < 0: self.rect.left = obstacle.right
                self.x = self.rect.x
                self.angle = random.randint(0, 360) 

        self.y += self.dy
        self.rect.y = int(self.y)
        for obstacle in obstacles:
            if self.rect.colliderect(obstacle):
                if self.dy > 0: self.rect.bottom = obstacle.top
                elif self.dy < 0: self.rect.top = obstacle.bottom
                self.y = self.rect.y
                self.angle = random.randint(0, 360)

        self.rect.topleft = (int(self.x), int(self.y))

    def _trigger_respawn(self, game):
        offset = 800
        angle = random.uniform(0, 6.28)
        sx = game.player.x + math.cos(angle) * offset
        sy = game.player.y + math.sin(angle) * offset
        new_z = Zombie.create_random(sx, sy)
        game.zombies.append(new_z)