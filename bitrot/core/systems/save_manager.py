import os
import shutil
import json
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
                "alcohol_level": getattr(game.player, 'alcohol_level', 0.0)
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

        # Save player file to data.rot/save/game/save_<TIMESTAMP>/player/<PLAYER_ID>.rot
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

        # Load existing players in host.rot if file exists
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

        # Update or add host player entry
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
        for npc in game.npcs:
            safe_clothes = {}
            for slot, item in npc.clothes.items():
                safe_clothes[slot] = item.to_dict() if (item and hasattr(item, 'to_dict')) else item

            safe_inventory = [i.to_dict() if hasattr(i, 'to_dict') else i for i in npc.inventory]
            safe_weapon = npc.equipped_weapon.to_dict() if (npc.equipped_weapon and hasattr(npc.equipped_weapon, 'to_dict')) else npc.equipped_weapon

            npc_data.append({
                "id": getattr(npc, 'id', None),
                "x": npc.rect.x,
                "y": npc.rect.y,
                "name": npc.name,
                "health": npc.health,
                "max_health": getattr(npc, 'max_health', 100),
                "is_following": npc.is_following,
                "is_friendly": npc.is_friendly,
                "is_static": getattr(npc, 'is_static', False),
                "inventory": safe_inventory,
                "equipped_weapon": safe_weapon,
                "clothes": safe_clothes,
                "loot_table": getattr(npc, 'loot_table', []),
                "dialog_flags": list(getattr(npc, 'dialog_flags', []))
            })
        
        with open(os.path.join(save_path, "npc.rot"), "w") as f:
            json.dump(npc_data, f, indent=4)

        # --- 4. SAVE ZOMBIES ---
        zombie_data = []
        for z in game.zombies:
            if getattr(z, 'type', 'zombie') == 'animal': continue
            
            safe_clothes = {}
            if hasattr(z, 'clothes') and z.clothes:
                for slot, item in z.clothes.items():
                    safe_clothes[slot] = item.to_dict() if (item and hasattr(item, 'to_dict')) else item
            
            safe_inventory = [i.to_dict() if hasattr(i, 'to_dict') else i for i in getattr(z, 'inventory', [])]

            zombie_data.append({
                "id": getattr(z, 'id', None),
                "x": z.x,
                "y": z.y,
                "health": z.health,
                "max_health": getattr(z, 'max_health', 10),
                "name": getattr(z, 'name', 'Zombie'),
                "sex": getattr(z, 'sex', 'Male'),
                "vaccine": getattr(z, 'vaccine', False),
                "speed": getattr(z, 'speed', 1.0),
                "loot_table": getattr(z, 'loot_table', []),
                "inventory": safe_inventory,
                "clothes": safe_clothes,
                "sprites": getattr(z, 'sprites_data', {})
            })

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

        # --- 7. SAVE CONTAINERS & GROUND ITEMS (Including corpses) ---
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

        safe_ground_items = []
        for i in game.items_on_ground:
            if isinstance(i, Animal): continue
            item_data = i.to_dict() if hasattr(i, 'to_dict') else i
            safe_ground_items.append({
                "data": item_data,
                "x": i.rect.x if hasattr(i, 'rect') else i.x,
                "y": i.rect.y if hasattr(i, 'rect') else i.y
            })

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
            "current_radio_freq": getattr(game, 'current_radio_freq', 110.42)
        }
        with open(os.path.join(save_path, "world.rot"), "w") as f:
            json.dump(world_data, f, indent=4)

        # Quests
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