# core/data/localization.py

import xml.etree.ElementTree as ET
import os
from core.data.config import BASE_DIR

translations = {}

def load_language(lang_code="pt_BR"):
    from core.systems.mod_manager import mod_manager
    global translations
    translations.clear()

    lang_dir = os.path.join(BASE_DIR, "data.rot", "lib", "lang")

    standard_files = [
        f"{lang_code}.xml",
        f"{lang_code}_items.xml",
        f"{lang_code}_clothes.xml",
        f"{lang_code}_traits.xml"
    ]

    # 1. Parse base language files first as the baseline
    for filename in standard_files:
        base_path = os.path.join(lang_dir, filename)
        if os.path.exists(base_path):
            try:
                _parse_xml_to_dict(base_path)
            except Exception as e:
                print(f"[Localization] Error loading base language file {filename}: {e}")

    # 2. Parse modded translation files (supports overrides & additions)
    for _, _, full_paths in mod_manager.vfs_walk(lang_dir):
        for filepath in full_paths:
            if not filepath.endswith('.xml'):
                continue
            fname = os.path.basename(filepath)
            if fname.startswith(lang_code) or f"_{lang_code}" in fname or lang_code in fname:
                # Avoid re-parsing the base file if it's the exact same file
                if os.path.abspath(filepath) in [os.path.abspath(os.path.join(lang_dir, sf)) for sf in standard_files]:
                    continue
                try:
                    _parse_xml_to_dict(filepath)
                except Exception as e:
                    print(f"[Localization] Error loading mod translation file {filepath}: {e}")

def _parse_xml_to_dict(filepath):
    global translations
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except Exception as e:
        print(f"[Localization] XML parse error in {filepath}: {e}")
        return

    def parse_element(element, category_hint=None):
        key = element.get('name') or element.get('id')
        if not key:
            return

        text_val = element.text.strip() if element.text and element.text.strip() else None

        for attr_name, attr_val in element.attrib.items():
            if attr_name.startswith('translation_'):
                real_cat = attr_name.replace('translation_', '')
                if real_cat == 'type': real_cat = 'item_type'
                translations.setdefault(real_cat, {})[key] = attr_val
                if real_cat == 'cloth':
                    translations.setdefault('item', {})[key] = attr_val
                if element.tag == 'cloth_id':
                    translations.setdefault('cloth_id', {})[key] = attr_val
                    translations.setdefault('ui', {})[key.capitalize()] = attr_val.capitalize()
            elif attr_name in ('translation', 'trans', 'value'):
                cat = category_hint or element.tag or 'ui'
                if cat == 'type': cat = 'item_type'
                translations.setdefault(cat, {})[key] = attr_val
                if cat == 'cloth':
                    translations.setdefault('item', {})[key] = attr_val

        # In case the translation is given inside the tag text: <cloth name="Hoodie">Moletom</cloth>
        if text_val:
            cat = category_hint or element.tag or 'ui'
            if cat == 'type': cat = 'item_type'
            translations.setdefault(cat, {})[key] = text_val
            if cat == 'cloth':
                translations.setdefault('item', {})[key] = text_val

    for node in root:
        if len(node) > 0:
            for child in node:
                parse_element(child, category_hint=node.tag)
        else:
            parse_element(node, category_hint=root.tag)

def tr(category, key):
    """Translates a key within a given category."""
    return translations.get(category, {}).get(key, key)