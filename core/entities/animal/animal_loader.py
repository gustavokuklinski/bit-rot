# core/entities/animal/animal_loader.py
import os
import xml.etree.ElementTree as ET

class AnimalLoader:
    definitions = {}
    DATA_PATH = "game/lib/data/animals"

    @staticmethod
    def load_animals():
        if AnimalLoader.definitions:
            return

        loaded_from_files = False

        # 1. Try to load from the specified directory
        if os.path.exists(AnimalLoader.DATA_PATH):
            for filename in os.listdir(AnimalLoader.DATA_PATH):
                if filename.endswith(".xml"):
                    full_path = os.path.join(AnimalLoader.DATA_PATH, filename)
                    try:
                        tree = ET.parse(full_path)
                        root = tree.getroot()
                        AnimalLoader._parse_root(root)
                        loaded_from_files = True
                        print(f"Loaded animal data from: {full_path}")
                    except Exception as e:
                        print(f"Error loading animal XML {filename}: {e}")


    @staticmethod
    def _parse_root(root):
        # Handle both a single <animal> root or a container like <animals>
        nodes = []
        if root.tag == 'animal':
            nodes.append(root)
        else:
            nodes.extend(root.findall('animal'))

        for animal_node in nodes:
            try:
                name = animal_node.get('name')
                spawn_weight = int(animal_node.get('spawn_weight', '10'))
                spawn_layer_raw = animal_node.get('spawn_layer', '[1]')
                
                spawn_layers = []
                try:
                    # Elegantly strip brackets and split into a list of ints
                    clean_str = spawn_layer_raw.replace('[', '').replace(']', '')
                    if clean_str.strip():
                        spawn_layers = [int(x.strip()) for x in clean_str.split(',')]
                    else:
                        spawn_layers = [1]
                except ValueError:
                    spawn_layers = [1] # Fallback if malformed

                stats_node = animal_node.find('stats')
                
                stats = {
                    'health': {
                        'min': int(stats_node.find('health').get('min')), 
                        'max': int(stats_node.find('health').get('max'))
                    },
                    'speed': {
                        'min': float(stats_node.find('speed').get('min')), 
                        'max': float(stats_node.find('speed').get('max'))
                    },
                    'attack': {
                        'min': int(stats_node.find('attack').get('min')), 
                        'max': int(stats_node.find('attack').get('max'))
                    },
                    'infection': {
                        'min': int(stats_node.find('infection').get('min')), 
                        'max': int(stats_node.find('infection').get('max'))
                    }
                }
                
                visuals_node = animal_node.find('visuals')
                sprite_file = visuals_node.find('sprite').get('file')
                
                loot = []
                loot_node = animal_node.find('loot')
                if loot_node is not None:
                    for item in loot_node.findall('item'):
                        chance_val = float(item.get('chance'))
                        # Normalize chance to 0-100 scale if it's 0-1
                        if chance_val <= 1.0: chance_val *= 100
                        
                        loot.append({
                            'item': item.get('item'),
                            'chance': chance_val
                        })

                cap_node = animal_node.find('capacity')
                capacity = int(cap_node.get('value', 0)) if cap_node is not None else 0

                sounds = {}
                sound_node = animal_node.find('sound')
                if sound_node is not None:
                    for sound_type in ['hit', 'wander', 'dead', 'attack', 'steps']:
                        node = sound_node.find(sound_type)
                        if node is not None:
                            sounds[sound_type] = node.get('src')

                AnimalLoader.definitions[name] = {
                    'name': name,
                    'type': animal_node.get('type'),
                    'spawn_weight': spawn_weight,  # <--- NEW
                    'spawn_layers': spawn_layers,
                    'stats': stats,
                    'sprite': sprite_file,
                    'loot': loot,
                    'capacity': capacity,
                    'sounds': sounds  # --- NEW: Save sounds to definition ---
                }

            except Exception as e:
                print(f"Error parsing animal node {animal_node.get('name', 'Unknown')}: {e}")