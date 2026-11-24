# core/data/radio_manager.py

import os
import random
import json
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH, BASE_DIR

class RadioManager:
    STATIONS = {}

    @classmethod
    def get_radio_folders(cls):
        """Resolves candidate radio folders across environments."""
        candidates = [
            os.path.join(DATA_PATH, 'radio'),
            os.path.join(BASE_DIR, 'data.rot', 'lib', 'data', 'radio'),
            os.path.abspath('data.rot/lib/data/radio'),
            os.path.join(DATA_PATH, 'radios'),
            os.path.join(BASE_DIR, 'data.rot', 'lib', 'data', 'radios'),
            os.path.abspath('data.rot/lib/data/radios'),
        ]
        return [f for f in candidates if os.path.exists(f)]

    @classmethod
    def sync_game_frequencies(cls, game):
        """Ensures all loaded radio stations have assigned frequencies in the game instance."""
        if not cls.STATIONS:
            cls.load_radios()

        if not hasattr(game, 'radio_frequencies') or not isinstance(game.radio_frequencies, dict):
            game.radio_frequencies = {}

        MIN_FREQ = 110.42
        MAX_FREQ = 120.42
        used_freqs = []

        # 1. Register fixed-frequency stations first so random stations never crowd them
        for name, data in cls.STATIONS.items():
            freq_raw = data.get('frequency', 'random')
            if str(freq_raw).lower() != 'random':
                try:
                    f = round(max(MIN_FREQ, min(MAX_FREQ, float(freq_raw))), 2)
                except (ValueError, TypeError):
                    f = MIN_FREQ
                game.radio_frequencies[name] = f
                used_freqs.append(f)

        # 2. Validate existing or assign new random frequencies with generous separation
        def _pick_spaced_freq():
            for min_gap in (1.00, 0.60, 0.30, 0.15):
                for _ in range(120):
                    cand = round(random.uniform(MIN_FREQ + 0.08, MAX_FREQ - 0.08), 2)
                    if all(abs(cand - uf) >= min_gap for uf in used_freqs):
                        return cand
            return round(random.uniform(MIN_FREQ + 0.08, MAX_FREQ - 0.08), 2)

        for name, data in cls.STATIONS.items():
            freq_raw = data.get('frequency', 'random')
            if str(freq_raw).lower() != 'random':
                continue

            existing = game.radio_frequencies.get(name)
            is_valid_existing = (
                isinstance(existing, (int, float))
                and MIN_FREQ <= float(existing) <= MAX_FREQ
                and all(abs(float(existing) - uf) >= 0.50 for uf in used_freqs)
            )
            if is_valid_existing:
                f = round(float(existing), 2)
            else:
                f = _pick_spaced_freq()

            game.radio_frequencies[name] = f
            used_freqs.append(f)

        if not hasattr(game, 'current_radio_freq') or game.current_radio_freq is None:
            game.current_radio_freq = MIN_FREQ
        else:
            game.current_radio_freq = round(max(MIN_FREQ, min(MAX_FREQ, float(game.current_radio_freq))), 2)
            

    @staticmethod
    def _parse_schedule(raw_schedule):
        if isinstance(raw_schedule, (list, tuple)):
            return [str(s).strip() for s in raw_schedule if str(s).strip()]
        if isinstance(raw_schedule, str):
            clean = raw_schedule.strip()
            if clean.startswith('[') and clean.endswith(']'):
                return [s.strip() for s in clean[1:-1].split(',') if s.strip()]
            if clean:
                return [clean]
        return []

    @staticmethod
    def _parse_messages(raw_streams):
        messages = []
        if isinstance(raw_streams, (list, tuple)):
            for entry in raw_streams:
                if isinstance(entry, dict):
                    txt = entry.get('text') or entry.get('msg') or ''
                else:
                    txt = str(entry)
                txt = txt.replace('\\n', '\n').strip()
                if txt:
                    messages.append(txt)
        elif isinstance(raw_streams, str):
            txt = raw_streams.replace('\\n', '\n').strip()
            if txt:
                messages.append(txt)
        return messages

    @staticmethod
    def load_radios():
        RadioManager.STATIONS.clear()
        folders = RadioManager.get_radio_folders()

        if not folders:
            fallback = os.path.join(DATA_PATH, 'radio')
            os.makedirs(fallback, exist_ok=True)
            folders = [fallback]

        from core.systems.mod_manager import mod_manager

        found_files = 0
        for radio_path in folders:
            for root_dir, _, full_paths in mod_manager.vfs_walk(radio_path):
                for full_path in full_paths:
                    filename = os.path.basename(full_path)
                    fallback_name = os.path.splitext(filename)[0].replace('_', ' ').title()

                    # --- 1. JSON RADIO DEFINITIONS ---
                    if full_path.endswith('.json'):
                        try:
                            with open(full_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)

                            # Support {"radio": {...}}, {"radios": [...]}, or direct object
                            radio_nodes = []
                            if 'radio' in data:
                                r_val = data['radio']
                                radio_nodes = r_val if isinstance(r_val, list) else [r_val]
                            elif 'radios' in data:
                                r_val = data['radios']
                                if isinstance(r_val, dict):
                                    radio_nodes = list(r_val.values())
                                else:
                                    radio_nodes = r_val
                            elif 'station' in data or 'stations' in data:
                                r_val = data.get('station') or data.get('stations')
                                radio_nodes = r_val if isinstance(r_val, list) else [r_val]
                            elif 'name' in data or 'streams' in data:
                                radio_nodes = [data]

                            for node in radio_nodes:
                                if not isinstance(node, dict):
                                    continue

                                name = node.get('name') or fallback_name
                                freq = node.get('frequency') or node.get('freq') or 'random'
                                raw_schedule = node.get('stream_config') or node.get('schedule') or node.get('stream') or []
                                raw_streams = node.get('streams') or node.get('messages') or node.get('msg') or []

                                schedule = RadioManager._parse_schedule(raw_schedule)
                                messages = RadioManager._parse_messages(raw_streams)

                                RadioManager.STATIONS[name] = {
                                    'name': name,
                                    'frequency': freq,
                                    'schedule': schedule,
                                    'messages': messages
                                }
                                found_files += 1

                        except Exception as e:
                            print(f"[RadioManager] Error loading JSON radio '{filename}': {e}")

                    # --- 2. BACKWARD-COMPATIBLE XML FALLBACK ---
                    elif full_path.endswith('.xml'):
                        try:
                            tree = ET.parse(full_path)
                            root = tree.getroot()

                            nodes = []
                            if root.tag in ('radio', 'station'):
                                nodes.append(root)
                            else:
                                nodes.extend(root.findall('.//radio') + root.findall('.//station'))

                            for node in nodes:
                                name = node.get('name') or node.get('id') or fallback_name
                                freq = node.get('frequency') or node.get('freq') or 'random'
                                stream_raw = node.get('stream') or node.get('schedule') or ''
                                schedule = RadioManager._parse_schedule(stream_raw)

                                messages = []
                                for stream_node in (node.findall('stream') + node.findall('message') + node.findall('msg')):
                                    text = stream_node.get('text') or stream_node.text or ''
                                    text = text.replace('\\n', '\n').strip()
                                    if text:
                                        messages.append(text)

                                RadioManager.STATIONS[name] = {
                                    'name': name,
                                    'frequency': freq,
                                    'schedule': schedule,
                                    'messages': messages
                                }
                                found_files += 1

                        except Exception as e:
                            print(f"[RadioManager] Error loading XML radio '{filename}': {e}")

        print(f"[RadioManager] Loaded {len(RadioManager.STATIONS)} Radio Stations from {found_files} definitions.")