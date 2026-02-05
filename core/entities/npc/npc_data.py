import os
import random
import xml.etree.ElementTree as ET
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
            print(f"NPC Warning: Folder not found at {npc_folder}")
            return
        for filename in os.listdir(npc_folder):
            if filename.endswith('.xml'):
                filepath = os.path.join(npc_folder, filename)
                try:
                    tree = ET.parse(filepath)
                    root = tree.getroot()
                    if root.tag == 'zombie':
                        template = {}
                        name_node = root.find('name')
                        template['name'] = name_node.get('value') if name_node is not None else 'Survivor'
                        stats_node = root.find('stats')
                        if stats_node is not None:
                            health_node = stats_node.find('health')
                            template['min_health'] = int(health_node.get('min', 100))
                            template['max_health'] = int(health_node.get('max', 100))
                            template['health'] = template['max_health'] 
                            speed_node = stats_node.find('speed')
                            template['min_speed'] = float(speed_node.get('min', 1.0))
                            template['max_speed'] = float(speed_node.get('max', 1.0))
                            template['speed'] = template['max_speed']
                            attack_node = stats_node.find('attack')
                            template['min_attack'] = int(attack_node.get('min', 5))
                            template['max_attack'] = int(attack_node.get('max', 10))
                            infection_node = stats_node.find('infection')
                            template['min_infection'] = int(infection_node.get('min', 0))
                            template['max_infection'] = int(infection_node.get('max', 0))
                        xp_node = root.find('xp')
                        if xp_node is not None:
                            template['min_xp'] = float(xp_node.get('min', 10))
                            template['max_xp'] = float(xp_node.get('max', 20))
                        else:
                            template['min_xp'], template['max_xp'] = 10, 20
                        visuals_node = root.find('visuals')
                        template['sprites'] = {}
                        if visuals_node is not None:
                            for sprite_node in visuals_node.findall('sprite'):
                                s_id = sprite_node.get('id')
                                s_file = sprite_node.get('file')
                                if s_id and s_file:
                                    template['sprites'][s_id] = s_file
                        clothes_node = root.find('clothes')
                        template['clothes_slots'] = []
                        if clothes_node is not None:
                            for slot_node in clothes_node:
                                template['clothes_slots'].append(slot_node.tag)
                        sound_node = root.find('sound')
                        template['sounds'] = {}
                        if sound_node is not None:
                            for sound_type in ['hit', 'wander', 'dead', 'attack', 'steps']:
                                node = sound_node.find(sound_type)
                                if node is not None:
                                    template['sounds'][sound_type] = node.get('src')
                        template['sex'] = root.find('sex').get('value') if root.find('sex') is not None else 'Random'
                        template['loot'] = [] 
                        NPCData.NPC_TEMPLATES.append(template)
                except Exception as e:
                    print(f"NPC Error: Could not load {filename}: {e}")

    def _assign_random_clothes(self):
        self.clothes = {}
        slots = ['hair', 'head','legs', 'feet', 'body','util','arms', 'hands', 'facial']
        for slot in slots:
            if slot == 'head' and random.random() < 0.3: continue 
            available = ZombieData.ZOMBIE_CLOTHES_POOL.get(slot, [])
            if available:
                choice = random.choice(available)
                if isinstance(choice, str):
                    self.clothes[slot] = Item.create_from_name(choice)
                elif isinstance(choice, dict) and 'name' in choice:
                    self.clothes[slot] = Item.create_from_name(choice['name'])