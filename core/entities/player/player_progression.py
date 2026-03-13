import random
import math
import core.data.config
from core.data.config import *
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.messages import display_message
# Import the new loader
from core.data.progression_loader import PROGRESSION_CONFIG

class PlayerProgression:
    def __init__(self, player_data):
        self.config = PROGRESSION_CONFIG
        self.attributes = {}
        # Store traits locally for initialization of XP reqs
        self.initial_traits = player_data.get('traits', [])

        # 1. Dynamic Initialization
        # Instead of hardcoding self.strength, self.fitness, etc.,
        # we iterate through the loaded XML configuration.
        for attr_id in self.config.attributes.keys():
            self.attributes[attr_id] = self._create_attribute(player_data, attr_id)

    # --- GENERIC GETTERS ---

    def get_level(self, attr_id):
        """Returns the level of a specific attribute (e.g. 'strength')."""
        return self.attributes.get(attr_id, {}).get('level', 0)

    def get_derived_bonus(self, target_effect):
        """
        Calculates the total passive bonus for a specific effect from ALL attributes.
        Example: get_derived_bonus('melee_damage') sums up bonuses from Strength, Melee, etc.
        """
        total_mult = 0.0
        total_flat = 0.0

        for attr_id, attr_data in self.attributes.items():
            effect = self.config.get_attr_effect(attr_id, target_effect)
            if effect:
                lvl = attr_data['level']
                val = effect['value']
                
                if effect['type'] == 'multiplier_add':
                    total_mult += (lvl * val)
                elif effect['type'] == 'flat':
                    total_flat += (lvl * val)

        return total_mult, total_flat

    # --- COMPATIBILITY GETTERS (Wrappers) ---
    
    def get_strength(self, player): return self.get_level('strength')
    def get_fitness(self, player): return self.get_level('fitness')
    def get_melee(self, player): return self.get_level('melee')
    def get_ranged(self, player): return self.get_level('ranged')
    def get_maintenance(self, player): return self.get_level('maintenance')
    
    def get_lucky(self, player):
        # Base Luck + Trait Bonus
        base = self.get_level('lucky')
        bonus_perc = self.get_total_attribute_bonus(player, 'lucky')
        return base * (1 + (bonus_perc / 100.0))

    def get_agility(self, player):
        base = self.get_level('agility')
        bonus_perc = self.get_total_attribute_bonus(player, 'agility')
        return base * (1 + (bonus_perc / 100.0))
        
    def get_intelligence(self, player):
        base = self.get_level('intelligence')
        bonus_perc = self.get_total_attribute_bonus(player, 'intelligence')
        return base * (1 + (bonus_perc / 100.0))

    # --- BONUS CALCULATORS (Traits & Items) ---

    def get_total_attribute_bonus(self, player, attr_name):
        """Calculates percentage bonus from Traits and Charms (Inventory)."""
        total_bonus = 0.0
        
        # Helper to check an item
        def check_item(item):
            if item and item.item_type == 'charm' and item.attribute_modifiers:
                return item.attribute_modifiers.get(attr_name, 0.0)
            return 0.0

        for item in player.inventory: total_bonus += check_item(item)
        for item in player.belt: total_bonus += check_item(item)
        
        # Traits
        for trait in player.traits:
            t_def = TRAIT_DEFINITIONS.get(trait)
            if t_def:
                total_bonus += t_def.get('attributes', {}).get(attr_name, 0.0)
                total_bonus += t_def.get('stats', {}).get(attr_name, 0.0)

        return total_bonus

    # Convenience wrappers for traits
    def get_stamina_bonus(self, player): return self.get_total_attribute_bonus(player, 'stamina')
    def get_anxiety_bonus(self, player): return self.get_total_attribute_bonus(player, 'anxiety')
    def get_infection_bonus(self, player): return self.get_total_attribute_bonus(player, 'infection')
    def get_health_bonus(self, player): return self.get_total_attribute_bonus(player, 'health')
    def get_tireness_bonus(self, player): return self.get_total_attribute_bonus(player, 'tireness')
    def get_food_bonus(self, player): return self.get_total_attribute_bonus(player, 'food')
    def get_water_bonus(self, player): return self.get_total_attribute_bonus(player, 'water')

    # --- XP & LEVELING ---

    def _create_attribute(self, player_data, attr_id):
        raw = player_data.get('attributes', {}).get(attr_id, 0.0)
        
        if isinstance(raw, dict):
            level = raw.get('level', 0)
            xp = raw.get('xp', 0)
        else:
            level = int(raw)
            xp = 0

        # Calculate XP req based on XML config and Initial Traits
        xp_req = self._calc_xp_req(attr_id, level, traits=self.initial_traits)
        
        return {
            "name": attr_id,
            "level": level,
            "xp": xp,
            "xp_to_next_level": xp_req
        }

    def _calc_xp_req(self, attr_id, current_level, player=None, traits=None):
        if current_level >= 10: return 999999
        
        attr_def = self.config.attributes.get(attr_id)
        base_xp = attr_def['base_xp'] if attr_def else 100
        
        base_req = base_xp * (current_level + 1)

        # Calculate Modifier (Percentage)
        bonus_perc = 0.0
        
        if player:
            bonus_perc = self.get_total_attribute_bonus(player, attr_id)
        elif traits:
             # Fallback for initialization when 'player' object doesn't exist yet
             for trait in traits:
                t_def = TRAIT_DEFINITIONS.get(trait)
                if t_def:
                     bonus_perc += t_def.get('attributes', {}).get(attr_id, 0.0)
                     bonus_perc += t_def.get('stats', {}).get(attr_id, 0.0)

        # Apply User's Logic:
        # Positive Bonus (e.g. +20%) -> Needs Less XP (Multiplier < 1.0)
        # Negative Bonus (e.g. -20%) -> Needs More XP (Multiplier > 1.0)
        
        modifier = 1.0 - (bonus_perc / 100.0)
        
        # Safety clamp to prevent 0 or negative requirement
        modifier = max(0.1, modifier)
        
        return base_req * modifier

    def add_xp(self, player, attr_id, amount):
        if attr_id not in self.attributes: return
        
        attr = self.attributes[attr_id]
        
        # Prevent gaining XP if already at max level (10)
        if attr['level'] >= 10:
            return

        # [MODIFIED] Calculate Global XP Gain Multiplier (Intelligence, Luck, etc.)
        # XML target: 'xp_gain' (multiplier_add)
        mult_bonus, _ = self.get_derived_bonus('xp_gain')
        
        # Base multiplier is 1.0. 
        # Example: Intelligence 5 (value 0.01) -> +0.05 bonus -> 1.05x multiplier
        final_multiplier = 1.0 + mult_bonus
        
        # Apply the multiplier to the incoming amount
        final_gain = max(0, amount * final_multiplier)

        attr['xp'] += final_gain
        
        # 2. Level Up Check
        if attr['xp'] >= attr['xp_to_next_level']:
            self._level_up(player, attr)

    def _level_up(self, player, attr):
        attr['level'] += 1
        attr['xp'] = 0
        # Pass player to recalculate dynamic requirements
        attr['xp_to_next_level'] = self._calc_xp_req(attr['name'], attr['level'], player=player)
        
        # Get nice name for display
        display_name = self.config.attributes.get(attr['name'], {}).get('name', attr['name'])
        display_message(f"Leveled up {display_name} to level {attr['level']}!")

    def add_agility_xp(self, player, amount):
        self.add_xp(player, 'agility', amount)

    def process_kill(self, player, weapon, zombie):
        # XP Calculation
        xp_val = zombie.xp_value
        lucky_mod = 1 + (self.get_lucky(player) * 0.01)
        base_xp = xp_val * lucky_mod

        if weapon and getattr(weapon, 'item_type', '') == 'weapon_ranged' and getattr(weapon, 'ammo_type', None):
            self.add_xp(player, 'ranged', base_xp)
        else:
            self.add_xp(player, 'melee', base_xp)
            self.add_xp(player, 'strength', base_xp * 0.5)

    # --- UPDATE LOOPS (Data Driven) ---

    def update(self, player, is_moving, game):
        self.update_stamina(player, is_moving)
        self.update_infection(player)
        self.update_anxiety(player, game)
        self.update_tireness(player, game, is_moving)

        if player.tireness <= 0 and not player.is_sleeping:
            player.is_sleeping = True
            player.vx = 0
            player.vy = 0
            display_message("You passed out from exhaustion!")

        if is_moving and player.is_running and player.stamina > 0:
            self.add_xp(player, 'fitness', 0.002)

    def update_stamina(self, player, is_moving):
        stamina_cap = player.max_stamina * (1 - player.infection / 100)
        
        if is_moving and player.stamina > 0:
            consumption = self.get_stamina_consumption(player.is_running, player)
            player.stamina = max(0, player.stamina - consumption)
        elif not is_moving and player.stamina < stamina_cap:
            regeneration = self.get_stamina_regeneration(player)
            player.stamina = min(stamina_cap, player.stamina + regeneration)


    def update_anxiety(self, player, game):
        # 1. Calculate Zombies nearby
        nearby_zombies = 0
        det_radius = core.data.config.ZOMBIE_DETECTION_RADIUS
        det_radius_sq = det_radius ** 2
        for zombie in game.zombies:
            dx = player.rect.centerx - zombie.rect.centerx
            dy = player.rect.centery - zombie.rect.centery
            dist_sq = dx*dx + dy*dy
            if dist_sq < det_radius_sq:
                nearby_zombies += 1
        
        # 2. Get XML Constants
        horde_gain = self.config.get_stat('anxiety', 'horde_gain', 0.05)
        passive_gain = self.config.get_stat('anxiety', 'passive_gain', 0.001)

        base = horde_gain if nearby_zombies > 2 else passive_gain
        
        # 3. Apply Trait Modifiers
        bonus_perc = self.get_anxiety_bonus(player)
        final = base * (1.0 + (bonus_perc / 100.0))
        
        player.anxiety = min(100, player.anxiety + final)

    def update_tireness(self, player, game, is_moving):
        # 1. Get XML Constants
        night_decay = self.config.get_stat('tireness', 'night_decay', -0.03)
        day_recov = self.config.get_stat('tireness', 'day_recovery', 0.002)
        
        # 2. Determine Base Change (Day/Night)
        world_state = game.world_time.state
        base_change = night_decay if "NIGHT" in world_state else day_recov

        # 3. Penalties (from XML)
        stam_penalty = self.config.get_stat('tireness', 'stamina_penalty', -0.01)
        run_penalty = self.config.get_stat('tireness', 'run_penalty', -0.02)
        
        current_penalty = 0.0
        if player.stamina <= 0: current_penalty += stam_penalty
        if is_moving and player.is_running: current_penalty += run_penalty

        # 4. Anxiety Modifier (Higher anxiety = faster tireness/slower recovery)
        anxiety_mod = 1.0 + (player.anxiety / 100.0)
        
        if base_change < 0: base_change *= anxiety_mod
        else: base_change /= anxiety_mod

        # 5. Trait Modifiers (Rested/Sleepy)
        trait_perc = self.get_tireness_bonus(player)
        trait_mod = 1.0 + (trait_perc / 100.0)

        if base_change < 0: base_change /= trait_mod # Rested slows decay
        else: base_change *= trait_mod               # Rested speeds recovery

        final_change = base_change + current_penalty
        player.tireness = max(0, min(player.max_tireness, player.tireness + final_change))

    def update_infection(self, player):
        if player.infection > 0:
            cap = self.config.get_stat('infection', 'death_threshold', 100.0)
            
            if player.infection >= cap:
                player.health = 1

    # --- COMBAT & ACTIONS (Calculated via Attributes) ---

    def handle_melee_attack(self, player):
        stamina_cost = self.config.get_stat('stamina', 'melee_cost', 0.02)
        tireness_cost = self.config.get_stat('tireness', 'melee_cost', 0.02)
        
        # Consume stamina
        if player.stamina > 0:
            player.stamina = max(0.0, player.stamina - stamina_cost)
            
        # Consume tiredness
        if player.tireness > 0:
            player.tireness = max(0.0, player.tireness - tireness_cost)
            
        return True

    def get_melee_damage_multiplier(self, player):
        # Now: Base 1.0 + (Sum of all attribute effects targeting 'melee_damage')
        mult_bonus, flat_bonus = self.get_derived_bonus('melee_damage')
        
        base_multiplier = 1.0 + mult_bonus
        
        tireness_mod = player.tireness / player.max_tireness
        return (base_multiplier * tireness_mod) + flat_bonus

    def get_unarmed_damage(self, player):
        mult_bonus, flat_bonus = self.get_derived_bonus('unarmed_damage')
        
        base_damage = 1.0 + mult_bonus
        tireness_mod = player.tireness / player.max_tireness
        return (base_damage * tireness_mod) + flat_bonus

    def get_ranged_damage_multiplier(self, player):
        mult_bonus, flat_bonus = self.get_derived_bonus('ranged_damage')
        
        base_multiplier = 1.0 + mult_bonus
        tireness_mod = player.tireness / player.max_tireness
        return base_multiplier * tireness_mod

    def get_headshot_chance(self, player):
        mult_bonus, flat_bonus = self.get_derived_bonus('headshot_chance')
        base_chance = 0.1 
        return base_chance + flat_bonus

    def get_stamina_consumption(self, is_running, player):
        base_run_cost = self.config.get_stat('stamina', 'run_cost_base', 0.08)
        base = base_run_cost if is_running else 0.0
        
        # Look for attributes that reduce consumption (e.g. Speed/Agility)
        mult_red, flat_red = self.get_derived_bonus('stamina_consumption_reduction')
        
        # If speed level 5 gives 0.05 reduction: 1 - 0.05 = 0.95 multiplier
        modifier = max(0.1, 1.0 - flat_red) 

        # --- Overweight Penalty ---
        if hasattr(player, 'max_carry_weight') and player.max_carry_weight > 0:
            weight_ratio = player.current_weight / player.max_carry_weight
            if weight_ratio > 1.0:
                base *= weight_ratio
        
        return base * modifier

    def get_stamina_regeneration(self, player):
        # Base from XML
        base_regen = self.config.get_stat('stamina', 'regen_base', 0.03)
        
        # Attribute Bonuses (Fitness)
        mult, flat = self.get_derived_bonus('stamina_regen')
        
        # Trait Bonuses (Athletic)
        trait_perc = self.get_stamina_bonus(player)
        trait_mod = 1.0 + (trait_perc / 100.0)
        
        return max(0, (base_regen + flat) * trait_mod)

    def get_weapon_durability_loss(self, player):
        # XML Effect target: 'durability_save_chance'
        # e.g., Maintenance gives 1.0 (1%) per level
        # e.g., Intelligence gives 0.5 (0.5%) per level
        _, save_chance = self.get_derived_bonus('durability_save_chance')
        
        if random.uniform(0, 100) < save_chance:
            return 0 # Saved

        # Keep hardcoded minor check for Strength/Melee or move to XML?
        # Keeping logic close to original for now but using generic getter
        _, minor_save = self.get_derived_bonus('durability_save_chance_minor')
        if random.uniform(0, 100) < minor_save:
             return 0.5
        return 1.0

    def get_ranged_durability_loss(self, player):
        _, save_chance = self.get_derived_bonus('durability_save_chance')
        if random.uniform(0, 100) < save_chance:
            return 0
        return 0.5