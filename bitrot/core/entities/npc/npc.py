# core/entities/npc/npc.py

import pygame
import random
import math
import time
import core.data.config
from core.data.config import *
from core.entities.item.item import Item, Projectile, ITEM_TEMPLATES
from core.entities.item.item_factory import get_tinted_sprite
from core.entities.zombie.zombie import Zombie
from core.entities.zombie.zombie_data import ZombieData  
from core.messages import display_message
from faker import Faker
from core.entities.npc.npc_dialog import NPCDialog
from core.systems.utils import create_smooth_entity_mask, resolve_stuck_in_obstacle

# Mixins
from core.entities.npc.npc_data import NPCData
from core.entities.npc.npc_graphics import NPCGraphics
from core.entities.npc.npc_dialog import NPCDialog
from core.entities.npc.npc_combat import NPCCombat

CLOTHING_COLORS = [
    (255, 255, 255), (50, 50, 50), (220, 50, 50), (50, 200, 50), 
    (50, 50, 220), (220, 220, 50), (255, 105, 180), (255, 165, 0), 
    (139, 69, 19), (128, 128, 128)
]

class NPC(NPCData, NPCGraphics, NPCDialog, NPCCombat, Zombie):
    def __init__(self, x, y, game, is_static=False, layer=None):
        if not NPCData.NPC_TEMPLATES:
            NPCData.load_templates()
            
        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(game)

        if NPCData.NPC_TEMPLATES:
            available_templates = []
            template_weights = []
            for t in NPCData.NPC_TEMPLATES:
                t_static = t.get('is_static', False)
                
                if is_static and not t_static:
                    continue
                if not is_static and t_static:
                    continue
                    
                available_templates.append(t)
                template_weights.append(t.get('spawn_weight', 10))
                
            if available_templates:
                template = random.choices(available_templates, weights=template_weights, k=1)[0]
            else:
                template = random.choices(NPCData.NPC_TEMPLATES, weights=[t.get('spawn_weight', 10) for t in NPCData.NPC_TEMPLATES], k=1)[0]
        else:
            template = {
                'type': 'common',
                'name': "RANDOM",
                'sex': random.choice(['Male', 'Female']),
                'health': 100,
                'speed': 1.0,
                'min_xp': 10,
                'max_xp': 20,
                'min_attack': 1,
                'max_attack': 5,
                'loot': [],
                'sprites': {},
                'clothes': {},
                'is_friendly': False,
                'is_static': False,
                'spawn_zombies': 0
            }

        Zombie.__init__(self, x, y, template)
        try:
            self.spawn_zombies_multiplier = float(
                template.get('spawn_zombies_multiplier', template.get('spawn_zombies', 0.0))
            )
        except (ValueError, TypeError):
            self.spawn_zombies_multiplier = 0.0
        self.spawn_zombies_max = self.spawn_zombies_multiplier

        self.trade_config = template.get('trade_config')
        self.trade_stock = []
        self.trade_stock_generated = False

        if hasattr(self, 'loot_table'):
            self.loot_table = [loot for loot in self.loot_table if loot.get('item') not in ["Pants", "Jacket", "Tshirt", "TShirt", "Sneakers"]]

        self.game = game
        
        if layer is not None:
            self.layer = layer
        else:
            self.layer = game.current_layer_index if hasattr(game, 'current_layer_index') else 1

        self.max_health = int(self.max_health * NPC_HEALTH_MULTIPLIER)
        self.health = int(self.health * NPC_HEALTH_MULTIPLIER)
        self.min_attack = int(self.min_attack * NPC_DAMAGE_MULTIPLIER)
        self.max_attack = int(self.max_attack * NPC_DAMAGE_MULTIPLIER)
        
        if not hasattr(self, 'speed') or self.speed == 0:
            self.speed = 1.1 
        self.speed = self.speed * NPC_SPEED_MULTIPLIER

        self.base_search_range = NPC_DETECTION_RADIUS
        
        name_val = template.get('name', 'RANDOM')
        template_static = template.get('is_static', False)

        sex_val = template.get('sex', 'Random').capitalize()
        if sex_val == 'Random':
            sex_val = random.choice(['Male', 'Female'])
        self.sex = sex_val

        if name_val != 'RANDOM' and name_val != 'Zombie':
            self.name = name_val
            self.is_static = True
        else:
            self.is_static = template_static or is_static
            try:
                fake = Faker()
                if self.sex == 'Male':
                    self.name = fake.first_name_male()
                else:
                    self.name = fake.first_name_female()
            except ImportError:
                self.name = f"Survivor {random.randint(100, 999)}"

        if self.is_static:
            self.is_friendly = True
        else:
            self.is_friendly = False
        
        if getattr(self, 'layer', 1) in (2, 3):
            self.is_static = False
            self.is_friendly = False
            
        self.state = 'wandering' if not self.is_static else 'idle'

        self.start_x = x
        self.start_y = y

        self.idle_timer = 0
        self.stuck_timer = 0
        self.stuck_angle = 0

        self.dialog_flags = set()
        self.special_dialogs = []

        loaded_data = locals().get('data', locals().get('save_data', None))

        if loaded_data:
            self.health = loaded_data.get('health', self.max_health)
            self.state = loaded_data.get('state', 'idle')
            
            if 'inventory' in loaded_data:
                self.inventory = [item_factory.create_item_from_dict(i_data) for i_data in loaded_data['inventory']]
            if 'belt' in loaded_data:
                self.belt = [item_factory.create_item_from_dict(i_data) if i_data else None for i_data in loaded_data['belt']]
            if 'clothes' in loaded_data:
                self.clothes = {}
                for slot, c_data in loaded_data['clothes'].items():
                    self.clothes[slot] = item_factory.create_item_from_dict(c_data) if c_data else None
                    
            self.dialog_flags = set(loaded_data.get('dialog_flags', []))
            self.special_dialogs = loaded_data.get('special_dialogs', [])

        self.knockback_velocity = [0, 0]
        self.knockback_timer = 0

        self.aggro_timer = 0
        self.current_attacker = None

        self.inventory = []
        self.inventory = []
        id_name = f"ID: {self.name}"
        id_card = Item.create_from_name(id_name)
        if id_card:
            id_text = f"Name: {self.name}\nSex: {self.sex}"
            id_card.text = id_text
            id_card.original_text = id_text
            self.inventory.append(id_card)
        
        mobile = Item.create_from_name("Mobile off")
        if mobile:
            mobile.state = "off"
            self.inventory.append(mobile)

        if not self.inventory:
             random_item = Item.generate_random()
             if random_item and not random_item.liquid:
                 self.inventory.append(random_item)

        # 1. Categorize all available weapons from templates
        melee_pool = [name for name, data in ITEM_TEMPLATES.items() if data.get('type') == 'weapon_melee']
        ranged_pool = [name for name, data in ITEM_TEMPLATES.items() if data.get('type') == 'weapon_ranged']
        
        template_weapons = []
        if hasattr(self, 'loot_table'):
            for loot_dict in self.loot_table:
                item_name = loot_dict.get('item')
                if item_name in ITEM_TEMPLATES and ITEM_TEMPLATES[item_name].get('type') in ['weapon_melee', 'weapon_ranged']:
                    template_weapons.append(item_name)
        
        weapon_name = None

        # 2. Handle Weapon Assignment
        if template_weapons:
            t_ranged = [w for w in template_weapons if ITEM_TEMPLATES[w].get('type') == 'weapon_ranged']
            t_melee = [w for w in template_weapons if ITEM_TEMPLATES[w].get('type') == 'weapon_melee']
            if not self.is_friendly:
                if random.random() < 0.01 and t_ranged:
                    weapon_name = random.choice(t_ranged)
                elif t_melee:
                    weapon_name = random.choice(t_melee)
                else:
                    weapon_name = random.choice(template_weapons)
            else:
                weapon_name = random.choice(template_weapons)
        elif not self.is_friendly:
            if random.random() < 0.01 and ranged_pool:
                weapon_name = random.choice(ranged_pool)
            elif melee_pool:
                weapon_name = random.choice(melee_pool)
            else:
                weapon_name = "Knife"
        else:
            all_weapons = melee_pool + ranged_pool
            if all_weapons:
                weapon_name = random.choice(all_weapons)
            else:
                weapon_name = "Knife"

        if weapon_name:
            self.equipped_weapon = Item.create_from_name(weapon_name, randomize_durability=True)
        else:
            self.equipped_weapon = Item.create_from_name("Knife", randomize_durability=True)
            
        if not self.equipped_weapon:
             self.equipped_weapon = Item.generate_random()

        if self.equipped_weapon and self.equipped_weapon.item_type == 'weapon_ranged':
            ammo_type = self.equipped_weapon.ammo_type
            if ammo_type:
                ammo_item = Item.create_from_name(ammo_type)
                if ammo_item:
                    ammo_item.load = 50 
                    self.inventory.append(ammo_item)

        self.melee_swing_timer = 0
        self.melee_swing_angle = 0

        self.is_dead = False
        self.dead_image = False
        
        if not hasattr(self, 'angle'): self.angle = 0
        if not hasattr(self, 'dx'): self.dx = 0
        if not hasattr(self, 'dy'): self.dy = 0
            
        self.attack_range = TILE_SIZE * 1.5
        self.last_attack_time = 0
        self.attack_cooldown = 1000
        
        self.health_bar_timer = 0
        
        if not hasattr(self, 'path'): self.path = []
        if not hasattr(self, 'last_path_calc_time'): self.last_path_calc_time = 0

        if not self.images or not self.images.get('center'):
            self._load_base_sprite()
            
        self.clothes = {}
        hair_options = ['Bald', 'Mowalk', 'Cut', 'Crew', 'Long']
        predefined_clothes = template.get('predefined_clothes', {})
        clothes_slots = template.get('clothes_slots', []) 
        
        clothes_to_equip = {
            "feet": "Sneakers",
            "legs": "Pants",
            "body": "Tshirt",
            "arms": "Jacket" if random.random() < 0.2 else None,
            "hair": random.choice(hair_options)
        }
        
        for slot_name in clothes_slots:
            cloth_name = predefined_clothes.get(slot_name)
            if cloth_name:
                clothes_to_equip[slot_name] = cloth_name
            else:
                available_pool = ZombieData.ZOMBIE_CLOTHES_POOL.get(slot_name, [])
                if available_pool:
                    choice = random.choice(available_pool)
                    clothes_to_equip[slot_name] = choice['name'] if isinstance(choice, dict) else choice
                elif slot_name not in clothes_to_equip:
                    clothes_to_equip[slot_name] = None
                    
        for slot_name, cloth_name in predefined_clothes.items():
            if slot_name not in clothes_to_equip:
                clothes_to_equip[slot_name] = cloth_name
        
        for slot_name, cloth_name in clothes_to_equip.items():
            if not cloth_name:
                continue
            item = Item.create_from_name(cloth_name)
            if item:
                is_explicitly_defined = (slot_name in predefined_clothes and predefined_clothes.get(slot_name) == cloth_name)

                if not is_explicitly_defined and cloth_name in ("Tshirt", "Pants", "Jacket", "Sneakers"):
                    item.color = random.choice(CLOTHING_COLORS)
                    if item.image:
                        item.image = get_tinted_sprite(item.image, item.name, item.color)
                
                actual_slot = getattr(item, 'slot', slot_name)
                
                if not getattr(item, 'slot', None):
                    if cloth_name == "Pants": actual_slot = "legs"
                    elif cloth_name == "Jacket": actual_slot = "arms"
                    elif cloth_name == "Tshirt": actual_slot = "body"
                    elif cloth_name == "Sneakers": actual_slot = "feet"
                    elif cloth_name in hair_options: actual_slot = "hair"

                if actual_slot not in self.clothes:
                    self.clothes[actual_slot] = item
        
        
        self.mask = create_smooth_entity_mask(TILE_SIZE, TILE_SIZE, inset_x=2, inset_y=2)

        self.last_grid_pos = (int(self.rect.centerx // TILE_SIZE), int(self.rect.centery // TILE_SIZE))

    def attack(self, target_entity, game):
        if getattr(self, 'is_dead', False) or getattr(self, 'health', 0) <= 0:
            return
        if getattr(target_entity, 'is_dead', False) or getattr(target_entity, 'health', 1) <= 0:
            return

        # Friendly NPCs or zombies or animals are not attacked by hostile NPCs
        if hasattr(game, 'npcs') and target_entity in game.npcs and getattr(target_entity, 'is_friendly', False):
            return
        if getattr(target_entity, 'type', '') == 'animal' or type(target_entity).__name__ == 'Animal':
            return
        if isinstance(target_entity, Zombie) and getattr(target_entity, 'type', '') != 'animal':
            return

        dx = target_entity.rect.centerx - self.rect.centerx
        dy = target_entity.rect.centery - self.rect.centery
        self.melee_swing_angle = math.atan2(-dy, dx)
        self.aim_angle = math.degrees(self.melee_swing_angle)

        weapon = getattr(self, 'equipped_weapon', None)
        is_ranged = weapon and getattr(weapon, 'item_type', '') == 'weapon_ranged'

        base_damage = random.randint(self.min_attack, self.max_attack)
        weapon_dmg = 0
        if weapon:
            if hasattr(weapon, 'damage'):
                weapon_dmg = weapon.damage
            elif hasattr(weapon, 'min_damage') and hasattr(weapon, 'max_damage'):
                weapon_dmg = random.randint(weapon.min_damage, weapon.max_damage)
        damage_to_deal = max(1, base_damage + weapon_dmg)

        current_time = pygame.time.get_ticks()

        if is_ranged:
            if self.has_line_of_sight(target_entity.rect, game, current_time):
                if weapon and hasattr(weapon, 'sounds') and weapon.sounds.get('shoot'):
                    game.sound_manager.play_sound(
                        weapon.sounds['shoot'],
                        subdir='items',
                        game=game,
                        source_pos=self.rect.center,
                        base_volume=0.5,
                        is_critical=True
                    )
                projectile = Projectile(
                    self.rect.centerx,
                    self.rect.centery,
                    target_entity.rect.centerx,
                    target_entity.rect.centery,
                    speed=20,
                    damage=damage_to_deal,
                    game=game
                )
                projectile.owner = self
                projectile.hostile = True
                game.projectiles.append(projectile)
        else:
            self.melee_swing_timer = 15
            if getattr(self, 'sound_attack', None):
                game.sound_manager.play_sound(
                    self.sound_attack,
                    subdir='npc',
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=0.4,
                    pitch_variance=0.15
                )
            elif weapon and hasattr(weapon, 'sounds') and weapon.sounds.get('swing'):
                game.sound_manager.play_sound(
                    weapon.sounds['swing'],
                    subdir='items',
                    game=game,
                    source_pos=self.rect.center,
                    base_volume=0.4,
                    is_critical=True
                )

            if target_entity == game.player:
                if getattr(game.player, 'vehicle', None):
                    veh = game.player.vehicle
                    veh.damage_motor(random.uniform(0.5, 1.5))
                else:
                    target_entity.take_damage(game, damage_to_deal, 0, attacker=self)
            else:
                is_dead = target_entity.take_damage(damage_to_deal, game, attacker=self)
                if is_dead:
                    target_entity.die(game)

    def update(self, game):
        if getattr(self, 'is_dead', False) or getattr(self, 'health', 0) <= 0:
            return

        if getattr(self, 'layer', 1) != getattr(game, 'current_layer_index', 1):
            return

        current_time = pygame.time.get_ticks()

        # Handle static friendly NPCs (storekeepers, quest givers, lobby survivors)
        if getattr(self, 'is_static', False):
            self.vx = 0
            self.vy = 0
            self.walk_anim_angle = 0
            self.state = 'idle'
            if game.player:
                dx = game.player.rect.centerx - self.rect.centerx
                dy = game.player.rect.centery - self.rect.centery
                if math.hypot(dx, dy) < TILE_SIZE * 3:
                    self.aim_angle = math.degrees(math.atan2(-dy, dx))
            if self.health_bar_timer > 0:
                self.health_bar_timer -= game.dt_ms
            return

        # Synchronize attack range from equipped weapon
        weapon = getattr(self, 'equipped_weapon', None)
        if weapon and getattr(weapon, 'item_type', '') == 'weapon_ranged':
            self.attack_range = TILE_SIZE * 8
        else:
            self.attack_range = TILE_SIZE * 1.5

        # Handle friendly roaming NPCs (wander peacefully, defend if attacked by player)
        if getattr(self, 'is_friendly', False):
            if getattr(self, 'current_attacker', None) == game.player:
                self.is_friendly = False
            else:
                if getattr(self, 'aggro_timer', 0) > 0:
                    self.aggro_timer -= game.dt_ms
                self.state = 'wandering'
                super().update_ai(game.player.rect, game.obstacles, [e for e in getattr(game, 'npcs', []) if e != self], game)
                if self.health_bar_timer > 0:
                    self.health_bar_timer -= game.dt_ms
                if self.melee_swing_timer > 0:
                    self.melee_swing_timer -= game.dt_ms
                return

        # --- HOSTILE NPC: Behaves exactly like a Zombie ---
        if getattr(self, 'knockback_timer', 0) > 0:
            super().update(game)
            return

        if getattr(self, 'aggro_timer', 0) > 0:
            self.aggro_timer -= game.dt_ms

        nearby_entities = [
            e for e in getattr(game, 'active_zombies', game.zombies)
            if getattr(e, 'layer', 1) == self.layer
        ] + [
            n for n in getattr(game, 'npcs', [])
            if n != self and getattr(n, 'layer', 1) == self.layer
        ]
        obstacles = getattr(game, 'obstacles', [])

        self.update_ai(game.player.rect, obstacles, nearby_entities, game)

        # Smooth aim angle for weapon graphics
        if game.player:
            dx = game.player.rect.centerx - self.rect.centerx
            dy = game.player.rect.centery - self.rect.centery
            dist_to_p = math.hypot(dx, dy)
            if dist_to_p <= self.attack_range * 1.5 or getattr(self, 'state', '') == 'chasing':
                self.aim_angle = math.degrees(math.atan2(-dy, dx))
            elif abs(self.vx) > 0.1 or abs(self.vy) > 0.1:
                self.aim_angle = math.degrees(math.atan2(-self.vy, self.vx))

        if self.health_bar_timer > 0:
            self.health_bar_timer -= game.dt_ms
        if self.melee_swing_timer > 0:
            self.melee_swing_timer -= game.dt_ms

    def stop_moving(self):
        self.state = 'idle'
        self.path = []      
        self.idle_timer = 500
    
    def die(self, game):
        if self.is_dead:
            return

        if not hasattr(self, 'inventory') or self.inventory is None:
            self.inventory = []

        if hasattr(self, 'equipped_weapon') and self.equipped_weapon:
            self.inventory.append(self.equipped_weapon)
            self.equipped_weapon = None
            
        EXCLUDED_CORPSE_SLOTS = ('hair', 'facial')
        if hasattr(self, 'clothes'):
            for slot, cloth_item in self.clothes.items():
                if cloth_item and slot not in EXCLUDED_CORPSE_SLOTS:
                    if getattr(cloth_item, 'slot', None) not in EXCLUDED_CORPSE_SLOTS:
                        self.inventory.append(cloth_item)
            self.clothes = {}

        if hasattr(self, 'trade_stock') and self.trade_stock:
            for it in self.trade_stock:
                self.inventory.append(it)
            self.trade_stock = []

        super().die(game)
        try:
            self.kill()
        except:
            pass

        # --- SPAWN ZOMBIES ON PLAYER RADIUS (Using spawn_zombies_multiplier) ---
        multiplier = float(getattr(self, 'spawn_zombies_multiplier', 0.0))
        if multiplier > 0 and getattr(game, 'player', None):
            from core.entities.zombie.zombie import Zombie
            from core.placement import find_free_tile

            base_spawns = getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 1) or 1
            num_z_to_spawn = max(1, int(round(base_spawns * multiplier)))

            max_z_global = getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500)
            p_center = game.player.rect.center
            view_radius = getattr(game, 'player_view_radius', 10 * TILE_SIZE)

            for _ in range(num_z_to_spawn):
                if len(game.zombies) >= max_z_global:
                    break
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(TILE_SIZE * 3, max(TILE_SIZE * 5, view_radius))
                zx = int(p_center[0] + math.cos(angle) * dist)
                zy = int(p_center[1] + math.sin(angle) * dist)

                z = Zombie.create_random(zx, zy)
                if z:
                    z.layer = getattr(self, 'layer', getattr(game, 'current_layer_index', 1))
                    free_pos = find_free_tile(z.rect, game.obstacles, initial_pos=(zx, zy), max_radius=8)
                    if free_pos:
                        z.rect.topleft = free_pos
                        z.x, z.y = free_pos
                        game.zombies.append(z)

        # ---------------------------------------------------------
        # Dynamic Instant Circular NPC Respawn (10 tiles from view radius)
        # ---------------------------------------------------------
        from core.map.spawn_manager import get_out_of_sight_spawn_pos

        max_npc = getattr(core.data.config, 'MAX_NPCS_GLOBAL', 1500)
        max_npc_chunk = getattr(core.data.config, 'NPC_MAX_CHUNK', 6)
        if getattr(core.data.config, 'NPC_RESPAWN', True) and max_npc > 0 and max_npc_chunk > 0:
            num_npcs = int(getattr(core.data.config, 'NPCS_PER_SPAWN', 1))
            if num_npcs > 0:
                for _ in range(num_npcs):
                    if len(game.npcs) >= max_npc:
                        break
                    spawn_pos = get_out_of_sight_spawn_pos(game)
                    if spawn_pos:
                        respawn_layer = getattr(self, 'layer', getattr(game, 'current_layer_index', 1))
                        new_npc = NPC(
                            spawn_pos[0], 
                            spawn_pos[1], 
                            game, 
                            is_static=False, 
                            layer=respawn_layer
                        )
                        if respawn_layer in (2, 3):
                            new_npc.is_friendly = False
                            new_npc.is_static = False
                        else:
                            new_npc.is_friendly = random.random() > getattr(core.data.config, 'NPC_HOSTILE_PERCENT', 0.6)
                        game.npcs.add(new_npc)

        max_zombies = getattr(core.data.config, 'MAX_ZOMBIES_GLOBAL', 500)
        max_z_chunk = getattr(core.data.config, 'ZOMBIE_MAX_CHUNK', 6)
        if getattr(core.data.config, 'ZOMBIE_RESPAWN', True) and max_zombies > 0 and max_z_chunk > 0:
            from core.entities.zombie.zombie import Zombie
            num_zombies = int(getattr(core.data.config, 'ZOMBIES_PER_SPAWN', 1))
            if num_zombies > 0:
                for _ in range(num_zombies):
                    if len(game.zombies) >= max_zombies:
                        break
                    spawn_pos = get_out_of_sight_spawn_pos(game)
                    if spawn_pos:
                        zombie = Zombie.create_random(spawn_pos[0], spawn_pos[1])
                        game.zombies.append(zombie)

        if hasattr(game, 'spatial_manager'):
            game.spatial_manager.rebuild_zombie_grid()

        # Add death burst visual effect
        if hasattr(game, 'splashes'):
            game.splashes.append({
                'pos': (self.rect.centerx, self.rect.bottom), 
                'time': pygame.time.get_ticks(),
                'duration': 250, 
                'radius': 5,    
                'type': 'death_burst'
            })

        self.rect.x = -9999
        self.rect.y = -9999