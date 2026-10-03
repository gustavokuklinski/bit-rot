import os
import shutil
import json
import re
import socket
import platform
import uuid
from datetime import datetime
from core.entities.vehicle.vehicle import Vehicle
from core.entities.animal.animal import Animal
from core.data.config import MAP_DIR, get_writable_dir
from core.entities.npc.npc_dialog import NPCDialog
from core.entities.item.item_helpers import deserialize_item, serialize_item
from core.data.radio_manager import RadioManager 

def get_host_ip():
    """Finds the local network IP of the host machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

def save_game(game):
    if game.current_save_folder_name:
        save_name = game.current_save_folder_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"save_{timestamp}"
        game.current_save_folder_name = save_name

    save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_name)
    game.logger.info(f"Saving game to {save_path}...")

    try:
        os.makedirs(save_path, exist_ok=True)
        player_dir = os.path.join(save_path, "player")
        os.makedirs(player_dir, exist_ok=True)

        map_src = os.path.abspath(game.map_manager.map_folder)
        map_dst = os.path.abspath(os.path.join(save_path, "map"))
        
        if map_src != map_dst:
            if os.path.exists(map_dst):
                shutil.rmtree(map_dst)
            shutil.copytree(map_src, map_dst, dirs_exist_ok=True)
            game.map_manager.map_folder = map_dst

        game.map_manager.save_map_to_file(map_dst)

        world_xml_path = os.path.join(save_path, "world.xml")
        if not os.path.exists(world_xml_path):
            from core.ui.helpers.trait_config_loader import save_config_xml, load_config_data
            w_data = getattr(game, 'world_setup_state', {}).get('world_data')
            if not w_data:
                w_data = load_config_data(os.path.join(DATA_PATH, "world.xml"))
            save_config_xml(w_data, world_xml_path)
        
        # --- 1. PREPARE INDIVIDUAL PLAYER DATA ---
        player_id = getattr(game.player, 'player_id', None)
        if not player_id:
            player_id = str(uuid.uuid4())
            game.player.player_id = player_id

        attributes_base = {
            "strength": game.player.progression.get_level('strength'),
            "fitness": game.player.progression.get_level('fitness'),
            "melee": game.player.progression.get_level('melee'),
            "ranged": game.player.progression.get_level('ranged'),
            "lucky": game.player.progression.get_level('lucky'),
            "intelligence": game.player.progression.get_level('intelligence'),
            "agility": game.player.progression.get_level('agility')
        }
        
        progression_data = game.player.progression.attributes
        is_player_alive = not getattr(game.player, 'is_dead', False) and game.player.health > 0

        player_data = {
            "player_id": player_id,
            "name": game.player.name,
            "sex": game.player.sex,
            "x": game.player.x,
            "y": game.player.y,
            "alive": is_player_alive,
            "map_filename": game.map_manager.current_map_filename,
            "zombies_killed": game.zombies_killed,
            "stats": {
                "health": game.player.health,
                "water": game.player.water,
                "food": game.player.food,
                "stamina": game.player.stamina,
                "infection": game.player.infection,
                "anxiety": game.player.anxiety,
                "drugs": getattr(game.player, 'drugs', 0.0)
            },
            "attributes": attributes_base,
            "progression": progression_data,
            "traits": game.player.traits,
            "known_recipes": game.player.known_recipes,
            "visuals": game.player.visuals,
            "sounds": game.player.sounds_data,
            "inventory": [serialize_item(i) for i in game.player.inventory if i],
            "belt": [serialize_item(i) for i in game.player.belt],
            "clothes": {slot: serialize_item(item) for slot, item in game.player.clothes.items()},
            "quests": getattr(game.player, 'quests', []),
            "completed_quests": getattr(game.player, 'completed_quests', []),
            "dialog_history": list(getattr(game.player, 'dialog_history', [])),
            "special_dialogs": getattr(game.player, 'special_dialogs', []),
            "completed_milestones": getattr(game.player, 'completed_milestones', []),
            "milestone_progress": getattr(game.player, 'milestone_progress', {})
        }

        player_file_path = os.path.join(player_dir, f"{player_id}.rot")
        with open(player_file_path, "w") as f:
            json.dump(player_data, f, indent=4)

        # --- 2. PREPARE & UPDATE host.rot REGISTRY ---
        host_path = os.path.join(save_path, "host.rot")
        host_data = {
            "os": platform.system(),
            "uip": get_host_ip(),
            "host": {},
            "remote": {}
        }

        if os.path.exists(host_path):
            try:
                with open(host_path, "r") as f:
                    existing_host = json.load(f)
                    if isinstance(existing_host, dict):
                        if "host" in existing_host:
                            host_data["host"] = existing_host["host"]
                        elif "players" in existing_host:
                            host_data["host"] = existing_host["players"]
                        if "remote" in existing_host:
                            host_data["remote"] = existing_host["remote"]
            except Exception as e:
                game.logger.info(f"Could not read existing host.rot: {e}")

        host_data["host"][player_id] = {
            "name": game.player.name,
            "playerID": f"{player_id}.rot",
            "alive": is_player_alive,
            "x": int(game.player.x),
            "y": int(game.player.y)
        }

        with open(host_path, "w") as f:
            json.dump(host_data, f, indent=4)

        # --- 3. SAVE NPCS ---
        npc_data = []
        saved_npc_ids = set()

        def add_npc_to_save(npc_obj, map_fname, l_idx):
            n_id = getattr(npc_obj, 'id', None)
            if n_id and n_id in saved_npc_ids: return
            if n_id: saved_npc_ids.add(n_id)

            safe_clothes = {}
            for slot, item in npc_obj.clothes.items():
                safe_clothes[slot] = item.to_dict() if (item and hasattr(item, 'to_dict')) else item

            safe_inventory = [i.to_dict() if hasattr(i, 'to_dict') else i for i in npc_obj.inventory]
            safe_weapon = npc_obj.equipped_weapon.to_dict() if (npc_obj.equipped_weapon and hasattr(npc_obj.equipped_weapon, 'to_dict')) else npc_obj.equipped_weapon
            safe_trade_stock = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(npc_obj, 'trade_stock', [])]

            actual_layer = getattr(npc_obj, 'layer', l_idx)
            actual_map = getattr(npc_obj, 'map_filename', map_fname)

            npc_data.append({
                "id": n_id,
                "x": npc_obj.rect.x,
                "y": npc_obj.rect.y,
                "layer": actual_layer,
                "map_filename": actual_map,
                "name": npc_obj.name,
                "health": npc_obj.health,
                "max_health": getattr(npc_obj, 'max_health', 100),
                "is_friendly": npc_obj.is_friendly,
                "is_static": getattr(npc_obj, 'is_static', False),
                "inventory": safe_inventory,
                "equipped_weapon": safe_weapon,
                "clothes": safe_clothes,
                "trade_stock": safe_trade_stock,
                "loot_table": getattr(npc_obj, 'loot_table', []),
                "dialog_flags": list(getattr(npc_obj, 'dialog_flags', []))
            })

        curr_map = getattr(game.map_manager, 'current_map_filename', '')
        curr_layer = getattr(game, 'current_layer_index', 1)
        
        for n in game.npcs:
            add_npc_to_save(n, curr_map, curr_layer)
            
        for map_fname, m_state in getattr(game, 'map_states', {}).items():
            if map_fname == curr_map: continue
            m_match = re.search(r'map_L(\d+)_', map_fname)
            l_idx = int(m_match.group(1)) if m_match else 1
            for n in m_state.get('npcs', []):
                add_npc_to_save(n, map_fname, l_idx)

        with open(os.path.join(save_path, "npc.rot"), "w") as f:
            json.dump(npc_data, f, indent=4)

        # --- 4. SAVE ZOMBIES ---
        zombie_data = []
        saved_zombie_ids = set()

        def add_zombie_to_save(z_obj, map_fname, l_idx):
            if getattr(z_obj, 'type', 'zombie') == 'animal': return
            z_id = getattr(z_obj, 'id', None)
            if z_id and z_id in saved_zombie_ids: return
            if z_id: saved_zombie_ids.add(z_id)

            safe_clothes = {}
            if hasattr(z_obj, 'clothes') and z_obj.clothes:
                for slot, item in z_obj.clothes.items():
                    safe_clothes[slot] = item.to_dict() if (item and hasattr(item, 'to_dict')) else item

            safe_inventory = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(z_obj, 'inventory', [])]
            actual_layer = getattr(z_obj, 'layer', l_idx)
            actual_map = getattr(z_obj, 'map_filename', map_fname)

            zombie_data.append({
                "id": z_id,
                "x": z_obj.x,
                "y": z_obj.y,
                "layer": actual_layer,
                "map_filename": actual_map,
                "health": z_obj.health,
                "max_health": getattr(z_obj, 'max_health', 10),
                "name": getattr(z_obj, 'name', 'Zombie'),
                "sex": getattr(z_obj, 'sex', 'Male'),
                "vaccine": getattr(z_obj, 'vaccine', False),
                "speed": getattr(z_obj, 'speed', 1.0),
                "loot_table": getattr(z_obj, 'loot_table', []),
                "inventory": safe_inventory,
                "clothes": safe_clothes,
                "sprites": getattr(z_obj, 'sprites_data', {})
            })

        for z in game.zombies:
            add_zombie_to_save(z, curr_map, curr_layer)
            
        for map_fname, m_state in getattr(game, 'map_states', {}).items():
            if map_fname == curr_map: continue
            m_match = re.search(r'map_L(\d+)_', map_fname)
            l_idx = int(m_match.group(1)) if m_match else 1
            for z in m_state.get('zombies', []):
                add_zombie_to_save(z, map_fname, l_idx)

        with open(os.path.join(save_path, "zombies.rot"), "w") as f:
            json.dump(zombie_data, f, indent=4)

        # --- 5. SAVE ANIMALS ---
        animal_data = []
        for item in game.items_on_ground:
            if isinstance(item, Animal):
                safe_clothes = {}
                if hasattr(item, 'clothes') and item.clothes:
                    for slot, it in item.clothes.items():
                        safe_clothes[slot] = it.to_dict() if (it and hasattr(it, 'to_dict')) else it

                safe_inventory = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(item, 'inventory', [])]

                animal_data.append({
                    "id": getattr(item, 'id', None),
                    "x": item.x,
                    "y": item.y,
                    "health": item.health,
                    "max_health": getattr(item, 'max_health', 10),
                    "name": getattr(item, 'name', 'Animal'),
                    "type": "animal",
                    "speed": getattr(item, 'speed', 1.0),
                    "loot_table": getattr(item, 'loot_table', []),
                    "inventory": safe_inventory,
                    "clothes": safe_clothes,
                    "sprites": getattr(item, 'sprites_data', {})
                })

        with open(os.path.join(save_path, "animal.rot"), "w") as f:
            json.dump(animal_data, f, indent=4)

        # --- 6. SAVE VEHICLES ---
        vehicle_data = []
        vehicles_to_save = [obj for obj in game.containers if isinstance(obj, Vehicle)]
        for v in vehicles_to_save:
            safe_inv = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(v, 'inventory', [])]

            safe_equipment = {}
            if hasattr(v, 'equipment'):
                for slot, item in v.equipment.items():
                    safe_equipment[slot] = item.to_dict() if (item and hasattr(item, 'to_dict')) else item

            vehicle_data.append({
                "id": str(uuid.uuid4()),
                "x": v.rect.x,
                "y": v.rect.y,
                "name": v.name, 
                "facing": getattr(v, 'facing', 'right'),
                "inventory": safe_inv,
                "equipment": safe_equipment, 
                "lights": getattr(v, 'lights', 'off')
            })

        with open(os.path.join(save_path, "vehicles.rot"), "w") as f:
            json.dump(vehicle_data, f, indent=4)

        # --- 7. SAVE CONTAINERS & GROUND ITEMS ACROSS ALL LAYERS ---
        container_data = []
        saved_container_keys = set()

        for c in game.containers:
            if isinstance(c, Vehicle): continue
            if getattr(c, 'item_type', '') == 'maptile_container' and not getattr(c, 'is_opened', False): continue

            ckey = f"{c.rect.x if hasattr(c, 'rect') else c.x}_{c.rect.y if hasattr(c, 'rect') else c.y}"
            if ckey in saved_container_keys: continue
            saved_container_keys.add(ckey)

            safe_inv = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(c, 'inventory', [])]

            container_data.append({
                "id": str(uuid.uuid4()),
                "x": c.rect.x if hasattr(c, 'rect') else c.x,
                "y": c.rect.y if hasattr(c, 'rect') else c.y,
                "inventory": safe_inv,
                "is_opened": True
            })

        if curr_map:
            game.map_states.setdefault(curr_map, {})
            game.map_states[curr_map]['items_on_ground'] = [
                it for it in game.items_on_ground if not isinstance(it, Animal) and getattr(it, 'type', '') != 'animal'
            ]

        safe_ground_items = []
        seen_item_ids = set()

        def add_item_to_save(it, map_fname, layer_idx):
            if not it or isinstance(it, Animal) or getattr(it, 'type', '') == 'animal':
                return
            item_id = getattr(it, 'id', None)
            if item_id and item_id in seen_item_ids:
                return
            if item_id:
                seen_item_ids.add(item_id)

            actual_layer = layer_idx
            if hasattr(it, 'layer') and it.layer is not None:
                actual_layer = it.layer
            elif layer_idx is not None:
                actual_layer = layer_idx
                it.layer = layer_idx

            actual_map = map_fname
            if hasattr(it, 'map_filename') and it.map_filename:
                actual_map = it.map_filename
            else:
                it.map_filename = map_fname

            item_data = it.to_dict() if hasattr(it, 'to_dict') else it
            if isinstance(item_data, dict):
                item_data['layer'] = actual_layer
                item_data['map_filename'] = actual_map
                if getattr(it, 'is_placed', False):
                    item_data['is_placed'] = True

            safe_ground_items.append({
                "data": item_data,
                "x": it.rect.x if hasattr(it, 'rect') else it.x,
                "y": it.rect.y if hasattr(it, 'rect') else it.y,
                "layer": actual_layer,
                "map_filename": actual_map
            })

        for it in game.items_on_ground:
            add_item_to_save(it, curr_map, curr_layer)

        for map_fname, m_state in getattr(game, 'map_states', {}).items():
            if map_fname == curr_map:
                continue
            m_match = re.search(r'map_L(\d+)_', map_fname)
            l_idx = int(m_match.group(1)) if m_match else 1
            for it in m_state.get('items_on_ground', []):
                add_item_to_save(it, map_fname, l_idx)

        saved_barricades = []
        for map_name, m_state in game.map_states.items():
            if 'barricades' in m_state:
                for (gx, gy), b in m_state['barricades'].items():
                    saved_barricades.append({
                        'map': map_name,
                        'gx': gx,
                        'gy': gy,
                        'item_name': b['item_name'],
                        'health': b['health'],
                        'max_health': b['max_health'],
                        'remove_items': b['remove_items'],
                        'remove_time': b['remove_time']
                    })

        saved_explored_tiles = {}
        if hasattr(game, 'explored_tiles_dict'):
            curr_map_name = getattr(game.map_manager, 'current_map_filename', '')
            if curr_map_name and hasattr(game, 'explored_tiles'):
                game.explored_tiles_dict[curr_map_name] = game.explored_tiles
            for m_name, b_arr in game.explored_tiles_dict.items():
                if isinstance(b_arr, (bytearray, bytes)):
                    saved_explored_tiles[m_name] = b_arr.hex()

        world_data = {
            "time": {
                "game_time_ms": game.world_time.game_time_ms,
                "day_count": game.world_time.day_count
            },
            "layer_spawn_triggers": {str(k): list(v) for k, v in game.layer_spawn_triggers.items()},
            "items": safe_ground_items,
            "containers": container_data,
            "modal_positions": game.last_modal_positions,
            "app_slots": [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(game, 'app_state', {}).get('slots', [])],
            "barricades": saved_barricades,
            "radio_frequencies": getattr(game, 'radio_frequencies', {}),
            "current_radio_freq": getattr(game, 'current_radio_freq', 110.42),
            "explored_tiles": saved_explored_tiles
        }

        with open(os.path.join(save_path, "world.rot"), "w") as f:
            json.dump(world_data, f, indent=4)

        if NPCDialog.NPC_DIALOGS is None:
            NPCDialog.load_dialogs(game)

        quests_dst = os.path.join(save_path, "quests.rot")
        if NPCDialog.NPC_DIALOGS:
            proc_triggers = [opt for opt in NPCDialog.NPC_DIALOGS.get("quest_branch", []) if "Proc_" in str(opt.get('unlock_flag', ''))]
            proc_nodes = {node_id: options for node_id, options in NPCDialog.NPC_DIALOGS.items() if str(node_id).startswith("Quest: Proc_")}
            try:
                with open(quests_dst, "w") as f:
                    json.dump({"triggers": proc_triggers, "nodes": proc_nodes}, f, indent=4)
            except Exception as e:
                game.logger.info(f"Error saving quests.rot: {e}")

        game.logger.info("Game saved successfully!")
        return True
        
    except Exception as e:
        game.logger.info(f"Error saving game: {e}")
        import traceback
        traceback.print_exc()
        return False