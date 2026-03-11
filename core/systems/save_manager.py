import os
import shutil
import json
from datetime import datetime
from core.entities.vehicle.vehicle import Vehicle
from core.entities.animal.animal import Animal
from core.data.config import MAP_DIR

def save_game(game):
    if game.current_save_folder_name:
        save_name = game.current_save_folder_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_name = f"save_{timestamp}"
        game.current_save_folder_name = save_name

    save_path = os.path.join("game", "save", "game", save_name)
    game.logger.info(f"Saving game to {save_path}...")

    try:
        os.makedirs(save_path, exist_ok=True)

        map_src = os.path.abspath(game.map_manager.map_folder)
        map_dst = os.path.abspath(os.path.join(save_path, "map"))
        
        if map_src != map_dst:
            if os.path.exists(map_dst):
                    shutil.rmtree(map_dst)
            shutil.copytree(map_src, map_dst, dirs_exist_ok=True)
            game.map_manager.map_folder = map_dst
        else:
            game.logger.info("Map folder is already in the save directory. Skipping map copy.")

        game.map_manager.save_map_to_file(map_dst)
        
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

        player_data = {
            "name": game.player.name,
            "sex": game.player.sex,
            "x": game.player.x,
            "y": game.player.y,
            "map_filename": game.map_manager.current_map_filename,
            "zombies_killed": game.zombies_killed,
            "stats": {
                "health": game.player.health,
                "water": game.player.water,
                "food": game.player.food,
                "stamina": game.player.stamina,
                "tireness": game.player.tireness,
                "infection": game.player.infection,
                "anxiety": game.player.anxiety
            },

            "attributes": attributes_base,
            "progression": progression_data,
            "traits": game.player.traits,
            "known_recipes": game.player.known_recipes,
            "visuals": game.player.visuals,
            "sounds": game.player.sounds_data,
            "inventory": [item.to_dict() if hasattr(item, 'to_dict') else item for item in game.player.inventory if item],
            "belt": [(item.to_dict() if hasattr(item, 'to_dict') else item) if item else None for item in game.player.belt],
            "clothes": {slot: ((item.to_dict() if hasattr(item, 'to_dict') else item)) if item else None for slot, item in game.player.clothes.items()},
        }
        
        if game.player.backpack:
                if hasattr(game.player.backpack, 'to_dict'):
                    player_data["backpack"] = game.player.backpack.to_dict()
                else:
                    player_data["backpack"] = game.player.backpack

        with open(os.path.join(save_path, "host.rot"), "w") as f:
            json.dump(player_data, f, indent=4)

        # --- NPC Save (npc.rot) ---
        npc_data = []
        for npc in game.npcs:
            safe_clothes = {}
            for slot, item in npc.clothes.items():
                if item:
                    if hasattr(item, 'to_dict'):
                        safe_clothes[slot] = item.to_dict()
                    else:
                        safe_clothes[slot] = item 
                else:
                    safe_clothes[slot] = None

            safe_inventory = []
            for i in npc.inventory:
                if hasattr(i, 'to_dict'):
                    safe_inventory.append(i.to_dict())
                else:
                    safe_inventory.append(i)

            safe_weapon = None
            if npc.equipped_weapon:
                if hasattr(npc.equipped_weapon, 'to_dict'):
                    safe_weapon = npc.equipped_weapon.to_dict()
                else:
                    safe_weapon = npc.equipped_weapon
            
            # Use getattr to safely get loot_table if it exists
            safe_loot = getattr(npc, 'loot_table', [])
            
            # Convert dialog flags set to list for JSON serialization
            d_flags = list(getattr(npc, 'dialog_flags', []))

            npc_entry = {
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
                "loot_table": safe_loot,
                "dialog_flags": d_flags
            }
            npc_data.append(npc_entry)
        
        with open(os.path.join(save_path, "npc.rot"), "w") as f:
            json.dump(npc_data, f, indent=4)

        # --- SEPARATE ZOMBIES AND ANIMALS ---
        zombie_data = []
        animal_data = []

        # Save zombies from game.zombies
        for z in game.zombies:
            # Skip animals (they're saved separately from items_on_ground)
            if getattr(z, 'type', 'zombie') == 'animal':
                continue
            
            # Serialize Clothes
            safe_clothes = {}
            if hasattr(z, 'clothes') and z.clothes:
                for slot, item in z.clothes.items():
                    if item:
                        if hasattr(item, 'to_dict'):
                            safe_clothes[slot] = item.to_dict()
                        else:
                            safe_clothes[slot] = item
                    else:
                        safe_clothes[slot] = None
            
            # Serialize Inventory
            safe_inventory = []
            if hasattr(z, 'inventory'):
                for i in z.inventory:
                    if hasattr(i, 'to_dict'):
                        safe_inventory.append(i.to_dict())
                    else:
                        safe_inventory.append(i)

            entity_entry = {
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
            }

            zombie_data.append(entity_entry)

        # Save Zombies
        with open(os.path.join(save_path, "zombies.rot"), "w") as f:
            json.dump(zombie_data, f, indent=4)

        # Save Animals from items_on_ground
        for item in game.items_on_ground:
            if isinstance(item, Animal):
                # Serialize Clothes
                safe_clothes = {}
                if hasattr(item, 'clothes') and item.clothes:
                    for slot, it in item.clothes.items():
                        if it:
                            if hasattr(it, 'to_dict'):
                                safe_clothes[slot] = it.to_dict()
                            else:
                                safe_clothes[slot] = it
                        else:
                            safe_clothes[slot] = None

                # Serialize Inventory
                safe_inventory = []
                if hasattr(item, 'inventory'):
                    for i in item.inventory:
                        if hasattr(i, 'to_dict'):
                            safe_inventory.append(i.to_dict())
                        else:
                            safe_inventory.append(i)

                animal_entry = {
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
                }
                animal_data.append(animal_entry)

        with open(os.path.join(save_path, "animal.rot"), "w") as f:
            json.dump(animal_data, f, indent=4)

        # --- Vehicle Save ---
        vehicle_data = []
        vehicles_to_save = [obj for obj in game.containers if isinstance(obj, Vehicle)]
        for v in vehicles_to_save:
            safe_inv = []
            if hasattr(v, 'inventory'):
                for i in v.inventory:
                    if hasattr(i, 'to_dict'):
                        safe_inv.append(i.to_dict())
                    else:
                        safe_inv.append(i)

            safe_equipment = {}
            if hasattr(v, 'equipment'):
                for slot, item in v.equipment.items():
                    if item:
                        if hasattr(item, 'to_dict'):
                            safe_equipment[slot] = item.to_dict()
                        else:
                            safe_equipment[slot] = item
                    else:
                        safe_equipment[slot] = None

            v_entry = {
                "x": v.rect.x,
                "y": v.rect.y,
                "name": v.name, 
                "facing": getattr(v, 'facing', 'right'),
                "inventory": safe_inv,
                "equipment": safe_equipment, 
                "lights": getattr(v, 'lights', 'off')
            }
            vehicle_data.append(v_entry)

        with open(os.path.join(save_path, "vehicles.rot"), "w") as f:
            json.dump(vehicle_data, f, indent=4)

        container_data = []
        for c in game.containers:
            if isinstance(c, Vehicle):
                continue
            
            safe_inv = []
            if hasattr(c, 'inventory'):
                for i in c.inventory:
                    if hasattr(i, 'to_dict'):
                        safe_inv.append(i.to_dict())
                    else:
                        safe_inv.append(i)
            
            c_entry = {
                "x": c.rect.x if hasattr(c, 'rect') else c.x,
                "y": c.rect.y if hasattr(c, 'rect') else c.y,
                "inventory": safe_inv
            }
            container_data.append(c_entry)

        # --- World Data Save ---
        safe_ground_items = []
        for i in game.items_on_ground:
            # Skip Animals - they are saved separately in animal.rot
            if isinstance(i, Animal):
                continue
            item_data = i.to_dict() if hasattr(i, 'to_dict') else i
            safe_ground_items.append({
                "data": item_data,
                "x": i.rect.x if hasattr(i, 'rect') else i.x,
                "y": i.rect.y if hasattr(i, 'rect') else i.y
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
        }
        with open(os.path.join(save_path, "world.rot"), "w") as f:
            json.dump(world_data, f, indent=4)

        game.logger.info("Game saved successfully!")
        return True
        
    except Exception as e:
        game.logger.info(f"Error saving game: {e}")
        import traceback
        traceback.print_exc()
        return False