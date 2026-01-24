import random
import math
from core.data.config import *
import core.data.config
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.messages import display_message_player

class PlayerProgression:
    def __init__(self, player_data):
        # Attributes with XP and level
        self.strength = self._create_attribute(player_data, 'strength')
        self.fitness = self._create_attribute(player_data, 'fitness')
        self.melee = self._create_attribute(player_data, 'melee')
        self.ranged = self._create_attribute(player_data, 'ranged')
        self.maintenance = self._create_attribute(player_data, 'maintenance')
        self.speed = self._create_attribute(player_data, 'speed')
        self.lucky = self._create_attribute(player_data, 'luck')
        
        
    def get_total_attribute_bonus(self, player, attr_name):
        """Calculates the total percentage bonus from 'charm' items in player's inventory."""
        total_bonus = 0.0
        
        # Check main inventory
        for item in player.inventory:
            if item and item.item_type == 'charm' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        # Check belt
        for item in player.belt:
            if item and item.item_type == 'charm' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        for trait in player.traits:
            if trait in TRAIT_DEFINITIONS:
                # Check BOTH 'attributes' (for charm) and 'stats' (for core stats)
                if attr_name in TRAIT_DEFINITIONS[trait].get('attributes', {}):
                    total_bonus += TRAIT_DEFINITIONS[trait]['attributes'][attr_name]
                if attr_name in TRAIT_DEFINITIONS[trait].get('stats', {}):
                    total_bonus += TRAIT_DEFINITIONS[trait]['stats'][attr_name]

        return total_bonus



    def get_item_attribute_bonus(self, player, attr_name):
        """
        Calculates the total percentage bonus from 'charm' items ONLY.
        This is used for display on the Record tab.
        """
        total_bonus = 0.0
        
        # Check main inventory
        for item in player.inventory:
            if item and item.item_type == 'charm' and item.attribute_modifiers:
                total_bonus += item.attribute_modifiers.get(attr_name, 0.0)
        
        # Check belt
        for item in player.belt:
            if item and item.item_type == 'charm' and item.attribute_modifiers:
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

    def get_maintenance(self, player):
        return self.maintenance['level']

    def get_lucky(self, player):
        base = self.lucky['level']
        bonus_perc = self.get_total_attribute_bonus(player, 'lucky')
        return base * (1 + (bonus_perc / 100.0))
    
    def get_speed(self, player):
        # [MODIFIED] Use 'level' from the speed attribute dict
        base = self.speed['level']
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


    def _get_xp_for_next_level(self, current_level, attr_name=None):
        if current_level >= 100: return 999999 # Cap at level 100

        # Default base
        base_xp = 100

        # Specific XP requirements for Level 1 (scaling from there)
        if attr_name in ['strength', 'fitness', 'lucky']:
            base_xp = 1000
        elif attr_name == 'ranged':
            base_xp = 200
        elif attr_name == 'maintenance':
            base_xp = 100
        elif attr_name == 'melee':
            base_xp = 100
        elif attr_name == 'speed':
            base_xp = 500
            
        # Linear scaling: Level 0->1 = Base. Level 1->2 = Base * 2.
        return base_xp * (current_level + 1)

    def _create_attribute(self, player_data, attr_name):
        

        # [FIX] Handle both loading (dict) and new creation (float/int)
        raw_value = player_data['attributes'].get(attr_name, 0.0)
        
        # If it's already a dictionary (from a save file), return it directly
        if isinstance(raw_value, dict):
            # Ensure xp_to_next_level exists (backward compatibility fix)
            if 'xp_to_next_level' not in raw_value:
                 current_lvl = raw_value.get('level', 0)
                 raw_value['xp_to_next_level'] = self._get_xp_for_next_level(current_lvl, attr_name)
            return raw_value

        # Otherwise, treat it as a base level (float/int) for new initialization
        base_level_from_traits = raw_value
        start_level = max(0.0, int(base_level_from_traits))
        
        return {
            "name": attr_name,
            "level": start_level,
            "xp": 0,
            "xp_to_next_level": self._get_xp_for_next_level(start_level, attr_name)
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
        display_message_player(f"Gained {final_xp_gain:.2f} XP for {attr_name}.") 
        
        # 4. Check for level up
        #    We calculate a modified XP-to-next-level to apply the penalty/bonus
        
        # This is the base amount needed (e.g., 100)
        attribute['xp_to_next_level'] = self._get_xp_for_next_level(attribute['level'], attribute.get('name'))

        if attribute['xp'] >= attribute['xp_to_next_level']:
            self._level_up(attribute)

    def _level_up(self, attribute):
        attribute['level'] += 1
        attribute['xp'] = 0
        attribute['xp_to_next_level'] = self._get_xp_for_next_level(attribute['level'], attribute.get('name')) # Use the formula
        display_message_player(f"Leveled up {attribute.get('name', 'attribute')} to level {attribute['level']}!")

    # [NEW] Public method to add speed XP
    def add_speed_xp(self, player, amount):
        self._add_xp(player, self.speed, 'speed', amount)

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
        self.update_tireness(player, game, is_moving)

        # Earn Fitness XP when running
        if is_moving and player.is_running:
            self._add_xp(player, self.fitness, 'fitness', 0.02)

    def update_stamina(self, player, is_moving):
        stamina_cap = player.max_stamina * (1 - player.infection / 100)
        if is_moving and player.stamina > 0:
            consumption = self.get_stamina_consumption(player.is_running, player)
            player.stamina = max(0, player.stamina - consumption)
        elif not is_moving and player.stamina < stamina_cap:
            regeneration = self.get_stamina_regeneration(player)
            player.stamina = min(stamina_cap, player.stamina + regeneration)

    def update_hp(self, player):
        health_cap = player.max_health * (1 - player.infection / 100)
        
        # Clamp current health if it exceeds the new cap
        if player.health > health_cap:
            player.health = health_cap

        regen_rate = self.get_hp_regeneration(player.infection)
        if player.health < health_cap:
            player.health = min(health_cap, player.health + regen_rate)

    def update_anxiety(self, player, game):
        nearby_zombies = 0
        # Count zombies within detection radius
        for zombie in game.zombies:
            dist = math.hypot(player.rect.centerx - zombie.rect.centerx, player.rect.centery - zombie.rect.centery)
            # Using ZOMBIE_DETECTION_RADIUS as the "seeing" range
            if dist < core.data.config.ZOMBIE_DETECTION_RADIUS:
                nearby_zombies += 1
        
        anxiety_gain = 0.0
        if nearby_zombies > 2:
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
    
    def update_tireness(self, player, game, is_moving):
        world_state = game.world_time.state
        base_change = 0.0
        if world_state == "NIGHT" or world_state == "TRANSITION_TO_NIGHT":
            base_change = -0.03 # Rate of getting tired (negative)
        else: # DAY or TRANSITION_TO_DAY
            base_change = 0.002 # Rate of recovery (positive)

        # 2. Modifiers that *decrease* tireness (penalties)
        stamina_penalty = 0.0
        if player.stamina <= 0:
            stamina_penalty = -0.01 # Extra penalty for being exhausted
            
        running_penalty = 0.0
        if is_moving and player.is_running:
            running_penalty = -0.02 # Tireness drain from running

        # 3. Anxiety modifier
        # Anxiety makes you more tired (makes recovery slower, decay faster)
        anxiety_modifier = 1.0 + (player.anxiety / 100.0) # 1.0 (calm) to 2.0 (max anxiety)
        
        if base_change < 0: # If decaying (at night)
            base_change *= anxiety_modifier # Make decay faster
        else: # If recovering (during day)
            base_change /= anxiety_modifier # Make recovery slower
            
        # 4. Trait modifier
        # "rested" (+15) -> 1.15 multiplier
        # "sleepy" (-20) -> 0.80 multiplier
        tireness_bonus_perc = self.get_tireness_bonus(player) 
        tireness_modifier = 1.0 + (tireness_bonus_perc / 100.0) 

        if base_change < 0: # If decaying (at night)
            base_change /= tireness_modifier # Rested (1.15) makes decay slower
        else: # If recovering (during day)
            base_change *= tireness_modifier # Rested (1.15) makes recovery faster
        
        # 5. Combine all changes
        final_gain_modified = base_change + stamina_penalty + running_penalty
        
        player.tireness = max(0, min(player.max_tireness, player.tireness + final_gain_modified))


    def update_infection(self, player):
        if player.infection > 0:
            player.infection += 0.0005

            if player.infection >= 100:
                player.health = 1 # Player dies

    def handle_melee_attack(self, player):
        # Cost to swing (energy consumption)
        fatigue_cost = 0.5 
        
        # [CHANGED] Logic to allow swinging even when exhausted (tireness <= 0)
        # If player has energy (tireness > 0), we consume it.
        # If player has NO energy, we still allow the swing (Return True).
        # Since 'tireness' is low/zero, 'get_melee_damage_multiplier' will naturally 
        # reduce damage to near zero, but the attack event will fire, allowing knockback.
        
        if player.tireness > 0:
            player.tireness = max(0.0, player.tireness - fatigue_cost)
            
        return True

    # --- HELPER FUNCTIONS ---
    def get_melee_damage_multiplier(self, player):
        base_multiplier = 1 + (self.get_melee(player) / 100.0)
        tireness_modifier = player.tireness / player.max_tireness
        return base_multiplier * tireness_modifier

    def get_unarmed_damage(self, player):
        base_damage = 1 + (self.get_strength(player) / 100.0)
        tireness_modifier = player.tireness / player.max_tireness
        return base_damage * tireness_modifier

    def get_ranged_damage_multiplier(self, player):
        # Ranged level gives a small bonus
        base_multiplier = 1 + (self.get_ranged(player) / 100.0)
        # Tiredness reduces it
        tireness_modifier = player.tireness / player.max_tireness
        return base_multiplier * tireness_modifier

    def get_headshot_chance(self, player):
        return 0.1 + (self.get_ranged(player) * 0.004)

    def get_weapon_durability_loss(self, player):
        """Calculates melee durability loss, reduced by Maintenance."""
        # Maintenance Chance to save durability
        # Level 0 = 0%, Level 10 = 10%, Level 50 = 50%
        maintenance_lvl = self.get_maintenance(player)
        if random.randint(0, 100) < maintenance_lvl:
            return 0 # Saved by maintenance skill!

        if random.randint(0, 10) < (self.get_melee(player) / 100.0):
            return 0.5
        else:
            return 2.0
    
    def get_ranged_durability_loss(self, player):
        """Calculates ranged durability loss, reduced by Maintenance."""
        maintenance_lvl = self.get_maintenance(player)
        if random.randint(0, 100) < maintenance_lvl:
            return 0 # Saved by maintenance skill!
        return 0.5 # Standard loss per shot
    
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