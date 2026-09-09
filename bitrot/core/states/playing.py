import pygame
from core.data.config import BASE_PLAYER_VIEW_RADIUS, NPC_DETECTION_RADIUS
from core.input import handle_input
from core.update import update_game_state
from core.draw import draw_game
from core.map.spawn_manager import manage_dynamic_npcs
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS
from core.entities.animal.animal import Animal
from core.ui.tooltip import draw_tooltip
from core.ui.dropdown import draw_context_menu

def run_playing(game):
    if getattr(game, 'is_mixer_paused', False):
        pygame.mixer.unpause()
        pygame.mixer.music.unpause()
        game.is_mixer_paused = False
        
    game.world_time.update()
    handle_input(game)
    game.frame_count += 1

    current_z_count = len(game.zombies)
    current_i_count = len(game.items_on_ground)
    current_c_count = len(game.containers)
    
    if game.frame_count % 30 == 0 or current_z_count != getattr(game, '_cached_z_count', -1):
        game.spatial_manager.rebuild_zombie_grid()
        game._cached_z_count = current_z_count
        game.last_quadtree_player_pos = (999999, 999999) 
    
    if game.frame_count % 60 == 0 or current_i_count != getattr(game, '_cached_i_count', -1):
        game.spatial_manager.rebuild_item_grid(force=True)
        game._cached_i_count = current_i_count

    if game.frame_count % 60 == 0 or current_c_count != getattr(game, '_cached_c_count', -1):
        game.spatial_manager.rebuild_container_grid()
        game._cached_c_count = current_c_count

    px, py = game.player.rect.center
    
    BASE_SIMULATION_DISTANCE = 250
    MAX_ACTIVE_ENTITIES_TARGET = 60
    MAX_ACTIVE_ZOMBIES = 20
    MAX_ACTIVE_ANIMALS = 10
    
    total_nearby_entities = len(getattr(game, 'active_zombies', []))
    
    if total_nearby_entities > MAX_ACTIVE_ENTITIES_TARGET:
        SIMULATION_DISTANCE = BASE_SIMULATION_DISTANCE * 0.75  
    elif total_nearby_entities < MAX_ACTIVE_ENTITIES_TARGET * 0.5:
        SIMULATION_DISTANCE = BASE_SIMULATION_DISTANCE * 1.25
    else:
        SIMULATION_DISTANCE = BASE_SIMULATION_DISTANCE
    
    start_grid_x = int((px - SIMULATION_DISTANCE) // game.GRID_CELL_SIZE)
    end_grid_x = int((px + SIMULATION_DISTANCE) // game.GRID_CELL_SIZE) + 1
    start_grid_y = int((py - SIMULATION_DISTANCE) // game.GRID_CELL_SIZE)
    end_grid_y = int((py + SIMULATION_DISTANCE) // game.GRID_CELL_SIZE) + 1

    game.active_zombies = []
    game.visible_items = []
    game.visible_containers = []
    game.active_animals = []

    for gy in range(start_grid_y, end_grid_y):
        for gx in range(start_grid_x, end_grid_x):
            key = (gx, gy)
            if key in game.zombie_grid:
                game.active_zombies.extend(game.zombie_grid[key])
            if key in game.item_grid:
                game.visible_items.extend(game.item_grid[key])
            if key in game.container_grid:
                game.visible_containers.extend(game.container_grid[key])

    game.active_animals = [z for z in game.active_zombies if isinstance(z, Animal)]
    game.active_zombies = [z for z in game.active_zombies if not isinstance(z, Animal)]

    for item in game.visible_items:
        if isinstance(item, Animal) and item not in game.active_animals:
            game.active_animals.append(item)

    if len(game.active_zombies) > MAX_ACTIVE_ZOMBIES:
        game.active_zombies.sort(key=lambda z: (z.rect.centerx - px)**2 + (z.rect.centery - py)**2)
        game.active_zombies = game.active_zombies[:MAX_ACTIVE_ZOMBIES]
    
    if len(game.active_animals) > MAX_ACTIVE_ANIMALS:
        game.active_animals.sort(key=lambda a: (a.rect.centerx - px)**2 + (a.rect.centery - py)**2)
        game.active_animals = game.active_animals[:MAX_ACTIVE_ANIMALS]

    game.active_npcs = [n for n in game.npcs if abs(n.rect.centerx - px) < SIMULATION_DISTANCE and abs(n.rect.centery - py) < SIMULATION_DISTANCE]
    
    MAX_ACTIVE_NPCS = 10
    if len(game.active_npcs) > MAX_ACTIVE_NPCS:
        game.active_npcs.sort(key=lambda n: (n.rect.centerx - px)**2 + (n.rect.centery - py)**2)
        game.active_npcs = game.active_npcs[:MAX_ACTIVE_NPCS]

    quadtree_needs_rebuild = False

    if hasattr(game, 'last_quadtree_player_pos'):
        dx = px - game.last_quadtree_player_pos[0]
        dy = py - game.last_quadtree_player_pos[1]
        if dx*dx + dy*dy > 4096:  
            quadtree_needs_rebuild = True
    else:
        quadtree_needs_rebuild = True

    if hasattr(game, 'last_quadtree_projectile_count'):
        if len(game.projectiles) != game.last_quadtree_projectile_count:
            quadtree_needs_rebuild = True
    else:
        quadtree_needs_rebuild = True

    if game.frame_count % 30 == 0:
        quadtree_needs_rebuild = True
    
    if quadtree_needs_rebuild:
        game.last_quadtree_player_pos = (px, py)
        game.last_quadtree_projectile_count = len(game.projectiles)
        
        game.quadtree.clear()
        for z in game.active_zombies: game.quadtree.insert(z)
        for a in game.active_animals:
            game.quadtree.insert(a)
        for n in game.active_npcs: game.quadtree.insert(n)
        for p in game.projectiles: game.quadtree.insert(p)

        if game.map_manager and hasattr(game.map_manager, 'vehicles'):
             for v in game.map_manager.vehicles:
                 if abs(v.rect.centerx - px) < SIMULATION_DISTANCE and abs(v.rect.centery - py) < SIMULATION_DISTANCE:
                    game.quadtree.insert(v)

    update_game_state(game)
    
    if game.player:
        base_radius = BASE_PLAYER_VIEW_RADIUS
        radius_mult = 1.0

        for trait_id in game.player.traits:
            t_def = TRAIT_DEFINITIONS.get(trait_id)
            if t_def and 'config_modifiers' in t_def:
                mod = t_def['config_modifiers'].get('BASE_PLAYER_VIEW_RADIUS')
                if mod is not None:
                    radius_mult *= mod

        health_ratio = max(0.1, game.player.health / game.player.max_health)
        radius_mult *= health_ratio

        game.player_view_radius = base_radius * radius_mult
    
    game.npc_spawn_timer += 1
    if game.npc_spawn_timer >= 30:
        manage_dynamic_npcs(game)
        game.npc_spawn_timer = 0

    player_pos = game.player.rect.center if game.player else None
    NPC_UPDATE_RADIUS_SQ = (NPC_DETECTION_RADIUS + 300) ** 2
    npcs_updated = 0
    MAX_NPCS_PER_FRAME = 8
    
    for npc in game.active_npcs:
        if player_pos:
            dx = npc.rect.centerx - player_pos[0]
            dy = npc.rect.centery - player_pos[1]
            dist_sq = dx*dx + dy*dy
            
            if dist_sq > NPC_UPDATE_RADIUS_SQ and npc.state != 'chasing':
                continue
            
            if dist_sq > 400**2 and npc.state != 'chasing':
                if dist_sq <= 800**2 and game.frame_count % 2 != 0:
                    continue
                elif dist_sq > 800**2 and game.frame_count % 4 != 0:
                    continue
        
        npcs_updated += 1
        if npcs_updated > MAX_NPCS_PER_FRAME:
            break
            
        npc.update(game)

    game._cleanup_modals()
    
    game.map_manager.reset_frame_metrics()
    if game.player:
         game.map_manager.update_chunks(game.player.rect.center)

    draw_game(game)

    if game.hovered_item and not game.context_menu.get('active', False):
        mouse_pos = game._get_scaled_mouse_pos()
        draw_tooltip(game.game_screen, game.hovered_item, mouse_pos)

    if game.context_menu['active']:
        draw_context_menu(game.game_screen, game.context_menu, game._get_scaled_mouse_pos())

    game._update_screen()