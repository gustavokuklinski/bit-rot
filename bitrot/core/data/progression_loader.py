# core/data/progression_loader.py

import json
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

def load_progression_json():
    config = ProgressionConfig()
    path = os.path.join(DATA_PATH, 'player', 'progression.json')

    if not os.path.exists(path):
        print(f"Warning: Progression JSON not found at {path}. Using defaults.")
        return config

    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        p_root = raw.get('progression', raw)

        # 1. Parse Attributes
        for aid, a_info in p_root.get('attributes', {}).items():
            config.attributes[aid] = {
                'name': a_info.get('name', aid.capitalize()),
                'image': a_info.get('image'),
                'base_xp': float(a_info.get('base_xp', 100)),
                'effects': []
            }
            for eff in a_info.get('effects', []):
                config.attributes[aid]['effects'].append({
                    'target': eff.get('target'),
                    'value': float(eff.get('value', 0.0)),
                    'type': eff.get('type', 'flat')
                })

        # 2. Parse Stats
        for sid, s_dict in p_root.get('stats', {}).items():
            config.stats[sid] = {}
            for param_name, param_val in s_dict.items():
                try:
                    config.stats[sid][param_name] = float(param_val)
                except (ValueError, TypeError):
                    config.stats[sid][param_name] = param_val

    except Exception as e:
        print(f"Error loading progression.json: {e}")

    return config

# Global instance matching existing imports
PROGRESSION_CONFIG = load_progression_json()
load_progression_xml = load_progression_json