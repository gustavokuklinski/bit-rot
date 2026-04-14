# core/multiplayer/client.py
import socket
import os
from core.data.config import get_writable_dir

class GameNetworkClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(3.0) # 3s timeout to prevent freezing
        self.is_connected = False
        self.server_name = "Local_Server"

    def connect(self, ip, port):
        """Attempts a TCP handshake with the designated server."""
        try:
            self.socket.connect((ip, int(port)))
            self.is_connected = True
            
            # Future expansion: Receive server name here.
            # self.socket.sendall(b"HANDSHAKE")
            # self.server_name = self.socket.recv(1024).decode()
            
            print(f"[Network Client] Handshake successful with {ip}:{port}")
            return True
        except Exception as e:
            print(f"[Network Client] Handshake failed: {e}")
            return False
            
    def handle_death(self, player_name):
        """Called when the player dies on a dedicated server to delete their local sync .rot"""
        player_file = os.path.join(get_writable_dir(), "game", "save", "server", self.server_name, f"{player_name}.rot")
        if os.path.exists(player_file):
            try:
                os.remove(player_file)
                print(f"[Multiplayer] Deleted dead player profile: {player_file}")
            except Exception as e:
                print(f"[Multiplayer] Error deleting file: {e}")

    def disconnect(self):
        self.is_connected = False
        try: self.socket.close()
        except: pass