# core/multiplayer/network.py
import socket
import threading

class GameNetworkServer:
    """
    A minimalist TCP socket server designed for local multiplayer sync.
    Binds to an ephemeral port (port 0) for zero-configuration local networking.
    """
    def __init__(self, host="0.0.0.0", port=0):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_running = False
        self.clients = []
        self.client_lock = threading.Lock()

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            # Fetch the dynamically assigned port from the OS
            actual_port = self.server_socket.getsockname()[1]
            self.is_running = True
            
            print(f"[Network] Server listening on Local Port: {actual_port}")
            
            self._accept_loop()
        except Exception as e:
            print(f"[Network] Critical error starting server: {e}")

    def _accept_loop(self):
        while self.is_running:
            try:
                # Block until a new player connects
                client_socket, client_address = self.server_socket.accept()
                print(f"[Network] Connection established with {client_address}")
                
                with self.client_lock:
                    self.clients.append(client_socket)
                
                # Handle individual client in their own thread to avoid blocking
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
            except socket.error:
                if self.is_running:
                    print("[Network] Socket interrupted.")
                    
    def _handle_client(self, client_socket, client_address):
        try:
            while self.is_running:
                data = client_socket.recv(4096)
                if not data:
                    break # Graceful disconnect from client
                
                # Future Implementation: Decode game states, entity updates, 
                # and broadcast to other connected clients.
                
        except ConnectionResetError:
            print(f"[Network] Connection lost with {client_address}")
        except Exception as e:
            print(f"[Network] Error handling client {client_address}: {e}")
        finally:
            self._disconnect_client(client_socket, client_address)

    def _disconnect_client(self, client_socket, client_address):
        print(f"[Network] Client disconnected: {client_address}")
        with self.client_lock:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
        try:
            client_socket.close()
        except:
            pass

    def stop(self):
        self.is_running = False
        print("[Network] Stopping server and disconnecting clients...")
        with self.client_lock:
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass
            self.clients.clear()
        
        try:
            self.server_socket.close()
        except:
            pass