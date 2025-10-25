import xml.etree.ElementTree as ET
import os

PROFESSIONS_XML_PATH = 'game/player/data/professions.xml'

def parse_professions_data():
    """Parses the professions XML file and returns a list of profession dictionaries."""
    tree = ET.parse(PROFESSIONS_XML_PATH)
    root = tree.getroot()
    
    professions = []
    for prof_node in root.findall('profession'):
        profession = {
            'name': prof_node.get('name'),
            'description': prof_node.find('description').text,
            'attributes': {},
            'initial_loot': [],
            'visuals': {}
        }
        for attr in prof_node.findall('attributes/*'):
            profession['attributes'][attr.tag] = float(attr.get('value'))
        for item in prof_node.findall('initial_loot/item'):
            profession['initial_loot'].append(item.get('name'))
        sprite_path_relative = prof_node.find('visuals/sprite').get('file')
        xml_dir = os.path.dirname(PROFESSIONS_XML_PATH)
        profession['visuals']['sprite'] = os.path.join(xml_dir, sprite_path_relative)
        professions.append(profession)
    
    return professions

def get_profession_by_name(name):
    professions = parse_professions_data()
    for profession in professions:
        if profession['name'] == name:
            return profession
    return None
