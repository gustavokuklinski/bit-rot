# core/entities/player/player_inventory.py
import random
from core.entities.item.item import Item
from core.ui.inventory_modal import get_inventory_slot_rect, get_belt_slot_rect_in_modal
from core.messages import display_message
from core.data.localization import tr

class PlayerInventory:
    def get_total_inventory_slots(self):
        return self.base_inventory_slots

    def find_consumable_at_mouse(self, mouse_pos):
        for i, item in enumerate(self.inventory):
            if item and item.item_type.startswith('consumable'):
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, i
        return None, None

    def find_item_at_mouse(self, mouse_pos):
        for i, item in enumerate(self.inventory):
            if item:
                slot_rect = get_inventory_slot_rect(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'inventory', i

        for i, item in enumerate(self.belt):
            if item:
                slot_rect = get_belt_slot_rect_in_modal(i)
                if slot_rect.collidepoint(mouse_pos):
                    return item, 'belt', i
        return None, None, None

    def find_matching_ammo(self, weapon):
        if not weapon or not weapon.ammo_type:
            return None, None, None, None
        ammo_type_needed = weapon.ammo_type
        
        def search_recursive(container_item):
            if not hasattr(container_item, 'inventory') or not container_item.inventory:
                return None
            for i, item in enumerate(container_item.inventory):
                if item:
                    if item.item_type.startswith('consumable') and (item.load or 0) > 0 and item.name == ammo_type_needed:
                        return item, 'container', i, container_item
                    result = search_recursive(item)
                    if result: return result
            return None

        for i, item in enumerate(self.belt):
            if item:
                if item.item_type.startswith('consumable') and (item.load or 0) > 0 and item.name == ammo_type_needed:
                    return item, 'belt', i, None
                res = search_recursive(item)
                if res: return res

        for i, item in enumerate(self.inventory):
            if item:
                if item.item_type.startswith('consumable') and (item.load or 0) > 0 and item.name == ammo_type_needed:
                    return item, 'inventory', i, None
                res = search_recursive(item)
                if res: return res
        
        for slot, item in self.clothes.items():
            if item:
                if item.item_type.startswith('consumable') and (item.load or 0) > 0 and item.name == ammo_type_needed:
                    return item, 'gear', slot, None
                res = search_recursive(item)
                if res: return res

        return None, None, None, None

    def find_fuel(self, fuel_identifier):
        if not fuel_identifier: return None, None, None, None
            
        candidates = []
        if isinstance(fuel_identifier, list):
            candidates = fuel_identifier
        elif isinstance(fuel_identifier, str):
            if fuel_identifier.startswith('[') and fuel_identifier.endswith(']'):
                candidates = [s.strip() for s in fuel_identifier[1:-1].split(',')]
            else:
                candidates = [fuel_identifier]
        
        def is_match(it):
            return it and it.name in candidates and getattr(it, 'load', 0) > 0

        for i, item in enumerate(self.belt):
            if is_match(item): return item, 'belt', i, None

        for i, item in enumerate(self.inventory):
            if is_match(item): return item, 'inventory', i, None
                    
        return None, None, None, None

    def _get_source_inventory(self, source_type, container_item=None):
        if source_type == 'inventory':
            return self.inventory
        elif source_type == 'belt':
            return self.belt
        elif source_type in ['container', 'nearby', 'gear', 'clothes'] and container_item:
            return container_item.inventory
        return None

    def equip_item_to_belt(self, item, source_type, item_index, container_item=None):
        if not any(slot is None for slot in self.belt):
            display_message(tr('msg', "Belt is full."))
            return False
        source_inventory = self._get_source_inventory(source_type, container_item)
        if source_inventory is None:
             print(f"Error: Could not find source inventory for {source_type}")
             return False

        for i, slot in enumerate(self.belt):
            if slot is None:
                self.belt[i] = item
                item.in_belt = True
                if source_type == 'belt':
                    source_inventory[item_index] = None
                else:
                    source_inventory.pop(item_index)
                display_message(f"{tr('msg', 'Equipped')} {tr('item', item.name)} {tr('msg', 'to belt.')}")
                return True
        return False
    
    def find_item_and_stack(self, source, index, container_item):
        source_inventory = self._get_source_inventory(source, container_item)
        if source_inventory and 0 <= index < len(source_inventory):
            item = source_inventory[index]
            return item, source_inventory
        return None, None

    def drop_item_stack(self, game, source, index, container_item, quantity):
        item, source_inventory = self.find_item_and_stack(source, index, container_item)
        if not item: return

        item_to_drop = None
        if quantity == 'all' or quantity >= item.load:
            item_to_drop = self.drop_item(game, source, index, container_item)
        elif quantity > 0 and item.load > 0:
            item_to_drop = Item.create_from_name(tr('item', item.name))
            if not item_to_drop: return

            transfer_amount = min(item.load, quantity)
            item_to_drop.load = transfer_amount
            item_to_drop.durability = item.durability 
            
            item.load -= transfer_amount
            if item.load <= 0:
                self.drop_item(game, source, index, container_item) 
        
        if item_to_drop:
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)
            item_to_drop.rect.center = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
            item_to_drop.x = item_to_drop.rect.x
            item_to_drop.y = item_to_drop.rect.y
            
            if item_to_drop not in game.items_on_ground:
                game.items_on_ground.append(item_to_drop)
            return item_to_drop
        return None

    def transfer_item_stack(self, source, index, container_item, target_container, game=None):
        if self.action_timer > 0:
            display_message(tr('msg', "Busy..."))
            return

        def execute_transfer():
            item = None
            source_inventory = self._get_source_inventory(source, container_item) 
            if source_inventory and 0 <= index < len(source_inventory): item = source_inventory[index] 

            # [FIX] Attach 'obj' to the target definitions so we can check their liquid flags
            targets = []
            if target_container is self:
                targets.append({'inv': self.inventory, 'cap': self.base_inventory_slots, 'name': "Inventory", 'obj': self})
            elif target_container and hasattr(target_container, 'inventory'):
                targets.append({'inv': target_container.inventory, 'cap': target_container.capacity or 0, 'name': target_container.name, 'obj': target_container})
            else: return

            if not item: return
            remaining_load = item.load
            is_item_liquid = getattr(item, 'liquid', False)
            
            for target in targets:
                # [FIX] Skip this target container if liquid flags don't perfectly match
                target_obj = target.get('obj')
                if getattr(target_obj, 'allow_liquid', False) != is_item_liquid:
                    continue
                    
                target_inv = target['inv']
                for target_item in target_inv:
                    if target_item.can_stack_with(item):
                        available_space = target_item.capacity - target_item.load
                        transfer = min(available_space, remaining_load)
                        target_item.load += transfer
                        remaining_load -= transfer
                        item.load = remaining_load 
                        if remaining_load <= 0: break
                if remaining_load <= 0: break
            
            if item.load <= 0:
                if source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                    if source == 'belt':
                        self.belt[index] = None
                        item.in_belt = False
                    else:
                        source_inventory.pop(index)
                    if game and getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                        game.items_on_ground.remove(item)
                dest_name = targets[0]['name'] if targets else "Inventory"
                
                display_message(f"{tr('msg', 'Merged all of')} {tr('item', item.name)} {tr('msg', 'into')} {dest_name}.")
                return
                
            if remaining_load > 0:
                transferred = False
                for target in targets:
                    # [FIX] Apply liquid match constraint for creating new item slots too
                    target_obj = target.get('obj')
                    if getattr(target_obj, 'allow_liquid', False) != is_item_liquid:
                        continue
                        
                    target_inv = target['inv']
                    target_cap = target['cap']
                    target_name = target['name']

                    if len(target_inv) < target_cap:
                        new_stack = Item.create_from_name(tr('item', item.name))
                        new_stack.load = remaining_load
                        new_stack.durability = item.durability 
                        target_inv.append(new_stack)
                        
                        if source_inventory and 0 <= index < len(source_inventory) and source_inventory[index] == item:
                            if source == 'belt':
                                self.belt[index] = None
                                item.in_belt = False
                            else:
                                source_inventory.pop(index)
                            if game and getattr(container_item, 'item_type', '') == 'ground' and item in game.items_on_ground:
                                game.items_on_ground.remove(item)

                        display_message(f"{tr('msg', 'Sent')} {remaining_load} {tr('item', item.name)} {tr('msg', 'to')} {target_name}.")
                        transferred = True
                        break 
                
                if not transferred:
                    display_message(f"{tr('msg', 'Inventory full. Could not transfer remaining')} {remaining_load}.")

        # --- CHANGED PART ---
        def is_on_player(container):
            if not container: return False
            if container is self: return True 
            
            # 1. Recognize the Player entity itself as "on player" by verifying if its inventory matches this one
            if hasattr(container, 'inventory'):
                # Handle cases where container.inventory is the PlayerInventory object (self)
                # or where container.inventory is the direct item list (self.inventory)
                if container.inventory is self or container.inventory is getattr(self, 'inventory', None):
                    return True

            # 2. Safely check if the container is a string that belongs to player slots
            if isinstance(container, str):
                if container in ['inventory', 'belt', 'gear', 'clothes']: return True
                # Catch specific slot transfers like 'util', 'legs', 'body'
                if hasattr(self, 'clothes') and container in self.clothes: return True
                return False

            # 3. Check objects robustly by reference and ID
            c_id = getattr(container, 'id', None)
            
            def check_recursive(items):
                if not items: return False
                # Handle both dicts (self.clothes) and lists (inventory, belt)
                items_to_check = items.values() if isinstance(items, dict) else items
                for item in items_to_check:
                    if not item: continue
                    if item is container or (c_id is not None and getattr(item, 'id', None) == c_id): return True
                    if hasattr(item, 'inventory') and item.inventory:
                        if check_recursive(item.inventory): return True
                return False

            if hasattr(self, 'belt') and check_recursive(self.belt): return True
            if hasattr(self, 'clothes') and check_recursive(self.clothes): return True
            if hasattr(self, 'inventory') and check_recursive(self.inventory): return True
            return False

        # source_is_on_player handles slot strings ('legs', 'util') OR the physical item object
        source_is_on_player = is_on_player(source) or is_on_player(container_item)
        target_is_on_player = is_on_player(target_container)
        # --------------------
        
        needs_timer = not (source_is_on_player and target_is_on_player)
        action_label = "Looting" if not source_is_on_player and target_is_on_player else "Transferring"

        if needs_timer: self.start_action(action_label, 1.5, execute_transfer, xp_reward=2)
        else: execute_transfer()

    def drop_item(self, game, source, index, container_item=None):
        if self.drop_cooldown > 0:
            display_message(tr('msg', "Cannot drop items so quickly."))
            return None

        item_to_drop = None
        
        if source == 'inventory' and index < len(self.inventory):
            item_to_drop = self.inventory.pop(index)
        elif source == 'belt' and index < len(self.belt):
            item_to_drop = self.belt[index]
            self.belt[index] = None
            if item_to_drop: item_to_drop.in_belt = False
            if self.active_weapon == item_to_drop: self.active_weapon = None
        elif source == 'gear':
            item_to_drop = self.clothes.get(index) 
            self.clothes[index] = None
        elif source in ['container', 'nearby', 'gear', 'clothes'] and container_item and index < len(container_item.inventory):
            item_to_drop = container_item.inventory.pop(index)

        if item_to_drop:
            offset_x = random.randint(-8, 8)
            offset_y = random.randint(-8, 8)
            item_to_drop.rect.center = (self.rect.centerx + offset_x, self.rect.centery + offset_y)
            item_to_drop.x = item_to_drop.rect.x
            item_to_drop.y = item_to_drop.rect.y
            game.items_on_ground.append(item_to_drop)
            self.drop_cooldown = 10 
            return item_to_drop
        return None

    def stack_item_in_inventory(self, item_to_stack):
        if not item_to_stack.is_stackable(): return 
        for item in self.inventory:
            if item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0: return 
        for item in self.belt:
            if item and item.can_stack_with(item_to_stack):
                available_space = item.capacity - item.load
                transfer = min(available_space, item_to_stack.load)
                item.load += transfer
                item_to_stack.load -= transfer
                if item_to_stack.load <= 0: return 

    def find_water_to_auto_drink(self):
        def search_recursive(container_item):
            if not hasattr(container_item, 'inventory') or not container_item.inventory: return None
            for i, item in enumerate(container_item.inventory):
                if item:
                    if 'Water' in tr('item', item.name) and (item.load or 0) > 0: return item, 'container', i, container_item
                    result = search_recursive(item)
                    if result: return result
            return None

        for i, item in enumerate(self.belt):
            if item:
                if 'Water' in tr('item', item.name) and (item.load or 0) > 0: return item, 'belt', i, None 
                res = search_recursive(item)
                if res: return res

        for i, item in enumerate(self.inventory):
            if item:
                if 'Water' in tr('item', item.name) and (item.load or 0) > 0: return item, 'inventory', i, None 
                res = search_recursive(item)
                if res: return res

        for slot, item in self.clothes.items():
            if item:
                if 'Water' in tr('item', item.name) and (item.load or 0) > 0: return item, 'gear', slot, None
                res = search_recursive(item)
                if res: return res

        return None, None, None, None