# core/server/client.py
import socket
import os
import time
import uuid
import select
import threading
import queue
import struct
import pygame
from core.data.config import *
import core.data.config
from core.server.network import (
    NetMsg, send_msg, recv_msgs, register_socket_queue, 
    unregister_socket, pack_payload, unpack_payload
)
from core.server.remote_player import RemotePlayer
from core.messages import display_message
from core.entities.item.item import Item
from core.entities.item.item_helpers import deserialize_item
from core.map.world_time import WorldTime
from core.systems.quadtree import Quadtree
from core.placement import find_free_tile
from core.entities.zombie.corpse import Corpse

class GameClient:
    def __init__(self, game):
        self.game = game
        self.socket = None        # TCP Socket (Reliable)
        self.udp_socket = None    # UDP Socket (High-speed sync)
        self.connected = False
        self.buffer = b''
        self.player_id = None
        self.target_host = ""
        self.target_port = 0
        self.server_udp_addr = None

        # Threading infrastructure
        self.inbox = queue.Queue()
        self.outbox = queue.Queue()
        self.udp_outbox = queue.Queue()
        self.worker_thread = None
        self.thread_running = False

    def connect(self, host, port, player_data):
        self.target_host = host
        self.target_port = int(port)

        try:
            # 1. Establish TCP Handshake Socket with TCP_NODELAY
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.settimeout(5.0)
            self.socket.connect((self.target_host, self.target_port))

            # Send initial JOIN_REQ over TCP
            join_payload = {
                'type': NetMsg.JOIN_REQ,
                'name': player_data.get('name', 'Survivor'),
                'player_id': player_data.get('player_id'),
                'player_data': player_data
            }
            send_msg(self.socket, join_payload)

            # Wait synchronously for JOIN_ACK during handshake
            start_t = time.time()
            ack_data = None
            while time.time() - start_t < 5.0:
                msgs, self.buffer, is_alive = recv_msgs(self.socket, self.buffer)
                if not is_alive:
                    break
                for msg in msgs:
                    if msg.get('type') == NetMsg.JOIN_ACK:
                        ack_data = msg
                        break
                    elif msg.get('type') == NetMsg.JOIN_DENY:
                        reason = msg.get('reason', 'Connection denied.')
                        display_message(self.game, f"[Network] {reason}")
                        self.socket.close()
                        self.socket = None
                        self.connected = False
                        return False, None
                if ack_data:
                    break
                time.sleep(0.02)

            if not ack_data:
                self.socket.close()
                self.socket = None
                self.connected = False
                return False, None

            self.socket.setblocking(False)
            self.connected = True
            self.player_id = ack_data.get('player_id')

            # 2. Setup UDP Socket
            server_udp_port = ack_data.get('server_udp_port', self.target_port)
            self.server_udp_addr = (self.target_host, server_udp_port)

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setblocking(False)

            # Register with server's UDP listener
            reg_bytes = pack_payload({
                'type': NetMsg.UDP_REGISTER,
                'player_id': self.player_id
            })
            self.udp_socket.sendto(reg_bytes, self.server_udp_addr)

            # 3. Launch background worker thread
            self.thread_running = True
            register_socket_queue(self.socket, self.outbox)
            self.worker_thread = threading.Thread(target=self._network_worker, daemon=True)
            self.worker_thread.start()

            return True, ack_data
        except Exception as e:
            if hasattr(self.game, 'logger'):
                self.game.logger.error(f"Failed to connect to {host}:{port} - {e}")
            self.connected = False
            return False, None

    def disconnect(self):
        if not self.connected and not self.thread_running:
            return
        self.connected = False
        self.thread_running = False
        if self.socket:
            unregister_socket(self.socket)
            try:
                data = pack_payload({'type': NetMsg.DISCONNECT})
                self.socket.sendall(struct.pack('>I', len(data)) + data)
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception:
                pass
            self.udp_socket = None

    def _network_worker(self):
        """Dedicated background thread for TCP/UDP socket I/O and msgpack deserialization."""
        while self.thread_running and self.connected and self.socket:
            # 1. Send outgoing TCP messages (Reliable)
            while not self.outbox.empty():
                try:
                    msg = self.outbox.get_nowait()
                    data = pack_payload(msg)
                    header = struct.pack('>I', len(data))
                    self.socket.sendall(header + data)
                except queue.Empty:
                    break
                except Exception:
                    self.connected = False
                    self.inbox.put({'type': '__DISCONNECTED__'})
                    return

            # 2. Send outgoing UDP packets (Unreliable fast stream)
            while not self.udp_outbox.empty():
                try:
                    udp_msg = self.udp_outbox.get_nowait()
                    payload = pack_payload(udp_msg)
                    if self.udp_socket and self.server_udp_addr:
                        self.udp_socket.sendto(payload, self.server_udp_addr)
                except queue.Empty:
                    break
                except Exception:
                    pass

            # 3. Receive incoming messages using select on both TCP and UDP
            readable_sockets = [self.socket]
            if self.udp_socket:
                readable_sockets.append(self.udp_socket)

            try:
                r_list, _, _ = select.select(readable_sockets, [], [], 0.002)
                for s in r_list:
                    if s == self.socket:
                        msgs, self.buffer, is_alive = recv_msgs(self.socket, self.buffer)
                        if not is_alive:
                            self.connected = False
                            self.inbox.put({'type': '__DISCONNECTED__'})
                            return
                        for msg in msgs:
                            self.inbox.put(msg)
                    elif s == self.udp_socket:
                        try:
                            data, _ = self.udp_socket.recvfrom(65535)
                            msg = unpack_payload(data)
                            self.inbox.put(msg)
                        except Exception:
                            pass
            except Exception:
                self.connected = False
                self.inbox.put({'type': '__DISCONNECTED__'})
                return

    def update(self):
        if not self.connected or not self.socket:
            return

        # 1. Drain inbox parsed by background thread
        while not self.inbox.empty():
            try:
                msg = self.inbox.get_nowait()
            except queue.Empty:
                break

            m_type = msg.get('type')

            if m_type == '__DISCONNECTED__':
                display_message(self.game, "[Network] Disconnected from server.")
                self.disconnect()
                self.game.game_state = 'MENU'
                return

            if m_type == NetMsg.NEW_CHUNKS:
                chunk_files = msg.get('chunk_files', {})
                map_dir = getattr(self.game.map_manager, 'map_folder', None)
                if map_dir:
                    os.makedirs(map_dir, exist_ok=True)
                    for fname, content in chunk_files.items():
                        try:
                            with open(os.path.join(map_dir, fname), 'w', encoding='utf-8') as f:
                                f.write(content)
                        except Exception:
                            pass
                    self.game.map_manager.refresh_maps()

            elif m_type == NetMsg.WORLD_SYNC:
                # Players
                players_list = msg.get('players', [])
                if not hasattr(self.game, 'remote_players'):
                    self.game.remote_players = {}

                current_p_ids = set()
                for p_data in players_list:
                    pid = p_data.get('id')
                    if pid == self.player_id:
                        continue
                    current_p_ids.add(pid)
                    if pid not in self.game.remote_players:
                        rp = RemotePlayer(pid, p_data.get('name', 'Player'), p_data.get('x', 0), p_data.get('y', 0))
                        self.game.remote_players[pid] = rp
                    self.game.remote_players[pid].update_from_network(p_data)

                for existing_id in list(self.game.remote_players.keys()):
                    if existing_id not in current_p_ids:
                        del self.game.remote_players[existing_id]

                # Zombies
                if not hasattr(self.game, '_synced_zombies'):
                    self.game._synced_zombies = {}

                current_z_ids = set()
                from core.entities.zombie.zombie import Zombie
                for z_data in msg.get('zombies', []):
                    zid = z_data['id']
                    current_z_ids.add(zid)
                    if zid not in self.game._synced_zombies:
                        z_obj = Zombie.create_random(z_data['x'], z_data['y'])
                        z_obj.id = zid
                        z_obj.name = z_data.get('name', 'Zombie')
                        self.game._synced_zombies[zid] = z_obj

                    z = self.game._synced_zombies[zid]
                    z.x = z_data['x']
                    z.y = z_data['y']
                    z.rect.topleft = (int(z.x), int(z.y))
                    z.health = z_data['hp']
                    z.max_health = z_data['max_hp']
                    z.vx = z_data.get('vx', 0)
                    z.vy = z_data.get('vy', 0)
                    z.walk_anim_angle = z_data.get('anim', 0)

                    server_hb = z_data.get('hb_timer', 0)
                    if server_hb > getattr(z, 'show_health_bar_timer', 0):
                        z.show_health_bar_timer = server_hb

                    new_clothes = z_data.get('clothes', {})
                    new_colors = z_data.get('clothes_colors', {})
                    if getattr(z, '_last_net_clothes', None) != new_clothes or getattr(z, '_last_net_colors', None) != new_colors:
                        z.clothes = {}
                        for slot, item_name in new_clothes.items():
                            if item_name and item_name != "None":
                                color = new_colors.get(slot, (255, 255, 255))
                                if isinstance(color, list): color = tuple(color)
                                z.clothes[slot] = Item.create_from_name(item_name, force_color=color, spawn_loot=False)
                        z._last_net_clothes = new_clothes
                        z._last_net_colors = new_colors

                for zid in list(self.game._synced_zombies.keys()):
                    if zid not in current_z_ids:
                        del self.game._synced_zombies[zid]

                self.game.zombies = list(self.game._synced_zombies.values())
                self.game.active_zombies = self.game.zombies

                # Animals
                if not hasattr(self.game, '_synced_animals'):
                    self.game._synced_animals = {}

                current_a_ids = set()
                from core.entities.animal.animal import Animal
                for a_data in msg.get('animals', []):
                    aid = a_data['id']
                    current_a_ids.add(aid)
                    if aid not in self.game._synced_animals:
                        a_obj = Animal(a_data['x'], a_data['y'], a_data.get('name', 'Rat'), game=self.game)
                        a_obj.id = aid
                        self.game._synced_animals[aid] = a_obj

                    a = self.game._synced_animals[aid]
                    a.x = a_data['x']
                    a.y = a_data['y']
                    a.rect.topleft = (int(a.x), int(a.y))
                    a.health = a_data['hp']
                    a.max_health = a_data['max_hp']

                for aid in list(self.game._synced_animals.keys()):
                    if aid not in current_a_ids:
                        del self.game._synced_animals[aid]

                self.game.active_animals = list(self.game._synced_animals.values())

                # Ground Items & Corpses
                # Ground Items & Corpses
                if not hasattr(self.game, '_synced_items'):
                    self.game._synced_items = {}

                current_i_ids = set()
                for it_data in msg.get('items', []):
                    iid = it_data.get('id')
                    current_i_ids.add(iid)

                    if iid not in self.game._synced_items:
                        if it_data.get('is_corpse'):
                            corpse = Corpse(
                                name=it_data.get('name', 'Corpse'),
                                pos=(it_data['x'], it_data['y']),
                                is_player_corpse=it_data.get('is_player_corpse', False)
                            )
                            corpse.id = iid
                            if 'inventory' in it_data:
                                corpse.inventory = [Item.from_dict(x) for x in it_data['inventory'] if x]
                            self.game._synced_items[iid] = corpse
                        else:
                            item = Item.from_dict(it_data)
                            if item:
                                item.id = iid
                                self.game._synced_items[iid] = item

                    it = self.game._synced_items.get(iid)
                    if it:
                        it.x = it_data['x']
                        it.y = it_data['y']
                        it.rect.topleft = (int(it.x), int(it.y))
                        if it_data.get('load') is not None:
                            it.load = it_data['load']
                        
                        # --- FIX: Corpse State-Locking (Prevents Item Duplication) ---
                        if it_data.get('is_corpse') and 'inventory' in it_data:
                            server_state = str([x.get('id', '') + str(x.get('load', '')) for x in it_data['inventory']])
                            local_state = getattr(it, '_last_sync_state', '')

                            if getattr(it, '_awaiting_server_sync', False):
                                # We made local changes. Ignore server until it catches up to our state
                                if server_state == local_state:
                                    it._awaiting_server_sync = False
                            else:
                                # Safe to accept server changes
                                if server_state != local_state:
                                    it.inventory = [Item.from_dict(x) for x in it_data['inventory'] if x]
                                    it._last_sync_state = server_state

                for iid in list(self.game._synced_items.keys()):
                    if iid not in current_i_ids:
                        del self.game._synced_items[iid]

                self.game.items_on_ground = list(self.game._synced_items.values())
                self.game.items_on_ground.extend(self.game.active_animals)

                # NPCs
                if not hasattr(self.game, '_synced_npcs'):
                    self.game._synced_npcs = {}
                current_n_ids = set()
                from core.entities.npc.npc import NPC
                for n_data in msg.get('npcs', []):
                    nid = n_data['id']
                    current_n_ids.add(nid)
                    is_static_npc = n_data.get('is_static', False)

                    if nid not in self.game._synced_npcs:
                        dummy = NPC(n_data['x'], n_data['y'], self.game, is_static=is_static_npc)
                        dummy.id = nid
                        self.game._synced_npcs[nid] = dummy

                    dummy = self.game._synced_npcs[nid]
                    dummy.x = n_data['x']
                    dummy.y = n_data['y']
                    dummy.rect.topleft = (int(dummy.x), int(dummy.y))
                    dummy.name = n_data['name']
                    dummy.health = n_data['hp']
                    dummy.max_health = n_data['max_hp']
                    dummy.is_friendly = n_data['is_friendly']
                    dummy.is_static = is_static_npc
                    dummy.walk_anim_angle = n_data.get('anim', 0)

                    server_hb = n_data.get('hb_timer', 0)
                    if server_hb > getattr(dummy, 'health_bar_timer', 0):
                        dummy.health_bar_timer = server_hb

                    wpn = n_data.get('weapon')
                    if wpn: dummy.equipped_weapon = Item.create_from_name(wpn, spawn_loot=False)
                    else: dummy.equipped_weapon = None

                    new_clothes = n_data.get('clothes', {})
                    new_colors = n_data.get('clothes_colors', {})
                    if getattr(dummy, '_last_net_clothes', None) != new_clothes or getattr(dummy, '_last_net_colors', None) != new_colors:
                        dummy.clothes = {}
                        for slot, c_name in new_clothes.items():
                            if c_name:
                                col = new_colors.get(slot, (255, 255, 255))
                                dummy.clothes[slot] = Item.create_from_name(c_name, force_color=tuple(col), spawn_loot=False)
                        dummy._last_net_clothes = new_clothes
                        dummy._last_net_colors = new_colors

                for nid in list(self.game._synced_npcs.keys()):
                    if nid not in current_n_ids:
                        del self.game._synced_npcs[nid]

                self.game.npcs.empty()
                for dummy in self.game._synced_npcs.values():
                    self.game.npcs.add(dummy)

                # Vehicles
                if hasattr(self.game.map_manager, 'vehicles'):
                    sync_v_ids = set()
                    from core.entities.vehicle.vehicle import Vehicle
                    from core.entities.vehicle.vehicle_data import VehicleData
                    for v_data in msg.get('vehicles', []):
                        vid = v_data.get('id')
                        sync_v_ids.add(vid)

                        existing_v = None
                        for v in self.game.vehicles:
                            if getattr(v, 'id', None) == vid:
                                existing_v = v
                                break

                        if not existing_v:
                            v_def = VehicleData.get_definition_by_name(v_data['name'])
                            existing_v = Vehicle(v_data['name'], v_data['x'], v_data['y'], TILE_SIZE, TILE_SIZE, v_def['images'] if v_def else None, v_def['stats'] if v_def else {}, facing=v_data['facing'])
                            existing_v.id = vid
                            self.game.map_manager.vehicles.append(existing_v)
                            self.game.vehicles.append(existing_v)
                            self.game.containers.append(existing_v)
                            self.game.obstacles.append(existing_v.rect)

                        existing_v.x = v_data['x']
                        existing_v.y = v_data['y']
                        existing_v.rect.topleft = (int(existing_v.x), int(existing_v.y))
                        existing_v.facing = v_data['facing']
                        existing_v.active = v_data['active']
                        existing_v.lights = v_data['lights']

                    for v in list(self.game.vehicles):
                        if getattr(v, 'id', None) not in sync_v_ids:
                            if v in self.game.vehicles: self.game.vehicles.remove(v)
                            if v in self.game.map_manager.vehicles: self.game.map_manager.vehicles.remove(v)
                            if v in self.game.containers: self.game.containers.remove(v)
                            if v.rect in self.game.obstacles: self.game.obstacles.remove(v.rect)

                self.game.items_on_ground.extend(self.game.active_animals)

                # Containers
                sync_conts = {(c['x'], c['y']): c for c in msg.get('containers', [])}
                for c in getattr(self.game, 'containers', []):
                    if getattr(c, 'item_type', '') == 'maptile_container':
                        key = (c.rect.x, c.rect.y)
                        if key in sync_conts:
                            c_data = sync_conts[key]
                            c.is_opened = c_data.get('is_opened', False)
                            c.is_opening = c_data.get('is_opening', False)
                            
                            # --- FIX: Standard Container State-Locking (Prevents Item Duplication) ---
                            server_state = str([i.get('id', '') + str(i.get('load', '')) for i in c_data.get('inventory', [])])
                            local_state = getattr(c, '_last_sync_state', '')

                            if getattr(c, '_awaiting_server_sync', False):
                                # We made local changes. Ignore server until it catches up
                                if server_state == local_state:
                                    c._awaiting_server_sync = False
                            else:
                                # Safe to accept server changes
                                if server_state != local_state:
                                    c.inventory = [Item.from_dict(d) for d in c_data.get('inventory', []) if d]
                                    c._last_sync_state = server_state

                # Projectiles
                local_projs = [p for p in self.game.projectiles if getattr(p, 'owner', None) == self.game.player]
                self.game.projectiles = local_projs
                from core.entities.item.projectile import Projectile
                for p_data in msg.get('projectiles', []):
                    dummy = Projectile(p_data['prev_x'], p_data['prev_y'], p_data['x'], p_data['y'], game=self.game)
                    dummy.x = p_data['x']
                    dummy.y = p_data['y']
                    color = p_data.get('color', (255, 255, 255))
                    dummy.color = tuple(color) if isinstance(color, list) else color
                    self.game.projectiles.append(dummy)

                map_name = getattr(self.game.map_manager, 'current_map_filename', '')
                if 'tile_health' in msg:
                    if map_name not in self.game.map_states:
                        self.game.map_states[map_name] = {}
                    if 'tile_health' not in self.game.map_states[map_name]:
                        self.game.map_states[map_name]['tile_health'] = {}

                    for th_data in msg['tile_health']:
                        gx, gy, hp = th_data['x'], th_data['y'], th_data['hp']
                        self.game.map_states[map_name]['tile_health'][(gx, gy)] = hp
                        # Activate the visual timer so it renders on the client
                        self.game.map_manager.tile_hit_timers[(gx, gy)] = 60

                # World Time & Weather
                if hasattr(self.game, 'world_time'):
                    self.game.world_time.game_time_ms = msg.get('time_ms', self.game.world_time.game_time_ms)
                    self.game.world_time.weather = msg.get('weather', self.game.world_time.weather)
                    self.game.world_time.day_count = msg.get('day_count', self.game.world_time.day_count)

            elif m_type == NetMsg.WORLD_ACTION and msg.get('action') == 'tile_change':
                gx, gy = msg.get('x'), msg.get('y')
                new_char = msg.get('char')
                if hasattr(self.game, 'map_manager') and hasattr(self.game, 'map_data'):
                    try:
                        new_def = self.game.tile_manager.definitions.get(new_char)
                        self.game.map_data[gy][gx] = new_char
                        tile_rect = pygame.Rect(gx * TILE_SIZE, gy * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                        self.game.obstacles = [rect for rect in self.game.obstacles if rect != tile_rect]
                        if new_def and new_def.get('is_obstacle'):
                            self.game.obstacles.append(tile_rect)
                        self.game.map_manager.invalidate_chunk(gx, gy)
                        self.game.cached_obstacle_count = -1
                    except Exception:
                        pass

            elif m_type == NetMsg.WORLD_ACTION and msg.get('action') == 'shake_tile':
                gx, gy = msg.get('x'), msg.get('y')
                if hasattr(self.game, 'map_manager'):
                    self.game.map_manager.shaking_tiles[(gx, gy)] = time.time()
                    self.game.map_manager.tile_hit_timers[(gx, gy)] = 60

            elif m_type == NetMsg.WORLD_ACTION and msg.get('action') == 'melee_swing':
                pid = msg.get('player_id')
                rp = self.game.remote_players.get(pid)
                if not rp:
                    for candidate in self.game.remote_players.values():
                        rp = candidate
                        break
                if rp:
                    rp.swing_timer = 15
                    rp.swing_angle = float(msg.get('angle', 0.0))

            elif m_type == NetMsg.WORLD_ACTION and msg.get('action') == 'shoot':
                pid = msg.get('player_id')
                rp = self.game.remote_players.get(pid)
                if rp:
                    from core.entities.item.projectile import Projectile
                    proj = Projectile(rp.rect.centerx, rp.rect.centery, msg.get('tx'), msg.get('ty'), speed=20, game=self.game)
                    self.game.projectiles.append(proj)

            elif m_type == NetMsg.ENTITY_DAMAGE:
                e_type = msg.get('entity_type')
                dmg = msg.get('damage', 1)
                inf = msg.get('infection', 0)

                if e_type == 'player' and self.game.player and not self.game.player.is_dead:
                    self.game.player.take_damage(self.game, dmg, inf)

            elif m_type == NetMsg.CHAT_BROADCAST:
                sender = msg.get('sender', 'Server')
                text = msg.get('text', '')
                display_message(self.game, f"{sender}: {text}")

            elif m_type == NetMsg.SERVER_CLOSED:
                display_message(self.game, "[Network] Host closed the server.")
                self.disconnect()
                self.game.game_state = 'MENU'

        # 2. Queue local player position updates over UDP (Non-blocking high-frequency stream)
        if self.game.player and not self.game.player.is_dead and self.server_udp_addr:
            wpn = self.game.player.active_weapon.name if self.game.player.active_weapon else None
            clothes_simple = {slot: (item.name if item else None) for slot, item in getattr(self.game.player, 'clothes', {}).items()}
            clothes_colors = {slot: item.color for slot, item in getattr(self.game.player, 'clothes', {}).items() if item and hasattr(item, 'color')}

            update_payload = {
                'type': NetMsg.PLAYER_UPDATE,
                'id': self.player_id,
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
                'weapon': wpn,
                'clothes': clothes_simple,
                'clothes_colors': clothes_colors,
                'swing_timer': getattr(self.game.player, 'melee_swing_timer', 0),
                'swing_angle': round(getattr(self.game.player, 'melee_swing_angle', 0), 2),
                'action_timer': getattr(self.game.player, 'action_timer', 0),
                'action_total_time': getattr(self.game.player, 'action_total_time', 0),
                'action_name': getattr(self.game.player, 'action_name', '')
            }
            self.udp_outbox.put(update_payload)

        # 3. Queue active container syncs over TCP (Reliable transactions)
        active_containers = []
        for modal in self.game.modals:
            if modal['type'] == 'container':
                active_containers.append(modal['item'])
            elif modal['type'] == 'nearby':
                for tab in modal.get('tabs_data', []):
                    active_containers.append(tab['container'])

        for c in active_containers:
            if getattr(c, 'item_type', '') == 'ground': continue
            
            # --- FIX: Always calculate local hash and lock it if changed ---
            current_state = str([getattr(i, 'id', '') + str(getattr(i, 'load', '')) for i in getattr(c, 'inventory', [])])
            
            if not hasattr(c, '_last_sync_state') or c._last_sync_state != current_state:
                c._last_sync_state = current_state
                c._awaiting_server_sync = True  # <--- MUST BE TRUE TO PREVENT OVERWRITES
                
                send_msg(self.socket, {
                    'type': NetMsg.WORLD_ACTION, 'action': 'container_sync',
                    'x': c.rect.x, 'y': c.rect.y,
                    'is_opened': getattr(c, 'is_opened', True),
                    'inventory': [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(c, 'inventory', [])]
                })

def init_client_world(game, ack_data, player_data):
    save_folder = ack_data.get('save_folder_name', 'client_session')
    map_filename = ack_data.get('map_filename', 'map_L1_0_0_map.csv')

    save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_folder)
    map_dir = os.path.join(save_path, "map")
    os.makedirs(map_dir, exist_ok=True)

    chunk_files = ack_data.get('chunk_files', {})
    for fname, content in chunk_files.items():
        out_file = os.path.join(map_dir, fname)
        try:
            with open(out_file, 'w', encoding='utf-8') as cf:
                cf.write(content)
        except Exception as e:
            print(f"Error saving chunk file {fname}: {e}")

    game.current_save_folder_name = save_folder
    game.map_manager.map_folder = map_dir
    game.map_manager.refresh_maps()

    if not map_filename or map_filename not in game.map_manager.map_files:
        map_filename = next(iter(game.map_manager.map_files.keys()), map_filename)

    game.map_manager.current_map_filename = map_filename

    game.zoom_level = getattr(core.data.config, 'START_ZOOM', 1.0)
    game.CHUNK_SIZE = getattr(core.data.config, 'CHUNK_SIZE', 128)
    if hasattr(game, 'map_manager'):
        game.map_manager.CHUNK_SIZE = game.CHUNK_SIZE
    game.player_view_radius = getattr(core.data.config, 'BASE_PLAYER_VIEW_RADIUS', 12 * TILE_SIZE)

    game.is_giant_map = False
    game.items_on_ground = []
    game.zombies = []
    game.obstacles = []
    game.containers = []
    game.renderable_tiles = []
    game.map_lights = []
    game.projectiles = []
    game.corpses = []
    game.splashes = []
    game.blood_stains = []
    if hasattr(game.npcs, 'empty'):
        game.npcs.empty()
    game.app_state = {'slots': [None] * 5}

    game.world_time = WorldTime(game)
    time_data = ack_data.get('time_data')
    if time_data:
        game.world_time.game_time_ms = time_data.get('game_time_ms', 0)
        game.world_time.day_count = time_data.get('day_count', 0)

    assigned_id = ack_data.get('player_id')
    restored = ack_data.get('restored_data')
    p_data = restored if restored else player_data
    if assigned_id:
        p_data['player_id'] = assigned_id

    from core.entities.player.player import Player
    game.player = Player(player_data=p_data)
    game.player.game = game
    game.player_name = game.player.name

    if restored and 'inventory' in restored:
        game.player.inventory = [deserialize_item(i) for i in restored['inventory'] if deserialize_item(i)]
    else:
        initial_loot = player_data.get('initial_loot', [])
        game.player.inventory = [Item.create_from_name(name) for name in initial_loot if Item.create_from_name(name)]

    game.load_map(map_filename)

    if hasattr(game, 'map_width_pixels') and hasattr(game, 'map_height_pixels'):
        game.quadtree = Quadtree(pygame.Rect(0, 0, game.map_width_pixels, game.map_height_pixels))

    spawn_x = ack_data.get('spawn_x', game.player.x)
    spawn_y = ack_data.get('spawn_y', game.player.y)

    test_rect = pygame.Rect(int(spawn_x), int(spawn_y), TILE_SIZE, TILE_SIZE)
    free_pos = find_free_tile(test_rect, getattr(game, 'obstacles', []), initial_pos=(spawn_x, spawn_y), max_radius=8)
    if free_pos:
        spawn_x, spawn_y = free_pos

    game.player.x = spawn_x
    game.player.y = spawn_y
    game.player.rect.topleft = (int(spawn_x), int(spawn_y))

    game.camera_pan_x = 0
    game.camera_pan_y = 0
    view_w = int(game.dynamic_w / game.zoom_level)
    view_h = int(game.dynamic_h / game.zoom_level)
    game.true_camera_x = game.player.rect.centerx - (view_w / 2)
    game.true_camera_y = game.player.rect.centery - (view_h / 2)

    stat_pos = game.last_modal_positions.get('status', (0, 0))
    inv_pos = game.last_modal_positions.get('inventory', (1034, 256))
    nearby_pos = game.last_modal_positions.get('nearby', (1034, 494))
    msg_pos = game.last_modal_positions.get('messages', (3, 460))
    gear_pos = game.last_modal_positions.get('gear', (1034, 3))
    slots_pos = game.last_modal_positions.get('slots', (1034, 3))

    game.modals = [
        {'type': 'status', 'id': str(uuid.uuid4()), 'position': stat_pos, 'rect': pygame.Rect(stat_pos, (STATUS_MODAL_WIDTH, STATUS_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0)},
        {'type': 'inventory', 'id': str(uuid.uuid4()), 'position': inv_pos, 'rect': pygame.Rect(inv_pos, (INVENTORY_MODAL_WIDTH, INVENTORY_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0), 'active_tab': 'Inventory'},
        {'type': 'gear', 'id': str(uuid.uuid4()), 'position': gear_pos, 'rect': pygame.Rect(gear_pos, (GEAR_MODAL_WIDTH, GEAR_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0)},
        {'type': 'nearby', 'id': str(uuid.uuid4()), 'position': nearby_pos, 'rect': pygame.Rect(nearby_pos, (NEARBY_MODAL_WIDTH, NEARBY_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0), 'active_tab': 'Ground'},
        {'type': 'messages', 'id': str(uuid.uuid4()), 'position': msg_pos, 'rect': pygame.Rect(msg_pos, (MESSAGES_MODAL_WIDTH, MESSAGES_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0)},
        {'type': 'slots', 'id': str(uuid.uuid4()), 'position': slots_pos, 'rect': pygame.Rect(slots_pos, (SLOTS_MODAL_WIDTH, SLOTS_MODAL_HEIGHT)), 'is_dragging': False, 'drag_offset': (0, 0)}
    ]