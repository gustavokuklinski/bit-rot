import pygame
import os
import xml.etree.ElementTree as ET

from editor.config import TILE_SIZE

def load_sprite_images(path):
    """Loads all sprite images from the given path and scales them."""
    sprites = {}
    for filename in os.listdir(path):
        if filename.endswith(".png"):
            name = os.path.splitext(filename)[0]
            image = pygame.image.load(os.path.join(path, filename)).convert_alpha()
            image = pygame.transform.scale(image, (TILE_SIZE, TILE_SIZE))
            sprites[name] = image
    return sprites

def load_map_tiles_from_xml(xml_dir, sprite_dir):
    """Loads map tile definitions from XML files and their corresponding sprites."""
    map_tiles = {}
    sprite_images = load_sprite_images(sprite_dir)

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
                        sprite_filename = os.path.splitext(sprite_element.attrib['file'])[0] # Get name without extension
                        if sprite_filename in sprite_images:
                            map_tiles[char_id] = sprite_images[sprite_filename]
                        else:
                            print(f"Warning: Sprite image '{sprite_filename}.png' not found for char '{char_id}' from {filename}")
                    else:
                        print(f"Warning: No sprite file found in {filename} for char '{char_id}'")
                else:
                    print(f"Warning: {filename} is not a map XML or missing 'char' attribute.")
            except ET.ParseError as e:
                print(f"Error parsing XML file {filename}: {e}")
            except Exception as e:
                print(f"An unexpected error occurred with {filename}: {e}")
    
    # Add a default 'bg' tile if not defined in XMLs but present in sprites
    if 'bg' not in map_tiles and 'bg' in sprite_images:
        map_tiles['bg'] = sprite_images['bg']

    return map_tiles
