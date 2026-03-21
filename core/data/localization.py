# core/data/localization.py
import os
import xml.etree.ElementTree as ET

_translations = {}
_current_lang = "en_US"

def load_language(lang_code, lang_dir="./game/lib/lang"):
    """Loads an XML language file and populates the translation dictionary."""
    global _translations, _current_lang
    filepath = os.path.join(lang_dir, f"{lang_code}.xml")
    
    _translations.clear()
    _current_lang = lang_code
    
    # --- NEW: Explicitly intercept en_US to use hardcoded defaults without throwing missing file warnings ---
    if lang_code == "en_US":
        print("Language set to en_US. Using default hardcoded English.")
        return 
    
    if not os.path.exists(filepath):
        print(f"Language file {filepath} not found. Defaulting to hardcoded English.")
        return 
        
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        # Dynamically parse categories: <modal>, <ui>, <tab>, <vehicle>, etc.
        for category in root:
            cat_name = category.tag
            _translations[cat_name] = {}
            
            # Look for attributes like 'translation_modal', 'translation_ui', etc.
            trans_attr = f"translation_{cat_name}" 
            
            for child in category:
                key = child.attrib.get('name')
                trans_val = child.attrib.get(trans_attr)
                
                if key and trans_val:
                    _translations[cat_name][key] = trans_val
                    
        print(f"Successfully loaded language: {lang_code}")
    except Exception as e:
        print(f"Error loading language {lang_code}: {e}")

def tr(category, key, default=None):
    """
    Fetches the translated string. 
    If not found, returns the 'default' string (usually the fallback English key).
    """
    if default is None:
        default = key
        
    if category in _translations and key in _translations[category]:
        return _translations[category][key]
        
    return default