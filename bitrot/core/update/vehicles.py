import pygame
import math
from core.update.combat import create_blood_splatter, handle_zombie_death
from core.messages import display_message

def update_vehicles(game, zombies_to_remove):
    if game.map_manager and hasattr(game.map_manager, 'vehicles'):
        roadkill_zombies = []
        multiplier = 1.0

        for vehicle in game.map_manager.vehicles:
            vehicle.update(game=game, dt_mult=game.dt_mult * multiplier)
            
            detected_entities = []
            if hasattr(vehicle, 'hit_entities') and vehicle.hit_entities:
                detected_entities.extend(vehicle.hit_entities)
                vehicle.hit_entities = []

            for entity in game.quadtree.query(vehicle.rect.inflate(10, 10)):
                if entity not in detected_entities and vehicle.rect.colliderect(entity.rect) and entity != vehicle:
                     detected_entities.append(entity)
            
            if detected_entities:
                speed = math.hypot(vehicle.velocity[0], vehicle.velocity[1])
                if speed > 0.5: 
                    for entity in detected_entities:
                        if entity in roadkill_zombies or getattr(entity, 'is_dead', False): continue

                        current_time = pygame.time.get_ticks()
                        if current_time - getattr(entity, 'last_vehicle_hit_time', 0) < 500: continue
                        entity.last_vehicle_hit_time = current_time

                        impact_damage = 10000 
                        vehicle.damage_motor(2.0)
                        
                        velocity_dir = [vehicle.velocity[0]/speed, vehicle.velocity[1]/speed] if speed > 0 else None
                        create_blood_splatter(game, entity.rect, 20, velocity_dir)

                        if entity in game.zombies:
                             if entity.take_damage(impact_damage, game):
                                roadkill_zombies.append(entity)
                                handle_zombie_death(game, entity, game.items_on_ground, game.obstacles, None)
                                game.zombies_killed += 1
                             else:
                                 if speed > 0:
                                     entity.knockback_velocity = [(vehicle.velocity[0] / speed) * 15, (vehicle.velocity[1] / speed) * 15]
                                     entity.knockback_timer = 200

                        elif getattr(entity, 'type', 'zombie') == 'animal':
                             if entity.take_damage(impact_damage, game):
                                 entity.die(game)
                                 if entity in game.items_on_ground: game.items_on_ground.remove(entity)
                                 if entity in getattr(game, 'active_animals', []): game.active_animals.remove(entity)
                                 display_message(f"You ran over an animal!")
                             else:
                                 if speed > 0:
                                     entity.knockback_velocity = [(vehicle.velocity[0] / speed) * 15, (vehicle.velocity[1] / speed) * 15]
                                     entity.knockback_timer = 200

                        elif hasattr(game, 'npcs') and entity in game.npcs:
                             if entity.take_damage(impact_damage, game, attacker=game.player):
                                 handle_zombie_death(game, entity, game.items_on_ground, game.obstacles, None)
                                 display_message(f"You ran over {entity.name}!")
                             else:
                                 if speed > 0:
                                     entity.knockback_velocity = [(vehicle.velocity[0] / speed) * 15, (vehicle.velocity[1] / speed) * 15]
                                     entity.knockback_timer = 200

        if roadkill_zombies:
            game.zombies = [z for z in game.zombies if z not in roadkill_zombies and z not in zombies_to_remove]
        
        if hasattr(game, 'npcs'):
            if hasattr(game.npcs, 'sprites'):
                for n in list(game.npcs):
                    if n.is_dead: n.kill() 
            else:
                game.npcs = [n for n in game.npcs if not n.is_dead]