import os
import random
import math
import pygame
import xml.etree.ElementTree as ET
import uuid

# Import the new config variables
from data.config import *

ZOMBIE_TEMPLATES = []

class Zombie:
    def __init__(self, x, y, template):
        self.x = x
        self.y = y
        self.id = str(uuid.uuid4())
        self.name = template.get('name', 'Zombie')
        self.max_health = template.get('health')
        self.health = self.max_health
        self.speed = template.get('speed', ZOMBIE_SPEED)
        self.loot_table = template.get('loot', [])
        self.xp_value = random.randint(template.get('min_xp'), template.get('max_xp'))
        self.image = self.load_sprite(template.get('sprite'))
        self.color = RED
        self.rect = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        self.show_health_bar_timer = 0
        self.last_attack_time = 0
        self.attack_range = TILE_SIZE * 1.5
        self.min_attack = template.get('min_attack')
        self.max_attack = template.get('max_attack')
        self.min_infection = template.get('min_infection')
        self.max_infection = template.get('max_infection')

        # --- NEW AI STATE VARIABLES ---
        self.state = 'wandering'  # Can be 'wandering' or 'chasing'
        self.wander_target = None # (x, y) coordinate
        self.last_wander_change = 0 # Timestamp for changing wander direction
        # --- END NEW AI VARIABLES ---

    def load_sprite(self, sprite_file):
        if not sprite_file: return None
        try:
            path = os.path.join('game', 'zombies', 'sprites', sprite_file)
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
        except Exception as e:
            print(f"Error loading zombie sprite {sprite_file}: {e}")
            return None

    def take_damage(self, amount):
        self.health -= amount
        self.health = max(0, self.health)
        self.show_health_bar_timer = 120 # Show health bar for 2 seconds (60fps)
        return self.health <= 0 # Return True if dead

    def draw(self, surface, offset_x, offset_y):
        # This draw method is for the pixelated zoom approach
        draw_rect = self.rect.move(offset_x, offset_y)

        if self.image:
            surface.blit(self.image, draw_rect)
        else:
            pygame.draw.rect(surface, self.color, draw_rect)

        if self.show_health_bar_timer > 0:
            bar_y = draw_rect.top - 7
            bg_bar_rect = pygame.Rect(draw_rect.left, bar_y, TILE_SIZE, 5)
            pygame.draw.rect(surface, DARK_GRAY, bg_bar_rect)

            health_percentage = max(0, self.health / self.max_health)
            health_bar_width = int(health_percentage * TILE_SIZE)
            health_bar_rect = pygame.Rect(draw_rect.left, bar_y, health_bar_width, 5)
            pygame.draw.rect(surface, GREEN, health_bar_rect)

            self.show_health_bar_timer -= 1

    def has_line_of_sight(self, target_rect, obstacles):
        """Checks if there is an uninterrupted line between zombie and target."""
        if not ZOMBIE_LINE_OF_SIGHT_CHECK:
            return True # Skip check if disabled in config

        start_pos = self.rect.center
        end_pos = target_rect.center

        # Simple line segment-rectangle intersection check using pygame's clipline
        # clipline returns the clipped points if it intersects, or empty tuple if not
        for obs in obstacles:
            if obs.clipline(start_pos, end_pos):
                return False # Line of sight is blocked

        return True # Line of sight is clear

    def update_ai(self, player_rect, obstacles, other_zombies):
        """Main AI logic: decide state (wander/chase) and target."""
        current_time = pygame.time.get_ticks()
        dist_to_player = math.hypot(player_rect.centerx - self.rect.centerx,
                                    player_rect.centery - self.rect.centery)

        can_see_player = self.has_line_of_sight(player_rect, obstacles)
        target_pos = None # Reset target each frame

        # Decide state: Chasing or Wandering
        if dist_to_player < ZOMBIE_DETECTION_RADIUS and can_see_player:
            self.state = 'chasing'
            target_pos = player_rect.center # Chase the player directly
        else:
            self.state = 'wandering'

            # Update wander target if needed
            if ZOMBIE_WANDER_ENABLED:
                # If interval passed, no target exists, or target was reached
                target_reached = self.wander_target and math.hypot(self.wander_target[0] - self.rect.centerx, self.wander_target[1] - self.rect.centery) < TILE_SIZE
                if (current_time - self.last_wander_change > ZOMBIE_WANDER_CHANGE_INTERVAL) or \
                   (self.wander_target is None) or target_reached:

                    # Pick a new random point within ~5 tiles
                    wander_radius = 5 * TILE_SIZE
                    new_target_x = self.rect.centerx + random.randint(-wander_radius, wander_radius)
                    new_target_y = self.rect.centery + random.randint(-wander_radius, wander_radius)

                    self.wander_target = (new_target_x, new_target_y)
                    self.last_wander_change = current_time

                target_pos = self.wander_target # Wander towards the target point
            else:
                target_pos = None # Wandering disabled, stand still

        # If we have a valid target (player or wander point), move towards it
        if target_pos:
            self.move_towards(target_pos, obstacles, other_zombies)
        else:
            # No target, do nothing (or add idle animation later)
            pass

    def move_towards(self, target_pos, obstacles, other_zombies):
        """Calculates movement vector towards a target_pos and handles collisions."""
        dx = target_pos[0] - self.rect.centerx
        dy = target_pos[1] - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist > TILE_SIZE / 2: # Don't move if already very close
            # Normalize and scale by speed
            move_x = (dx / dist) * self.speed
            move_y = (dy / dist) * self.speed
        else:
            move_x, move_y = 0, 0

        # Collision Handling (separated X and Y checks)
        old_x, old_y = self.x, self.y

        # Move X
        self.x += move_x
        self.rect.x = int(self.x)
        collided_x = False
        for obs in obstacles:
            if self.rect.colliderect(obs): collided_x = True; break
        if not collided_x:
            for z in other_zombies:
                if z is not self and self.rect.colliderect(z.rect): collided_x = True; break

        if collided_x:
            self.x = old_x
            self.rect.x = int(self.x)

        # Move Y
        self.y += move_y
        self.rect.y = int(self.y)
        collided_y = False
        for obs in obstacles:
            if self.rect.colliderect(obs): collided_y = True; break
        if not collided_y:
            for z in other_zombies:
                 if z is not self and self.rect.colliderect(z.rect): collided_y = True; break

        if collided_y:
            self.y = old_y
            self.rect.y = int(self.y)

        # Update final position based on potential collision adjustments
        self.rect.topleft = (int(self.x), int(self.y))

    def attack(self, player):
        damage = random.randint(self.min_attack, self.max_attack)
        infection = random.randint(self.min_infection, self.max_infection)
        player.health -= damage
        player.health = max(0, player.health)
        if infection > 0:
            player.infection = min(100, player.infection + infection)
            print(f"**HIT!** Player takes {damage} damage and {infection}% infection.")
        else:
            print(f"**HIT!** Player takes {damage} damage.")

    @staticmethod
    def load_templates(folder='game/zombies/data'):
        """Loads all zombie templates from XML files in a folder."""
        global ZOMBIE_TEMPLATES
        ZOMBIE_TEMPLATES = []
        try:
            for filename in os.listdir(folder):
                if filename.endswith('.xml'):
                    filepath = os.path.join(folder, filename)
                    try:
                        tree = ET.parse(filepath)
                        root = tree.getroot()
                        if root.tag == 'zombie':
                            # --- Corrected XML Parsing ---
                            template = {}
                            name_node = root.find('name')
                            stats_node = root.find('stats')
                            visuals_node = root.find('visuals')
                            attack_node = root.find('attack')
                            infection_node = root.find('infection')
                            xp_node = root.find('xp')
                            loot_node = root.find('loot')

                            # Safely get values, providing defaults
                            template['name'] = name_node.get('value') if name_node is not None else 'Unknown Zombie'

                            template['health'] = float(stats_node.find('health').get('value')) if stats_node and stats_node.find('health') is not None else 10.0
                            template['speed'] = float(stats_node.find('speed').get('value')) if stats_node and stats_node.find('speed') is not None else ZOMBIE_SPEED

                            template['sprite'] = visuals_node.find('sprite').get('file') if visuals_node and visuals_node.find('sprite') is not None else None

                            template['min_attack'] = int(attack_node.find('min').get('value')) if attack_node and attack_node.find('min') is not None else 1
                            template['max_attack'] = int(attack_node.find('max').get('value')) if attack_node and attack_node.find('max') is not None else 3

                            template['min_infection'] = int(infection_node.find('min').get('value')) if infection_node and infection_node.find('min') is not None else 0
                            template['max_infection'] = int(infection_node.find('max').get('value')) if infection_node and infection_node.find('max') is not None else 1

                            template['min_xp'] = int(xp_node.find('min').get('value')) if xp_node and xp_node.find('min') is not None else 1
                            template['max_xp'] = int(xp_node.find('max').get('value')) if xp_node and xp_node.find('max') is not None else 5

                            template['loot'] = []
                            if loot_node is not None:
                                for item_node in loot_node.findall('item'): # Corrected findall path
                                    template['loot'].append({
                                        'item': item_node.get('name'),
                                        'chance': float(item_node.get('chance'))
                                    })
                            # --- End Corrected XML Parsing ---

                            ZOMBIE_TEMPLATES.append(template)
                            print(f"Loaded zombie template: {template['name']}")
                    except Exception as e:
                        print(f"Error loading zombie template from {filename}: {e}")
        except FileNotFoundError:
             print(f"Error: Zombie template folder not found: {folder}")


    @staticmethod
    def create_random(x, y):
        """Creates a zombie instance from a random template."""
        if not ZOMBIE_TEMPLATES:
            Zombie.load_templates() # Load templates if not already loaded
        if not ZOMBIE_TEMPLATES:
            # Fallback if loading failed or no templates exist
            print("Error: No zombie templates loaded. Creating default zombie.")
            default_template = {
                'name':'Zombie',
                'health':10,
                'speed':ZOMBIE_SPEED, 
                'loot':[], 
                'min_xp':1,
                'max_xp':5, 
                'min_attack':1, 
                'max_attack':3, 
                'min_infection':0, 
                'max_infection':1
            }
            return Zombie(x, y, default_template)

        template = random.choice(ZOMBIE_TEMPLATES)
        return Zombie(x, y, template)

# Load templates when the module is imported (ensure it only happens once)
if not ZOMBIE_TEMPLATES:
    Zombie.load_templates()
