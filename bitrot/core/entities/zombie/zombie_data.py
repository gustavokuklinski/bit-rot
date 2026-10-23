# core/entities/zombie/zombie_data.py

import os
import json
from core.data.config import DATA_PATH, ZOMBIE_SPEED, ZOMBIE_INFECTION_CHANCE
import core.data.config
from core.systems.mod_manager import mod_manager

class ZombieData:
    ZOMBIE_TEMPLATES = []
    ZOMBIE_CLOTHES_POOL = {}
    ALL_ITEM_TEMPLATES = []

    @staticmethod
    def load_templates(folder=None):
        """Loads all zombie templates from JSON files recursively."""
        if folder is None:
            folder = os.path.join(DATA_PATH, 'zombie')

        ZombieData.ZOMBIE_TEMPLATES = []
        ZombieData.ZOMBIE_CLOTHES_POOL.clear()
        ZombieData.ALL_ITEM_TEMPLATES.clear()

        # 1. Populate item templates and clothes pool for random loot and NPC generation
        try:
            from core.entities.item.item_data import ITEM_TEMPLATES, load_item_templates_data
            if not ITEM_TEMPLATES:
                load_item_templates_data()

            for name, tmpl in ITEM_TEMPLATES.items():
                if not tmpl.get('liquid', False):
                    ZombieData.ALL_ITEM_TEMPLATES.append(name)

                if tmpl.get('type') == 'cloth':
                    props = tmpl.get('properties', {})
                    slot = props.get('slot', {}).get('value')
                    if slot:
                        if slot not in ZombieData.ZOMBIE_CLOTHES_POOL:
                            ZombieData.ZOMBIE_CLOTHES_POOL[slot] = []
                        ZombieData.ZOMBIE_CLOTHES_POOL[slot].append(name)
        except Exception as e:
            print(f"[ZombieData] Error initializing clothes/items pool: {e}")

        # 2. Parse Zombie Templates from JSON
        if not os.path.exists(folder):
            print(f"[ZombieData] Warning: Zombie folder not found at '{folder}'")
            return
        
        

        loaded_count = 0
        for root_dir, _, full_paths in mod_manager.vfs_walk(folder):
            for filepath in full_paths:
                if filepath.endswith('.json'):
                    filename = os.path.basename(filepath)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            raw_data = json.load(f)

                        # Support "zombies": { ... } or "zombie": { ... } or direct object
                        raw_zombies = raw_data.get('zombies', {})
                        if not raw_zombies:
                            if 'zombie' in raw_data:
                                raw_zombies = {os.path.splitext(filename)[0]: raw_data['zombie']}
                            elif 'stats' in raw_data or 'name' in raw_data:
                                raw_zombies = {os.path.splitext(filename)[0]: raw_data}

                        for z_type, z_info in raw_zombies.items():
                            spawn_weight = int(z_info.get('spawn_weight', 10))
                            name = z_info.get('name', 'Zombie')
                            sex = z_info.get('sex', 'Random')

                            # Parse Stats
                            stats = z_info.get('stats', {})
                            health_node = stats.get('health', {})
                            min_health = int(health_node.get('min', 20))
                            max_health = int(health_node.get('max', 40))

                            speed_node = stats.get('speed', {})
                            min_speed = float(speed_node.get('min', 1.0)) * ZOMBIE_SPEED
                            max_speed = float(speed_node.get('max', 1.0)) * ZOMBIE_SPEED

                            attack_node = stats.get('attack', {})
                            min_attack = int(attack_node.get('min', 1))
                            max_attack = int(attack_node.get('max', 5))

                            infection_node = stats.get('infection', {})
                            min_infection = float(infection_node.get('min', 0)) * ZOMBIE_INFECTION_CHANCE
                            max_infection = float(infection_node.get('max', 1)) * ZOMBIE_INFECTION_CHANCE

                            # Parse XP
                            xp_node = z_info.get('xp', {})
                            min_xp = float(xp_node.get('min', 1.0))
                            max_xp = float(xp_node.get('max', 5.0))

                            # Parse Visuals / Sprites
                            sprites = {}
                            visuals = z_info.get('visuals', {})
                            if isinstance(visuals, dict):
                                sprites = dict(visuals)
                            if 'center' not in sprites and 'sprite' in z_info:
                                sprite_file = z_info['sprite']
                                sprites = {'center': sprite_file, 'left': sprite_file, 'right': sprite_file}

                            # Parse Clothes
                            predefined_clothes = {}
                            clothes_slots = []
                            clothes_raw = z_info.get('clothes', {})
                            if isinstance(clothes_raw, dict):
                                for slot_name, cloth_name in clothes_raw.items():
                                    if cloth_name:
                                        predefined_clothes[slot_name] = cloth_name
                                        clothes_slots.append(slot_name)
                            elif isinstance(clothes_raw, list):
                                for c_item in clothes_raw:
                                    if isinstance(c_item, dict):
                                        slot = c_item.get('slot')
                                        c_name = c_item.get('name')
                                        if slot and c_name:
                                            predefined_clothes[slot] = c_name
                                            clothes_slots.append(slot)

                            # Parse Loot Table
                            loot = []
                            for item_entry in z_info.get('loot', []):
                                iname = item_entry.get('item') or item_entry.get('name')
                                chance = float(item_entry.get('chance', 1.0))
                                if iname:
                                    loot.append({
                                        'item': iname,
                                        'chance': chance
                                    })

                            # Parse Sounds
                            sound_data = z_info.get('sound') or z_info.get('sounds') or {}
                            sounds = dict(sound_data)

                            template = {
                                'type': z_type.lower(),
                                'spawn_weight': spawn_weight,
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
                                'sounds': sounds
                            }

                            ZombieData.ZOMBIE_TEMPLATES.append(template)
                            loaded_count += 1

                    except Exception as e:
                        print(f"[ZombieData] Error loading zombie JSON '{filepath}': {e}")

        print(f"[ZombieData] Successfully loaded {loaded_count} zombie templates from '{folder}'.")