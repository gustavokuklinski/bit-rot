import math
from data.config import *
from core.entities.corpse import Corpse

def try_grab_item(game):
    closest_item = None
    closest_dist = float('inf')
    for item in game.items_on_ground:
        if isinstance(item, Corpse):
            continue
        dist = math.hypot(item.rect.centerx - game.player.rect.centerx, item.rect.centery - game.player.rect.centery)
        if dist < closest_dist:
            closest_dist = dist
            closest_item = item

    if closest_item and closest_dist < TILE_SIZE * 1.5:
        target_inventory = game.player.inventory
        target_capacity = game.player.base_inventory_slots
        if game.player.backpack and any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals):
            target_inventory = game.player.backpack.inventory
            target_capacity = game.player.backpack.capacity or 0
        if len(target_inventory) < target_capacity:
            target_inventory.append(closest_item)
            game.items_on_ground.remove(closest_item)
            print(f"Grabbed {closest_item.name}.")
            current_map_filename = game.map_manager.current_map_filename
            if current_map_filename not in game.map_states:
                game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': []}
            game.map_states[current_map_filename]['picked_up_items'].append(closest_item.id)
        elif len(game.player.inventory) < game.player.get_total_inventory_slots():
            game.player.inventory.append(closest_item)
            game.items_on_ground.remove(closest_item)
            print(f"Grabbed {closest_item.name} into inventory.")
            current_map_filename = game.map_manager.current_map_filename
            if current_map_filename not in game.map_states:
                game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': []}
            game.map_states[current_map_filename]['picked_up_items'].append(closest_item.id)
        else:
            print("No space to grab the item.")
