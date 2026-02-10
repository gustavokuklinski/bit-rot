# core/entities/player/player_stats.py

import random
from core.messages import display_message

class PlayerStats:
    def update_global_health(self):
        if not self.body_parts:
            return
        total_value = sum(part['value'] for part in self.body_parts.values())
        max_possible = 100.0 * len(self.body_parts)
        self.health = (total_value / max_possible) * 100.0

    def get_vulnerable_part(self):
        slot_map = {
            'hand': 'hands',
            'facial': 'facial_hair', 
            'utility': 'util'
        } 
        candidates = []
        lowest_def = float('inf')

        for part, data in self.body_parts.items():
            defence = data.get('defence', 0.0)
            c_slot = slot_map.get(part, part)
            item = self.clothes.get(c_slot)
            if item and hasattr(item, 'defence'):
                defence += item.defence
            
            if defence < lowest_def:
                lowest_def = defence
                candidates = [part]
            elif defence == lowest_def:
                candidates.append(part)
        
        return random.choice(candidates) if candidates else 'body'

    def take_damage_to_part(self, part, amount):
        if part in self.body_parts:
            self.body_parts[part]['value'] = max(0.0, self.body_parts[part]['value'] - amount)
            self.update_global_health()

    def get_most_damaged_part(self):
        candidates = []
        lowest_val = 101.0
        for part, data in self.body_parts.items():
            if data['value'] < lowest_val:
                lowest_val = data['value']
                candidates = [part]
            elif data['value'] == lowest_val:
                candidates.append(part)
        if lowest_val >= 100.0:
            return None
        return random.choice(candidates)

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
        if self.vehicle: return 0, 0
        
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
        
        target_part = random.choice(list(self.body_parts.keys()))
        self.take_damage_to_part(target_part, final_damage_taken)

        if final_infection_taken > 0:
            self.infection = min(100, self.infection + final_infection_taken)
            
        return final_damage_taken, final_infection_taken