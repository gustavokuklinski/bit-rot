# core/data/radio_manager.py

import os
import xml.etree.ElementTree as ET
from core.data.config import DATA_PATH

class RadioManager:
    STATIONS = {}

    @staticmethod
    def load_radios():
        radio_path = os.path.join(DATA_PATH, 'radio')
        if not os.path.exists(radio_path):
            os.makedirs(radio_path, exist_ok=True)
            return

        RadioManager.STATIONS.clear()

        for filename in os.listdir(radio_path):
            if filename.endswith('.xml'):
                try:
                    tree = ET.parse(os.path.join(radio_path, filename))
                    root = tree.getroot()
                    
                    if root.tag == 'radio':
                        name = root.get('name', 'Unknown Radio')
                        freq = root.get('frequency', 'random')
                        stream_raw = root.get('stream', '')
                        
                        schedule = []
                        if stream_raw.startswith('[') and stream_raw.endswith(']'):
                            schedule = [s.strip() for s in stream_raw[1:-1].split(',')]
                        
                        messages = []
                        for stream_node in root.findall('stream'):
                            text = stream_node.get('text', '')
                            # Allow newlines natively from XML using \n
                            text = text.replace('\\n', '\n')
                            if text:
                                messages.append(text)
                            
                        RadioManager.STATIONS[name] = {
                            'name': name,
                            'frequency': freq,
                            'schedule': schedule,
                            'messages': messages
                        }
                        
                except Exception as e:
                    print(f"Error loading radio XML {filename}: {e}")
                    
        print(f"Loaded {len(RadioManager.STATIONS)} Radio Stations.")