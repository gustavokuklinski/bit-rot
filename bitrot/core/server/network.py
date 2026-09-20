# core/server/network.py
import struct
import socket
import threading
import queue
import msgpack

class NetMsg:
    JOIN_REQ = "JOIN_REQ"           # Client -> Server (TCP)
    JOIN_ACK = "JOIN_ACK"           # Server -> Client (TCP)
    JOIN_DENY = "JOIN_DENY"         # Server -> Client (TCP)
    DISCONNECT = "DISCONNECT"       # Either direction (TCP)
    PLAYER_UPDATE = "PLAYER_UPDATE" # Client -> Server (UDP)
    WORLD_SYNC = "WORLD_SYNC"       # Server -> Client (UDP)
    WORLD_ACTION = "WORLD_ACTION"   # Client -> Server (TCP)
    CHAT_BROADCAST = "CHAT_BROADCAST" # Either direction (TCP)
    ENTITY_DAMAGE = "ENTITY_DAMAGE" # Client -> Server (TCP)
    SERVER_CLOSED = "SERVER_CLOSED" # Server -> Client on shutdown (TCP)
    NEW_CHUNKS = "NEW_CHUNKS"       # Server -> Client (TCP)
    UDP_REGISTER = "UDP_REGISTER"   # Client -> Server (UDP handshake)

NetworkMessage = NetMsg

_sock_queues = {}
_sock_locks = {}
_registry_lock = threading.Lock()

def register_socket_queue(sock, q):
    """Registers an asynchronous outbox queue for a TCP socket."""
    with _registry_lock:
        _sock_queues[sock] = q

def unregister_socket(sock):
    """Removes a socket from registered queues and locks."""
    with _registry_lock:
        _sock_queues.pop(sock, None)
        _sock_locks.pop(sock, None)

def pack_payload(msg_dict):
    """Serializes a dictionary using msgpack."""
    return msgpack.packb(msg_dict, use_bin_type=True)

def unpack_payload(raw_bytes):
    """Deserializes raw msgpack bytes into a Python dictionary."""
    return msgpack.unpackb(raw_bytes, raw=False)

def send_msg(sock, msg_dict):
    """Sends a length-prefixed msgpack packet over a TCP socket."""
    if sock is None:
        return False

    with _registry_lock:
        q = _sock_queues.get(sock)
        if q is not None:
            q.put(msg_dict)
            return True
        lock = _sock_locks.setdefault(sock, threading.Lock())

    try:
        with lock:
            data = pack_payload(msg_dict)
            header = struct.pack('>I', len(data))
            sock.sendall(header + data)
            return True
    except Exception:
        return False

def recv_msgs(sock, buffer):
    """Reads available bytes from a non-blocking TCP socket into buffer."""
    messages = []
    try:
        chunk = sock.recv(65536)
        if not chunk:
            return messages, buffer, False
        buffer += chunk
    except (BlockingIOError, socket.error):
        pass
    except Exception:
        return messages, buffer, False

    while len(buffer) >= 4:
        msg_len = struct.unpack('>I', buffer[:4])[0]
        if len(buffer) < 4 + msg_len:
            break
        raw_msg = buffer[4:4 + msg_len]
        buffer = buffer[4 + msg_len:]
        try:
            parsed = unpack_payload(raw_msg)
            messages.append(parsed)
        except Exception:
            pass

    return messages, buffer, True