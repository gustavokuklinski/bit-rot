import math
import random
import time
import pygame
from core.data.config import *
from core.entities.item.item import Projectile
from core.update import player_hit_zombie, handle_zombie_death, create_blood_splatter
from core.ui.inventory_modal import get_belt_hud_slot_rect
from core.messages import display_message
from core.data.localization import tr

def handle_attack(game, mouse_pos):
    if any(modal['is_dragging'] for modal in game.modals):
        return

    click_in_modal = False
    for modal in reversed(game.modals):
        modal_rect = modal['rect']
        if modal_rect.collidepoint(mouse_pos):
            click_in_modal = True
            break
    
    if not click_in_modal:
        for i in range(5):
            if get_belt_hud_slot_rect(i).collidepoint(mouse_pos):
                click_in_modal = True
                break

    if click_in_modal:
        return

    if GAME_OFFSET_X <= mouse_pos[0] < GAME_OFFSET_X + GAME_WIDTH:
        weapon = game.player.active_weapon
        if game.player.is_reloading:
            print("Cannot shoot while reloading.")
            return

        if weapon and weapon.item_type == 'weapon_ranged' and weapon.ammo_type:
            firing_delay = getattr(weapon, 'firing_second', 0.0)
            if firing_delay > 0:
                if time.time() - game.player.last_shot_time < firing_delay:
                    return
            
            if weapon.load > 0 and weapon.durability > 0:
                game.player.last_shot_time = time.time()
                if 'shoot' in weapon.sounds and weapon.sounds['shoot']:
                    game.sound_manager.play_sound(
                        weapon.sounds['shoot'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center,
                        base_volume=0.5,
                        pitch_variance=0.15,
                        is_critical=True
                    )
                
                if hasattr(game, 'emit_noise'):
                    game.emit_noise(game.player.rect.center, radius=TILE_SIZE * 30, source_type="gunshot")

                aim_pos = game._get_scaled_mouse_pos()
                adjusted_aim_pos = (aim_pos[0] - game.viewport_left_offset, aim_pos[1])
                target_world_x, target_world_y = game.screen_to_world(adjusted_aim_pos)
                
                if getattr(game, 'is_client', False):
                    from core.server.network import NetMsg, send_msg
                    send_msg(game.client.socket, {
                        'type': NetMsg.WORLD_ACTION, 'action': 'shoot',
                        'tx': target_world_x, 'ty': target_world_y
                    })
                elif getattr(game, 'is_server', False):
                    from core.server.network import NetMsg, send_msg
                    for s in game.server.clients:
                        send_msg(s, {
                            'type': NetMsg.WORLD_ACTION, 'action': 'shoot',
                            'player_id': getattr(game.player, 'player_id', 'host'),
                            'tx': target_world_x, 'ty': target_world_y
                        })
                
                dx = target_world_x - game.player.rect.centerx
                dy = target_world_y - game.player.rect.centery
                base_angle = math.atan2(dy, dx)

                base_aim_inaccuracy = game.player.current_aim_factor * 25.0
                ranged_level = game.player.progression.get_ranged(game.player)
                skill_modifier = max(0.1, 1.0 - (ranged_level * 0.05))
                final_inaccuracy = base_aim_inaccuracy * skill_modifier
                total_spread_deg = weapon.spread_angle + final_inaccuracy

                distance_tiles = getattr(weapon, 'firing_distance', None)
                max_dist_pixels = None 
                
                calc_dist = 1000 
                
                if distance_tiles is not None:
                    max_dist_pixels = distance_tiles * TILE_SIZE
                    calc_dist = max_dist_pixels

                damage = game.player.get_attack_damage()

                for _ in range(weapon.pellets):
                    spread = math.radians(random.uniform(-total_spread_deg / 2, total_spread_deg / 2))
                    angle = base_angle + spread
                    
                    target_x = game.player.rect.centerx + math.cos(angle) * calc_dist
                    target_y = game.player.rect.centery + math.sin(angle) * calc_dist

                    game.projectiles.append(Projectile(
                        game.player.rect.centerx, 
                        game.player.rect.centery, 
                        target_x, 
                        target_y,
                        max_distance=max_dist_pixels,
                        damage=damage,
                        game=game
                    ))

                weapon.load -= 1

                dur_loss = game.player.progression.get_ranged_durability_loss(game.player)
                weapon.durability = max(0, weapon.durability - dur_loss)

                game.player.gun_flash_timer = 5
                
                if weapon.durability <= 0:
                    print(f"{weapon.name} broke!")
                    game.player.progression.add_xp(game.player, 'maintenance', 50)
                    game.player.active_weapon = None 
                    display_message(game, f"{tr('item', weapon.name)} {tr('msg', 'is broken and unequipped.')}")
                
                # --- AUTO RELOAD: Trigger right after ammo hits 0 ---
                elif weapon.load <= 0 and not game.player.is_reloading:
                    ammo_item, _, _, _ = game.player.find_matching_ammo(weapon)
                    if ammo_item:
                        game.player.reload_active_weapon(game=game)
                    
            elif weapon.load <= 0: 
                # --- AUTO RELOAD: Trigger when attempting to shoot an empty gun ---
                ammo_item, _, _, _ = game.player.find_matching_ammo(weapon)
                if ammo_item and not game.player.is_reloading:
                    game.player.reload_active_weapon(game=game)
                else:
                    if 'noammo' in weapon.sounds and weapon.sounds['noammo']:
                        game.sound_manager.play_sound(
                            weapon.sounds['noammo'], 
                            subdir='items', 
                            game=game, 
                            source_pos=game.player.rect.center, 
                            base_volume=0.5, 
                            pitch_variance=0.15, 
                            is_critical=True
                        )
                    print(f"**CLICK!** {weapon.name} is out of ammo.")
                    display_message(f"{tr('item', weapon.name)} {tr('msg', 'is out of ammo.')}")
            else:
                print(f"**CLUNK!** {weapon.name} is broken.")
                display_message(f"{tr('item', weapon.name)} {tr('msg', 'is broken.')}")

        # ... (Rest of the melee and throw logic below remains perfectly unchanged) ...
        elif weapon and weapon.item_type == 'weapon_throw':
            # --- THROW ATTACK LOGIC ---
            firing_delay = getattr(weapon, 'firing_second', 0.5)
            if firing_delay > 0:
                if time.time() - getattr(game.player, 'last_shot_time', 0) < firing_delay:
                    return

            if getattr(weapon, 'load', 1) > 0 or getattr(weapon, 'capacity', 1) > 0:
                game.player.last_shot_time = time.time()
                if 'shoot' in weapon.sounds and weapon.sounds['shoot']:
                    game.sound_manager.play_sound(
                        weapon.sounds['shoot'], 
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center,
                        base_volume=0.5,
                        pitch_variance=0.15,
                        is_critical=True
                    )

                aim_pos = game._get_scaled_mouse_pos()
                adjusted_aim_pos = (aim_pos[0] - game.viewport_left_offset, aim_pos[1])
                target_world_x, target_world_y = game.screen_to_world(adjusted_aim_pos)
                
                dx = target_world_x - game.player.rect.centerx
                dy = target_world_y - game.player.rect.centery
                calc_dist = math.hypot(dx, dy)
                angle = math.atan2(dy, dx)
                
                max_dist_pixels = (getattr(weapon, 'firing_distance', 8) or 8) * TILE_SIZE
                if calc_dist > max_dist_pixels:
                    calc_dist = max_dist_pixels
                    target_world_x = game.player.rect.centerx + math.cos(angle) * calc_dist
                    target_world_y = game.player.rect.centery + math.sin(angle) * calc_dist

                damage = game.player.get_attack_damage()

                explosion_radius = 3
                from core.entities.item.item_data import ITEM_TEMPLATES
                template = ITEM_TEMPLATES.get(weapon.name)
                if template and 'properties' in template and 'explosion' in template['properties']:
                    explosion_radius = int(template['properties']['explosion'].get('value', 3))

                proj = Projectile(
                    game.player.rect.centerx, 
                    game.player.rect.centery, 
                    target_world_x, 
                    target_world_y,
                    speed=8,
                    max_distance=calc_dist,
                    damage=damage,
                    game=game
                )
                proj.is_explosive = True
                proj.explosion_radius = explosion_radius
                proj.image = weapon.image
                proj.owner = game.player
                
                if hasattr(weapon, 'sounds') and 'explosion' in weapon.sounds:
                    proj.explosion_sound = weapon.sounds['explosion']
                else:
                    proj.explosion_sound = None

                game.projectiles.append(proj)

                weapon.load = (getattr(weapon, 'load', 1) or 1) - 1
                if weapon.load <= 0:
                    game.player.destroy_broken_weapon(weapon)
                    game.player.active_weapon = None

        else:
            # --- MELEE ATTACK LOGIC ---
            if game.player.progression.handle_melee_attack(game.player, weapon):
                aim_pos = game._get_scaled_mouse_pos()
                adjusted_aim_pos = (aim_pos[0] - game.viewport_left_offset, aim_pos[1])
                world_pos = game.screen_to_world(adjusted_aim_pos)

                dx_swing = world_pos[0] - game.player.rect.centerx
                dy_swing = world_pos[1] - game.player.rect.centery
                game.player.melee_swing_angle = math.atan2(-dy_swing, dx_swing)
                game.player.melee_swing_timer = 15

                if getattr(game, 'is_client', False):
                    from core.server.network import NetMsg, send_msg
                    send_msg(game.client.socket, {
                        'type': NetMsg.WORLD_ACTION, 'action': 'melee_swing',
                        'angle': game.player.melee_swing_angle
                    })
                elif getattr(game, 'is_server', False):
                    from core.server.network import NetMsg, send_msg
                    for s in game.server.clients:
                        send_msg(s, {
                            'type': NetMsg.WORLD_ACTION, 'action': 'melee_swing',
                            'player_id': getattr(game.player, 'player_id', 'host'),
                            'angle': game.player.melee_swing_angle
                        })

                if weapon and weapon.item_type in ['weapon_melee', 'tool'] and 'swing' in weapon.sounds and weapon.sounds['swing']:
                    game.sound_manager.play_sound(
                        weapon.sounds['swing'],
                        subdir='items',
                        game=game,
                        source_pos=game.player.rect.center,
                        base_volume=0.5,
                        pitch_variance=0.15,
                        is_critical=True
                    )

                hit_something = False
                attack_range = TILE_SIZE * 1.5 
                if weapon and hasattr(weapon, 'reach'):
                     attack_range = weapon.reach * TILE_SIZE

                has_melee_weapon = weapon is not None and getattr(weapon, 'item_type', '') in ['weapon_melee', 'tool']
                can_deal_damage = game.player.stamina > 0 or has_melee_weapon

                # 1. Hit Zombies
                for zombie in game.zombies:
                    dist = math.hypot(zombie.rect.centerx - game.player.rect.centerx, zombie.rect.centery - game.player.rect.centery)
                    if dist <= attack_range:
                        dx = zombie.rect.centerx - game.player.rect.centerx
                        dy_inv = game.player.rect.centery - zombie.rect.centery
                        z_angle = math.atan2(dy_inv, dx)

                        angle_diff = abs(game.player.melee_swing_angle - z_angle)
                        if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff

                        if zombie.rect.collidepoint(world_pos) or angle_diff < 1.0:
                            dx_kb = zombie.rect.centerx - game.player.rect.centerx
                            dy_kb = zombie.rect.centery - game.player.rect.centery 
                            kb_angle = math.atan2(dy_kb, dx_kb)

                            if can_deal_damage:
                                damage = game.player.get_attack_damage()
                                create_blood_splatter(game, zombie.rect, damage, [math.cos(kb_angle), math.sin(kb_angle)])
                                game.splashes.append({'pos': (zombie.rect.centerx, zombie.rect.bottom), 'time': pygame.time.get_ticks(), 'duration': 350, 'radius': 2, 'type': 'hit_puff'})

                                force = 7
                                kb_x = math.cos(kb_angle) * force
                                kb_y = math.sin(kb_angle) * force
                                zombie.knockback_velocity = [kb_x, kb_y]
                                zombie.knockback_timer = 200

                                if getattr(game, 'is_client', False) and getattr(game, 'client', None):
                                    send_msg(game.client.socket, {
                                        'type': NetMsg.ENTITY_DAMAGE,
                                        'entity_type': 'zombie',
                                        'id': getattr(zombie, 'id', None),
                                        'damage': damage,
                                        'kb_x': kb_x,
                                        'kb_y': kb_y
                                    })
                                else:
                                    if player_hit_zombie(game.player, zombie, game):
                                        handle_zombie_death(game, zombie, game.items_on_ground, game.obstacles, weapon)
                                        game.zombies_killed += 1

                            force = 7 
                            zombie.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                            zombie.knockback_timer = 200 

                            if weapon is None and can_deal_damage:
                                self_damage = random.randint(1, 3)
                                game.player.stamina = max(0.0, game.player.stamina - self_damage)

                            hit_something = True
                            break

                # 2. Hit Remote Players (PvP)
                if not hit_something:
                    for rp in getattr(game, 'remote_players', {}).values():
                        if getattr(rp, 'is_dead', False): continue
                        dist = math.hypot(rp.rect.centerx - game.player.rect.centerx, rp.rect.centery - game.player.rect.centery)
                        if dist <= attack_range:
                            dx = rp.rect.centerx - game.player.rect.centerx
                            dy_inv = game.player.rect.centery - rp.rect.centery
                            rp_angle = math.atan2(dy_inv, dx)
                            angle_diff = abs(game.player.melee_swing_angle - rp_angle)
                            if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff

                            if rp.rect.collidepoint(world_pos) or angle_diff < 1.0:
                                dx_kb = rp.rect.centerx - game.player.rect.centerx
                                dy_kb = rp.rect.centery - game.player.rect.centery 
                                kb_angle = math.atan2(dy_kb, dx_kb)

                                if can_deal_damage:
                                    damage = game.player.get_attack_damage()
                                    create_blood_splatter(game, rp.rect, damage, [math.cos(kb_angle), math.sin(kb_angle)])
                                    game.splashes.append({'pos': rp.rect.center, 'time': pygame.time.get_ticks(), 'duration': 350, 'radius': 3, 'type': 'hit_puff'})

                                    if getattr(game, 'is_client', False):
                                        from core.server.network import NetMsg, send_msg
                                        send_msg(game.client.socket, {
                                            'type': NetMsg.ENTITY_DAMAGE, 'entity_type': 'player',
                                            'id': rp.player_id, 'damage': damage
                                        })
                                    else:
                                        for s, info in game.server.clients.items():
                                            if info.get('id') == rp.player_id:
                                                from core.server.network import NetMsg, send_msg
                                                send_msg(s, {'type': NetMsg.ENTITY_DAMAGE, 'entity_type': 'player', 'damage': damage})
                                                break
                                hit_something = True
                                break

                # 3. Hit Animals
                if not hit_something:
                    for animal in getattr(game, 'active_animals', []):
                        dist = math.hypot(animal.rect.centerx - game.player.rect.centerx, animal.rect.centery - game.player.rect.centery)
                        if dist <= attack_range:
                            dx = animal.rect.centerx - game.player.rect.centerx
                            dy_inv = game.player.rect.centery - animal.rect.centery
                            animal_angle = math.atan2(dy_inv, dx)

                            angle_diff = abs(game.player.melee_swing_angle - animal_angle)
                            if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff

                            if animal.rect.collidepoint(world_pos) or angle_diff < 1.0:
                                dx_kb = animal.rect.centerx - game.player.rect.centerx
                                dy_kb = animal.rect.centery - game.player.rect.centery
                                kb_angle = math.atan2(dy_kb, dx_kb)

                                if can_deal_damage:
                                    damage = game.player.get_attack_damage()
                                    create_blood_splatter(game, animal.rect, damage, [math.cos(kb_angle), math.sin(kb_angle)])
                                    is_dead = animal.take_damage(damage, game, attacker=game.player)
                                    display_message(f"{tr('msg', 'You attacked the animal for')} {damage} {tr('msg', 'damage!')}")

                                    if is_dead:
                                        animal.die(game)
                                        if animal in game.items_on_ground: game.items_on_ground.remove(animal)
                                        if animal in game.active_animals: game.active_animals.remove(animal)
                                        display_message(tr('msg', "You killed the animal!"))

                                if dist > 0:
                                    force = 7
                                    animal.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                                    animal.knockback_timer = 200

                                if weapon is None and can_deal_damage:
                                    self_damage = random.randint(1, 3)
                                    game.player.stamina = max(0.0, game.player.stamina - self_damage)

                                hit_something = True
                                break

                # 4. Hit NPCs
                if not hit_something:
                    for npc in getattr(game, 'npcs', []):
                        if not npc.is_dead:
                            dist = math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery)
                            if dist <= attack_range:
                                dx = npc.rect.centerx - game.player.rect.centerx
                                dy_inv = game.player.rect.centery - npc.rect.centery
                                npc_angle = math.atan2(dy_inv, dx)

                                angle_diff = abs(game.player.melee_swing_angle - npc_angle)
                                if angle_diff > math.pi: angle_diff = 2 * math.pi - angle_diff

                                if npc.rect.collidepoint(world_pos) or angle_diff < 1.0:
                                    dx_kb = npc.rect.centerx - game.player.rect.centerx
                                    dy_kb = npc.rect.centery - game.player.rect.centery
                                    kb_angle = math.atan2(dy_kb, dx_kb)

                                    if can_deal_damage:
                                        damage = game.player.get_attack_damage()
                                        direction = [math.cos(kb_angle), math.sin(kb_angle)]
                                        create_blood_splatter(game, npc.rect, damage, direction)

                                        force = 7
                                        kb_x = math.cos(kb_angle) * force
                                        kb_y = math.sin(kb_angle) * force
                                        npc.knockback_velocity = [kb_x, kb_y]
                                        npc.knockback_timer = 200

                                        if getattr(game, 'is_client', False) and getattr(game, 'client', None):
                                            from core.server.network import NetMsg, send_msg
                                            send_msg(game.client.socket, {
                                                'type': NetMsg.ENTITY_DAMAGE,
                                                'entity_type': 'npc',
                                                'id': getattr(npc, 'id', None),
                                                'damage': damage,
                                                'kb_x': kb_x,
                                                'kb_y': kb_y
                                            })
                                        else:
                                            is_dead = npc.take_damage(damage, game, attacker=game.player)
                                            display_message(game, f"{tr('msg', 'You attacked')} {npc.name} {tr('msg', 'for')} {damage} {tr('msg', 'damage!')}")
                                    
                                    if dist > 0:
                                        force = 7
                                        npc.knockback_velocity = [math.cos(kb_angle) * force, math.sin(kb_angle) * force]
                                        npc.knockback_timer = 200

                                    if weapon is None and can_deal_damage:
                                        self_damage = random.randint(1, 3)
                                        game.player.stamina = max(0.0, game.player.stamina - self_damage)

                                    hit_something = True
                                    break

                if not hit_something:
                    clicked_grid_x = int(world_pos[0] // TILE_SIZE)
                    clicked_grid_y = int(world_pos[1] // TILE_SIZE)

                    target_found = False

                    for offset_y in range(4):
                        target_y = clicked_grid_y + offset_y

                        if game.map_manager.is_tile_destructible(clicked_grid_x, target_y):

                            tile_center_x = clicked_grid_x * TILE_SIZE + TILE_SIZE / 2
                            tile_center_y = target_y * TILE_SIZE + TILE_SIZE / 2
                            dist = math.hypot(game.player.rect.centerx - tile_center_x, game.player.rect.centery - tile_center_y)

                            if dist <= TILE_SIZE * 2:
                                if weapon is None:
                                    if not can_deal_damage:
                                        hit_something = True
                                        break
                                    self_damage = random.randint(1, 2)
                                    game.player.stamina = max(0.0, game.player.stamina - self_damage)

                                damage = game.player.get_attack_damage()
                                result = game.map_manager.hit_tile(clicked_grid_x, target_y, damage, weapon=weapon)
                                 
                                if result:
                                    hit_something = True
                                    target_found = True
                                    if weapon is None and game.player.stamina > 0:
                                        game.player.stamina = max(0.0, game.player.stamina - 0.5)
                                    break

                if not hit_something: print("Swung and missed!")