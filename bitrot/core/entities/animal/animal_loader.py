# core/entities/animal/animal_loader.py

import os
import json
import random
from core.data.config import DATA_PATH, BASE_DIR

class AnimalLoader:
    definitions = {}
    animal_folder = os.path.join(DATA_PATH, 'animals')

    @classmethod
    def get_animal_folder(cls):
        candidates = [
            cls.animal_folder,
            os.path.join(BASE_DIR, 'data.rot', 'lib', 'data', 'animals'),
            os.path.abspath('data.rot/lib/data/animals')
        ]
        for folder in candidates:
            if os.path.exists(folder):
                return folder
        return cls.animal_folder

    @classmethod
    def load_animals(cls, force_reload=False):
        if cls.definitions and not force_reload:
            return

        cls.definitions.clear()
        target_folder = cls.get_animal_folder()

        if not os.path.exists(target_folder):
            print(f"[AnimalLoader] Warning: Animal folder not found at '{target_folder}'")
            return

        from core.systems.mod_manager import mod_manager

        loaded_files = 0
        for root_dir, _, full_paths in mod_manager.vfs_walk(target_folder):
            for full_path in full_paths:
                if full_path.endswith(".json"):
                    filename = os.path.basename(full_path)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            raw_data = json.load(f)

                        # Support "animals": { ... } or "animal": { ... } or direct object
                        raw_animals = raw_data.get('animals', {})
                        if not raw_animals:
                            if 'animal' in raw_data:
                                raw_animals = {os.path.splitext(filename)[0]: raw_data['animal']}
                            elif 'stats' in raw_data or 'name' in raw_data:
                                raw_animals = {os.path.splitext(filename)[0]: raw_data}

                        fallback_name = os.path.splitext(filename)[0].capitalize()

                        for animal_id, a_info in raw_animals.items():
                            name = a_info.get('name') or fallback_name
                            animal_type = a_info.get('type', 'animal')
                            attack_player = bool(a_info.get('attack_player', False))

                            try:
                                mult_val = a_info.get('spawn_zombies_multiplier')
                                if mult_val is not None:
                                    spawn_zombies_multiplier = float(mult_val)
                                else:
                                    spawn_zombies_multiplier = float(a_info.get('spawn_zombies', 0.0))
                            except (ValueError, TypeError):
                                spawn_zombies_multiplier = 0.0

                            try:
                                spawn_weight = max(1, int(float(a_info.get('spawn_weight', 10))))
                            except (ValueError, TypeError):
                                spawn_weight = 10

                            # Parse spawn_layer (supports ["L1", "L2", "L3"], [1, 2, 3], or comma-separated string)
                            raw_layers = a_info.get('spawn_layer') or a_info.get('spawn_layers') or a_info.get('layer', [1, 2, 3])
                            spawn_layers = []

                            if isinstance(raw_layers, (list, tuple)):
                                for l_item in raw_layers:
                                    clean_num = str(l_item).upper().replace('L', '').strip()
                                    if clean_num.isdigit():
                                        spawn_layers.append(int(clean_num))
                            elif isinstance(raw_layers, str):
                                clean_str = raw_layers.replace('[', '').replace(']', '').replace('"', '').replace("'", '').strip()
                                for part in clean_str.split(','):
                                    clean_num = part.upper().replace('L', '').strip()
                                    if clean_num.isdigit():
                                        spawn_layers.append(int(clean_num))
                            elif isinstance(raw_layers, int):
                                spawn_layers.append(raw_layers)

                            if not spawn_layers:
                                spawn_layers = [1, 2, 3]

                            # Parse Stats
                            stats_node = a_info.get('stats', {})
                            stats = {
                                'health': cls._parse_stat_range(stats_node.get('health'), default_min=10, default_max=20),
                                'speed': cls._parse_stat_range(stats_node.get('speed'), default_min=0.5, default_max=0.8, is_float=True),
                                'attack': cls._parse_stat_range(stats_node.get('attack'), default_min=1, default_max=5),
                                'infection': cls._parse_stat_range(stats_node.get('infection'), default_min=0, default_max=0)
                            }

                            # Parse Visuals / Sprites
                            visuals = a_info.get('visuals', {})
                            sprites = {}
                            if isinstance(visuals, dict):
                                sprites = dict(visuals)

                            sprite_file = sprites.get('center') or a_info.get('sprite') or f"{name.lower()}.png"
                            sprite_file = os.path.basename(sprite_file)
                            if 'center' not in sprites:
                                sprites = {'center': sprite_file, 'left': sprite_file, 'right': sprite_file}

                            # Parse Loot
                            loot = []
                            for item_entry in a_info.get('loot', []):
                                item_name = item_entry.get('item') or item_entry.get('name')
                                if not item_name:
                                    continue
                                try:
                                    chance_val = float(item_entry.get('chance', 1.0))
                                    if chance_val <= 1.0:
                                        chance_val *= 100.0
                                except (ValueError, TypeError):
                                    chance_val = 50.0
                                loot.append({'item': item_name, 'chance': chance_val})

                            capacity = int(float(a_info.get('capacity', 0)))

                            # Parse Sounds
                            sound_data = a_info.get('sound') or a_info.get('sounds') or {}
                            sounds = dict(sound_data)

                            cls.definitions[name] = {
                                'name': name,
                                'type': animal_type,
                                'attack_player': attack_player,
                                'spawn_weight': spawn_weight,
                                'spawn_layers': spawn_layers,
                                'spawn_zombies_multiplier': spawn_zombies_multiplier,
                                'stats': stats,
                                'sprite': sprite_file,
                                'sprites': sprites,
                                'loot': loot,
                                'capacity': capacity,
                                'sounds': sounds
                            }

                        loaded_files += 1
                    except Exception as e:
                        print(f"[AnimalLoader] Error loading {filename}: {e}")

        print(f"[AnimalLoader] Successfully loaded {len(cls.definitions)} species from {loaded_files} JSON files: {list(cls.definitions.keys())}")

    @staticmethod
    def _parse_stat_range(stat_node, default_min=0, default_max=0, is_float=False):
        converter = float if is_float else lambda v: int(float(v))
        if stat_node is None:
            return {'min': default_min, 'max': default_max}

        if isinstance(stat_node, (int, float)):
            v = converter(stat_node)
            return {'min': v, 'max': v}

        if isinstance(stat_node, dict):
            val_min = stat_node.get('min')
            val_max = stat_node.get('max')
            val_single = stat_node.get('value')
            try:
                if val_min is not None and val_max is not None:
                    return {'min': converter(val_min), 'max': converter(val_max)}
                elif val_single is not None:
                    parsed = converter(val_single)
                    return {'min': parsed, 'max': parsed}
                elif val_max is not None:
                    parsed = converter(val_max)
                    return {'min': parsed, 'max': parsed}
                elif val_min is not None:
                    parsed = converter(val_min)
                    return {'min': parsed, 'max': parsed}
            except (ValueError, TypeError):
                pass

        return {'min': default_min, 'max': default_max}

    @classmethod
    def get_definition(cls, animal_type=None, layer=None):
        if not cls.definitions:
            cls.load_animals()

        if not animal_type:
            return cls.get_random_definition(layer=layer)

        target_lower = str(animal_type).strip().lower()
        for k, v in cls.definitions.items():
            if k.lower().strip() == target_lower:
                return v

        return cls.get_random_definition(layer=layer)

    @classmethod
    def get_random_definition(cls, layer=None):
        if not cls.definitions:
            cls.load_animals()

        if not cls.definitions:
            return None

        candidates = []
        weights = []

        for name, data in cls.definitions.items():
            if layer is not None:
                allowed_layers = data.get('spawn_layers', [1, 2, 3])
                if layer not in allowed_layers:
                    continue
            weight = max(1, int(data.get('spawn_weight', 10)))
            candidates.append(data)
            weights.append(weight)

        if candidates:
            return random.choices(candidates, weights=weights, k=1)[0]

        if layer is not None:
            return None

        all_defs = list(cls.definitions.values())
        return random.choice(all_defs) if all_defs else None

    @classmethod
    def get_random_animal_type(cls, layer=None):
        defn = cls.get_random_definition(layer=layer)
        if defn:
            return defn['name']
        return None