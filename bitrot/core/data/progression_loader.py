import xml.etree.ElementTree as ET
import os
from core.data.config import DATA_PATH

class ProgressionConfig:
    def __init__(self):
        self.attributes = {} 
        self.stats = {}
        self.healing_rates = {}
        self.default_xp_req = 100

    def get_stat(self, stat_id, param, default=0.0):
        """Retrieves a specific parameter for a stat (e.g., stamina -> regen_base)."""
        return self.stats.get(stat_id, {}).get(param, default)

    def get_attr_effect(self, attr_id, target_effect):
        """Finds if an attribute has a specific effect and returns its data."""
        attr = self.attributes.get(attr_id)
        if not attr: return None
        for eff in attr.get('effects', []):
            if eff['target'] == target_effect:
                return eff
        return None

def load_progression_xml():
    config = ProgressionConfig()
    path = os.path.join(DATA_PATH, 'player/progression.xml')
    
    if not os.path.exists(path):
        print(f"Warning: Progression XML not found at {path}. Using defaults.")
        return config

    try:
        tree = ET.parse(path)
        root = tree.getroot()

        # 1. Parse Attributes
        for attr in root.findall('./attributes/attribute'):
            aid = attr.get('id')
            config.attributes[aid] = {
                'name': attr.get('name', aid),
                'image': attr.get('image'),
                'base_xp': float(attr.get('base_xp', 100)),
                'effects': []
            }
            for eff in attr.findall('effect'):
                config.attributes[aid]['effects'].append({
                    'target': eff.get('target'),
                    'value': float(eff.get('value', 0.0)),
                    'type': eff.get('type', 'flat') # 'flat' or 'multiplier_add'
                })

        # 2. Parse Stats
        for stat in root.findall('./stats/stat'):
            sid = stat.get('id')
            config.stats[sid] = {}
            for param in stat.findall('param'):
                try:
                    config.stats[sid][param.get('name')] = float(param.get('value'))
                except ValueError:
                    config.stats[sid][param.get('name')] = param.get('value')
        
                    
    except Exception as e:
        print(f"Error loading progression.xml: {e}")

    return config

# Global instance for easy access, similar to TRAIT_DEFINITIONS
PROGRESSION_CONFIG = load_progression_xml()