# core/server/server.py
import socket
import os
import json
import uuid
import platform
import select
import math
import threading
import queue
import time
import struct
import pygame
from core.data.config import get_writable_dir, TILE_SIZE
import core.data.config
from core.server.network import (
    NetMsg, send_msg, recv_msgs, register_socket_queue, 
    unregister_socket, pack_payload, unpack_payload
)
from core.server.remote_player import RemotePlayer
from core.messages import display_message
from core.placement import find_free_tile
from core.entities.animal.animal import Animal
from core.entities.zombie.corpse import Corpse

class GameServer:
    def __init__(self, game):
        self.game = game
        self.server_socket = None
        self.udp_socket = None
        self.port = 0
        self.ip = ""
        self.running = False
        self.clients = {}  # sock -> info dict
        self.udp_clients = {}  # player_id -> (ip, port)
        self.sync_counter = 0
        self.known_chunk_files = set()

        # Threading infrastructure
        self.inbox = queue.Queue()            
        self.broadcast_queue = queue.Queue()  
        self.worker_thread = None

    def start(self):
        if self.running:
            return True, self.ip, self.port

        try:
            self.max_clients = getattr(core.data.config, 'MAX_CLIENTS', 16)
            
            # 1. TCP Server (Reliable Connection)
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.server_socket.bind(("", 0))
            self.server_socket.listen(10)
            self.server_socket.setblocking(False)

            self.port = self.server_socket.getsockname()[1]
            from core.systems.save_manager import get_host_ip
            self.ip = get_host_ip()

            # 2. UDP Server (High-frequency state synchronization)
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(("", self.port))
            self.udp_socket.setblocking(False)

            self.running = True

            map_dir = getattr(self.game.map_manager, 'map_folder', None)
            if map_dir and os.path.exists(map_dir):
                self.known_chunk_files = set(f for f in os.listdir(map_dir) if f.endswith('.csv'))

            # Launch background worker
            self.worker_thread = threading.Thread(target=self._network_worker, daemon=True)
            self.worker_thread.start()

            return True, self.ip, self.port
        except Exception as e:
            if hasattr(self.game, 'logger'):
                self.game.logger.error(f"Failed to start server: {e}")
            return False, "", 0

    def stop(self):
        if not self.running:
            return

        self.running = False
        for sock in list(self.clients.keys()):
            send_msg(sock, {'type': NetMsg.SERVER_CLOSED})
            unregister_socket(sock)
            try:
                sock.close()
            except Exception:
                pass
        self.clients.clear()
        self.udp_clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
            self.server_socket = None

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception:
                pass
            self.udp_socket = None

        if hasattr(self.game, 'remote_players'):
            self.game.remote_players.clear()

    def _network_worker(self):
        worker_clients = {}  

        while self.running and self.server_socket and self.udp_socket:
            while not self.broadcast_queue.empty():
                try:
                    msg_dict, target_socks = self.broadcast_queue.get_nowait()
                    data = pack_payload(msg_dict)
                    header = struct.pack('>I', len(data))
                    packet = header + data

                    dest_socks = target_socks if target_socks is not None else list(worker_clients.keys())
                    for s in dest_socks:
                        try:
                            s.sendall(packet)
                        except Exception:
                            pass
                except queue.Empty:
                    break
                except Exception:
                    pass

            for s, c_data in list(worker_clients.items()):
                out_q = c_data['outbox']
                while not out_q.empty():
                    try:
                        msg = out_q.get_nowait()
                        data = pack_payload(msg)
                        header = struct.pack('>I', len(data))
                        s.sendall(header + data)
                    except queue.Empty:
                        break
                    except Exception:
                        break

            readable = [self.server_socket, self.udp_socket] + list(worker_clients.keys())
            try:
                r_list, _, _ = select.select(readable, [], [], 0.002)
            except Exception:
                r_list = []

            for s in r_list:
                if s == self.server_socket:
                    try:
                        client_sock, addr = self.server_socket.accept()
                        client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        client_sock.setblocking(False)
                        out_q = queue.Queue()
                        worker_clients[client_sock] = {'buffer': b'', 'outbox': out_q}
                        register_socket_queue(client_sock, out_q)
                        self.inbox.put(('CONNECT', client_sock, addr[0]))
                    except Exception:
                        pass
                elif s == self.udp_socket:
                    try:
                        data, addr = self.udp_socket.recvfrom(65535)
                        msg = unpack_payload(data)
                        self.inbox.put(('UDP_MSG', addr, msg))
                    except Exception:
                        pass
                else:
                    c_data = worker_clients.get(s)
                    if not c_data:
                        continue
                    msgs, c_data['buffer'], is_alive = recv_msgs(s, c_data['buffer'])
                    if not is_alive:
                        unregister_socket(s)
                        worker_clients.pop(s, None)
                        self.inbox.put(('DISCONNECT', s, None))
                    else:
                        for msg in msgs:
                            self.inbox.put(('MSG', s, msg))

        for s in list(worker_clients.keys()):
            unregister_socket(s)
            try:
                s.close()
            except Exception:
                pass

    def update(self):
        if not self.running:
            return

        while not self.inbox.empty():
            try:
                event_type, source, payload = self.inbox.get_nowait()
            except queue.Empty:
                break

            if event_type == 'CONNECT':
                sock, client_ip = source, payload
                self.clients[sock] = {
                    'uip': client_ip,
                    'id': None,
                    'player': None,
                    'last_data': None
                }
            elif event_type == 'DISCONNECT':
                self._handle_client_disconnect(source)
            elif event_type == 'MSG':
                sock, msg = source, payload
                c_info = self.clients.get(sock)
                if c_info:
                    self._handle_client_msg(sock, c_info, msg)
            elif event_type == 'UDP_MSG':
                addr, msg = source, payload
                self._handle_udp_msg(addr, msg)

        if hasattr(self.game, 'map_manager'):
            for rp in getattr(self.game, 'remote_players', {}).values():
                self.game.map_manager.update_chunks(rp.rect.center)

        self.sync_counter += 1
        if self.sync_counter % 2 == 0 and (self.clients or self.udp_clients) and hasattr(self.game, 'player') and self.game.player:
            self._broadcast_world_sync_udp()

        if self.sync_counter % 30 == 0 and self.clients:
            map_dir = getattr(self.game.map_manager, 'map_folder', None)
            if map_dir and os.path.exists(map_dir):
                current_files = set(f for f in os.listdir(map_dir) if f.endswith('.csv'))
                new_files = current_files - self.known_chunk_files
                if new_files:
                    chunk_payload = {}
                    for fname in new_files:
                        try:
                            with open(os.path.join(map_dir, fname), 'r', encoding='utf-8') as f:
                                chunk_payload[fname] = f.read()
                            self.known_chunk_files.add(fname)
                        except Exception:
                            pass
                    if chunk_payload:
                        self.broadcast_queue.put(({'type': NetMsg.NEW_CHUNKS, 'chunk_files': chunk_payload}, None))

    def _handle_udp_msg(self, addr, msg):
        m_type = msg.get('type')
        if m_type == NetMsg.UDP_REGISTER:
            p_id = msg.get('player_id')
            if p_id:
                self.udp_clients[p_id] = addr
        elif m_type == NetMsg.PLAYER_UPDATE:
            p_id = msg.get('id')
            if p_id:
                self.udp_clients[p_id] = addr
                rp = getattr(self.game, 'remote_players', {}).get(p_id)
                if rp:
                    rp.update_from_network(msg)
                for c in self.clients.values():
                    if c.get('id') == p_id:
                        c['last_data'] = msg
                        break

    def _broadcast_world_sync_udp(self):
        if not self.udp_socket or not self.udp_clients:
            return

        all_players = []
        host_wpn = self.game.player.active_weapon.name if self.game.player.active_weapon else None
        clothes_simple = {slot: (item.name if item else None) for slot, item in getattr(self.game.player, 'clothes', {}).items()}
        clothes_colors = {slot: item.color for slot, item in getattr(self.game.player, 'clothes', {}).items() if item and hasattr(item, 'color')}

        all_players.append({
            'id': getattr(self.game.player, 'player_id', 'host'),
            'name': self.game.player.name,
            'x': round(self.game.player.x, 1),
            'y': round(self.game.player.y, 1),
            'facing': self.game.player.facing_direction,
            'aim_angle': round(self.game.player.aim_angle, 2),
            'is_moving': self.game.player.is_moving,
            'is_running': self.game.player.is_running,
            'is_aiming': getattr(self.game.player, 'is_aiming', False),
            'health': self.game.player.health,
            'max_health': self.game.player.max_health,
            'is_dead': self.game.player.is_dead,
            'weapon': host_wpn,
            'clothes': clothes_simple,
            'clothes_colors': clothes_colors,
            'swing_timer': getattr(self.game.player, 'melee_swing_timer', 0),
            'swing_angle': round(getattr(self.game.player, 'melee_swing_angle', 0), 2),
            'action_timer': getattr(self.game.player, 'action_timer', 0),
            'action_total_time': getattr(self.game.player, 'action_total_time', 0),
            'action_name': getattr(self.game.player, 'action_name', '')
        })

        for s, info in self.clients.items():
            if info.get('last_data'):
                all_players.append(info['last_data'])

        zombies_data = []
        for z in getattr(self.game, 'active_zombies', self.game.zombies):
            if getattr(z, 'is_dead', False):
                continue
            cl = {slot: (item.name if item else None) for slot, item in getattr(z, 'clothes', {}).items()}
            cl_col = {slot: item.color for slot, item in getattr(z, 'clothes', {}).items() if item and hasattr(item, 'color')}
            zombies_data.append({
                'id': getattr(z, 'id', str(id(z))),
                'name': getattr(z, 'name', 'Zombie'),
                'x': round(z.x, 1),
                'y': round(z.y, 1),
                'hp': int(z.health),
                'max_hp': int(z.max_health),
                'vx': round(getattr(z, 'vx', 0), 2),
                'vy': round(getattr(z, 'vy', 0), 2),
                'anim': round(getattr(z, 'walk_anim_angle', 0), 2),
                'hb_timer': getattr(z, 'show_health_bar_timer', 0),
                'clothes': cl,
                'clothes_colors': cl_col
            })

        npcs_data = []
        for n in getattr(self.game, 'npcs', []):
            if getattr(n, 'is_dead', False):
                continue
            wpn = n.equipped_weapon.name if getattr(n, 'equipped_weapon', None) else None
            cl = {slot: (item.name if item else None) for slot, item in getattr(n, 'clothes', {}).items()}
            cl_col = {slot: item.color for slot, item in getattr(n, 'clothes', {}).items() if item and hasattr(item, 'color')}
            npcs_data.append({
                'id': getattr(n, 'id', str(id(n))),
                'name': n.name,
                'x': round(n.x, 1),
                'y': round(n.y, 1),
                'hp': int(n.health),
                'max_hp': int(n.max_health),
                'is_friendly': getattr(n, 'is_friendly', True),
                'is_static': getattr(n, 'is_static', False),
                'hb_timer': getattr(n, 'health_bar_timer', 0),
                'weapon': wpn,
                'clothes': cl,
                'clothes_colors': cl_col,
                'anim': round(getattr(n, 'walk_anim_angle', 0), 2)
            })

        animals_data = []
        all_animals = list(getattr(self.game, 'active_animals', [])) + [i for i in getattr(self.game, 'items_on_ground', []) if getattr(i, 'type', '') == 'animal' or isinstance(i, Animal)]
        seen_animal_ids = set()
        for a in all_animals:
            if getattr(a, 'is_dead', False):
                continue
            aid = getattr(a, 'id', str(id(a)))
            if aid in seen_animal_ids:
                continue
            seen_animal_ids.add(aid)
            animals_data.append({
                'id': aid,
                'name': getattr(a, 'name', 'Rat'),
                'x': round(a.x, 1),
                'y': round(a.y, 1),
                'hp': int(a.health),
                'max_hp': int(a.max_health),
                'dx': round(getattr(a, 'dx', 0), 2),
                'dy': round(getattr(a, 'dy', 0), 2)
            })

        vehicles_data = []
        for v in getattr(self.game.map_manager, 'vehicles', []):
            vehicles_data.append({
                'id': getattr(v, 'id', str(id(v))),
                'name': v.name,
                'x': round(v.x, 1),
                'y': round(v.y, 1),
                'facing': getattr(v, 'facing', 'right'),
                'active': v.active,
                'lights': getattr(v, 'lights', 'off')
            })

        items_data = []
        for it in getattr(self.game, 'items_on_ground', []):
            if isinstance(it, Animal) or getattr(it, 'type', '') == 'animal':
                continue
            d = it.to_dict() if hasattr(it, 'to_dict') else {}
            d['id'] = getattr(it, 'id', str(id(it)))
            d['name'] = it.name
            d['x'] = it.rect.x
            d['y'] = it.rect.y
            d['is_corpse'] = isinstance(it, Corpse)
            d['is_player_corpse'] = getattr(it, 'is_player_corpse', False)
            d['state'] = getattr(it, 'state', None)
            if getattr(it, 'load', None) is not None:
                d['load'] = it.load
            items_data.append(d)

        containers_data = []
        for c in getattr(self.game, 'containers', []):
            if getattr(c, 'item_type', '') == 'maptile_container':
                containers_data.append({
                    'x': c.rect.x,
                    'y': c.rect.y,
                    'is_opened': getattr(c, 'is_opened', False),
                    'is_opening': getattr(c, 'is_opening', False), # <--- ADD THIS
                    'inventory': [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(c, 'inventory', [])]
                })

        projectiles_data = []
        for p in getattr(self.game, 'projectiles', []):
            projectiles_data.append({
                'x': round(p.x, 1), 
                'y': round(p.y, 1), 
                'prev_x': round(p.prev_x, 1), 
                'prev_y': round(p.prev_y, 1), 
                'color': p.color
            })

        tile_health_data = []
        map_name = getattr(self.game.map_manager, 'current_map_filename', '')
        if map_name in getattr(self.game, 'map_states', {}) and 'tile_health' in self.game.map_states[map_name]:
            for (gx, gy), hp in self.game.map_states[map_name]['tile_health'].items():
                if self.game.map_manager.tile_hit_timers.get((gx, gy), 0) > 0:
                    tile_health_data.append({'x': gx, 'y': gy, 'hp': hp})

        blood_data = []
        if hasattr(self.game, 'blood_stains'):
            for s in self.game.blood_stains[-40:]:
                blood_data.append({
                    'x': int(s['pos'][0]),
                    'y': int(s['pos'][1]),
                    'size': s.get('size', 4),
                    'color': tuple(s.get('color', (139, 0, 0)))
                })

        sync_packet = {
            'type': NetMsg.WORLD_SYNC,
            'players': all_players,
            'zombies': zombies_data,
            'npcs': npcs_data,
            'animals': animals_data,
            'vehicles': vehicles_data,
            'items': items_data,
            'containers': containers_data,
            'projectiles': projectiles_data,
            'tile_health': tile_health_data,
            'blood': blood_data,
            'time_ms': getattr(self.game.world_time, 'game_time_ms', 0),
            'weather': getattr(self.game.world_time, 'weather', 'CLEAR'),
            'day_count': getattr(self.game.world_time, 'day_count', 0)
        }

        try:
            udp_payload = pack_payload(sync_packet)
            for addr in list(self.udp_clients.values()):
                try:
                    self.udp_socket.sendto(udp_payload, addr)
                except Exception:
                    pass
        except Exception:
            pass

    def _handle_client_msg(self, sock, c_info, msg):
        m_type = msg.get('type')

        if m_type == NetMsg.JOIN_REQ:
            active_client_count = sum(1 for c in self.clients.values() if c.get('id') is not None)
            max_limit = getattr(self, 'max_clients', getattr(core.data.config, 'MAX_CLIENTS', 16))

            if active_client_count >= max_limit:
                send_msg(sock, {
                    'type': NetMsg.JOIN_DENY,
                    'reason': f"Server is full (Max {max_limit} players)."
                })
                self._handle_client_disconnect(sock)
                return

            client_ip = c_info['uip']
            requested_id = msg.get('player_id')
            p_name = msg.get('name', 'Survivor')
            raw_player_data = msg.get('player_data', {})

            save_folder = self.game.current_save_folder_name or "save_multiplayer"
            save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_folder)
            map_path = getattr(self.game.map_manager, 'map_folder', os.path.join(save_path, "map"))
            current_map = getattr(self.game.map_manager, 'current_map_filename', 'map_L1_0_0_map.csv')

            remote_dir = os.path.join(save_path, "player", "remote")
            os.makedirs(remote_dir, exist_ok=True)

            matched_file = None
            assigned_id = requested_id

            if requested_id:
                candidate = f"{client_ip}-{requested_id}.rot"
                if os.path.exists(os.path.join(remote_dir, candidate)):
                    matched_file = candidate

            if not matched_file:
                for fname in os.listdir(remote_dir):
                    if fname.startswith(f"{client_ip}-") and fname.endswith(".rot"):
                        matched_file = fname
                        assigned_id = fname[len(client_ip) + 1:-4]
                        break

            restored_player_data = None
            if matched_file:
                try:
                    with open(os.path.join(remote_dir, matched_file), 'r') as pf:
                        restored_player_data = json.load(pf)
                    p_name = restored_player_data.get('name', p_name)
                    assigned_id = restored_player_data.get('player_id', assigned_id)
                except Exception:
                    pass

            if not assigned_id:
                assigned_id = str(uuid.uuid4())

            c_info['id'] = assigned_id
            c_info['name'] = p_name

            spawn_x, spawn_y = self.game.player.x, self.game.player.y
            if restored_player_data and 'x' in restored_player_data:
                spawn_x = restored_player_data['x']
                spawn_y = restored_player_data['y']

            test_rect = pygame.Rect(int(spawn_x), int(spawn_y), TILE_SIZE, TILE_SIZE)
            free_pos = find_free_tile(test_rect, getattr(self.game, 'obstacles', []), initial_pos=(spawn_x, spawn_y), max_radius=8)
            if free_pos:
                spawn_x, spawn_y = free_pos

            remote_p = RemotePlayer(assigned_id, p_name, spawn_x, spawn_y)
            c_info['player'] = remote_p

            if not hasattr(self.game, 'remote_players'):
                self.game.remote_players = {}
            self.game.remote_players[assigned_id] = remote_p

            save_data = restored_player_data or raw_player_data
            save_data['player_id'] = assigned_id
            save_data['name'] = p_name
            save_data['x'] = spawn_x
            save_data['y'] = spawn_y
            self._save_remote_player_to_disk(client_ip, assigned_id, save_data)

            chunk_files = {}
            if os.path.exists(map_path):
                for fname in os.listdir(map_path):
                    if fname.endswith('.csv'):
                        fpath = os.path.join(map_path, fname)
                        try:
                            with open(fpath, 'r', encoding='utf-8') as cf:
                                chunk_files[fname] = cf.read()
                        except Exception:
                            pass

            ack_payload = {
                'type': NetMsg.JOIN_ACK,
                'player_id': assigned_id,
                'server_udp_port': self.port,
                'save_folder_name': save_folder,
                'map_filename': current_map,
                'spawn_x': spawn_x,
                'spawn_y': spawn_y,
                'restored_data': restored_player_data,
                'chunk_files': chunk_files,
                'time_data': {
                    'game_time_ms': getattr(self.game.world_time, 'game_time_ms', 0),
                    'day_count': getattr(self.game.world_time, 'day_count', 0)
                } if hasattr(self.game, 'world_time') else None
            }
            send_msg(sock, ack_payload)
            display_message(self.game, f"[Server] Player '{p_name}' ({client_ip}) joined the game.")

        elif m_type == NetMsg.PLAYER_UPDATE:
            p_id = c_info.get('id')
            if p_id:
                msg['id'] = p_id
                c_info['last_data'] = msg
                if c_info.get('player'):
                    c_info['player'].update_from_network(msg)

        elif m_type == NetMsg.ENTITY_DAMAGE:
            e_type = msg.get('entity_type')
            e_id = msg.get('id')
            dmg = msg.get('damage', 1)
            kb_x = msg.get('kb_x')
            kb_y = msg.get('kb_y')

            if e_type == 'player':
                target_id = e_id
                host_id = getattr(self.game.player, 'player_id', 'host')
                
                # Check target is alive
                is_host_target = (target_id in (host_id, 'host'))
                target_alive = True
                if is_host_target and (not self.game.player or self.game.player.health <= 0 or self.game.player.is_dead):
                    target_alive = False
                elif not is_host_target:
                    rp = self.game.remote_players.get(target_id)
                    if not rp or rp.health <= 0 or rp.is_dead:
                        target_alive = False
                
                if target_alive:
                    if is_host_target:
                        self.game.player.take_damage(self.game, dmg, msg.get('infection', 0))
                        from core.update.combat import create_blood_splatter
                        create_blood_splatter(self.game, self.game.player.rect, dmg)
                    else:
                        for s, info in self.clients.items():
                            if info.get('id') == target_id:
                                send_msg(s, {
                                    'type': NetMsg.ENTITY_DAMAGE,
                                    'entity_type': 'player',
                                    'damage': dmg,
                                    'infection': msg.get('infection', 0)
                                })
                                break

            elif e_type == 'zombie':
                for z in getattr(self.game, 'active_zombies', []) + getattr(self.game, 'zombies', []):
                    if getattr(z, 'id', None) == e_id:
                        if kb_x is not None and kb_y is not None:
                            z.knockback_velocity = [float(kb_x), float(kb_y)]
                            z.knockback_timer = 200

                        if z.take_damage(dmg, self.game, attacker=c_info.get('player')):
                            z.die(self.game)
                        else:
                            z.aggro_timer = 10000
                            z.state = 'chasing'
                        break

            elif e_type == 'animal':
                all_animals = list(getattr(self.game, 'active_animals', [])) + [i for i in getattr(self.game, 'items_on_ground', []) if getattr(i, 'type', '') == 'animal' or isinstance(i, Animal)]
                for a in all_animals:
                    if getattr(a, 'id', None) == e_id:
                        if kb_x is not None and kb_y is not None:
                            a.knockback_velocity = [float(kb_x), float(kb_y)]
                            a.knockback_timer = 200

                        if a.take_damage(dmg, self.game, attacker=c_info.get('player')):
                            a.die(self.game)
                        break

            elif e_type == 'npc':
                for n in getattr(self.game, 'npcs', []):
                    if getattr(n, 'id', None) == e_id:
                        if kb_x is not None and kb_y is not None:
                            n.knockback_velocity = [float(kb_x), float(kb_y)]
                            n.knockback_timer = 200

                        if n.take_damage(dmg, self.game, attacker=c_info.get('player')):
                            n.die(self.game)
                        break

        elif m_type == NetMsg.WORLD_ACTION:
            action = msg.get('action')

            if action == 'drop':
                from core.entities.item.item import Item
                item_data = msg.get('item_data')
                existing = next((it for it in self.game.items_on_ground if getattr(it, 'id', None) == item_data.get('id')), None)
                if existing:
                    existing.x = msg.get('x')
                    existing.y = msg.get('y')
                    existing.rect.topleft = (existing.x, existing.y)
                    existing.is_placed = msg.get('is_placed', False)
                else:
                    item = Item.from_dict(item_data)
                    if item:
                        item.x, item.y = msg.get('x'), msg.get('y')
                        item.rect.topleft = (item.x, item.y)
                        item.is_placed = msg.get('is_placed', False)
                        self.game.items_on_ground.append(item)

            elif action == 'pickup':
                item_id = msg.get('id')
                for it in self.game.items_on_ground:
                    if getattr(it, 'id', None) == item_id:
                        self.game.items_on_ground.remove(it)
                        break
            
            elif action == 'update_item':
                iid = msg.get('id')
                item_data = msg.get('item_data', {})
                for idx, it in enumerate(self.game.items_on_ground):
                    if getattr(it, 'id', None) == iid:
                        new_it = Item.from_dict(item_data)
                        if new_it:
                            new_it.x = it.x
                            new_it.y = it.y
                            new_it.rect.topleft = it.rect.topleft
                            self.game.items_on_ground[idx] = new_it
                        break
                        
            elif action == 'update_vehicle':
                vid = msg.get('id')
                for v in getattr(self.game.map_manager, 'vehicles', []):
                    if getattr(v, 'id', None) == vid:
                        v.lights = msg.get('lights', 'off')
                        v.active = msg.get('active', False)
                        break

            elif action == 'lock_container':
                cx, cy = msg.get('x'), msg.get('y')
                for c in self.game.containers:
                    if hasattr(c, 'rect') and c.rect.x == cx and c.rect.y == cy:
                        c.is_opening = True
                        break

            elif action == 'open_container':
                cx, cy = msg.get('x'), msg.get('y')
                for c in self.game.containers:
                    if hasattr(c, 'rect') and c.rect.x == cx and c.rect.y == cy:
                        c.is_opening = False
                        if not getattr(c, 'is_opened', False):
                            if hasattr(c, 'open'):
                                c.open(self.game)
                        break

            elif action == 'melee_swing':
                other_socks = [s for s in self.clients if s != sock]
                self.broadcast_queue.put(({'type': NetMsg.WORLD_ACTION, 'action': 'melee_swing', 'player_id': c_info['id'], 'angle': msg.get('angle', 0)}, other_socks))
                rp = self.game.remote_players.get(c_info.get('id'))
                if rp:
                    rp.swing_timer = 15
                    rp.swing_angle = float(msg.get('angle', 0.0))

            elif action == 'shoot':
                tx, ty = msg.get('tx', 0), msg.get('ty', 0)
                pellets = msg.get('pellets', 1)
                spread = msg.get('spread', 0)
                
                other_socks = [s for s in self.clients if s != sock]
                self.broadcast_queue.put(({'type': NetMsg.WORLD_ACTION, 'action': 'shoot', 'player_id': c_info['id'], 'tx': tx, 'ty': ty, 'pellets': pellets, 'spread': spread}, other_socks))
                
                rp = self.game.remote_players.get(c_info.get('id'))
                if rp:
                    rp.gun_flash_timer = 5
                    from core.entities.item.projectile import Projectile
                    dx = tx - rp.rect.centerx
                    dy = ty - rp.rect.centery
                    base_angle = math.atan2(dy, dx)
                    for _ in range(pellets):
                        import random
                        spr = math.radians(random.uniform(-spread/2, spread/2))
                        target_x = rp.rect.centerx + math.cos(base_angle + spr) * 1000
                        target_y = rp.rect.centery + math.sin(base_angle + spr) * 1000
                        proj = Projectile(rp.rect.centerx, rp.rect.centery, target_x, target_y, speed=20, game=self.game)
                        self.game.projectiles.append(proj)

            elif action == 'toggle_door':
                self.game.map_manager.toggle_door_state(msg.get('x'), msg.get('y'))

            elif action == 'hit_tile':
                self.game.map_manager._ignore_net = True
                self.game.map_manager.hit_tile(msg.get('x'), msg.get('y'), msg.get('damage', 1), attacker=c_info.get('player'))
                self.game.map_manager._ignore_net = False

            elif action == 'player_death':
                p_x = msg.get('x', 0)
                p_y = msg.get('y', 0)
                p_name = msg.get('name', 'Survivor')
                corpse = Corpse(
                    name=f"Corpse of {p_name}",
                    capacity=35,
                    pos=(p_x, p_y),
                    image_path="player/dead.png",
                    decay_ms=1800000,
                    is_player_corpse=True
                )
                from core.entities.item.item import Item
                for i_data in msg.get('inventory', []):
                    it = Item.from_dict(i_data) if isinstance(i_data, dict) else Item.create_from_name(i_data)
                    if it: corpse.inventory.append(it)
                self.game.items_on_ground.append(corpse)
                if c_info.get('player'):
                    c_info['player'].is_dead = True
                save_data = c_info.get('last_data', {})
                save_data['alive'] = False
                self._save_remote_player_to_disk(c_info['uip'], c_info['id'], save_data)

            elif action == 'container_sync':
                cx, cy = msg.get('x'), msg.get('y')
                from core.entities.item.item import Item
                for c in self.game.containers:
                    if hasattr(c, 'rect') and c.rect.x == cx and c.rect.y == cy:
                        c.is_opened = msg.get('is_opened', True)
                        inv_data = msg.get('inventory', [])
                        c.inventory = [Item.from_dict(d) for d in inv_data if d]
                        break
                for c in self.game.items_on_ground:
                    if hasattr(c, 'inventory') and hasattr(c, 'rect') and c.rect.x == cx and c.rect.y == cy:
                        inv_data = msg.get('inventory', [])
                        c.inventory = [Item.from_dict(d) for d in inv_data if d]
                        break

        elif m_type == NetMsg.CHAT_BROADCAST:
            text = msg.get('text', '')
            sender = c_info.get('name', 'Remote')
            full_msg = f"{sender}: {text}"
            display_message(self.game, full_msg)
            other_socks = [s for s in self.clients if s != sock]
            self.broadcast_queue.put(({'type': NetMsg.CHAT_BROADCAST, 'text': text, 'sender': sender}, other_socks))

    def _handle_client_disconnect(self, sock):
        info = self.clients.pop(sock, None)
        if not info:
            return
        unregister_socket(sock)
        p_id = info.get('id')
        p_name = info.get('name', 'Player')
        if p_id:
            self.udp_clients.pop(p_id, None)
            if hasattr(self.game, 'remote_players') and p_id in self.game.remote_players:
                del self.game.remote_players[p_id]

        if info.get('last_data'):
            self._save_remote_player_to_disk(info['uip'], p_id, info['last_data'])

        display_message(self.game, f"[Server] Player '{p_name}' disconnected.")
        try:
            sock.close()
        except Exception:
            pass

    def _save_remote_player_to_disk(self, uip, player_id, player_data):
        save_folder = self.game.current_save_folder_name or "save_multiplayer"
        save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_folder)
        remote_dir = os.path.join(save_path, "player", "remote")
        os.makedirs(remote_dir, exist_ok=True)

        file_name = f"{uip}-{player_id}.rot"
        with open(os.path.join(remote_dir, file_name), "w") as f:
            json.dump(player_data, f, indent=4)

        host_path = os.path.join(save_path, "host.rot")
        host_data = {"os": platform.system(), "uip": self.ip, "host": {}, "remote": {}}
        if os.path.exists(host_path):
            try:
                with open(host_path, "r") as f:
                    host_data = json.load(f)
            except Exception:
                pass

        if "remote" not in host_data:
            host_data["remote"] = {}

        remote_key = f"{uip}-{player_id}"
        host_data["remote"][remote_key] = {
            "name": player_data.get("name", "Survivor"),
            "playerID": f"{uip}-{player_id}.rot",
            "playerUIP": uip,
            "alive": player_data.get("health", 100) > 0,
            "x": int(player_data.get("x", 0)),
            "y": int(player_data.get("y", 0))
        }

        try:
            with open(host_path, "w") as f:
                json.dump(host_data, f, indent=4)
        except Exception:
            pass