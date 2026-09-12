import xml.etree.ElementTree as ET
import os
from core.data.config import BASE_DIR

# Seu dicionário global de traduções
translations = {} 

def load_language(lang_code="pt_BR"):
    global translations
    translations.clear()
    
    # 1. Carrega o arquivo principal (pt_BR.xml)
    main_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}.xml")
    if os.path.exists(main_file):
        _parse_xml_to_dict(main_file)
        
    # 2. Carrega o arquivo de itens (pt_BR_items.xml)
    items_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}_items.xml")
    if os.path.exists(items_file):
        _parse_xml_to_dict(items_file)
    
    traits_file = os.path.join(BASE_DIR, "data.rot", "lib", "lang", f"{lang_code}_traits.xml")
    if os.path.exists(traits_file):
        _parse_xml_to_dict(traits_file)

def _parse_xml_to_dict(filepath):
    """Improved function to read XML and support multiple translations per element"""
    global translations
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    for category in root:
        # We loop through every element (e.g., <item> or <item_type>)
        for element in category:
            key = element.get('name')
            if not key:
                continue
                
            # Look at EVERY attribute in this tag (e.g., translation_item, translation_tips)
            for attr_name, attr_val in element.attrib.items():
                if attr_name.startswith('translation_'):
                    # Extract the category from the attribute name
                    # 'translation_item' -> 'item'
                    # 'translation_tips' -> 'tips'
                    # 'translation_type' -> 'type'
                    real_cat = attr_name.replace('translation_', '')
                    
                    # SPECIAL CASE: Your XML uses 'translation_type' but we want the category 'item_type'
                    if real_cat == 'type':
                        real_cat = 'item_type'
                    
                    # Ensure the category dictionary exists
                    if real_cat not in translations:
                        translations[real_cat] = {}
                        
                    # Save the translation
                    translations[real_cat][key] = attr_val

def tr(category, key):
    """Sua função tr existente."""
    return translations.get(category, {}).get(key, key)