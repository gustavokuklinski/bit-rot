import pygame
from core.data.config import *
from core.entities.zombie.corpse import Corpse
from core.data.localization import tr

def try_grab_item(game):
    closest_item = None
    closest_dist_sq = float('inf')
    for item in game.items_on_ground:
        if isinstance(item, Corpse):
            continue
        dx = item.rect.centerx - game.player.rect.centerx
        dy = item.rect.centery - game.player.rect.centery
        dist_sq = dx*dx + dy*dy
        if dist_sq < closest_dist_sq:
            closest_dist_sq = dist_sq
            closest_item = item

    if closest_item and closest_dist_sq < (TILE_SIZE * 2) ** 2:
        # Convert "Campfire on" to "Campfire off" when picking up
        item_to_grab = closest_item
        if closest_item.name == "Campfire on":
            from core.entities.item.item import Item
            new_item = Item.create_from_name("Campfire off")
            if new_item:
                new_item.durability = closest_item.durability
                new_item.load = closest_item.load
                new_item.rect.center = closest_item.rect.center
                new_item.x = closest_item.x
                new_item.y = closest_item.y
                item_to_grab = new_item
                display_message(tr('msg', "Campfire extinguished when picked up."))

        target_inventory = game.player.inventory
        target_capacity = game.player.base_inventory_slots
        if game.player.backpack and any(m['type'] == 'container' and m['item'] == game.player.backpack for m in game.modals):
            target_inventory = game.player.backpack.inventory
            target_capacity = game.player.backpack.capacity or 0

        success = False
        if len(target_inventory) < target_capacity:
            target_inventory.append(item_to_grab)
            game.items_on_ground.remove(closest_item)
            success = True
            print(f"Grabbed {item_to_grab.name}.")
            display_message(f"{tr('msg', 'Grabbed')} {item_to_grab.name}.")
        elif len(game.player.inventory) < game.player.get_total_inventory_slots():
            game.player.inventory.append(item_to_grab)
            game.items_on_ground.remove(closest_item)
            success = True
            print(f"Grabbed {item_to_grab.name} into inventory.")
            display_message(f"{tr('msg', 'Grabbed')} {item_to_grab.name} {tr('msg', 'into inventory.')}")
        else:
            print("No space to grab the item.")
            display_message(tr('msg', "No space to grab the item."))

        if success:
            current_map_filename = game.map_manager.current_map_filename
            if current_map_filename not in game.map_states:
                game.map_states[current_map_filename] = {'items': [], 'zombies': [], 'killed_zombies': [], 'picked_up_items': [], 'last_respawn_time': pygame.time.get_ticks()}
            game.map_states[current_map_filename]['picked_up_items'].append(closest_item.id)

            # --- MAP UPDATE LOGIC ---
            # Remove the item from the map's spawn layout so it doesn't respawn on reload
            # This requires access to the spawn layout grid in game.
            if hasattr(game, 'spawn_layout') and game.spawn_layout:
                grid_x = int(closest_item.x // TILE_SIZE)
                grid_y = int(closest_item.y // TILE_SIZE)
                try:
                    if 0 <= grid_y < len(game.spawn_layout) and 0 <= grid_x < len(game.spawn_layout[0]):
                        if game.spawn_layout[grid_y][grid_x] == closest_item.name:
                            game.spawn_layout[grid_y][grid_x] = ' '
                            print(f"Removed world item '{closest_item.name}' from spawn layout at ({grid_x}, {grid_y})")
                except Exception as e:
                    print(f"Error updating map layout on pickup: {e}")