import pygame
import os
import xml.etree.ElementTree as ET

from editor.config import TILE_SIZE, ICON_SIZE

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
                        sprite_filename = os.path.splitext(sprite_element.attrib['file'])[0] # Get name without extension
                        if sprite_filename in sprite_images:
                            map_tiles[char_id] = sprite_images[sprite_filename]
                        else:
                            print(f"Warning: Sprite image '{sprite_filename}.png' not found for char '{char_id}' from {filename}")
                    else:
                        print(f"Warning: No sprite file found in {filename} for char '{char_id}'")
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
    # 1. Load all sprites by filename first (e.g. 'tent' -> Image)
    sprites = load_sprite_images(sprite_dir)
    items = sprites.copy() 
    
    if not os.path.exists(xml_dir):
        return items

    # 2. Iterate over XML files to find name overrides
    for filename in os.listdir(xml_dir):
        if filename.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(xml_dir, filename))
                root = tree.getroot()
                
                # Look for <item name="...">
                if root.tag == 'item' and 'name' in root.attrib:
                    name = root.attrib['name']
                    
                    # Find sprite file. Check <properties><sprite file="...">
                    # Using .//sprite will find the sprite tag nested anywhere (e.g. inside properties)
                    sprite_node = root.find(".//sprite")
                    
                    if sprite_node is not None and 'file' in sprite_node.attrib:
                        sprite_file = sprite_node.attrib['file']
                        # Normalize sprite name (remove extension) to match load_sprite_images keys
                        sprite_key = os.path.splitext(os.path.basename(sprite_file))[0]
                        
                        if sprite_key in sprites:
                            # Map the human-readable Name -> Sprite Image
                            # This ensures 'Camp Tent' is the key used in the editor
                            items[name] = sprites[sprite_key]
                            
                            # Remove the raw filename key from the list to avoid duplication
                            # (e.g. remove 'tent' so only 'Camp Tent' appears)
                            if sprite_key != name and sprite_key in items:
                                del items[sprite_key]
                        else:
                            print(f"Warning: Sprite '{sprite_key}' referenced in {filename} not found.")
                    
            except Exception as e:
                print(f"Error parsing item XML {filename}: {e}")
    
    return items