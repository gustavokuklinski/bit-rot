def build_obstacle_grid(obstacles, grid_size):
    """
    Builds a static spatial grid for STATIC obstacles (Walls).
    """
    grid = {}
    for ob in obstacles:
        grid_x = int(ob.centerx // grid_size)
        grid_y = int(ob.centery // grid_size)
        cell = (grid_x, grid_y)
        
        if cell not in grid:
            grid[cell] = [ob]
        else:
            grid[cell].append(ob)
    return grid

def get_nearby_obstacles(entity_rect, grid, grid_size):
    nearby = []
    grid_x = int(entity_rect.centerx // grid_size)
    grid_y = int(entity_rect.centery // grid_size)
    
    for i in range(-1, 2):
        for j in range(-1, 2):
            cell = (grid_x + i, grid_y + j)
            if cell in grid:
                nearby.extend(grid[cell])
    return nearby