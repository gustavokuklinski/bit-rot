import xml.etree.ElementTree as ET
import random
from core.data.config import DATA_PATH, SPRITE_PATH

PLAYER_XML_PATH = DATA_PATH + 'player/player.xml'

def parse_player_data():
    """
    Parses the player.xml file and returns a dictionary of attributes
    and a list of trait names.
    """
    tree = ET.parse(PLAYER_XML_PATH)
    root = tree.getroot()
    
    data = {
        'name': root.find('name').get('value'),
        'sex': root.find('sex').get('value'),
        'profession': root.find('profession').get('value'),
        'stats': {},
        'attributes': {},
        'body_parts': {},
        'initial_loot': [],
        'visuals': {},
        'known_recipes': []
    }
    
    # Parse stats
    for stat in root.findall('stats/*'):
        data['stats'][stat.tag] = float(stat.get('value'))
        
    # Parse attributes (NEW)
    for attr in root.findall('attributes/*'):
        data['attributes'][attr.tag] = float(attr.get('value'))

    # Parse body parts (NEW)
    body_node = root.find('body')
    if body_node is not None:
        for part in body_node:
             data['body_parts'][part.tag] = {
                 'value': float(part.get('value', 100.0)),
                 'defence': float(part.get('defence', 0.0))
             }
        
    # Parse initial loot
    if root.find('initial_loot') is not None:       
        for item in root.findall('initial_loot/item'):
            name = item.get('name')
            try:
                chance = float(item.get('chance', 1.0))
            except (ValueError, TypeError):
                chance = 1.0
                
            if name and random.random() < chance:
                data['initial_loot'].append(name)
    
    # Parse visuals
    visuals_node = root.find('visuals')
    if visuals_node is not None:
        if visuals_node.find('sprite') is not None:
            sprite_path_relative = visuals_node.find('sprite').get('file')
            data['visuals']['sprite'] = 'player/' + sprite_path_relative
        # Handle multiple sprites (left, right, center) if present
        for s in visuals_node.findall('sprite'):
            sid = s.get('id')
            if sid:
                data['visuals'][sid] = s.get('file')

    trait_names = []
    traits_node = root.find('traits')
    if traits_node is not None:
        for trait in traits_node:
            trait_names.append(trait.tag)
    
    recipes_node = root.find('recipes')
    if recipes_node is not None:
        for recipe in recipes_node.findall('recipe'):
            magazine = recipe.get('magazine')
            if magazine:
                data['known_recipes'].append(magazine)
                
    return data, trait_names