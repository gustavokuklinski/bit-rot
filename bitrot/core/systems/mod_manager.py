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
        self.available_mods = {}
        self.mods_order = []
        self.enabled_mods = []
        
        # Ensure the active runtime mod directory exists
        primary_mods_dir = os.path.abspath(os.path.join(config.get_writable_dir(), "data.rot", "mods"))
        try:
            os.makedirs(primary_mods_dir, exist_ok=True)
        except OSError:
            pass

        self.load_configs()

    def get_mod_search_dirs(self):
        candidates = [
            os.path.abspath(os.path.join(config.get_writable_dir(), "data.rot", "mods")),
            os.path.abspath(os.path.join(".", "data.rot", "mods")),
            os.path.abspath(os.path.join("..", "data.rot", "mods")),
            os.path.abspath(os.path.join(self.base_dir, "data.rot", "mods")),
            os.path.abspath(os.path.join(self.base_dir, "..", "data.rot", "mods"))
        ]

        seen = set()
        unique_dirs = []
        for d in candidates:
            norm = os.path.normpath(d)
            if norm not in seen:
                seen.add(norm)
                unique_dirs.append(norm)

        return unique_dirs

    def load_configs(self):
        """Discovers mods across all search directories and restores user load order."""
        self.available_mods = {}

        for search_dir in self.get_mod_search_dirs():
            if not os.path.exists(search_dir) or not os.path.isdir(search_dir):
                continue

            for folder in os.listdir(search_dir):
                mod_path = os.path.join(search_dir, folder)
                config_path = os.path.join(mod_path, "config.json")

                if os.path.isdir(mod_path) and os.path.exists(config_path):
                    try:
                        with open(config_path, "r", encoding="utf-8") as f:
                            cfg = json.load(f)
                            mod_name = cfg.get("name", folder)

                            if mod_name not in self.available_mods:
                                self.available_mods[mod_name] = {
                                    "folder": folder,
                                    "path": mod_path,
                                    "config": cfg
                                }
                    except Exception as e:
                        print(f"[ModManager] Error loading mod {folder} from {search_dir}: {e}")

        # Restore load order and enabled status from preferences
        pref_path = config.get_preferences_path(for_save=False)
        saved_order = []
        saved_enabled = None
        try:
            if os.path.exists(pref_path):
                with open(pref_path, "r", encoding="utf-8") as f:
                    pref_data = json.load(f)
                mods_pref = pref_data.get("preferences", {}).get("mods", {})
                saved_order = mods_pref.get("order", mods_pref.get("load_order", []))
                saved_enabled = mods_pref.get("enabled", None)
        except Exception:
            pass

        # Build load order: saved order first, followed by any newly discovered mods
        self.mods_order = [m for m in saved_order if m in self.available_mods]
        for m in self.available_mods.keys():
            if m not in self.mods_order:
                self.mods_order.append(m)

        if saved_enabled is not None:
            self.enabled_mods = [m for m in self.mods_order if m in saved_enabled]
        else:
            self.enabled_mods = list(self.mods_order)

    def move_mod_up(self, mod_name):
        """Moves a mod higher in priority (towards index 0)."""
        if mod_name not in self.mods_order:
            return False
        idx = self.mods_order.index(mod_name)
        if idx > 0:
            self.mods_order[idx], self.mods_order[idx - 1] = self.mods_order[idx - 1], self.mods_order[idx]
            self._sync_enabled_order()
            self.save_mods_config()
            return True
        return False

    def move_mod_down(self, mod_name):
        """Moves a mod lower in priority (towards the bottom)."""
        if mod_name not in self.mods_order:
            return False
        idx = self.mods_order.index(mod_name)
        if idx < len(self.mods_order) - 1:
            self.mods_order[idx], self.mods_order[idx + 1] = self.mods_order[idx + 1], self.mods_order[idx]
            self._sync_enabled_order()
            self.save_mods_config()
            return True
        return False

    def _sync_enabled_order(self):
        """Ensures enabled_mods strictly mirrors the priority set in mods_order."""
        self.enabled_mods = [m for m in self.mods_order if m in self.enabled_mods]

    def toggle_mod_enabled(self, mod_name):
        if mod_name in self.enabled_mods:
            self.enabled_mods.remove(mod_name)
        else:
            self.enabled_mods.append(mod_name)
            self._sync_enabled_order()
        self.save_mods_config()

    def save_mods_config(self):
        """Persists load order and enabled status into preferences.json."""
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
            pref_data["preferences"]["mods"]["order"] = self.mods_order

            os.makedirs(os.path.dirname(pref_path), exist_ok=True)
            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(pref_data, f, indent=2)
        except Exception as e:
            print(f"[ModManager] Error saving mod preferences: {e}")

    def get_mod_translation_files(self, mod_name, lang_code):
        """Discovers all XML translation files provided by a specific mod for lang_code."""
        if mod_name not in self.available_mods:
            return []

        mod_info = self.available_mods[mod_name]
        mod_path = mod_info["path"]
        found_files = []
        seen = set()

        candidate_dirs = [
            os.path.join(mod_path, "data.rot", "lib", "lang"),
            os.path.join(mod_path, "lib", "lang"),
            os.path.join(mod_path, "lang"),
            mod_path
        ]

        for c_dir in candidate_dirs:
            if os.path.exists(c_dir) and os.path.isdir(c_dir):
                for f in sorted(os.listdir(c_dir)):
                    full_p = os.path.join(c_dir, f)
                    if os.path.isfile(full_p) and f.endswith(".xml"):
                        if lang_code in f or f.startswith(lang_code):
                            norm = os.path.normpath(full_p)
                            if norm not in seen:
                                seen.add(norm)
                                found_files.append(norm)

        if not found_files and os.path.exists(mod_path):
            for root, _, files in os.walk(mod_path):
                for f in sorted(files):
                    if f.endswith(".xml") and (lang_code in f or f.startswith(lang_code)):
                        norm = os.path.normpath(os.path.join(root, f))
                        if norm not in seen:
                            seen.add(norm)
                            found_files.append(norm)

        return found_files

    def get_override_path(self, original_path):
        """Returns the overridden path from the highest priority enabled mod (index 0 first)."""
        if not self.enabled_mods or not original_path:
            return original_path

        try:
            rel_path = os.path.relpath(original_path, self.base_dir).replace('\\', '/')
        except ValueError:
            rel_path = original_path.replace('\\', '/')

        filename = os.path.basename(original_path)

        # Iterate from top priority (index 0) to lowest priority
        for mod_name in self.enabled_mods:
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
                    if rel_under_override:
                        candidates.append(os.path.join(mod_path, rel_under_override))
                        parts = rel_under_override.split('/')
                        for idx in range(1, len(parts)):
                            candidates.append(os.path.join(mod_path, *parts[idx:]))

                    candidates.append(os.path.join(mod_path, filename))
                    candidates.append(os.path.join(mod_path, rel_path))

                    for cand in candidates:
                        if os.path.exists(cand):
                            return cand

                    for root, _, files in os.walk(mod_path):
                        if filename in files:
                            return os.path.join(root, filename)

        return original_path

    def vfs_walk(self, top):
        """Walks directory, merging files from base game and all enabled mods (top priority wins on duplicate names)."""
        try:
            top_rel_base = os.path.relpath(top, self.base_dir).replace('\\', '/')
        except ValueError:
            yield from os.walk(top)
            return

        file_map = {}

        # 1. Map base game files
        if os.path.exists(top):
            for root, _, files in os.walk(top):
                for file in files:
                    file_map[file] = os.path.join(root, file)

        folder_name = os.path.basename(top.rstrip('/\\'))

        # 2. Inject mods from lowest priority to highest priority
        for mod_name in reversed(self.enabled_mods):
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

                    if os.path.exists(mod_path):
                        for m_file in os.listdir(mod_path):
                            full_m_path = os.path.join(mod_path, m_file)
                            if not os.path.isfile(full_m_path):
                                continue

                            if m_file.lower() == 'config.json':
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
                                if folder_name in ('npc', 'animals', 'world_builds', 'player_builds', 'npc_dialogs', 'radio', 'radios'):
                                    belongs = True
                            elif m_file.endswith('.csv') and folder_name == 'buildings':
                                belongs = True

                            if belongs:
                                file_map[m_file] = full_m_path

        yield top, [], list(file_map.values())

mod_manager = ModManager()