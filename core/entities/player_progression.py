import random

class PlayerProgression:
    def __init__(self, player_data):
        self.level = player_data['stats'].get('level', 1)
        self.experience = player_data['stats'].get('experience', 0)
        self.xp_to_next_level = 100 * self.level

        self.strength = player_data['attributes'].get('strength', 0.0)
        self.fitness = player_data['attributes'].get('fitness', 0.0)
        self.melee = player_data['attributes'].get('melee', 0.0)
        self.ranged = player_data['attributes'].get('ranged', 0.0)
        self.lucky = player_data['attributes'].get('lucky', 0.0)
        self.speed = player_data['attributes'].get('speed', 0.0)

    def add_xp(self, amount, player):
        self.experience += amount
        print(f"Gained {amount} XP.")
        if self.experience >= self.xp_to_next_level:
            self.level_up(player)

    def level_up(self, player):
        self.level += 1
        self.experience = 0
        self.xp_to_next_level = 100 * self.level
        player.max_health += 0.1
        player.health = player.max_health
        self.speed += 0.1
        self.lucky += 0.1
        self.fitness += 0.001
        print(f"Leveled up to level {self.level}!")

    def process_kill(self, player, weapon):
        lucky_bonus = 1 + (self.lucky * 0.01)
        if weapon and weapon.item_type == 'weapon' and weapon.ammo_type: # Ranged
            self.ranged += 0.5 * lucky_bonus
        elif weapon and weapon.item_type == 'weapon' and not weapon.ammo_type: # Melee
            self.strength += 0.5 * lucky_bonus
            self.fitness += 0.5 * lucky_bonus
            self.melee += 1.0 * lucky_bonus
        else: # Bare hands
            self.strength += 0.1 * lucky_bonus
            self.fitness += 0.1 * lucky_bonus
            self.melee += 0.5 * lucky_bonus

    def update_stamina(self, player, is_moving):
        stamina_cap = player.max_stamina * (1 - player.infection / 100)
        if is_moving and player.stamina > 0:
            player.stamina = max(0, player.stamina - 0.2)
        elif not is_moving and player.stamina < stamina_cap:
            player.stamina = min(stamina_cap, player.stamina + 0.3)

    def handle_melee_attack(self, player):
        if player.stamina >= 10:
            player.stamina -= 5
            return True
        print("Too tired to swing!")
        return False
