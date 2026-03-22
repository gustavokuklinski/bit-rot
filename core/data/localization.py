import xml.etree.ElementTree as ET
import os

# Seu dicionário global de traduções
translations = {} 

def load_language(lang_code="pt_BR"):
    global translations
    translations.clear()
    
    # 1. Carrega o arquivo principal (pt_BR.xml)
    main_file = f"./game/lib/lang/{lang_code}.xml"
    if os.path.exists(main_file):
        _parse_xml_to_dict(main_file)
        
    # 2. Carrega o arquivo de itens (pt_BR_items.xml)
    items_file = f"./game/lib/lang/{lang_code}_items.xml"
    if os.path.exists(items_file):
        _parse_xml_to_dict(items_file)
    
    traits_file = f"./game/lib/lang/{lang_code}_traits.xml"
    if os.path.exists(traits_file):
        _parse_xml_to_dict(traits_file)

def _parse_xml_to_dict(filepath):
    """Função auxiliar para ler o XML e guardar no dicionário"""
    global translations
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    # Loop dinâmico por todas as categorias (<ui>, <msg>, <item>, etc)
    for category in root:
        cat_name = category.tag
        if cat_name not in translations:
            translations[cat_name] = {}
            
        for element in category:
            key = element.get('name')
            # O valor a ser pego dinamicamente (ex: translation_ui, translation_item)
            val_attr = f"translation_{cat_name}" 
            val = element.get(val_attr)
            
            if key and val:
                translations[cat_name][key] = val

def tr(category, key):
    """Sua função tr existente."""
    return translations.get(category, {}).get(key, key)