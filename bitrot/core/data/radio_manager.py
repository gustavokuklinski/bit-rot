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