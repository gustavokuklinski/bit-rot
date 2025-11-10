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

    def _get_xp_for_next_level(self, current_level):
        """Calculates the XP needed to reach the next level."""

        return 100 * (current_level + 1)

    def _create_attribute(self, player_data, attr_name):
        start_level = player_data['attributes'].get(attr_name, 0.0) # Get starting level (e.g., 0, or 2 from "strong")
        return {
            "level": start_level,
            "xp": 0,
            "xp_to_next_level": self._get_xp_for_next_level(start_level) # Use the formula
        }

    def _add_xp(self, attribute, amount):
        attribute['xp'] += amount
        print(f"Gained {amount} XP for an {attribute}.")
        if attribute['xp'] >= attribute['xp_to_next_level']:
            self._level_up(attribute)

    def _level_up(self, attribute):
        attribute['level'] += 1
        attribute['xp'] = 0
        attribute['xp_to_next_level'] = self._get_xp_for_next_level(attribute['level']) # Use the formula
        print(f"Leveled up an attribute to level {attribute['level']}!")

    def process_kill(self, player, weapon, zombie):
        xp_amount = zombie.xp_value
        
        # Base XP (includes lucky bonus)
        base_xp = xp_amount * self.get_xp_bonus() 

        if weapon and weapon.item_type == 'weapon' and weapon.ammo_type:  # Ranged
            # Apply ranged skill modifier (level is the percentage, e.g., -10 or +5)
            ranged_skill_percent = self.ranged['level']
            ranged_xp_modifier = 1.0 + (ranged_skill_percent / 100.0)
            final_ranged_xp = max(0, base_xp * ranged_xp_modifier) # Ensure XP isn't negative
            
            self._add_xp(self.ranged, final_ranged_xp)
            
        else:  # Melee or bare hands
            # Apply melee skill modifier
            melee_skill_percent = self.melee['level']
            melee_xp_modifier = 1.0 + (melee_skill_percent / 100.0)
            final_melee_xp = max(0, base_xp * melee_xp_modifier)
            
            # Apply strength skill modifier (for the strength XP portion)
            strength_skill_percent = self.strength['level']
            strength_xp_modifier = 1.0 + (strength_skill_percent / 100.0)
            final_strength_xp = max(0, (base_xp / 2) * strength_xp_modifier) # Strength gets half
            
            self._add_xp(self.strength, final_strength_xp)
            self._add_xp(self.melee, final_melee_xp)

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

    def handle_melee_attack(self, player):
        if player.stamina >= 10:
            player.stamina = max(0, player.stamina - 0.01)
            player.tireness = min(100, player.tireness + 0.01)
            return True
        print("Too tired to swing!")
        return False

    # --- HELPER FUNCTIONS ---
    def get_melee_damage_multiplier(self, player):
        base_multiplier = 1 + (self.melee['level'] / 100.0)
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_multiplier * tireness_modifier

    def get_unarmed_damage(self, player):
        base_damage = 1 + (self.strength['level'] / 100.0)
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_damage * tireness_modifier

    def get_ranged_damage_multiplier(self, player):
        # Ranged level gives a small bonus
        base_multiplier = 1 + (self.ranged['level'] / 100.0)
        # Tiredness reduces it
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_multiplier * tireness_modifier

    def get_headshot_chance(self):
        return 0.1 + (self.ranged['level'] * 0.04)

    def get_weapon_durability_loss(self):
        if random.randint(0, 10) < (self.melee['level'] / 100.0):
            return 0.5
        else:
            return 2.0
    
    def get_stamina_consumption(self, is_running):
        base_consumption = 0.08 if is_running else 0.0
        modifier = 1 - (self.speed / 100.0)
        return base_consumption * modifier

    def get_stamina_regeneration(self):
        return 0.03 + (self.fitness['level'] / 100.0)

    def get_xp_bonus(self):
        return 1 + (self.lucky * 0.01)

    def get_hp_regeneration(self, infection_level):
        hp_regen_rate = 0.01
        if infection_level > 0:
            hp_regen_rate /= (1 + infection_level / 25)
        return hp_regen_rate