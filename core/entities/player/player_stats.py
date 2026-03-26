# core/entities/player/player_stats.py

import random
from core.messages import display_message
from core.data.localization import tr

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
        # We keep this intact in case environmental hazards or explosions call it directly
        worn_clothes = [item for item in self.clothes.values() if item and hasattr(item, 'durability') and item.durability is not None and item.durability > 0]
        if not worn_clothes: return

        item_hit = random.choice(worn_clothes)
        dur_damage = raw_damage * 0.25 
        
        if dur_damage > 0:
            item_hit.durability = max(0, item_hit.durability - dur_damage)
            if item_hit.durability <= 0:
                display_message(f"{tr('msg', 'Your')} {item_hit.name} {tr('msg', 'broke!')}")

    def take_damage(self, game, base_damage, base_infection):
        
        if getattr(self, 'vehicle', None):
            if hasattr(self.vehicle, 'damage_motor'):
                self.vehicle.damage_motor(base_damage)
            return 0, 0

        # 1. Damage will first go to DEFENCE (Clothes Durability acts as the Defense Pool)
        remaining_damage = base_damage
        worn_clothes = [item for item in self.clothes.values() if item and hasattr(item, 'durability') and item.durability is not None and item.durability > 0]
        
        if worn_clothes:
            # Distribute damage across worn clothes to act as an armor shield
            while remaining_damage > 0 and worn_clothes:
                item_hit = random.choice(worn_clothes)
                
                # Calculate how much damage this specific item can absorb before breaking
                absorb_amount = min(item_hit.durability, remaining_damage)
                item_hit.durability -= absorb_amount
                remaining_damage -= absorb_amount
                
                if item_hit.durability <= 0:
                    item_hit.durability = 0
                    worn_clothes.remove(item_hit)
                    display_message(f"{tr('msg', 'Your')} {item_hit.name} {tr('msg', 'broke!')}")

        # 2. When the defence reach Zero, start depleting the player Health
        health_bonus_perc = self.progression.get_health_bonus(self)
        
        # Apply biological health bonus resistances to the overflow damage
        if health_bonus_perc > 0 and remaining_damage > 0:
             remaining_damage *= (1.0 - (health_bonus_perc / 100.0))
             
        final_damage_taken = max(0, remaining_damage)
        self.health = max(0.0, self.health - final_damage_taken)

        # 3. Calculate Infection logically
        infection_bonus_perc = self.progression.get_infection_bonus(self)
        infection_modifier = 1.0 + (infection_bonus_perc / 100.0)
        final_infection_taken = max(0, base_infection * infection_modifier)

        if final_infection_taken > 0:
            self.infection = min(100, self.infection + final_infection_taken)
            
        return final_damage_taken, final_infection_taken