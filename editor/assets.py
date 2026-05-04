import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import TILE_SIZE, ICON_SIZE

def create_placeholder(name, size=TILE_SIZE):
    """Generates a dynamic placeholder image for items without sprite files."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((80, 60, 70, 220)) # Distinct reddish-grey tint
    pygame.draw.rect(surf, (200, 150, 160), surf.get_rect(), 2)
    
    # Draw up to 2 initials
    font = pygame.font.Font(None, max(18, int(size * 0.6)))
    initials = name[:2].upper() if name else "?"
    text = font.render(initials, True, (255, 220, 220))
    text_rect = text.get_rect(center=(size//2, size//2))
    surf.blit(text, text_rect)
    
    return surf

def load_sprite_images(path):
    """Loads all sprite images from the given path and scales them."""
    sprites = {}
    if not os.path.exists(path):
        return sprites
             
    for filename in os.listdir(path):
        if filename.endswith(".png"):
            name = os.path.splitext(filename)[0]
            image = pygame.image.load(os.path.join(path, filename)).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            sprites[name] = image
    return sprites

def load_editor_icons(path):
    """Loads all sprite images from the given path and scales them to ICON_SIZE."""
    icons = {}
    if not os.path.exists(path):
        return icons
    for filename in os.listdir(path):
        if filename.endswith(".png"):
            name = os.path.splitext(filename)[0]
            image = pygame.image.load(os.path.join(path, filename)).convert_alpha()
            image = pygame.transform.scale(image, (ICON_SIZE, ICON_SIZE))
            icons[name] = image
    return icons

def load_map_tiles_from_xml(xml_dir, sprite_dir):
    """Loads map tile definitions from XML files and their corresponding sprites."""
    map_tiles = {}
    sprite_images = load_sprite_images(sprite_dir)
    if not os.path.exists(xml_dir):
        return map_tiles
        
    for filename in os.listdir(xml_dir):
        if filename.endswith(".xml"):
            filepath = os.path.join(xml_dir, filename)
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                
                # Assuming the root element is <map> and has a 'char' attribute
                if root.tag == 'map' and 'char' in root.attrib:
                    char_id = root.attrib['char']
                    
                    # Find the sprite file within <visuals><sprite file="..." />
                    sprite_element = root.find('visuals/sprite')
                    if sprite_element is not None and 'file' in sprite_element.attrib:
                        sprite_filename = os.path.splitext(sprite_element.attrib['file'])[0] 
                        if sprite_filename in sprite_images:
                            map_tiles[char_id] = sprite_images[sprite_filename]
                        else:
                            print(f"Warning: Sprite image '{sprite_filename}.png' not found for '{char_id}'")
                            map_tiles[char_id] = create_placeholder(char_id)
                    else:
                        map_tiles[char_id] = create_placeholder(char_id)
                        
            except ET.ParseError as e:
                print(f"Error parsing XML file {filename}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred with {filename}: {e}")
                
    # Add a default 'bg' tile if not defined in XMLs but present in sprites
    if 'bg' not in map_tiles and 'bg' in sprite_images:
        map_tiles['bg'] = sprite_images['bg']
    return map_tiles

def load_items_from_xml(xml_dir, sprite_dir):
    """
    Loads item sprites and maps them to the 'name' attribute 
    found in their corresponding XML definitions.
    """
    sprites = load_sprite_images(sprite_dir)
    # Start with an empty dictionary for items so we don't carry over raw sprite names
    items = {}
         
    if not os.path.exists(xml_dir):
        return items
        
    for filename in os.listdir(xml_dir):
        if filename.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(xml_dir, filename))
                root = tree.getroot()
                
                # Check for either 'item' or 'cloth' tag
                if root.tag in ['item', 'cloth'] and 'name' in root.attrib:
                    name = root.attrib['name']
                    sprite_node = root.find(".//sprite")
                    
                    sprite_key = None
                    if sprite_node is not None and 'file' in sprite_node.attrib:
                        sprite_file = sprite_node.attrib['file']
                        sprite_key = os.path.splitext(os.path.basename(sprite_file))[0]
                    else:
                        # FALLBACK: If there's no <sprite> tag, assume the sprite matches the XML filename
                        sprite_key = os.path.splitext(filename)[0]
                        
                    if sprite_key and sprite_key in sprites:
                        items[name] = sprites[sprite_key]
                    else:
                        print(f"Warning: Sprite '{sprite_key}' referenced in {filename} not found.")
                        items[name] = create_placeholder(name)
                                     
            except Exception as e:
                print(f"Error parsing item XML {filename}: {e}")
                
    return items