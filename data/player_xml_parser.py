import xml.etree.ElementTree as ET
from data.config import DATA_PATH, SPRITE_PATH

PLAYER_XML_PATH = DATA_PATH + 'player/player.xml'

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
    data['visuals']['sprite'] = SPRITE_PATH + 'player/' + sprite_path_relative
    
    return data