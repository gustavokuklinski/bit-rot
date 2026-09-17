# core/data/radio_manager.py

import os
import random
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
    def load_radios():
        RadioManager.STATIONS.clear()
        folders = RadioManager.get_radio_folders()

        if not folders:
            fallback = os.path.join(DATA_PATH, 'radio')
            os.makedirs(fallback, exist_ok=True)
            folders = [fallback]

        found_files = 0
        for radio_path in folders:
            for root_dir, _, filenames in os.walk(radio_path):
                for filename in filenames:
                    if filename.endswith('.xml'):
                        full_path = os.path.join(root_dir, filename)
                        try:
                            tree = ET.parse(full_path)
                            root = tree.getroot()

                            # Support both <radio> as root or container <radios><radio>...</radios>
                            nodes = []
                            if root.tag in ('radio', 'station'):
                                nodes.append(root)
                            else:
                                nodes.extend(root.findall('.//radio') + root.findall('.//station'))

                            for node in nodes:
                                fallback_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                                name = node.get('name') or node.get('id') or fallback_name
                                freq = node.get('frequency') or node.get('freq') or 'random'
                                stream_raw = node.get('stream') or node.get('schedule') or ''

                                schedule = []
                                if stream_raw.startswith('[') and stream_raw.endswith(']'):
                                    schedule = [s.strip() for s in stream_raw[1:-1].split(',')]
                                elif stream_raw:
                                    schedule = [stream_raw.strip()]

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
                            print(f"[RadioManager] Error loading {filename}: {e}")

        print(f"[RadioManager] Loaded {len(RadioManager.STATIONS)} Radio Stations from {found_files} definitions.")

    @staticmethod
    def sync_game_frequencies(game):
        """Ensures all XML stations are registered and assigned a unique frequency on the dial."""
        if not RadioManager.STATIONS:
            RadioManager.load_radios()

        if not hasattr(game, 'radio_frequencies') or game.radio_frequencies is None:
            game.radio_frequencies = {}

        used_freqs = set(game.radio_frequencies.values())

        for name, data in RadioManager.STATIONS.items():
            if name not in game.radio_frequencies:
                raw_freq = str(data.get('frequency', 'random')).replace('MHz', '').replace('mhz', '').strip()

                if raw_freq.lower() == 'random':
                    f = round(random.uniform(110.80, 123.20), 2)
                    attempts = 0
                    while any(abs(f - uf) <= 0.25 for uf in used_freqs) and attempts < 100:
                        f = round(random.uniform(110.80, 123.20), 2)
                        attempts += 1
                    game.radio_frequencies[name] = f
                    used_freqs.add(f)
                else:
                    try:
                        f = round(float(raw_freq), 2)
                        game.radio_frequencies[name] = f
                        used_freqs.add(f)
                    except ValueError:
                        f = round(random.uniform(110.80, 123.20), 2)
                        game.radio_frequencies[name] = f
                        used_freqs.add(f)