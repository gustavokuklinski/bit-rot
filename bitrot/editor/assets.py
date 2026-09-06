import pygame
import os
import xml.etree.ElementTree as ET
from editor.config import TILE_SIZE, ICON_SIZE

def create_placeholder(name, size=TILE_SIZE):
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((80, 60, 70, 220)) 
    pygame.draw.rect(surf, (200, 150, 160), surf.get_rect(), 2)
    
    font = pygame.font.Font(None, max(18, int(size * 0.6)))
    initials = name[:2].upper() if name else "?"
    text = font.render(initials, True, (255, 220, 220))
    text_rect = text.get_rect(center=(size//2, size//2))
    surf.blit(text, text_rect)
    
    return surf

def load_sprite_images(path):
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
                
                if root.tag == 'map' and 'char' in root.attrib:
                    char_id = root.attrib['char']
                    
                    sprite_element = root.find('visuals/sprite')
                    if sprite_element is not None and 'file' in sprite_element.attrib:
                        sprite_filename = os.path.splitext(sprite_element.attrib['file'])[0] 
                        if sprite_filename in sprite_images:
                            map_tiles[char_id] = sprite_images[sprite_filename]
                        else:
                            map_tiles[char_id] = create_placeholder(char_id)
                    else:
                        map_tiles[char_id] = create_placeholder(char_id)
                        
            except ET.ParseError as e:
                pass
            except Exception as e:
                pass
                
    if 'bg' not in map_tiles and 'bg' in sprite_images:
        map_tiles['bg'] = sprite_images['bg']
    return map_tiles

def load_items_from_xml(xml_dir, sprite_dir):
    sprites = load_sprite_images(sprite_dir)
    items = {}
         
    if not os.path.exists(xml_dir):
        return items
        
    for filename in os.listdir(xml_dir):
        if filename.endswith(".xml"):
            try:
                tree = ET.parse(os.path.join(xml_dir, filename))
                root = tree.getroot()
                
                if root.tag in ['item', 'cloth'] and 'name' in root.attrib:
                    name = root.attrib['name']
                    sprite_node = root.find(".//sprite")
                    
                    sprite_key = None
                    if sprite_node is not None and 'file' in sprite_node.attrib:
                        sprite_file = sprite_node.attrib['file']
                        sprite_key = os.path.splitext(os.path.basename(sprite_file))[0]
                    else:
                        sprite_key = os.path.splitext(filename)[0]
                        
                    if sprite_key and sprite_key in sprites:
                        items[name] = sprites[sprite_key]
                    else:
                        items[name] = create_placeholder(name)
                                     
            except Exception as e:
                pass
                
    return items