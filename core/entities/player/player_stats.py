# core/entities/player/player_stats.py

import random
from core.messages import display_message

class PlayerStats:


    def get_total_defence(self):
        total_defence = 0
        for item in self.clothes.values():
            if item and hasattr(item, 'defence') and item.defence is not None:
                if hasattr(item, 'durability') and item.durability is not None:
                    if item.max_durability > 0:
                        defence_factor = item.durability / item.max_durability
                        total_defence += item.defence * defence_factor
                    elif item.durability > 0:
                         total_defence += item.defence
                elif not hasattr(item, 'durability') or item.durability is None:
                     total_defence += item.defence
        return total_defence

    def take_durability_damage(self, raw_damage, game):
        worn_clothes = [item for item in self.clothes.values() if item and hasattr(item, 'durability') and item.durability is not None and item.durability > 0]
        if not worn_clothes: return

        item_hit = random.choice(worn_clothes)
        dur_damage = raw_damage * 0.25 
        
        if dur_damage > 0:
            item_hit.durability = max(0, item_hit.durability - dur_damage)
            if item_hit.durability <= 0:
                display_message(f"Your {item_hit.name} broke!")

    def take_damage(self, game, base_damage, base_infection):
        
        if getattr(self, 'vehicle', None):
            if hasattr(self.vehicle, 'damage_motor'):
                self.vehicle.damage_motor(base_damage)
            return 0, 0


        self.take_durability_damage(base_damage, game)

        total_defence = self.get_total_defence()
        health_bonus_perc = self.progression.get_health_bonus(self)
        infection_bonus_perc = self.progression.get_infection_bonus(self)
        
        # [CHANGED] 5 pieces at 1.0 each = 5.0 total defense
        # We divide by 5.0 to scale it so that 5.0 raw defense = 100% reduction
        clothes_reduction_perc = (total_defence / 5.0) * 100.0
        
        total_reduction_perc = health_bonus_perc + clothes_reduction_perc
        
        damage_modifier = 1.0 - (total_reduction_perc / 100.0)
        damage_modifier = max(0.0, damage_modifier)

        infection_modifier = 1.0 + (infection_bonus_perc / 100.0)
        
        final_damage_taken = max(0, base_damage * damage_modifier)
        final_infection_taken = max(0, base_infection * infection_modifier)
        
        self.health = max(0.0, self.health - final_damage_taken)

        if final_infection_taken > 0:
            self.infection = min(100, self.infection + final_infection_taken)
            
        return final_damage_taken, final_infection_taken