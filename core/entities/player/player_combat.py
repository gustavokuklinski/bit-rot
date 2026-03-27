import random
from core.messages import display_message
from core.entities.item.item import Item
from core.placement import find_free_tile
from core.data.localization import tr

class PlayerCombat:
    def get_attack_damage(self):
        min_dmg = 1
        max_dmg = 3 
        is_ranged = False
        
        if self.active_weapon:
            min_dmg = getattr(self.active_weapon, 'min_damage', 1)
            max_dmg = getattr(self.active_weapon, 'max_damage', 5)
            is_ranged = self.active_weapon.item_type == 'weapon_ranged'
            
            if hasattr(self.active_weapon, 'current_damage_range'):
                rng = self.active_weapon.current_damage_range
                min_dmg = rng[0]
                max_dmg = rng[1]

        # 1. Slide minimum damage up based on weapon skill
        if is_ranged:
            skill_level = self.progression.get_ranged(self)
        else:
            skill_level = self.progression.get_melee(self)
            
        scale = min(10, skill_level) / 10.0
        effective_min = min_dmg + (max_dmg - min_dmg) * scale

        # Calculate base randomized damage
        base_damage = random.randint(int(effective_min), int(max_dmg))
        
        # 2. Apply Strength Multiplier for Melee/Unarmed Attacks
        if not is_ranged:
            str_level = self.progression.get_strength(self)
            # Level 0 = 1.0x (no bonus), Level 10 = 2.0x (+100% bonus)
            str_multiplier = 1.0 + (min(10, str_level) / 10.0)
            
            base_damage = int(base_damage * str_multiplier)

        return base_damage

    def process_kill(self, weapon, zombie):
        self.progression.process_kill(self, weapon, zombie)

    def reload_active_weapon(self, weapon=None, game=None):
        if self.is_reloading:
            display_message(tr('msg', "Already reloading."))
            return
            
        target_weapon = weapon if weapon else self.active_weapon
        
        if not target_weapon or not getattr(target_weapon, 'ammo_type', None):
            display_message(tr('msg', "Cannot reload: No gun equipped."))
            return
            
        if target_weapon.load >= target_weapon.capacity:
            display_message(f"{tr('item', target_weapon.name)} {tr('msg', 'is already full')} ({target_weapon.load:.0f}/{target_weapon.capacity:.0f}).")
            return
        
        ammo_item, _, _, _ = self.find_matching_ammo(target_weapon)
        
        if not ammo_item:
            display_message(f"{tr('msg', 'No')} {tr('item', target_weapon.ammo_type)} {tr('msg', 'found.')}")
            return
        
        if game and hasattr(target_weapon, 'sounds') and 'reload' in target_weapon.sounds and target_weapon.sounds['reload']:
            game.sound_manager.play_sound(
                target_weapon.sounds['reload'],
                subdir='items',
                game=game,
                source_pos=self.rect.center,
                base_volume=random.uniform(0.2, 0.7),
                pitch_variance=0.15
            )
            
        self.is_reloading = True
        self.reloading_weapon = target_weapon 
        self.reload_timer = self.reload_duration
        display_message(f"{tr('msg', 'Reloading')} {tr('item', target_weapon.name)}...")

    def _finish_reload(self):
        self.is_reloading = False
        weapon = getattr(self, 'reloading_weapon', self.active_weapon)
        self.reloading_weapon = None 
        if not weapon: return
        
        ammo_item, source_type, index, container_obj = self.find_matching_ammo(weapon)
        if not ammo_item: return
        needed = int(weapon.capacity - weapon.load)
        available = int(ammo_item.load)
        transfer_amount = min(needed, available)
        
        if transfer_amount > 0:
            weapon.load += transfer_amount
            ammo_item.load -= transfer_amount
            display_message(f"{tr('msg', 'Finished reloading')} {tr('item', weapon.name)}. {tr('msg', 'Load:')} {weapon.load:.0f}/{weapon.capacity:.0f}.")
            if ammo_item.load <= 0:
                if source_type == 'inventory':
                    try: self.inventory.remove(ammo_item)
                    except ValueError: pass
                elif source_type == 'belt': self.belt[index] = None
                elif source_type == 'gear': self.clothes[index] = None
                elif source_type == 'container' and container_obj:
                    try: container_obj.inventory.remove(ammo_item)
                    except ValueError: pass

    def reload_utility_item(self, item, source, index, container_item):
        if not item.fuel_type:
            display_message(f"{tr('item', item.name)} {tr('msg', 'does not use fuel.')}")
            return

        # Parse fuel_type if it is a list or formatted as "[Item1, Item2]"
        raw_fuel = item.fuel_type
        if isinstance(raw_fuel, dict) and 'type' in raw_fuel:
            raw_fuel = raw_fuel['type']
            
        candidates = []
        if isinstance(raw_fuel, list):
            candidates = raw_fuel
        elif isinstance(raw_fuel, str):
            if raw_fuel.startswith('[') and raw_fuel.endswith(']'):
                candidates = [s.strip() for s in raw_fuel[1:-1].split(',')]
            else:
                candidates = [raw_fuel]

        fuel_item = None
        f_source = None
        f_index = -1
        f_container = None

        # Try to find any of the accepted fuels
        for cand in candidates:
            fuel_item, f_source, f_index, f_container = self.find_fuel(cand)
            if fuel_item:
                break

        if not fuel_item:
            cand_str = " or ".join([tr('item', c) for c in candidates])
            display_message(f"{tr('msg', 'No')} {cand_str} {tr('msg', 'found to reload.')}")
            return
            
        max_dur = item.max_durability
        dur_needed = max_dur - (item.durability or 0)
        
        if dur_needed <= 0:
            display_message(f"{tr('item', item.name)} {tr('msg', 'durability is already full.')}")
            return

        if fuel_item.load <= 0:
            display_message(f"{tr('msg', 'No')} {tr('item', fuel_item.name)} {tr('msg', 'left to use.')}")
            return

        fuel_item.load -= 1
        item.durability = max_dur
        display_message(f"{tr('msg', 'Used 1')} {tr('item', fuel_item.name)} {tr('msg', 'to reload')} {tr('item', item.name)}. {tr('msg', 'Durability set to:')} {item.durability:.0f}")
        
        if fuel_item.load <= 0:
            f_inv = self._get_source_inventory(f_source, f_container)
            if f_inv and f_index < len(f_inv) and f_inv[f_index] == fuel_item:
                f_inv.pop(f_index)

    def unload_weapon(self, game, weapon):
        if not weapon.ammo_type or weapon.load <= 0: return
        ammo = Item.create_from_name(weapon.ammo_type)
        if not ammo:
            print(f"Error creating ammo: {weapon.ammo_type}")
            return
        ammo.load = weapon.load
        weapon.load = 0
        display_message(f"{tr('msg', 'Unloaded')} {int(ammo.load)} {tr('item', ammo.name)} {tr('msg', 'from')} {tr('item', weapon.name)}.")
        self.stack_item_in_inventory(ammo)
        if ammo.load <= 0: return 
        if len(self.inventory) < self.base_inventory_slots:
             self.inventory.append(ammo); return
        
        ammo.rect.center = self.rect.center
        if find_free_tile(ammo.rect, game.obstacles, [], initial_pos=self.rect.center, max_radius=1):
            game.items_on_ground.append(ammo)
            display_message(tr('msg', "Inventory full. Dropped ammo on ground."))
        else:
             weapon.load = ammo.load
             display_message(tr('msg', "No space to unload ammo!"))

    def destroy_broken_weapon(self, broken_weapon):
        if self.active_weapon == broken_weapon: self.active_weapon = None
        for i, item in enumerate(self.belt):
            if item == broken_weapon:
                self.belt[i] = None
                display_message(f"{broken_weapon.name} {tr('msg', 'broke and was removed from your inventory.')}")
                return
        try:
            self.inventory.remove(broken_weapon)
            display_message(f"{tr('item', broken_weapon.name)} {tr('msg', 'broke and was removed from your inventory.')}")
        except ValueError: pass