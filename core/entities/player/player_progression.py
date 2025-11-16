import random
import math
from data.config import *
from core.ui.helpers import TRAIT_DEFINITIONS

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


    def get_total_attribute_bonus(self, player, attr_name):
        """Calculates the total percentage bonus from 'skill' items in player's inventory."""
        total_bonus = 0.0
        
        # Check main inventory
        for item in player.inventory:
            if item and item.item_type == 'skill' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        # Check belt
        for item in player.belt:
            if item and item.item_type == 'skill' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        for trait in player.traits:
            if trait in TRAIT_DEFINITIONS:
                # Check BOTH 'attributes' (for skills) and 'stats' (for core stats)
                if attr_name in TRAIT_DEFINITIONS[trait].get('attributes', {}):
                    total_bonus += TRAIT_DEFINITIONS[trait]['attributes'][attr_name]
                if attr_name in TRAIT_DEFINITIONS[trait].get('stats', {}):
                    total_bonus += TRAIT_DEFINITIONS[trait]['stats'][attr_name]

        return total_bonus



    def get_item_attribute_bonus(self, player, attr_name):
        """
        Calculates the total percentage bonus from 'skill' items ONLY.
        This is used for display on the Record tab.
        """
        total_bonus = 0.0
        
        # Check main inventory
        for item in player.inventory:
            if item and item.item_type == 'skill' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        # Check belt
        for item in player.belt:
            if item and item.item_type == 'skill' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        return total_bonus


    def get_strength(self, player):
        return self.strength['level']

    def get_fitness(self, player):
        return self.fitness['level']

    def get_melee(self, player):
        return self.melee['level']

    def get_ranged(self, player):
        return self.ranged['level']

    def get_lucky(self, player):
        base = self.lucky
        bonus_perc = self.get_total_attribute_bonus(player, 'lucky')
        return base * (1 + (bonus_perc / 100.0))
    
    def get_speed(self, player):
        base = self.speed
        bonus_perc = self.get_total_attribute_bonus(player, 'speed')
        return base * (1 + (bonus_perc / 100.0))

    def get_stamina_bonus(self, player):
        """Gets bonus from 'stamina' traits (e.g., athletic)."""
        return self.get_total_attribute_bonus(player, 'stamina')

    def get_anxiety_bonus(self, player):
        """Gets bonus from 'anxiety' traits (e.g., smoker)."""
        return self.get_total_attribute_bonus(player, 'anxiety')

    def get_infection_bonus(self, player):
        """Gets bonus from 'infection' traits (e.g., vaccine)."""
        return self.get_total_attribute_bonus(player, 'infection')

    def get_health_bonus(self, player):
        """Gets bonus from 'health' traits."""
        return self.get_total_attribute_bonus(player, 'health')
        
    def get_tireness_bonus(self, player):
        """Gets bonus from 'tireness' traits."""
        return self.get_total_attribute_bonus(player, 'tireness')
        
    def get_food_bonus(self, player):
        """Gets bonus from 'food' traits (e.g., slower metabolism)."""
        return self.get_total_attribute_bonus(player, 'food')
        
    def get_water_bonus(self, player):
        """Gets bonus from 'water' traits (e.g., slower metabolism)."""
        return self.get_total_attribute_bonus(player, 'water')



    def _get_xp_for_next_level(self, current_level):
        """Calculates the XP needed to reach the next level."""
        return 100 * (current_level + 1)

    def _create_attribute(self, player_data, attr_name):
        base_level_from_traits = player_data['attributes'].get(attr_name, 0.0)
        start_level = max(0.0, base_level_from_traits)
        return {
            "level": start_level,
            "xp": 0,
            "xp_to_next_level": self._get_xp_for_next_level(start_level) # Use the formula
        }

    def _add_xp(self, player, attribute, attr_name, base_amount):
        """Adds XP to an attribute, modified by the attribute's level and bonuses."""
        
        # 1. Get the skill modifier (e.g., -10% or +5%)
        #    We use get_total_attribute_bonus here, NOT get_melee(), 
        #    because the level itself shouldn't affect XP gain.
        skill_bonus_perc = self.get_total_attribute_bonus(player, attr_name)
        
        # 2. Calculate the modifier (e.g., 1.0 + (-10 / 100.0) = 0.9)
        xp_modifier = 1.0 + (skill_bonus_perc / 100.0)

        # 3. Calculate final XP, ensuring it's never negative
        final_xp_gain = max(0, base_amount * xp_modifier)

        attribute['xp'] += final_xp_gain
        print(f"Gained {final_xp_gain:.2f} XP for {attr_name}.")
        
        # 4. Check for level up
        #    We calculate a modified XP-to-next-level to apply the penalty/bonus
        
        # This is the base amount needed (e.g., 100)
        attribute['xp_to_next_level'] = self._get_xp_for_next_level(attribute['level']) 

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
        base_xp = xp_amount * self.get_xp_bonus(player)

        if weapon and weapon.item_type == 'weapon_ranged' and weapon.ammo_type:  # Ranged
            self._add_xp(player, self.ranged, 'ranged', base_xp)
            
        else:  # Melee or bare hands
            self._add_xp(player, self.melee, 'melee', base_xp)
            self._add_xp(player, self.strength, 'strength', base_xp * 0.5)

    def update(self, player, is_moving, game):
        self.update_stamina(player, is_moving)
        self.update_hp(player)
        self.update_infection(player)
        self.update_anxiety(player, game)
        self.update_tireness(player, game)

    def update_stamina(self, player, is_moving):
        stamina_cap = player.max_stamina * (1 - player.infection / 100)
        if is_moving and player.stamina > 0:
            consumption = self.get_stamina_consumption(player.is_running, player)
            player.stamina = max(0, player.stamina - consumption)
        elif not is_moving and player.stamina < stamina_cap:
            regeneration = self.get_stamina_regeneration(player)
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
            

        anxiety_bonus_perc = self.get_anxiety_bonus(player) # e.g., +15%
        anxiety_modifier = 1.0 + (anxiety_bonus_perc / 100.0) # e.g., 1.15
        
        final_anxiety_gain = anxiety_gain * anxiety_modifier
        
        player.anxiety = min(100, player.anxiety + final_anxiety_gain)
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
        tireness_bonus_perc = self.get_tireness_bonus(player)
        tireness_modifier = 1.0 + (tireness_bonus_perc / 100.0)

        # Apply modifier to both base gain/recovery and stamina penalty
        final_gain_modified = final_gain * tireness_modifier
        
        player.tireness = max(0, min(100, player.tireness + final_gain_modified))


    def update_infection(self, player):
        if player.infection > 0:
            player.infection += 0.0005

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
        base_multiplier = 1 + (self.get_melee(player) / 100.0)
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_multiplier * tireness_modifier

    def get_unarmed_damage(self, player):
        base_damage = 1 + (self.get_strength(player) / 100.0)
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_damage * tireness_modifier

    def get_ranged_damage_multiplier(self, player):
        # Ranged level gives a small bonus
        base_multiplier = 1 + (self.get_ranged(player) / 100.0)
        # Tiredness reduces it
        tireness_modifier = 1.0 - (player.tireness / 100.0)
        return base_multiplier * tireness_modifier

    def get_headshot_chance(self, player):
        return 0.1 + (self.get_ranged(player) * 0.004)

    def get_weapon_durability_loss(self, player):
        if random.randint(0, 10) < (self.get_melee(player) / 100.0):
            return 0.5
        else:
            return 2.0
    
    def get_stamina_consumption(self, is_running, player):
        base_consumption = 0.08 if is_running else 0.0
        modifier = 1 - (self.get_speed(player) / 100.0)
        return base_consumption * modifier

    def get_stamina_regeneration(self, player):
        base_regen = 0.03 + (self.get_fitness(player) / 100.0)
        stamina_bonus_perc = self.get_stamina_bonus(player) # e.g., +10%
        regen_modifier = 1.0 + (stamina_bonus_perc / 100.0) # e.g., 1.1
        # A negative bonus (e.g., -15%) will make this 0.85
        return max(0, base_regen * regen_modifier)

    def get_xp_bonus(self, player):
        return 1 + (self.get_lucky(player) * 0.01)

    def get_hp_regeneration(self, infection_level):
        hp_regen_rate = 0.01
        if infection_level > 0:
            hp_regen_rate /= (1 + infection_level / 25)
        
        
        return hp_regen_rate