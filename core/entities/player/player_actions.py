import random
from core.messages import display_message
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.data.recipe_manager import RecipeManager
from core.data.localization import tr

class PlayerActions:
    def start_action(self, action_name, base_duration_mult, callback, xp_reward=5):
        if self.action_timer > 0:
            display_message(tr('msg', "Busy..."))
            return False

        UNIT_TIME = 60
        
        # Calculate transfer timer based on Agility
        # Default (Level 0): 3.0 seconds
        # Max (Level 10): 1.0 second
        agility = self.attributes.get('agility', 0.0)
        agility = max(0.0, min(10.0, agility))
        
        # Linear interpolation: 3.0s at 0 -> 1.0s at 10
        # Slope = (1.0 - 3.0) / 10 = -0.2
        base_seconds = 3.0 - (0.2 * agility)
        
        total_duration = int(UNIT_TIME * base_seconds * base_duration_mult)
        
        self.action_timer = total_duration
        self.action_total_time = total_duration
        self.action_name = action_name
        self.action_callback = callback
        self.action_xp_reward = xp_reward
        
        display_message(f"{action_name}...")
        return True

    def consume_item(self, item, source_type, item_index, container_item=None, is_auto_drink=False, game=None, target_part=None):
        if self.action_timer > 0 and not is_auto_drink:
            display_message(tr('msg', "Busy..."))
            return False

        if getattr(item, 'item_type', '').lower() == 'recipe':
            self.read_recipe_book(item)
            return True

        # Requirement Check Logic
        required_item_found = None
        required_source = None
        required_index = -1
        required_container = None

        if hasattr(item, 'require') and item.require:
            raw_req = item.require
            candidates = []
            if isinstance(raw_req, list):
                candidates = raw_req
            elif isinstance(raw_req, str):
                if raw_req.startswith('[') and raw_req.endswith(']'):
                    candidates = [s.strip() for s in raw_req[1:-1].split(',')]
                else:
                    candidates = [raw_req]
            
            # Helper to find candidate
            def find_candidate(cand_name):
                # Check Belt
                for i, it in enumerate(self.belt):
                    if it and it.name == cand_name:
                        if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                        return it, 'belt', i, None
                # Check Inventory
                for i, it in enumerate(self.inventory):
                    if it and it.name == cand_name:
                        if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                        return it, 'inventory', i, None
                # Check Backpack
                if self.backpack and hasattr(self.backpack, 'inventory'):
                    for i, it in enumerate(self.backpack.inventory):
                        if it and it.name == cand_name:
                             if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                             return it, 'container', i, self.backpack
                return None, None, None, None

            for cand in candidates:
                r_item, r_src, r_idx, r_cont = find_candidate(cand)
                if r_item:
                    required_item_found = r_item
                    required_source = r_src
                    required_index = r_idx
                    required_container = r_cont
                    break
            
            if not required_item_found:
                req_str = " or ".join(candidates)
                display_message(f"{tr('msg', 'Requires')} {req_str} {tr('msg', 'to use.')}")
                return False

        source_inventory = self._get_source_inventory(source_type, container_item)
        
        if not (item.item_type.startswith('consumable') or item.item_type == 'liquid'):
            return False

        if item.load <= 0:
            display_message(f"{tr('msg', 'Cannot use')} {item.name}{tr('msg', ', it is empty.')}")
            return False
            
        duration_mult = 1.0
        if item.item_type == 'consumable_medication' or 'Medkit' in item.name:
            duration_mult = 2.0
        elif item.item_type == 'consumable_drink' or item.item_type == 'liquid':
            duration_mult = 1.0
        elif item.item_type == 'consumable_food':
            duration_mult = 1.0
            
        def execute_consume():
            status_effect_legacy = getattr(item, 'status_effect', None)
            ammo_type = getattr(item, 'ammo_type', None) 
            consumed = False

            if item.item_type == 'consumable_ammo' or status_effect_legacy == 'ammo' or ammo_type is not None:
                self.reload_active_weapon(game=game)
                return 

            if hasattr(item, 'effects') and item.effects:
                for effect in item.effects:
                    eff_type = effect['type'] 
                    targets = effect['targets'] 
                    val = random.randint(effect['min'], effect['max'])
                    
                    for target_stat in targets:
                        if eff_type == 'restore' and target_stat == 'health':
                             if self.health >= self.max_health:
                                 
                                 consumed = False
                             else:
                                self.health = min(self.max_health, self.health + val)
                                display_message(f"{tr('msg', 'Used')} {item.name}. {tr('msg', 'Restored')} {val} {tr('msg', 'Health.')}")
                                consumed = True
                                 
                        elif hasattr(self, target_stat):
                            current_val = getattr(self, target_stat)
                            
                            if eff_type == 'restore':
                                stat_cap = 100.0
                                if target_stat == 'health': stat_cap = self.max_health # Fallback
                                elif target_stat == 'stamina': stat_cap = self.max_stamina
                                elif target_stat == 'tireness': stat_cap = self.max_tireness

                                new_val = min(stat_cap, current_val + val)
                                setattr(self, target_stat, new_val)
                                display_message(f"{tr('msg', 'Used')} {item.name}. {tr('msg', 'Restored')} {val} {target_stat.capitalize()}.")
                                consumed = True

                            elif eff_type == 'reduce':
                                min_cap = 0.0
                                new_val = max(min_cap, current_val - val)
                                setattr(self, target_stat, new_val)
                                display_message(f"{tr('msg', 'Used')} {item.name}. {tr('msg', 'Reduced')} {target_stat.capitalize()} {tr('msg', 'by')} {val}.")
                                consumed = True
            
            elif status_effect_legacy and hasattr(self, status_effect_legacy):
                pass
            
            else:
                if not consumed:
                    display_message(f"{tr('msg', 'Cannot consume')} {item.name}{tr('msg', ': no valid effects found.')}")
                    return 

            if consumed:
                item.load -= 1
                if item.load <= 0:
                    if source_type == 'belt':
                        self.belt[item_index] = None
                    elif source_type == 'inventory':
                        if item_index < len(self.inventory) and self.inventory[item_index] == item:
                            self.inventory.pop(item_index)
                    elif source_type == 'gear':
                        self.clothes[item_index] = None
                    elif (source_type == 'container' or source_type == 'nearby') and container_item:
                        if item_index < len(container_item.inventory) and container_item.inventory[item_index] == item:
                            container_item.inventory.pop(item_index)
                            
                # Consume required item (Match/Lighter)
                if required_item_found:
                    if hasattr(required_item_found, 'load') and required_item_found.load is not None:
                        required_item_found.load -= 1
                        if required_item_found.load <= 0:
                            if required_source == 'belt':
                                self.belt[required_index] = None
                            elif required_source == 'inventory':
                                try:
                                    idx = self.inventory.index(required_item_found)
                                    self.inventory.pop(idx)
                                except ValueError: pass
                            elif required_source == 'container' and required_container:
                                try:
                                    idx = required_container.inventory.index(required_item_found)
                                    required_container.inventory.pop(idx)
                                except ValueError: pass
                            
                            display_message(f"{required_item_found.name} {tr('msg', 'used up.')}")

        if is_auto_drink:
            execute_consume()
            return True
        else:
            return self.start_action(f"Using {item.name}", duration_mult, execute_consume, xp_reward=5)
    
    def toggle_utility_item(self, item, source, index, container_item):
        if not hasattr(item, 'state'):
            return

        # Prevent turning on campfires in inventory (they can only be on when placed on ground)
        if item.state == "off" and "Campfire" in item.name and source not in ['ground', 'nearby']:
            display_message(tr('msg', "Campfires can only be lit when placed on the ground."))
            return

        new_name = ""
        if item.state == "on":
            new_name = item.name.replace(" on", " off")
        elif item.state == "off":
            if item.durability is not None and item.durability <= 0:
                display_message(f"{tr('msg', 'Cannot turn on')} {item.name}{tr('msg', ", it's out of power.")}")
                return

            if item.fuel_type == "Matches":
                matches, m_source, m_index, m_container = self.find_fuel("Matches")
                if not matches:
                    display_message(tr('msg', "No matches to light the lantern."))
                    return

                matches.load -= 1
                if matches.load <= 0:
                    m_inv = self._get_source_inventory(m_source, m_container)
                    if m_inv and m_index < len(m_inv) and m_inv[m_index] == matches:
                        m_inv.pop(m_index)

            new_name = item.name.replace(" off", " on")

        if not new_name:
            return

        new_item = Item.create_from_name(new_name)
        if not new_item:
            print(f"Error: Could not find item template for '{new_name}'")
            return

        new_item.durability = item.durability
        new_item.load = item.load
        # Copy position and rect for ground items
        new_item.rect.center = item.rect.center
        new_item.x = item.x
        new_item.y = item.y

        # Handle ground and nearby sources (items on ground or in VirtualGroundContainer)
        if source == 'ground':
            # Item is in game.items_on_ground, but we don't have game reference here
            # The replacement will be handled by the caller in mouse_context.py
            return new_item
        elif source == 'nearby' and container_item:
            # Check if it's a VirtualGroundContainer (ground items in nearby modal)
            if getattr(container_item, 'item_type', '') == 'ground':
                # Return new_item for caller to handle replacement in game.items_on_ground
                return new_item
            # For other containers (corpse, backpack on ground, etc.), modify directly
            if index is not None and 0 <= index < len(container_item.inventory):
                container_item.inventory[index] = new_item
                return
        elif source and index is not None:
            source_inventory = self._get_source_inventory(source, container_item)
            if source_inventory and index < len(source_inventory) and source_inventory[index] == item:
                source_inventory[index] = new_item
                return
            else:
                print(f"Error: Could not find item {item.name} in {source} to toggle.")
        elif item in self.belt:
             self.belt[self.belt.index(item)] = new_item
        elif item in self.inventory:
             self.inventory[self.inventory.index(item)] = new_item

    def read_recipe_book(self, item):
        recipes_taught = RecipeManager.get_recipes_by_magazine(item.name)
        
        if not recipes_taught:
            display_message(f"{tr('msg', 'You read')} {item.name}{tr('msg', ', but learn nothing new.')}")
            return

        new_recipes = [r for r in recipes_taught if r.magazine not in self.known_recipes] 
        
        if not new_recipes and item.name in self.known_recipes:
            display_message(f"{tr('msg', 'You already know the recipes in')} {item.name}.")
            return

        def finish_reading():
            if item.name not in self.known_recipes:
                self.known_recipes.append(item.name)
                
            else:
                display_message(f"{tr('msg', 'You reviewed')} {item.name}.")
            
            # Add the intelligence XP here, right when the action successfully finishes
            self.progression.add_xp(self, 'intelligence', 10)

        # Call start_action without the xp_attr or xp_reward parameters
        self.start_action(f"Reading {item.name}", 3.0, finish_reading)

    def find_repair_kit(self, target_item):
        if not target_item: return None, None, None, None
        def is_valid_kit(it):
            return (it and it.item_type == 'consumable_repair' and 
                    hasattr(it, 'repair_list') and 
                    target_item.name in it.repair_list and 
                    it.load > 0)
        for i, item in enumerate(self.belt):
            if is_valid_kit(item): return item, 'belt', i, None
        for i, item in enumerate(self.inventory):
            if is_valid_kit(item): return item, 'inventory', i, None
        if self.backpack:
            for i, item in enumerate(self.backpack.inventory):
                if is_valid_kit(item): return item, 'container', i, self.backpack
        return None, None, None, None

    def repair_item(self, game, target_item):
        if self.action_timer > 0:
            display_message(tr('msg', "Busy..."))
            return
        kit, source, index, container = self.find_repair_kit(target_item)
        if not kit:
            display_message(f"{tr('msg', 'No repair kit found for')} {target_item.name}.")
            return
        if target_item.durability >= target_item.max_durability:
            display_message(f"{target_item.name} is already in perfect condition.")
            return
        def execute_repair():
            restore_amount = random.randint(kit.min_restore, kit.max_restore)
            old_dur = target_item.durability
            target_item.durability = min(target_item.max_durability, target_item.durability + restore_amount)
            restored = target_item.durability - old_dur
            display_message(f"{tr('msg', 'Repaired')} {target_item.name} {tr('msg', 'by')} {restored:.0f} {tr('msg', 'points using')} {kit.name}.")
            self.progression.add_xp(self, 'maintenance', 20)
            kit.load -= 1
            if kit.load <= 0:
                inv = self._get_source_inventory(source, container)
                if inv:
                    if source == 'belt': self.belt[index] = None
                    else: inv.pop(index)
                display_message(f"{kit.name} {tr('msg', 'used up.')}")
        self.start_action("Repairing", 2.0, execute_repair, xp_reward=10)

    def get_item_context_options(self, item, source, container_item=None):
        options = []
        
        # Safely get item_type using getattr to prevent AttributeError for NPCs/Animals
        item_type = getattr(item, 'item_type', '')
        
        if item_type == 'vehicle':
             options.append("Inspect"); return options
        if isinstance(item, Corpse):
            options.append('Open'); return options
        
        if item_type == 'text' or item_type == 'recipe' or item_type == 'map':
            if item_type == 'recipe': options.append('Use')
            elif item_type == 'map': options.append('Open')
            else: options.append('Read')
            if hasattr(item, 'is_stackable') and item.is_stackable():
                options.append('Drop one')
                if getattr(item, 'load', 0) > 1: options.append('Drop all')
            else: options.append('Drop')
            return options

        if item_type.startswith('consumable') or item_type == 'liquid':
            item_name = getattr(item, 'name', '')
            if item_type == 'consumable_ammo' or 'Ammo' in item_name or 'Shells' in item_name:
                pass
            elif item_type == 'consumable_medication' or 'Medkit' in item_name or 'Bandage' in item_name:
                options.append('Use')
                
            else: options.append('Use')
            
            # CHECK ALLOW BELT FOR CONSUMABLES
            if getattr(item, 'allow_belt', False):
                options.append('Equip')
                
        elif item_type in ['utility', 'mobile']:
            item_state = getattr(item, 'state', '')
            if item_state == 'on': options.append('Turn off')
            elif item_state == 'off':
                # Campfires can only be turned on when on the ground
                if "Campfire" in getattr(item, 'name', '') and source not in ['ground', 'nearby']:
                    pass  # Don't add "Turn on" for campfires in inventory
                else:
                    options.append('Turn on')
            if getattr(item, 'fuel_type', None): options.append('Reload')
            if item_type == 'mobile': options.append('Open')
            
            # CHECK ALLOW BELT FOR UTILITIES
            if getattr(item, 'allow_belt', False):
                options.append('Equip')
                
        elif item_type == 'backpack':
            options.append('Open')
            if not self.backpack: options.append('Equip')
        elif item_type == 'cloth':
            options.append('Open'); options.append('Equip')
        elif item_type in ['weapon_melee', 'weapon_ranged', 'tool']:
            options.append('Equip')
            if item_type == 'weapon_ranged': options.append('Reload')
            if item_type == 'weapon_ranged' and getattr(item, 'load', None) is not None and getattr(item, 'load', 0) > 0: options.append('Get bullets')
        elif item_type == 'container':
            options.append('Open')
            if getattr(item, 'allow_belt', False):
                options.append('Equip')
                
        is_liquid = getattr(item, 'liquid', False)
        
        if is_liquid:
            found_names = set()
            
            def can_accept_liquid(container):
                if not container or not getattr(container, 'allow_liquid', False):
                    return False
                if len(container.inventory) < (container.capacity or 0):
                    return True
                for inv_item in container.inventory:
                    if hasattr(inv_item, 'can_stack_with') and inv_item.can_stack_with(item):
                        if getattr(inv_item, 'load', 0) < getattr(inv_item, 'capacity', 1):
                            return True
                return False

            for b_item in self.belt:
                if can_accept_liquid(b_item):
                    found_names.add(b_item.name)
            for i_item in self.inventory:
                if can_accept_liquid(i_item):
                    found_names.add(i_item.name)
            if can_accept_liquid(self.backpack):
                found_names.add(self.backpack.name)
            for c_item in self.clothes.values():
                if can_accept_liquid(c_item):
                    found_names.add(c_item.name)
            
            for name in sorted(found_names):
                options.append(f"Add to {name}")

        if hasattr(item, 'is_stackable') and item.is_stackable() and getattr(item, 'load', None) is not None:
            options.append('Drop one')
            if getattr(item, 'load', 0) > 1: options.append('Drop all')
            
            if self.backpack and container_item is not self.backpack:
                # [FIX] Ensure matching liquid states before allowing transfer stack
                bp_allow_liquid = getattr(self.backpack, 'allow_liquid', False)
                if bp_allow_liquid == is_liquid:
                    options.append('Send all to Backpack')
            
            if source != 'inventory':
                if not is_liquid:
                    options.append('Send all to Inventory')
        else: options.append('Drop')
        return options