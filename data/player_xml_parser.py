import xml.etree.ElementTree as ET
import os

PLAYER_XML_PATH = 'game/player/data/player.xml'

def parse_player_data():
    """Parses the player XML file and returns a dictionary of attributes."""
    tree = ET.parse(PLAYER_XML_PATH)
    root = tree.getroot()
    
    data = {
        'name': root.find('name').get('value'),
        'stats': {},
        'skills': {},
        'attributes': {},
        'initial_loot': [],
        'visuals': {}
    }
    
    for stat in root.findall('stats/*'):
        data['stats'][stat.tag] = float(stat.get('value'))
        
    for skill in root.findall('skills/*'):
        data['skills'][skill.tag] = int(skill.get('value'))

    for attr in root.findall('attributes/*'):
        data['attributes'][attr.tag] = float(attr.get('value'))
        
    for item in root.findall('initial_loot/inventory'):
        data['initial_loot'].append(item.get('item'))
        
    sprite_path_relative = root.find('visuals/sprite').get('file')
    xml_dir = os.path.dirname(PLAYER_XML_PATH)
    data['visuals']['sprite'] = os.path.join(xml_dir, sprite_path_relative)
    
    return data