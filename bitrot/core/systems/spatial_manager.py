import pygame
from core.entities.animal.animal import Animal

class SpatialManager:
    def __init__(self, game):
        self.game = game

    def _check_significant_movement(self, entity, tracked_dict, entity_id):
        current_pos = (entity.rect.centerx, entity.rect.centery)
        if entity_id not in tracked_dict:
            tracked_dict[entity_id] = current_pos
            return True
        last_pos = tracked_dict[entity_id]
        dx = current_pos[0] - last_pos[0]
        dy = current_pos[1] - last_pos[1]
        if (dx*dx + dy*dy) > self.game.GRID_REBUILD_THRESHOLD ** 2:
            tracked_dict[entity_id] = current_pos
            return True
        return False

    def rebuild_zombie_grid(self):
        g = self.game
        current_zombie_count = len(g.zombies)
        current_animal_count = sum(1 for item in g.items_on_ground if isinstance(item, Animal))
        current_total = current_zombie_count + current_animal_count

        tracked_total = len(g.last_zombie_grid_positions)
        needs_rebuild = False
        if current_total != tracked_total:
            needs_rebuild = True
        else:
            for z in g.zombies:
                if self._check_significant_movement(z, g.last_zombie_grid_positions, id(z)):
                    needs_rebuild = True
                    break
            if not needs_rebuild:
                for item in g.items_on_ground:
                    if isinstance(item, Animal):
                        if self._check_significant_movement(item, g.last_zombie_grid_positions, id(item)):
                            needs_rebuild = True
                            break
            if not needs_rebuild:
                return 

        zombie_ids = {id(z) for z in g.zombies}
        animal_ids = {id(item) for item in g.items_on_ground if isinstance(item, Animal)}
        valid_ids = zombie_ids | animal_ids
        for z_id in list(g.last_zombie_grid_positions.keys()):
            if z_id not in valid_ids:
                del g.last_zombie_grid_positions[z_id]

        g.zombie_grid.clear()
        for z in g.zombies:
            key = (int(z.rect.centerx // g.GRID_CELL_SIZE), int(z.rect.centery // g.GRID_CELL_SIZE))
            if key not in g.zombie_grid: g.zombie_grid[key] = []
            g.zombie_grid[key].append(z)

        for item in g.items_on_ground:
            if isinstance(item, Animal):
                key = (int(item.rect.centerx // g.GRID_CELL_SIZE), int(item.rect.centery // g.GRID_CELL_SIZE))
                if key not in g.zombie_grid: g.zombie_grid[key] = []
                g.zombie_grid[key].append(item)

    def rebuild_item_grid(self, force=False):
        g = self.game
        if not hasattr(self, '_last_item_count'): self._last_item_count = 0
        if len(g.items_on_ground) != self._last_item_count:
            self._last_item_count = len(g.items_on_ground)
            force = True
        if not force and g.frame_count % 60 != 0: return 
        g.item_grid.clear()
        for i in g.items_on_ground:
            key = (int(i.rect.centerx // g.GRID_CELL_SIZE), int(i.rect.centery // g.GRID_CELL_SIZE))
            if key not in g.item_grid: g.item_grid[key] = []
            g.item_grid[key].append(i)

    def rebuild_container_grid(self):
        g = self.game
        if not hasattr(self, '_last_container_count'): self._last_container_count = 0
        if len(g.containers) == self._last_container_count and g.frame_count % 60 != 0: return  
        self._last_container_count = len(g.containers)
        g.container_grid.clear()
        for c in g.containers:
            key = (int(c.rect.centerx // g.GRID_CELL_SIZE), int(c.rect.centery // g.GRID_CELL_SIZE))
            if key not in g.container_grid: g.container_grid[key] = []
            g.container_grid[key].append(c)