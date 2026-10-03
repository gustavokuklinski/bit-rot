import time
import threading

CLIENT_ID = "1555657488341143582"  # <-- Paste your Discord Application ID here

class DiscordManager:
    def __init__(self, client_id=CLIENT_ID):
        self.client_id = client_id
        self.rpc = None
        self.connected = False
        self.start_time = int(time.time())
        self.last_update_time = 0
        self.update_cooldown = 15.0  # Discord RPC limits updates to ~15s intervals

        self._connect_thread()

    def _connect_thread(self):
        """Attempts connection in a background thread to prevent game launch freezes."""
        def _connect():
            try:
                from pypresence import Presence
                self.rpc = Presence(self.client_id)
                self.rpc.connect()
                self.connected = True
                print("[Discord RPC] Connected successfully.")
            except Exception:
                self.connected = False

        threading.Thread(target=_connect, daemon=True).start()

    def update_presence(self, state="In Main Menu", details=None, large_image="logo_large", large_text="Bit Rot"):
        """Safely updates Discord Rich Presence without blocking the game."""
        if not self.connected or not self.rpc:
            return

        current_time = time.time()
        # Avoid spamming Discord's IPC rate limits
        if current_time - self.last_update_time < self.update_cooldown:
            return

        self.last_update_time = current_time

        def _send():
            try:
                self.rpc.update(
                    state=state,
                    details=details,
                    start=self.start_time,
                    large_image=large_image,
                    large_text=large_text
                )
            except Exception:
                # Disconnected (e.g. Discord closed by user)
                self.connected = False

        threading.Thread(target=_send, daemon=True).start()

    def close(self):
        """Disconnects cleanly when exiting the game."""
        if self.connected and self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
            self.connected = False