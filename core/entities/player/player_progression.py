import random

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

    def update(self, player, is_moving):
        self.update_stamina(player, is_moving)
        self.update_hp(player)
        self.update_infection(player)

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

    def update_infection(self, player):
        if player.infection > 0:
            player.infection += 0.005 # Progressive infection
            if player.infection >= 100:
                player.health = 1 # Player dies

    def handle_melee_attack(self, player):
        if player.stamina >= 10:
            player.stamina -= 5
            return True
        print("Too tired to swing!")
        return False

    # --- HELPER FUNCTIONS ---

    def get_melee_damage_multiplier(self):
        return 1 + (self.melee['level'] * 0.1)

    def get_unarmed_damage(self):
        return 1 + (self.strength['level'] * 0.1)

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
