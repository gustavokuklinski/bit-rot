import xml.etree.ElementTree as ET
import os
from core.data.config import BASE_DIR

# Seu dicionário global de traduções
translations = {} 

def load_language(lang_code="pt_BR"):
    global translations
    translations.clear()
    
    # 1. Main file (pt_BR.xml)
    main_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}.xml")
    if os.path.exists(main_file):
        _parse_xml_to_dict(main_file)
        
    # 2. Items file (pt_BR_items.xml)
    items_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}_items.xml")
    if os.path.exists(items_file):
        _parse_xml_to_dict(items_file)

    # 3. Clothes file (pt_BR_clothes.xml)
    clothes_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}_clothes.xml")
    if os.path.exists(clothes_file):
        _parse_xml_to_dict(clothes_file)
    
    # 4. Traits file (pt_BR_traits.xml)
    traits_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}_traits.xml")
    if os.path.exists(traits_file):
        _parse_xml_to_dict(traits_file)

def _parse_xml_to_dict(filepath):
    global translations
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    for category in root:
        for element in category:
            key = element.get('name')
            if not key:
                continue
                
            for attr_name, attr_val in element.attrib.items():
                if attr_name.startswith('translation_'):
                    real_cat = attr_name.replace('translation_', '')
                    
                    if real_cat == 'type':
                        real_cat = 'item_type'
                    
                    if real_cat not in translations:
                        translations[real_cat] = {}
                        
                    translations[real_cat][key] = attr_val

                    # Mirror clothing into 'item' so tr('item', item.name) translates clothes automatically
                    if real_cat == 'cloth':
                        translations.setdefault('item', {})[key] = attr_val

                    # Mirror slot IDs into 'ui' and 'cloth_id'
                    if element.tag == 'cloth_id':
                        translations.setdefault('cloth_id', {})[key] = attr_val
                        translations.setdefault('ui', {})[key.capitalize()] = attr_val.capitalize()

def tr(category, key):
    """Sua função tr existente."""
    return translations.get(category, {}).get(key, key)