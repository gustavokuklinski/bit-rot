# core/entities/player/player_actions.py

import random
import os
import core.messages
from core.messages import display_message
from core.entities.item.item import Item
from core.entities.zombie.corpse import Corpse
from core.data.recipe_manager import RecipeManager
from core.data.localization import tr
from core.entities.item.item_helpers import is_container_on_player

class PlayerActions:
    def start_action(self, action_name, base_duration_mult, callback, xp_reward=5, 
                     allow_walk=False, cancel_on_move=False, on_cancel=None, 
                     action_sound=None, action_sound_subdir='items'):
        if self.action_timer > 0:
            display_message(tr('msg', "Busy..."))
            return False

        UNIT_TIME = 60
        agility = self.attributes.get('agility', 0.0)
        agility = max(0.0, min(10.0, agility))
        base_seconds = 3.0 - (0.2 * agility)
        
        total_duration = int(UNIT_TIME * base_seconds * base_duration_mult)
        
        # Stop any previous action sound channel
        if getattr(self, 'action_sound_channel', None):
            try:
                self.action_sound_channel.stop()
            except Exception:
                pass
            self.action_sound_channel = None

        self.action_timer = total_duration
        self.action_total_time = total_duration
        self.action_name = action_name
        self.action_callback = callback
        self.action_xp_reward = xp_reward
        self.action_allow_walk = allow_walk
        self.action_cancel_on_move = cancel_on_move
        self.action_on_cancel = on_cancel

        # Start looping action sound if provided
        if action_sound:
            target_game = getattr(self, 'game', None) or getattr(core.messages, '_game_instance', None)
            if target_game and hasattr(target_game, 'sound_manager'):
                self.action_sound_channel = target_game.sound_manager.play_sound(
                    action_sound,
                    subdir=action_sound_subdir,
                    game=target_game,
                    source_pos=self.rect.center,
                    base_volume=0.5,
                    loops=-1,
                    is_critical=True
                )
        
        display_message(f"{action_name}...")
        return True

    def consume_item(self, item, source_type, item_index, container_item=None, is_auto_drink=False, game=None, target_part=None):
        if self.action_timer > 0 and not is_auto_drink:
            display_message(tr('msg', "Busy..."))
            return False

        # Restrict 'Use' to items in player inventory/possession
        is_on_player = (source_type in ('inventory', 'belt', 'gear')) or (source_type == 'container' and container_item and is_container_on_player(container_item, self))
        if not is_on_player:
            display_message(tr('msg', "Item must be in inventory to use."))
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
            if isinstance(raw_req, dict) and 'type' in raw_req:
                raw_req = raw_req['type']
            candidates = []
            if isinstance(raw_req, list):
                candidates = raw_req
            elif isinstance(raw_req, str):
                if raw_req.startswith('[') and raw_req.endswith(']'):
                    candidates = [s.strip() for s in raw_req[1:-1].split(',')]
                else:
                    candidates = [raw_req]
            
            def find_candidate(cand_name):
                for i, it in enumerate(self.belt):
                    if it and it.name == cand_name:
                        if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                        return it, 'belt', i, None
                for i, it in enumerate(self.inventory):
                    if it and it.name == cand_name:
                        if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                        return it, 'inventory', i, None
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
            display_message(f"{tr('msg', 'Cannot use')} {tr('item', item.name)}{tr('msg', ', it is empty.')}")
            return False
            
        duration_mult = getattr(item, 'consume_time', 1.0)
        
        # Check action walking vs cancel-on-move
        item_type = getattr(item, 'item_type', '')
        walkable_types = {'consumable_food', 'consumable_drink', 'consumable_drugs', 'consumable_medication', 'liquid'}
        is_book = (item_type == 'consumable_book' or 'book' in item_type.lower() or item_type == 'recipe' or 'book' in getattr(item, 'name', '').lower())

        allow_walk = (item_type in walkable_types) and not is_book
        cancel_on_move = is_book
        action_sound = 'read.ogg' if is_book else None

        def execute_consume():
            consumed = False
            old_alcohol = getattr(self, 'drugs', 0.0)

            if hasattr(item, 'effects') and item.effects:
                for effect in item.effects:
                    eff_type = effect['type'] 
                    targets = effect['targets'] 
                    val = effect.get('value', 0)
                    
                    for target_stat in targets:
                        if eff_type == 'restore' and target_stat == 'health':
                             if self.health >= self.max_health:
                                 consumed = False
                             else:
                                self.health = min(self.max_health, self.health + val)
                                display_message(f"{tr('msg', 'Used')} {tr('item', item.name)}. {tr('msg', 'Restored')} {val} {tr('msg', 'Health.')}")
                                consumed = True
                                 
                        elif hasattr(self, target_stat):
                            current_val = getattr(self, target_stat)
                            
                            if eff_type == 'restore':
                                stat_cap = 100.0
                                if target_stat == 'health': stat_cap = self.max_health
                                elif target_stat == 'stamina': stat_cap = self.max_stamina

                                new_val = min(stat_cap, current_val + val)
                                setattr(self, target_stat, new_val)
                                if target_stat != 'drugs':
                                    display_message(f"{tr('msg', 'Used')} {tr('item', item.name)}. {tr('msg', 'Restored')} {val} {target_stat.capitalize()}.")
                                consumed = True

                            elif eff_type == 'reduce':
                                min_cap = 0.0
                                new_val = max(min_cap, current_val - val)
                                setattr(self, target_stat, new_val)
                                if target_stat != 'drugs':
                                    display_message(f"{tr('msg', 'Used')} {tr('item', item.name)}. {tr('msg', 'Reduced')} {target_stat.capitalize()} {tr('msg', 'by')} {val}.")
                                consumed = True
            
            if consumed:
                item.load -= 1
                if old_alcohol < 30.0 <= getattr(self, 'drugs', 0.0):
                    display_message(tr('msg', "You feel dizzy and your vision narrows..."))
                    
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
                            
                            display_message(f"{tr('item', required_item_found.name)} {tr('msg', 'used up.')}")

        if is_auto_drink:
            execute_consume()
            return True
        else:
            return self.start_action(
                f"Using {tr('item', item.name)}",
                duration_mult,
                execute_consume,
                xp_reward=5,
                allow_walk=allow_walk,
                cancel_on_move=cancel_on_move,
                action_sound=action_sound,
                action_sound_subdir='items'
            )

    def toggle_utility_item(self, item, source, index, container_item):
        if not hasattr(item, 'state'):
            return None

        is_on_ground = (source == 'ground') or (source == 'nearby' and getattr(container_item, 'item_type', '') == 'ground')

        # Prevent turning on/off campfires if they are not explicitly placed on the ground
        restricted_toggle_items = ["Campfire"]
        if any(name in item.name for name in restricted_toggle_items):
            if not is_on_ground or not getattr(item, 'is_placed', False):
                display_message(tr('msg', "This item can only be turned on/off when Placed on the ground."))
                return None

        new_name = ""
        if item.state == "on":
            new_name = item.name.replace(" on", " off")
        elif item.state == "off":
            if item.durability is not None and item.durability <= 0:
                display_message(f"{tr('msg', 'Cannot turn on')} {tr('item', item.name)}{tr('msg', ', it´s out of power.')}")
                return None

            # Check Requirements (Lighters/Matches) for ignition
            req_consumed = False
            if hasattr(item, 'require') and item.require:
                raw_req = item.require
                if isinstance(raw_req, dict) and 'type' in raw_req:
                    raw_req = raw_req['type']
                candidates = []
                if isinstance(raw_req, list):
                    candidates = raw_req
                elif isinstance(raw_req, str):
                    if raw_req.startswith('[') and raw_req.endswith(']'):
                        candidates = [s.strip() for s in raw_req[1:-1].split(',')]
                    else:
                        candidates = [raw_req]

                def find_candidate(cand_name):
                    for i, it in enumerate(self.belt):
                        if it and it.name == cand_name:
                            if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                            return it, 'belt', i, None
                    for i, it in enumerate(self.inventory):
                        if it and it.name == cand_name:
                            if hasattr(it, 'load') and it.load is not None and it.load <= 0: continue
                            return it, 'inventory', i, None
                    return None, None, None, None

                required_item_found = None
                required_source = None
                required_index = -1
                required_container = None

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
                    display_message(f"{tr('msg', 'Requires')} {req_str} {tr('msg', 'to turn on.')}")
                    return None
                
                if hasattr(required_item_found, 'load') and required_item_found.load is not None:
                    required_item_found.load -= 1
                    if required_item_found.load <= 0:
                        if required_source == 'belt':
                            self.belt[required_index] = None
                        elif required_source == 'inventory':
                            try: self.inventory.remove(required_item_found)
                            except ValueError: pass
                        elif required_source == 'container' and required_container:
                            try: required_container.inventory.remove(required_item_found)
                            except ValueError: pass
                        display_message(f"{tr('item', required_item_found.name)} {tr('msg', 'used up.')}")
                req_consumed = True

            # Fallback for older code behavior
            if not req_consumed and getattr(item, 'fuel_type', None) == "Matches":
                matches, m_source, m_index, m_container = self.find_fuel("Matches")
                if not matches:
                    display_message(tr('msg', "No matches to light the lantern."))
                    return None

                matches.load -= 1
                if matches.load <= 0:
                    m_inv = self._get_source_inventory(m_source, m_container)
                    if m_inv and m_index < len(m_inv) and m_inv[m_index] == matches:
                        m_inv.pop(m_index)

            new_name = item.name.replace(" off", " on")

        if not new_name:
            return None

        new_item = Item.create_from_name(new_name)
        if not new_item:
            print(f"Error: Could not find item template for '{new_name}'")
            return None

        new_item.durability = item.durability
        new_item.load = item.load
        new_item.rect.center = item.rect.center
        new_item.x = item.x
        new_item.y = item.y
        new_item.is_placed = getattr(item, 'is_placed', False)

        if getattr(item, 'item_type', '') == 'mobile' or 'Mobile' in getattr(item, 'name', ''):
            target_game = getattr(self, 'game', None) or getattr(core.messages, '_game_instance', None)
            if target_game and hasattr(target_game, 'modals'):
                target_game.modals = [m for m in target_game.modals if m.get('type') != 'mobile']

        # Handle ground and nearby sources
        if source == 'ground':
            return new_item
        elif source == 'nearby' and container_item:
            if getattr(container_item, 'item_type', '') == 'ground':
                return new_item
            if index is not None and 0 <= index < len(container_item.inventory):
                container_item.inventory[index] = new_item
                return new_item
        elif source and index is not None:
            source_inventory = self._get_source_inventory(source, container_item)
            if source_inventory and index < len(source_inventory) and source_inventory[index] == item:
                source_inventory[index] = new_item
                return new_item
            else:
                print(f"Error: Could not find item {tr('item', item.name)} in {source} to toggle.")
        elif item in self.belt:
            self.belt[self.belt.index(item)] = new_item
            return new_item
        elif item in self.inventory:
            self.inventory[self.inventory.index(item)] = new_item
            return new_item

        return new_item

    def read_recipe_book(self, item):
        recipes_taught = RecipeManager.get_recipes_by_magazine(item.name)
        
        if not recipes_taught:
            display_message(f"{tr('msg', 'You read')} {tr('item', item.name)}{tr('msg', ', but learn nothing new.')}")
            return

        new_recipes = [r for r in recipes_taught if r.magazine not in self.known_recipes] 
        
        if not new_recipes and item.name in self.known_recipes:
            display_message(f"{tr('msg', 'You already know the recipes in')} {tr('item', item.name)}.")
            return

        def finish_reading():
            if item.name not in self.known_recipes:
                self.known_recipes.append(item.name)
            else:
                display_message(f"{tr('msg', 'You reviewed')} {tr('item', item.name)}.")
            self.progression.add_xp(self, 'intelligence', 10)

        self.start_action(
            f"{tr('msg', 'Reading')} {tr('item', item.name)}",
            3.0,
            finish_reading,
            cancel_on_move=True,
            action_sound='read.ogg',
            action_sound_subdir='items'
        )

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
        return None, None, None, None

    def repair_item(self, game, target_item):
        if self.action_timer > 0:
            display_message(tr('msg', "Busy..."))
            return
        kit, source, index, container = self.find_repair_kit(target_item)
        if not kit:
            display_message(f"{tr('msg', 'No repair kit found for')} {tr('item', target_item.name)}.")
            return
        if target_item.durability >= target_item.max_durability:
            display_message(f"{tr('item', target_item.name)} {tr('msg', 'is already in perfect condition.')}")
            return
        def execute_repair():
            restore_amount = random.randint(kit.min_restore, kit.max_restore)
            old_dur = target_item.durability
            target_item.durability = min(target_item.max_durability, target_item.durability + restore_amount)
            restored = target_item.durability - old_dur
            display_message(f"{tr('msg', 'Repaired')} {tr('item', target_item.name)} {tr('msg', 'by')} {restored:.0f} {tr('msg', 'points using')} {tr('item', kit.name)}.")
            self.progression.add_xp(self, 'maintenance', 20)
            kit.load -= 1
            if kit.load <= 0:
                inv = self._get_source_inventory(source, container)
                if inv:
                    if source == 'belt': self.belt[index] = None
                    else: inv.pop(index)
                display_message(f"{tr('item', kit.name)} {tr('msg', 'used up.')}")

        self.start_action(
            "Repairing",
            2.0,
            execute_repair,
            xp_reward=10,
            cancel_on_move=True,
            action_sound='repair.ogg',
            action_sound_subdir='craft'
        )

    def get_item_context_options(self, item, source, container_item=None):
        options = []
        item_type = getattr(item, 'item_type', '')
        
        if item_type == 'vehicle':
             options.append("Inspect"); return options
        if isinstance(item, Corpse):
            options.append('Open'); return options

        # Check if the item's source is in inventory, belt, gear, or a carried container
        is_on_player = (
            (source in ('inventory', 'belt', 'gear')) 
            or (source == 'container' and container_item and is_container_on_player(container_item, self))
        )

        # Non-player items in Nearby only get Grab and Send to (handled in mouse_context.py)
        if not is_on_player:
            return options
        
        if item_type == 'text' or item_type == 'recipe' or item_type == 'map':
            if item_type == 'recipe':
                options.append('Use')
            elif item_type == 'map':
                options.append('Open')
            else:
                options.append('Read')
            if hasattr(item, 'is_stackable') and item.is_stackable():
                options.append('Drop one')
                if getattr(item, 'load', 0) > 1: options.append('Drop all')
            else: options.append('Drop')
            return options

        if item_type.startswith('consumable') or item_type == 'liquid':
            item_name = getattr(item, 'name', '')
            if item_type == 'consumable_ammo' or 'Ammo' in item_name or 'Shells' in item_name:
                pass
            else:
                options.append('Use')
            
            if getattr(item, 'allow_belt', False):
                options.append('Equip')
                
        elif item_type in ['utility', 'mobile']:
            item_state = getattr(item, 'state', '')
            is_restricted_toggle = any(name in getattr(item, 'name', '') for name in ["Campfire"])
            is_on_ground = (source == 'ground') or (source == 'nearby' and getattr(container_item, 'item_type', '') == 'ground')
            can_toggle = True
            
            if is_restricted_toggle:
                if not is_on_ground or not getattr(item, 'is_placed', False):
                    can_toggle = False
                    
            if can_toggle:
                if item_state == 'on': options.append('Turn off')
                elif item_state == 'off': options.append('Turn on')
                
            if getattr(item, 'fuel_type', None): options.append('Reload')
            if item_type == 'mobile': options.append('Open')
            
            if getattr(item, 'allow_belt', False):
                options.append('Equip')
                
        elif item_type == 'cloth':
            options.append('Open'); options.append('Equip')
        elif item_type in ['weapon_melee', 'weapon_ranged', 'weapon_throw', 'tool']:
            options.append('Equip')
            if item_type == 'weapon_ranged': options.append('Reload')
            if item_type == 'weapon_ranged' and getattr(item, 'load', None) is not None and getattr(item, 'load', 0) > 0: options.append('Get bullets')
        elif item_type == 'container':
            options.append('Open')
            options.append('Equip')
            
        is_liquid = getattr(item, 'liquid', False)
        
        if is_liquid:
            found_names = set()
            from core.entities.item.item_helpers import get_container_available_liquid
            
            def can_accept_liquid(container):
                if not container or not getattr(container, 'allow_liquid', False):
                    return False
                if get_container_available_liquid(container) <= 0:
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
            for c_item in self.clothes.values():
                if can_accept_liquid(c_item):
                    found_names.add(c_item.name)
            
            for name in sorted(found_names):
                options.append(f"Add to {name}")

        if hasattr(item, 'is_stackable') and item.is_stackable() and getattr(item, 'load', None) is not None:
            options.append('Drop one')
            if getattr(item, 'load', 0) > 1: options.append('Drop all')
        else: 
            options.append('Drop')

        return options