# core/entities/npc/npc_data.py

import os
import json
import random
from core.entities.item.item import Item
from core.entities.zombie.zombie_data import ZombieData
from core.data.config import DATA_PATH

class NPCData:
    NPC_TEMPLATES = [] 
    
    @staticmethod
    def load_templates():
        npc_folder = os.path.join(DATA_PATH, 'npc')
        NPCData.NPC_TEMPLATES = []

        if not os.path.exists(npc_folder):
            print(f"[NPCData] Warning: Folder not found at {npc_folder}")
            return

        from core.systems.mod_manager import mod_manager

        loaded_count = 0
        for root_dir, _, full_paths in mod_manager.vfs_walk(npc_folder):
            for filepath in full_paths:
                if filepath.endswith('.json'):
                    filename = os.path.basename(filepath)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            raw_data = json.load(f)

                        # Support "npcs": { ... } or "npc": { ... } or direct object
                        raw_npcs = raw_data.get('npcs', {})
                        if not raw_npcs:
                            if 'npc' in raw_data:
                                raw_npcs = {os.path.splitext(filename)[0]: raw_data['npc']}
                            elif 'stats' in raw_data or 'name' in raw_data:
                                raw_npcs = {os.path.splitext(filename)[0]: raw_data}

                        for npc_type, n_info in raw_npcs.items():
                            spawn_weight = int(n_info.get('spawn_weight', 10))
                            is_friendly = bool(n_info.get('is_friendly', False))
                            is_static = bool(n_info.get('is_static', False))

                            try:
                                mult_val = n_info.get('spawn_zombies_multiplier')
                                if mult_val is not None:
                                    spawn_zombies_multiplier = float(mult_val)
                                else:
                                    spawn_zombies_multiplier = float(n_info.get('spawn_zombies', 0.0))
                            except (ValueError, TypeError):
                                spawn_zombies_multiplier = 0.0

                            name = n_info.get('name', 'Survivor')
                            sex = n_info.get('sex', 'Random')

                            # Parse Stats
                            stats = n_info.get('stats', {})
                            health_node = stats.get('health', {})
                            min_health = int(health_node.get('min', 100))
                            max_health = int(health_node.get('max', 100))

                            speed_node = stats.get('speed', {})
                            min_speed = float(speed_node.get('min', 1.0))
                            max_speed = float(speed_node.get('max', 1.0))

                            attack_node = stats.get('attack', {})
                            min_attack = int(attack_node.get('min', 1))
                            max_attack = int(attack_node.get('max', 15))

                            infection_node = stats.get('infection', {})
                            min_infection = int(infection_node.get('min', 0))
                            max_infection = int(infection_node.get('max', 0))

                            # Parse XP
                            xp_node = n_info.get('xp', {})
                            min_xp = float(xp_node.get('min', 10.0))
                            max_xp = float(xp_node.get('max', 20.0))

                            # Parse Visuals / Sprites
                            sprites = {}
                            visuals = n_info.get('visuals', {})
                            if isinstance(visuals, dict):
                                sprites = dict(visuals)
                            if 'center' not in sprites and 'sprite' in n_info:
                                sprite_file = n_info['sprite']
                                sprites = {'center': sprite_file, 'left': sprite_file, 'right': sprite_file}

                            # Parse Clothes
                            predefined_clothes = {}
                            clothes_slots = []
                            clothes_raw = n_info.get('clothes', {})
                            if isinstance(clothes_raw, dict):
                                for slot_name, cloth_name in clothes_raw.items():
                                    clothes_slots.append(slot_name)
                                    if cloth_name:
                                        predefined_clothes[slot_name] = cloth_name
                            elif isinstance(clothes_raw, list):
                                for c_item in clothes_raw:
                                    if isinstance(c_item, dict):
                                        slot = c_item.get('slot')
                                        c_name = c_item.get('name')
                                        if slot:
                                            clothes_slots.append(slot)
                                            if c_name:
                                                predefined_clothes[slot] = c_name

                            # Parse Loot Table
                            loot = []
                            for item_entry in n_info.get('loot', []):
                                iname = item_entry.get('item') or item_entry.get('name')
                                chance = float(item_entry.get('chance', 1.0))
                                if iname:
                                    loot.append({
                                        'item': iname,
                                        'chance': chance
                                    })

                            # Parse Trade Configuration
                            trade_node = n_info.get('trade')
                            trade_config = None
                            if trade_node:
                                try:
                                    limit = int(trade_node.get('limit', 15))
                                except (ValueError, TypeError):
                                    limit = 15

                                allowed_types = trade_node.get('types') or trade_node.get('allowed_types') or []
                                allowed_items = trade_node.get('items') or trade_node.get('allowed_items') or []

                                trade_config = {
                                    'limit': limit,
                                    'types': list(allowed_types),
                                    'items': list(allowed_items)
                                }

                            # Parse Sounds
                            sound_data = n_info.get('sound') or n_info.get('sounds') or {}
                            sounds = dict(sound_data)

                            template = {
                                'type': npc_type.lower(),
                                'spawn_weight': spawn_weight,
                                'is_friendly': is_friendly,
                                'is_static': is_static,
                                'spawn_zombies_multiplier': spawn_zombies_multiplier,
                                'spawn_zombies': spawn_zombies_multiplier,
                                'name': name,
                                'sex': sex,
                                'min_health': min_health,
                                'max_health': max_health,
                                'health': max_health,
                                'min_speed': min_speed,
                                'max_speed': max_speed,
                                'speed': max_speed,
                                'min_attack': min_attack,
                                'max_attack': max_attack,
                                'min_infection': min_infection,
                                'max_infection': max_infection,
                                'min_xp': min_xp,
                                'max_xp': max_xp,
                                'sprites': sprites,
                                'clothes_slots': clothes_slots,
                                'predefined_clothes': predefined_clothes,
                                'loot': loot,
                                'trade_config': trade_config,
                                'sounds': sounds
                            }

                            NPCData.NPC_TEMPLATES.append(template)
                            loaded_count += 1

                    except Exception as e:
                        print(f"[NPCData] Error loading NPC JSON '{filepath}': {e}")

        print(f"[NPCData] Successfully loaded {loaded_count} NPC templates from '{npc_folder}'.")

    def _assign_random_clothes(self):
        self.clothes = {}
        slots = ['hair', 'head', 'legs', 'feet', 'body', 'util', 'arms', 'hands', 'facial']
        for slot in slots:
            if slot == 'head' and random.random() < 0.3: continue 
            available = ZombieData.ZOMBIE_CLOTHES_POOL.get(slot, [])
            if available:
                choice = random.choice(available)
                if isinstance(choice, str):
                    self.clothes[slot] = Item.create_from_name(choice)
                elif isinstance(choice, dict) and 'name' in choice:
                    self.clothes[slot] = Item.create_from_name(choice['name'])