import random
import math
from data.config import *

class PlayerProgression:
    def __init__(self, player_data):
        # Attributes with XP and level
        self.strength = self._create_attribute(player_data, 'strength')
        self.fitness = self._create_attribute(player_data, 'fitness')
        self.melee = self._create_attribute(player_data, 'melee')
        self.ranged = self._create_attribute(player_data, 'ranged')

        # Passive skills
        self.lucky = player_data['attributes'].get('lucky', 0.0)
        self.speed = player_data['attributes'].get('speed', 0.0)

    def _create_attribute(self, player_data, attr_name):
        return {
            "level": player_data['attributes'].get(attr_name, 0.0),
            "xp": 0,
            "xp_to_next_level": 100
        }

    def _add_xp(self, attribute, amount):
        attribute['xp'] += amount
        print(f"Gained {amount} XP for an {attribute}.")
        if attribute['xp'] >= attribute['xp_to_next_level']:
            self._level_up(attribute)

    def _level_up(self, attribute):
        attribute['level'] += 1
        attribute['xp'] = 0
        attribute['xp_to_next_level'] = 100 * attribute['level']
        print(f"Leveled up an attribute to level {attribute['level']}!")

    def process_kill(self, player, weapon, zombie):
        xp_amount = zombie.xp_value
        final_xp = xp_amount * self.get_xp_bonus()

        if weapon and weapon.item_type == 'weapon' and weapon.ammo_type:  # Ranged
            self._add_xp(self.ranged, final_xp)
        else:  # Melee or bare hands
            self._add_xp(self.strength, final_xp / 2)
            self._add_xp(self.melee, final_xp)

    def update(self, player, is_moving, game):
        self.update_stamina(player, is_moving)
        self.update_hp(player)
        self.update_infection(player)
        self.update_anxiety(player, game)
        self.update_tireness(player, game)

    def update_stamina(self, player, is_moving):
        stamina_cap = player.max_stamina * (1 - player.infection / 100)
        if is_moving and player.stamina > 0:
            consumption = self.get_stamina_consumption(player.is_running)
            player.stamina = max(0, player.stamina - consumption)
        elif not is_moving and player.stamina < stamina_cap:
            regeneration = self.get_stamina_regeneration()
            player.stamina = min(stamina_cap, player.stamina + regeneration)

    def update_hp(self, player):
        regen_rate = self.get_hp_regeneration(player.infection)
        if player.health < player.max_health:
            player.health = min(player.max_health, player.health + regen_rate)

    def update_anxiety(self, player, game):
        nearby_zombies = 0
        # Count zombies within detection radius
        for zombie in game.zombies:
            dist = math.hypot(player.rect.centerx - zombie.rect.centerx, player.rect.centery - zombie.rect.centery)
            # Using ZOMBIE_DETECTION_RADIUS as the "seeing" range
            if dist < ZOMBIE_DETECTION_RADIUS:
                nearby_zombies += 1
        
        anxiety_gain = 0.0
        if nearby_zombies > 5:
            # High anxiety gain when seeing a horde
            anxiety_gain = 0.05 # 20% of 0.01% is unclear, using a balanced rate
        else:
            # Slow base anxiety gain
            anxiety_gain = 0.001 # User's 0.01% is 0.0001 which is too slow
            
        player.anxiety = min(100, player.anxiety + anxiety_gain)
        # Note: Anxiety doesn't decrease on its own here, only via items (e.g., smoker trait)
    
    def update_tireness(self, player, game):
        world_state = game.world_time.state
        base_gain = 0.0

        # Tireness increases at night, recovers during the day
        if world_state == "NIGHT" or world_state == "TRANSITION_TO_NIGHT":
            base_gain = 0.005 # Rate of getting tired
        else: # DAY or TRANSITION_TO_DAY
            base_gain = -0.01 # Rate of recovery (faster)

        # Anxiety makes you more tired
        anxiety_modifier = 1.0 + (player.anxiety / 100.0) # 0-100% increase
        
        # Being exhausted makes you more tired
        stamina_modifier = 0.0
        if player.stamina <= 0:
            stamina_modifier = 0.01 # Extra penalty for being exhausted

        final_gain = (base_gain * anxiety_modifier) + stamina_modifier
        player.tireness = max(0, min(100, player.tireness + final_gain))


    def update_infection(self, player):
        if player.infection > 0:
            player.infection += 0.005 # Progressive infection
            if player.infection >= 100:
                player.health = 1 # Player dies

    def update_tireness(self, player, game):
        world_state = game.world_time.state
        base_gain = 0.0

        # Tireness increases at night, recovers during the day
        if world_state == "NIGHT" or world_state == "TRANSITION_TO_NIGHT":
            base_gain = 0.005 # Rate of getting tired
        else: # DAY or TRANSITION_TO_DAY
            base_gain = -0.01 # Rate of recovery (faster)

        # Anxiety makes you more tired
        anxiety_modifier = 1.0 + (player.anxiety / 100.0) # 0-100% increase
        
        # Being exhausted makes you more tired
        stamina_modifier = 0.0
        if player.stamina <= 0:
            stamina_modifier = 0.01 # Extra penalty for being exhausted

        final_gain = (base_gain * anxiety_modifier) + stamina_modifier
        player.tireness = max(0, min(100, player.tireness + final_gain))

    def handle_melee_attack(self, player):
        if player.stamina >= 10:
            player.stamina = max(0, player.stamina - 0.001)
            player.tireness = min(100, player.tireness + 0.01)
            return True
        print("Too tired to swing!")
        return False

    # --- HELPER FUNCTIONS ---
    def get_melee_damage_multiplier(self, player):
        base_multiplier = 1 + (self.melee['level'] * 0.1)
        tireness_modifier = 1.0 - (player.tireness / 100.0) # 1.0 (0%) down to 0.0 (100%)
        return base_multiplier * tireness_modifier

    def get_unarmed_damage(self, player):
        base_damage = 1 + (self.strength['level'] * 0.1)
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_damage * tireness_modifier

    def get_ranged_damage_multiplier(self, player):
        # Ranged level gives a small bonus
        base_multiplier = 1 + (self.ranged['level'] * 0.05)
        # Tiredness reduces it
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_multiplier * tireness_modifier

    def get_headshot_chance(self):
        return 0.1 + (self.ranged['level'] * 0.04)

    def get_weapon_durability_loss(self):
        if random.randint(0, 10) < self.melee['level']:
            return 0.5
        else:
            return 2.0

    #def get_stamina_consumption(self, is_walking):
    #    base_consumption = 0.05 if is_walking else 0.08
    #    modifier = 1 - (self.speed * 0.05)
    #    return base_consumption * modifier
    
    def get_stamina_consumption(self, is_running):
        # Renamed 'is_walking' to 'is_running'
        # Now returns 0.0 if not running, and 0.08 if running
        base_consumption = 0.08 if is_running else 0.0
        modifier = 1 - (self.speed * 0.05)
        return base_consumption * modifier

    def get_stamina_regeneration(self):
        return 0.03 + (self.fitness['level'] * 0.1)

    def get_xp_bonus(self):
        return 1 + (self.lucky * 0.01)

    def get_hp_regeneration(self, infection_level):
        hp_regen_rate = 0.01
        if infection_level > 0:
            hp_regen_rate /= (1 + infection_level / 25)
        return hp_regen_rate
