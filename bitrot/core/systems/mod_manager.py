# core/systems/mod_manager.py

import os
import json
import xml.etree.ElementTree as ET
import core.data.config as config

class ModManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized: return
        self.initialized = True
        
        self.base_dir = config.BASE_DIR
        self.mods_dir = os.path.join(self.base_dir, "data.rot", "mods")
        self.available_mods = {}
        self.enabled_mods = []
        self.load_configs()

    def load_configs(self):
        self.available_mods = {}
        if os.path.exists(self.mods_dir):
            for folder in os.listdir(self.mods_dir):
                mod_path = os.path.join(self.mods_dir, folder)
                config_path = os.path.join(mod_path, "config.json")
                if os.path.isdir(mod_path) and os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                            mod_name = cfg.get("name", folder)
                            self.available_mods[mod_name] = {
                                "folder": folder,
                                "path": mod_path,
                                "config": cfg
                            }
                    except Exception as e:
                        print(f"[ModManager] Error loading mod {folder}: {e}")

        pref_path = config.get_preferences_path(for_save=False)
        try:
            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    pref_data = json.load(f)
                mods_pref = pref_data.get("preferences", {}).get("mods")
                # If explicit list exists in preferences, honor it; otherwise enable all available mods by default
                if mods_pref is not None and "enabled" in mods_pref:
                    self.enabled_mods = [m for m in mods_pref["enabled"] if m in self.available_mods]
                else:
                    self.enabled_mods = list(self.available_mods.keys())
            else:
                self.enabled_mods = list(self.available_mods.keys())
        except Exception:
            self.enabled_mods = list(self.available_mods.keys())

    def save_enabled_mods(self, enabled_list):
        self.enabled_mods = enabled_list
        pref_path = config.get_preferences_path(for_save=True)
        try:
            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    pref_data = json.load(f)
            else:
                pref_data = {"preferences": {}}
                
            if "preferences" not in pref_data:
                pref_data["preferences"] = {}
            if "mods" not in pref_data["preferences"]:
                pref_data["preferences"]["mods"] = {}
            pref_data["preferences"]["mods"]["enabled"] = self.enabled_mods
            
            os.makedirs(os.path.dirname(pref_path), exist_ok=True)
            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(pref_data, f, indent=2)
        except Exception as e:
            print(f"[ModManager] Error saving mod preferences: {e}")

    def get_override_path(self, original_path):
        """Returns the overridden path if a mod overrides it, otherwise the original."""
        if not self.enabled_mods or not original_path:
            return original_path

        try:
            rel_path = os.path.relpath(original_path, self.base_dir).replace('\\', '/')
        except ValueError:
            return original_path

        filename = os.path.basename(original_path)

        for mod_name in reversed(self.enabled_mods):
            if mod_name in self.available_mods:
                mod_info = self.available_mods[mod_name]
                mod_path = mod_info["path"]
                cfg = mod_info["config"]
                override_dirs = cfg.get("overide_dir", cfg.get("override_dir", []))

                is_overridden = False
                rel_under_override = None

                for o_dir in override_dirs:
                    o_dir_clean = o_dir.replace('./', '').replace('*', '').strip('/\\').replace('\\', '/')
                    if rel_path.startswith(o_dir_clean):
                        is_overridden = True
                        rel_under_override = rel_path[len(o_dir_clean):].lstrip('/\\')
                        break

                if is_overridden:
                    candidates = []
                    # 1. Path relative to override directory (e.g., pt_BR.xml or sprites/clothes/arms_hoodie.png)
                    if rel_under_override:
                        candidates.append(os.path.join(mod_path, rel_under_override))
                        parts = rel_under_override.split('/')
                        for idx in range(1, len(parts)):
                            candidates.append(os.path.join(mod_path, *parts[idx:]))

                    # 2. Directly in the mod root
                    candidates.append(os.path.join(mod_path, filename))

                    # 3. Full relative path from base_dir
                    candidates.append(os.path.join(mod_path, rel_path))

                    for cand in candidates:
                        if os.path.exists(cand):
                            return cand

                    # 4. Recursive search inside the mod for the filename
                    for root, _, files in os.walk(mod_path):
                        if filename in files:
                            return os.path.join(root, filename)

        return original_path

    def vfs_walk(self, top):
        try:
            top_rel_base = os.path.relpath(top, self.base_dir).replace('\\', '/')
        except ValueError:
            yield from os.walk(top)
            return

        file_map = {}

        # 1. Map Original Base Game Files
        if os.path.exists(top):
            for root, _, files in os.walk(top):
                for file in files:
                    file_map[file] = os.path.join(root, file)

        folder_name = os.path.basename(top.rstrip('/\\'))

        # 2. Inject / Override with Mod Files
        for mod_name in self.enabled_mods:
            if mod_name in self.available_mods:
                mod_info = self.available_mods[mod_name]
                mod_path = mod_info["path"]
                cfg = mod_info["config"]
                fallback = cfg.get("fallback", cfg.get("fallack", True))
                override_dirs = cfg.get("overide_dir", cfg.get("override_dir", []))

                is_overridden = False
                rel_under_override = None

                for o_dir in override_dirs:
                    o_dir_clean = o_dir.replace('./', '').replace('*', '').strip('/\\').replace('\\', '/')
                    if top_rel_base.startswith(o_dir_clean) or o_dir_clean.startswith(top_rel_base):
                        is_overridden = True
                        if top_rel_base.startswith(o_dir_clean):
                            rel_under_override = top_rel_base[len(o_dir_clean):].lstrip('/\\')
                        if not fallback:
                            file_map.clear()
                        break

                if is_overridden:
                    candidate_dirs = []
                    if rel_under_override:
                        candidate_dirs.append(os.path.join(mod_path, rel_under_override))
                    candidate_dirs.append(os.path.join(mod_path, folder_name))
                    candidate_dirs.append(os.path.join(mod_path, top_rel_base))

                    for c_dir in candidate_dirs:
                        if os.path.exists(c_dir):
                            for m_root, _, m_files in os.walk(c_dir):
                                for m_file in m_files:
                                    file_map[m_file] = os.path.join(m_root, m_file)

                    # Inspect files sitting directly in the mod's root folder matching this category
                    if os.path.exists(mod_path):
                        for m_file in os.listdir(mod_path):
                            full_m_path = os.path.join(mod_path, m_file)
                            if not os.path.isfile(full_m_path):
                                continue

                            belongs = False
                            if m_file.endswith('.xml'):
                                try:
                                    tree = ET.parse(full_m_path)
                                    tag = tree.getroot().tag.lower()
                                    if tag == 'cloth' and folder_name == 'clothes': belongs = True
                                    elif tag == 'item' and folder_name == 'items': belongs = True
                                    elif tag == 'recipe' and folder_name == 'craft': belongs = True
                                    elif tag == 'map' and folder_name in ('map', 'maps'): belongs = True
                                    elif tag in ('radio', 'radios', 'station') and folder_name in ('radio', 'radios'): belongs = True
                                    elif tag == 'vehicle' and folder_name == 'vehicle': belongs = True
                                    elif folder_name == 'lang':
                                        if tag in ('languages', 'language', 'translations') or any(code in m_file for code in ('pt_BR', 'en_US', 'lang')):
                                            belongs = True
                                except Exception:
                                    pass
                            elif m_file.endswith('.json'):
                                if folder_name in ('npc', 'animals', 'world_builds', 'player_builds', 'npc_dialogs'):
                                    belongs = True
                            elif m_file.endswith('.csv') and folder_name == 'buildings':
                                belongs = True

                            if belongs:
                                file_map[m_file] = full_m_path

        yield top, [], list(file_map.values())

mod_manager = ModManager()