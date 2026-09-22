# core/entities/animal/animal_loader.py
import os
import random
import xml.etree.ElementTree as ET
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
            print(f"[AnimalLoader] Warning: Animal folder not found at {target_folder}")
            return

        loaded_files = 0
        for filename in os.listdir(target_folder):
            if filename.endswith(".xml"):
                full_path = os.path.join(target_folder, filename)
                try:
                    tree = ET.parse(full_path)
                    root = tree.getroot()
                    cls._parse_root(root, filename)
                    loaded_files += 1
                except Exception as e:
                    print(f"[AnimalLoader] Error loading {filename}: {e}")

        print(f"[AnimalLoader] Successfully loaded {len(cls.definitions)} species from {loaded_files} XML files: {list(cls.definitions.keys())}")

    @classmethod
    def _parse_root(cls, root, filename):
        nodes = []
        if root.tag == 'animal':
            nodes.append(root)
        else:
            nodes.extend(root.findall('.//animal'))

        fallback_name = os.path.splitext(filename)[0].capitalize()

        for animal_node in nodes:
            try:
                name = animal_node.get('name') or animal_node.get('id') or fallback_name
                animal_type = animal_node.get('type', 'animal')
                attack_player = str(animal_node.get('attack_player', 'false')).strip().lower() == 'true'
                
                try:
                    spawn_zombies = int(float(animal_node.get('spawn_zombies', '0')))
                except (ValueError, TypeError):
                    spawn_zombies = 0

                try:
                    spawn_weight = max(1, int(float(animal_node.get('spawn_weight', '10'))))
                except (ValueError, TypeError):
                    spawn_weight = 10

                # Robust layer parser: accepts [1, 2], [L1, L2], [L1], 1, L2, etc.
                spawn_layer_raw = animal_node.get('spawn_layer') or animal_node.get('spawn_layers') or animal_node.get('layer') or '[1, 2]'
                spawn_layers = []
                try:
                    clean_str = str(spawn_layer_raw).replace('[', '').replace(']', '').replace('"', '').replace("'", '').strip()
                    if clean_str:
                        for part in clean_str.split(','):
                            cleaned_num = part.strip().upper().replace('L', '')
                            if cleaned_num.isdigit():
                                spawn_layers.append(int(cleaned_num))
                except Exception:
                    spawn_layers = [1, 2]

                if not spawn_layers:
                    spawn_layers = [1, 2]

                stats_node = animal_node.find('stats')
                stats = {
                    'health': cls._parse_stat_range(stats_node, 'health', default_min=10, default_max=20),
                    'speed': cls._parse_stat_range(stats_node, 'speed', default_min=0.5, default_max=0.8, is_float=True),
                    'attack': cls._parse_stat_range(stats_node, 'attack', default_min=1, default_max=5),
                    'infection': cls._parse_stat_range(stats_node, 'infection', default_min=0, default_max=0)
                }

                sprite_file = None
                visuals_node = animal_node.find('visuals')
                if visuals_node is not None:
                    spr = visuals_node.find('sprite')
                    if spr is not None:
                        sprite_file = spr.get('file') or spr.get('src')

                if not sprite_file:
                    spr = animal_node.find('sprite')
                    if spr is not None:
                        sprite_file = spr.get('file') or spr.get('src') or spr.text

                if not sprite_file:
                    sprite_file = f"{name.lower()}.png"

                sprite_file = os.path.basename(sprite_file)

                loot = []
                loot_node = animal_node.find('loot')
                if loot_node is not None:
                    for item in loot_node.findall('item'):
                        item_name = item.get('item') or item.get('name')
                        if not item_name:
                            continue
                        try:
                            chance_val = float(item.get('chance', 1.0))
                            if chance_val <= 1.0: chance_val *= 100
                        except (ValueError, TypeError):
                            chance_val = 50.0
                        loot.append({'item': item_name, 'chance': chance_val})

                cap_node = animal_node.find('capacity')
                capacity = int(float(cap_node.get('value', 0))) if cap_node is not None else 0

                sounds = {}
                sound_node = animal_node.find('sound') or animal_node.find('sounds')
                if sound_node is not None:
                    for sound_type in ['hit', 'wander', 'dead', 'attack', 'steps']:
                        node = sound_node.find(sound_type)
                        if node is not None:
                            sounds[sound_type] = node.get('src') or node.get('file')

                cls.definitions[name] = {
                    'name': name,
                    'type': animal_type,
                    'attack_player': attack_player,
                    'spawn_weight': spawn_weight,
                    'spawn_layers': spawn_layers,
                    'spawn_zombies': spawn_zombies,
                    'stats': stats,
                    'sprite': sprite_file,
                    'loot': loot,
                    'capacity': capacity,
                    'sounds': sounds
                }

            except Exception as e:
                print(f"[AnimalLoader] Error parsing animal node '{animal_node.get('name', fallback_name)}' in {filename}: {e}")

    @staticmethod
    def _parse_stat_range(stats_node, tag, default_min=0, default_max=0, is_float=False):
        converter = float if is_float else lambda v: int(float(v))
        if stats_node is None:
            return {'min': default_min, 'max': default_max}

        node = stats_node.find(tag)
        if node is None:
            return {'min': default_min, 'max': default_max}

        val_min = node.get('min')
        val_max = node.get('max')
        val_single = node.get('value')

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
                allowed_layers = data.get('spawn_layers', [1, 2])
                if layer not in allowed_layers:
                    continue
            weight = max(1, int(data.get('spawn_weight', 10)))
            candidates.append(data)
            weights.append(weight)

        if candidates:
            return random.choices(candidates, weights=weights, k=1)[0]

        # Do NOT pick animals from forbidden layers
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