# core/systems/network_manager.py

import socket
import threading
import json
import time
import random
import re
import os
from core.data.config import get_writable_dir, TILE_SIZE
from core.data.localization import tr
from core.messages import display_message
from core.entities.item.item import Item

DEFAULT_PORT = 7170
DEFAULT_MAX_PEERS = 4

class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.is_server = False
        self.is_connected = False
        self.server_ip = ""
        self.server_port = DEFAULT_PORT
        self.max_peers = DEFAULT_MAX_PEERS
        
        # Sockets & Threads
        self.server_socket = None
        self.client_socket = None
        self.server_thread = None
        self.client_thread = None
        self.running = True
        
        # Connected Peers list: list of dicts: {'ip': str, 'port': int, 'freq': float, 'role': 'S'/'C', 'socket': sock}
        self.connected_peers = []
        self.peer_lock = threading.Lock()
        
        # Dedicated Frequency for this local player instance
        self.my_frequency = round(random.uniform(111.00, 122.90), 2)
        
        # Connection status message shown in Mobile UI
        self.status_message = ""
        self.status_is_error = False
        
        # Ping calculation
        self.last_ping_rtt = 0.0
        self.ping_start_time = 0.0
        
        # Recent IPs persistence
        self.recent_ips_file = os.path.join(get_writable_dir(), "data.rot", "save", "config", "radio_history.json")
        self.recent_ips = self.load_recent_ips()

    # --- IP History Management ---
    def load_recent_ips(self):
        if os.path.exists(self.recent_ips_file):
            try:
                with open(self.recent_ips_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data[:3]
            except Exception:
                pass
        return ["127.0.0.1:7170"]

    def save_recent_ip(self, ip_str):
        clean_ip = ip_str.strip()
        if not clean_ip:
            return
        if clean_ip in self.recent_ips:
            self.recent_ips.remove(clean_ip)
        self.recent_ips.insert(0, clean_ip)
        self.recent_ips = self.recent_ips[:3]
        try:
            os.makedirs(os.path.dirname(self.recent_ips_file), exist_ok=True)
            with open(self.recent_ips_file, "w") as f:
                json.dump(self.recent_ips, f, indent=4)
        except Exception:
            pass

    # --- Local IP Detection ---
    @staticmethod
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # --- Server Hosting ---
    def open_server(self, port=DEFAULT_PORT, max_peers=DEFAULT_MAX_PEERS):
        self.disconnect()
        self.server_port = int(port)
        self.max_peers = int(max_peers)
        self.is_server = True
        self.server_ip = self.get_local_ip()

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(("0.0.0.0", self.server_port))
            self.server_socket.listen(self.max_peers)
            self.is_connected = True
            
            with self.peer_lock:
                self.connected_peers = [{
                    'ip': self.server_ip,
                    'port': self.server_port,
                    'freq': self.my_frequency,
                    'role': 'S',
                    'socket': None
                }]

            self.status_message = f"Connected: Radio freq: {self.my_frequency:.2f}mhz"
            self.status_is_error = False
            
            self.server_thread = threading.Thread(target=self._server_listen_loop, daemon=True)
            self.server_thread.start()
            
            display_message(self.game, f"[LAN VOIP] Server listening on {self.server_ip}:{self.server_port} (Max: {self.max_peers})")
            return True
        except Exception as e:
            self.is_connected = False
            self.is_server = False
            self.status_message = "Connection failed"
            self.status_is_error = True
            display_message(self.game, f"[LAN VOIP] Failed to open server: {e}")
            return False

    def _server_listen_loop(self):
        while self.running and self.is_server:
            try:
                sock, addr = self.server_socket.accept()
                with self.peer_lock:
                    if len(self.connected_peers) >= self.max_peers:
                        reject_pkt = json.dumps({'type': 'rejected', 'reason': 'Server full'}) + "\n"
                        sock.sendall(reject_pkt.encode('utf-8'))
                        sock.close()
                        continue
                t = threading.Thread(target=self._server_client_handler, args=(sock, addr), daemon=True)
                t.start()
            except Exception:
                break

    def _server_client_handler(self, client_sock, client_addr):
        client_ip = client_addr[0]
        client_port = client_addr[1]
        buffer = ""
        peer_entry = None

        try:
            while self.running and self.is_connected:
                data = client_sock.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    pkt = json.loads(line)
                    
                    if pkt.get('type') == 'handshake':
                        client_freq = round(float(pkt.get('freq', 114.0)), 2)
                        with self.peer_lock:
                            peer_entry = {
                                'ip': client_ip,
                                'port': client_port,
                                'freq': client_freq,
                                'role': 'C',
                                'socket': client_sock
                            }
                            self.connected_peers.append(peer_entry)
                        
                        # Send welcome with full peer list
                        self._broadcast_peer_list()
                        display_message(self.game, f"[LAN VOIP] Peer connected from {client_ip} ({client_freq:.2f}mhz)")
                    else:
                        self._handle_incoming_packet(pkt, client_sock)
        except Exception:
            pass
        finally:
            with self.peer_lock:
                if peer_entry in self.connected_peers:
                    self.connected_peers.remove(peer_entry)
            try:
                client_sock.close()
            except Exception:
                pass
            self._broadcast_peer_list()

    def _broadcast_peer_list(self):
        """Sends current connected peers table to all clients."""
        with self.peer_lock:
            peers_info = [{
                'ip': p['ip'], 'port': p['port'], 'freq': p['freq'], 'role': p['role']
            } for p in self.connected_peers]
            
            pkt = json.dumps({'type': 'peers_update', 'peers': peers_info, 'max_peers': self.max_peers}) + "\n"
            for p in self.connected_peers:
                if p.get('socket'):
                    try:
                        p['socket'].sendall(pkt.encode('utf-8'))
                    except Exception:
                        pass

    # --- Client Connection ---
    def connect_to_peer(self, address_str):
        self.disconnect()
        address_str = address_str.strip()
        if not address_str:
            self.status_message = "Connection failed"
            self.status_is_error = True
            return False

        if ":" in address_str:
            ip, port_s = address_str.split(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                port = DEFAULT_PORT
        else:
            ip = address_str
            port = DEFAULT_PORT

        self.server_ip = ip
        self.server_port = port
        self.is_server = False

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(4.0)
            self.client_socket.connect((ip, port))
            self.client_socket.settimeout(None)
            self.is_connected = True

            # Send handshake with our local player frequency
            handshake = json.dumps({
                'type': 'handshake',
                'freq': self.my_frequency,
                'name': getattr(self.game.player, 'name', 'Survivor')
            }) + "\n"
            self.client_socket.sendall(handshake.encode('utf-8'))

            self.status_message = f"Connected: Radio freq: {self.my_frequency:.2f}mhz"
            self.status_is_error = False
            self.save_recent_ip(f"{ip}:{port}")

            self.client_thread = threading.Thread(target=self._client_receive_loop, daemon=True)
            self.client_thread.start()

            display_message(self.game, f"[LAN VOIP] Connected to {ip}:{port} (Radio: {self.my_frequency:.2f}mhz)")
            return True
        except Exception:
            self.is_connected = False
            self.status_message = "Connection failed"
            self.status_is_error = True
            return False

    def _client_receive_loop(self):
        buffer = ""
        try:
            while self.running and self.is_connected:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    pkt = json.loads(line)
                    self._handle_incoming_packet(pkt, self.client_socket)
        except Exception:
            pass
        finally:
            self.is_connected = False
            self.status_message = "Disconnected"
            self.status_is_error = True

    # --- Incoming Packet Dispatcher ---
    def _handle_incoming_packet(self, pkt, source_sock=None):
        p_type = pkt.get('type')

        # 1. Peers update from server
        if p_type == 'peers_update':
            with self.peer_lock:
                self.connected_peers = pkt.get('peers', [])
                self.max_peers = pkt.get('max_peers', self.max_peers)

        # 2. Ping request / response
        elif p_type == 'ping_req':
            pong = json.dumps({
                'type': 'ping_res',
                'freq': pkt.get('freq'),
                'origin_time': pkt.get('time')
            }) + "\n"
            self._send_raw_packet(pong, source_sock)

        elif p_type == 'ping_res':
            orig = pkt.get('origin_time', 0)
            if orig > 0:
                self.last_ping_rtt = round((time.time() - orig) * 1000.0, 1)
                display_message(self.game, f"[Radio {pkt.get('freq')}mhz] Pong received! Latency: {self.last_ping_rtt}ms")

        # 3. Radio Text Transmission
        elif p_type == 'radio_msg':
            target_freq = round(float(pkt.get('freq', 0)), 2)
            sender_name = pkt.get('sender', 'Unknown Survivor')
            msg_text = pkt.get('text', '')

            # If host server, forward to all other peers
            if self.is_server:
                self._forward_to_peers(pkt, exclude_sock=source_sock)

            # ONLY deliver message if tuned to the same frequency or sent directly to personal frequency
            is_my_freq = abs(target_freq - self.my_frequency) <= 0.05
            cur_radio_freq = getattr(self.game, 'current_radio_freq', None)
            is_tuned = (cur_radio_freq is not None and abs(cur_radio_freq - target_freq) <= 0.05)

            if is_tuned or is_my_freq:
                formatted = f"[Radio {target_freq:.2f}mhz] {sender_name}: {msg_text}"
                display_message(self.game, formatted)

                # Show radio transmission speech bubble above player
                if getattr(self.game, 'player', None):
                    truncated = msg_text if len(msg_text) <= 45 else (msg_text[:42] + "...")
                    self.game.player.chat_text = f"[{sender_name} @ {target_freq:.2f}mhz]\n{truncated}"
                    self.game.player.chat_timer = getattr(self.game.player, 'chat_duration', 300)
                
                if hasattr(self.game, 'sound_manager'):
                    self.game.sound_manager.play_sound(
                        "radio.ogg", subdir="radio", game=self.game, source_pos=None, base_volume=0.8, is_critical=True
                    )
                if hasattr(self.game, 'emit_noise') and getattr(self.game, 'player', None):
                    self.game.emit_noise(self.game.player.rect.center, radius=TILE_SIZE * 16, source_type="radio")

        # 4. Item Transfer Over Network
        elif p_type == 'item_send':
            target_freq = round(float(pkt.get('freq', 0)), 2)
            sender_name = pkt.get('sender', 'Survivor')
            item_data = pkt.get('item_data', {})

            if self.is_server:
                self._forward_to_peers(pkt, exclude_sock=source_sock)

            is_my_freq = abs(target_freq - self.my_frequency) <= 0.05
            cur_radio_freq = getattr(self.game, 'current_radio_freq', None)
            is_tuned = (cur_radio_freq is not None and abs(cur_radio_freq - target_freq) <= 0.05)

            if is_my_freq or is_tuned:
                self._receive_network_item(item_data, sender_name, target_freq)

    def _forward_to_peers(self, pkt, exclude_sock=None):
        if not self.is_server:
            return
        raw = json.dumps(pkt) + "\n"
        with self.peer_lock:
            for p in self.connected_peers:
                s = p.get('socket')
                if s and s != exclude_sock:
                    try:
                        s.sendall(raw.encode('utf-8'))
                    except Exception:
                        pass

    def _send_raw_packet(self, raw_str, direct_sock=None):
        if direct_sock:
            try:
                direct_sock.sendall(raw_str.encode('utf-8'))
                return
            except Exception:
                pass
        if self.is_server:
            with self.peer_lock:
                for p in self.connected_peers:
                    s = p.get('socket')
                    if s:
                        try:
                            s.sendall(raw_str.encode('utf-8'))
                        except Exception:
                            pass
        elif self.client_socket and self.is_connected:
            try:
                self.client_socket.sendall(raw_str.encode('utf-8'))
            except Exception:
                pass

    # --- Outgoing Actions ---
    def send_radio_message(self, target_freq, message):
        """Broadcasts a radio message to all peers tuned to target_freq."""
        if not self.is_connected:
            display_message(self.game, tr('msg', "Not connected to any LAN radio network."))
            return

        target_freq = round(float(target_freq), 2)
        sender_name = getattr(self.game.player, 'name', 'Survivor')
        pkt = {
            'type': 'radio_msg',
            'freq': target_freq,
            'sender': sender_name,
            'text': message
        }
        raw = json.dumps(pkt) + "\n"
        self._send_raw_packet(raw)

        # Local echo
        display_message(self.game, f"[Radio {target_freq:.2f}mhz] You: {message}")
        if hasattr(self.game, 'sound_manager'):
            self.game.sound_manager.play_sound("radio.ogg", subdir="radio", game=self.game, base_volume=0.8, is_critical=True)
        if hasattr(self.game, 'emit_noise') and getattr(self.game, 'player', None):
            self.game.emit_noise(self.game.player.rect.center, radius=TILE_SIZE * 15, source_type="radio")

    def send_item(self, target_freq, item_name):
        """Transfers an item from player's inventory across the network to a peer."""
        if not self.is_connected:
            display_message(self.game, tr('msg', "Not connected to any LAN radio network."))
            return

        if not getattr(self.game, 'player', None):
            return

        target_item = None
        inv = self.game.player.inventory
        for idx, it in enumerate(inv):
            if it and (it.name.lower() == item_name.lower() or item_name.lower() in it.name.lower()):
                target_item = it
                # Deduct from inventory
                if hasattr(it, 'load') and it.load is not None and it.load > 1 and it.is_stackable():
                    it.load -= 1
                    target_item = Item.create_from_name(it.name)
                    target_item.load = 1
                else:
                    inv.pop(idx)
                break

        if not target_item:
            display_message(self.game, f"[LAN VOIP] Item '{item_name}' not found in inventory.")
            return

        item_dict = target_item.to_dict() if hasattr(target_item, 'to_dict') else {'name': target_item.name}

        pkt = {
            'type': 'item_send',
            'freq': round(float(target_freq), 2),
            'sender': getattr(self.game.player, 'name', 'Survivor'),
            'item_data': item_dict
        }
        self._send_raw_packet(json.dumps(pkt) + "\n")
        display_message(self.game, f"[LAN VOIP] Sent '{target_item.name}' across frequency {target_freq:.2f}mhz.")
        if hasattr(self.game, 'sound_manager'):
            self.game.sound_manager.play_sound("grab.ogg", subdir="items", game=self.game, base_volume=0.5, is_critical=True)

    def _receive_network_item(self, item_dict, sender_name, freq):
        """Unpacks item and places it into player inventory or drops at feet."""
        new_item = Item.from_dict(item_dict) if isinstance(item_dict, dict) else Item.create_from_name(item_dict)
        if not new_item:
            return

        player = getattr(self.game, 'player', None)
        if not player:
            return

        if len(player.inventory) < player.get_total_inventory_slots():
            player.inventory.append(new_item)
            if hasattr(player, 'stack_item_in_inventory'):
                player.stack_item_in_inventory(new_item)
            display_message(self.game, f"[Air-Drop] Received '{new_item.name}' from {sender_name} ({freq:.2f}mhz) into inventory!")
        else:
            new_item.rect.center = player.rect.center
            new_item.x, new_item.y = new_item.rect.topleft
            new_item.layer = getattr(self.game, 'current_layer_index', 1)
            self.game.items_on_ground.append(new_item)
            display_message(self.game, f"[Air-Drop] Received '{new_item.name}' from {sender_name} ({freq:.2f}mhz). Inventory full: dropped at your feet.")

        if hasattr(self.game, 'sound_manager'):
            self.game.sound_manager.play_sound("grab.ogg", subdir="items", game=self.game, base_volume=0.6, is_critical=True)

    def send_ping(self, target_freq):
        """Sends a ping request packet to calculate latency."""
        if not self.is_connected:
            display_message(self.game, tr('msg', "Not connected to any LAN radio network."))
            return

        self.ping_start_time = time.time()
        pkt = {
            'type': 'ping_req',
            'freq': round(float(target_freq), 2),
            'time': self.ping_start_time
        }
        self._send_raw_packet(json.dumps(pkt) + "\n")
        display_message(self.game, f"[Radio] Pinging frequency {target_freq}mhz...")

    def disconnect(self):
        self.is_connected = False
        self.is_server = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
            self.client_socket = None
        with self.peer_lock:
            self.connected_peers.clear()