import xml.etree.ElementTree as ET
from data.config import DATA_PATH, SPRITE_PATH

PLAYER_XML_PATH = DATA_PATH + 'player/player.xml'

def parse_player_data():
    """
    Parses the player.xml file and returns a dictionary of attributes
    and a list of trait names.
    """
    # Use the provided player.xml file
    tree = ET.parse(PLAYER_XML_PATH)
    root = tree.getroot()
    
    data = {
        'name': root.find('name').get('value'),
        'sex': root.find('sex').get('value'),
        'profession': root.find('profession').get('value'),
        'stats': {},
        'attributes': {},
        'initial_loot': [],
        'visuals': {}
    }
    
    # Parse stats
    for stat in root.findall('stats/*'):
        data['stats'][stat.tag] = float(stat.get('value'))
        
    # Parse attributes
    for attr in root.findall('attributes/*'):
        data['attributes'][attr.tag] = float(attr.get('value'))
        
    # Parse initial loot
    for item in root.findall('initial_loot/inventory'): # Corrected path if items are under 'inventory' tag
        data['initial_loot'].append(item.get('item'))
    
    # Parse visuals
    sprite_path_relative = root.find('visuals/sprite').get('file')
    # Assumes player.png is in 'game/sprites/player/'
    data['visuals']['sprite'] = 'player/' + sprite_path_relative
    
    # --- MODIFICATION: Parse the trait names ---
    trait_names = []
    for trait in root.findall('traits/*'):
        trait_names.append(trait.tag)
    
    # Return both the data dictionary and the list of trait names
    return data, trait_names