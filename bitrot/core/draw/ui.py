import pygame
import math
from core.data.config import *
import core.data.config
from core.entities.animal.animal import Animal
from core.ui.inventory_modal import draw_inventory_modal, get_inventory_slot_rect, get_belt_slot_rect_in_modal, draw_belt_hud, get_belt_hud_slot_rect
from core.ui.container_modal import draw_container_view, get_container_slot_rect
from core.ui.status_modal import draw_status_modal
from core.ui.dropdown import draw_context_menu
from core.ui.nearby_modal import draw_nearby_modal
from core.ui.helpers.buttons import draw_inventory_button, draw_status_button, draw_pause_button, draw_nearby_button, draw_messages_button, draw_gear_button, draw_crafting_button, draw_help_button, draw_slots_button
from core.ui.tooltip import draw_tooltip
from core.ui.help_modal import draw_help_modal
from core.ui.gear_modal import draw_gear_modal
from core.ui.messages_modal import draw_messages_modal
from core.ui.text_modal import draw_text_modal
from core.ui.mobile_modal import draw_mobile_modal
from core.ui.alerts import draw_player_alerts
from core.ui.vehicle_modal import draw_vehicle_modal
from core.ui.crafting_modal import CraftingModal
from core.ui.mobile_map_tab import draw_big_map_modal
from core.ui.npc_dialog_modal import draw_npc_dialog_modal
from core.ui.slots_modal import draw_slots_modal
from core.systems.utils import get_player_facing_tile, get_targeted_interactable, find_nearby_containers
from core.data.localization import tr
from core.ui.helpers.keybinds import keybind_manager

def get_key_name(action):
    val = keybind_manager.kb_binds.get(action)
    if val is None: return ""
    if val < 0:
        btn_num = -val
        if btn_num == 1: return "LMB"
        elif btn_num == 2: return "MMB"
        elif btn_num == 3: return "RMB"
        else: return f"MB{btn_num}"
    else:
        name = pygame.key.name(val).upper()
        if name == "SPACE": return "SPACE"
        if name == "LEFT SHIFT": return "LSHIFT"
        if name == "LEFT CTRL": return "LCTRL"
        if name == "RETURN": return "ENTER"
        return name

def _draw_tt(game, tip, x, y, center_align=False, dynamic_h=GAME_HEIGHT):
    """Helper to render interaction tooltips"""
    if isinstance(tip, str):
        lines = tip.split('\n')
        max_w = max((font_12.render(line, False, WHITE).get_width() for line in lines), default=0)
        tt_w, tt_h = max_w + 10, len(lines) * 20 + 10
        if center_align: 
            x -= tt_w // 2
        else: 
            x, y = min(x, GAME_WIDTH - tt_w - 5), min(y, dynamic_h - tt_h - 5) # Use dynamic_h
        
        tip_bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
        tip_bg.fill((0, 0, 0, 220))
        game.game_screen.blit(tip_bg, (x, y))
        pygame.draw.rect(game.game_screen, WHITE, pygame.Rect(x, y, tt_w, tt_h), 1)
        for i, line in enumerate(lines):
            ls = font_12.render(line, False, WHITE)
            lx = x + (tt_w//2 - ls.get_width()//2 if center_align else 5)
            game.game_screen.blit(ls, (lx, y + 5 + i*20))
            
    elif isinstance(tip, dict) and tip.get('type') == 'vehicle':
        if not hasattr(game, 'vehicle_icons'):
            game.vehicle_icons = {}
            icon_paths = {'fuel': SPRITE_PATH + '/items/car_fuel_unit.png', 'motor': SPRITE_PATH + '/items/car_motor.png', 'power': SPRITE_PATH + '/items/car_battery.png', 'tires': SPRITE_PATH + '/items/car_tire.png', 'key': SPRITE_PATH + '/items/car_key_pickup.png'}
            for k, path in icon_paths.items():
                try: game.vehicle_icons[k] = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (16, 16))
                except: game.vehicle_icons[k] = None
        
        lines = tip['text_lines']
        stats_w = sum((20 if game.vehicle_icons.get(s['icon']) else font_12.render(s['text'] + ": ", False, WHITE).get_width()) + font_12.render(s['val'], False, WHITE).get_width() + 10 for s in tip['stats']) - 10
        tt_w = max(max((font_12.render(line, False, WHITE).get_width() for line in lines), default=0), stats_w) + 10
        tt_h = len(lines) * 20 + 30
        if center_align: 
            x -= tt_w // 2
        else: 
            x, y = min(x, GAME_WIDTH - tt_w - 5), min(y, dynamic_h - tt_h - 5) # Use dynamic_h
        
        tip_bg = pygame.Surface((tt_w, tt_h), pygame.SRCALPHA)
        tip_bg.fill((0, 0, 0, 220))
        game.game_screen.blit(tip_bg, (x, y))
        pygame.draw.rect(game.game_screen, WHITE, pygame.Rect(x, y, tt_w, tt_h), 1)
        for i, line in enumerate(lines):
            ls = font_12.render(line, False, WHITE)
            lx = x + (tt_w//2 - ls.get_width()//2 if center_align else 5)
            game.game_screen.blit(ls, (lx, y + 5 + i*20))
        
        curr_x, curr_y = x + (tt_w//2 - stats_w//2 if center_align else 5), y + 5 + len(lines)*20
        for stat in tip['stats']:
            if game.vehicle_icons.get(stat['icon']):
                game.game_screen.blit(game.vehicle_icons[stat['icon']], (curr_x, curr_y)); curr_x += 20
            else:
                ts = font_12.render(stat['text'] + ": ", False, WHITE)
                game.game_screen.blit(ts, (curr_x, curr_y + 2)); curr_x += ts.get_width()
            vs = font_12.render(stat['val'], False, WHITE)
            game.game_screen.blit(vs, (curr_x, curr_y + 2)); curr_x += vs.get_width() + 10
            
def draw_hovers(game, surface, offset_x, offset_y, screen_rect, zoom):
    view_radius_sq = (game.player_view_radius + TILE_SIZE) ** 2
    world_mouse_pos = game.screen_to_world((game._get_scaled_mouse_pos()[0] - game.viewport_left_offset, game._get_scaled_mouse_pos()[1]))

    if game.hovered_container:
        dx, dy = game.hovered_container.rect.centerx - game.player.rect.centerx, game.hovered_container.rect.centery - game.player.rect.centery
        if (dx*dx + dy*dy) <= view_radius_sq: pygame.draw.rect(surface, YELLOW, game.hovered_container.rect.move(offset_x, offset_y), 2)

    for npc in game.npcs:
        if screen_rect.colliderect(npc.rect) and npc.rect.collidepoint(world_mouse_pos):
            pygame.draw.rect(surface, GRAY, npc.rect.move(offset_x, offset_y), 2)
            break
    
    for zombie in game.active_zombies:
        if screen_rect.colliderect(zombie.rect) and zombie.rect.collidepoint(world_mouse_pos):
            pygame.draw.rect(surface, (128, 0, 128), zombie.rect.move(offset_x, offset_y), 2)
            break

    for animal in game.active_animals:
        if screen_rect.colliderect(animal.rect) and animal.rect.collidepoint(world_mouse_pos):
            pygame.draw.rect(surface, (128, 0, 128), animal.rect.move(offset_x, offset_y), 2)
            break

    if game.hovered_interactable_tile_rect:
        pygame.draw.rect(surface, BLUE, game.hovered_interactable_tile_rect.move(offset_x, offset_y), 2)
    
    target = get_targeted_interactable(game)
    target_world_rect = None

    if target:
        if target['type'] in ['npc', 'vehicle', 'container']: target_world_rect = target['entity'].rect
        elif target['type'] in ['tile', 'stair']: target_world_rect = pygame.Rect(target['entity'][0] * TILE_SIZE, target['entity'][1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        if target_world_rect: pygame.draw.rect(surface, (0, 255, 100), target_world_rect.move(offset_x, offset_y), 2)

    return target_world_rect

def draw_ui(game, offset_x, offset_y, zoom, dynamic_h, screen_rect, target_world_rect):
    mouse_pos = game._get_scaled_mouse_pos()
    
    # --- LAYER 1: World Space Indicators ---
    interactables = []
    for npc in game.npcs:
        if npc.is_friendly and npc.aggro_timer <= 0 and screen_rect.colliderect(npc.rect) and math.hypot(game.player.rect.centerx - npc.rect.centerx, game.player.rect.centery - npc.rect.centery) < TILE_SIZE * 1.5:
            interactables.append({'rect': npc.rect, 'tip': tr('tooltip', 'Press E to Talk\nRMB For Talk option')})
                
    for obj in game.containers:
        if getattr(obj, 'item_type', '') == 'vehicle' and getattr(game.player, 'vehicle', None) != obj and screen_rect.colliderect(obj.rect):
            if math.hypot(game.player.rect.centerx - obj.rect.centerx, game.player.rect.centery - obj.rect.centery) < TILE_SIZE * 2.0:
                equip = getattr(obj, 'equipment', {})
                req_tires = getattr(obj, 'required_tires', [])
                tires_count = sum(1 for t in req_tires if equip.get(t) and getattr(equip.get(t), 'durability', 0) > 0)
                key_status = tr('tooltip', "Not Req") if not getattr(obj, 'required_key_id', None) else (tr('tooltip', "Yes") if equip.get('key') else tr('tooltip', "Missing"))
                interactables.append({'rect': obj.rect, 'tip': {
                    'type': 'vehicle',
                    'text_lines': [tr('tooltip', f"Press {get_key_name('interact')} to enter/exit vehicle"), tr('tooltip', f"Press {get_key_name('vehicle_engine')} to turn on/off engine"), tr('tooltip', "RMB for Vehicle Options and Trunk"), ""],
                    'stats': [{'icon': 'motor', 'text': tr('tooltip', "Motor"), 'val': f"{int(getattr(obj, 'motor', 0.0) * 100)}%"}, {'icon': 'fuel', 'text': tr('tooltip', "Fuel"), 'val': f"{int(getattr(obj, 'fuel', 0))}"}, {'icon': 'power', 'text': tr('tooltip', "Power"), 'val': f"{int(getattr(obj, 'battery', 0))}"}, {'icon': 'tires', 'text': tr('tooltip', "Tires"), 'val': f"{tires_count}/{len(req_tires) if req_tires else 4}"}, {'icon': 'key', 'text': tr('tooltip', "Key"), 'val': key_status}]
                }})

    fx, fy = get_player_facing_tile(game)
    if fx is not None:
        t = game.map_manager.get_tile_at(fx, fy)
        if t and (t.get('is_stair') or t.get('is_statable')) and math.hypot(game.player.rect.centerx - (fx*TILE_SIZE + TILE_SIZE/2), game.player.rect.centery - (fy*TILE_SIZE + TILE_SIZE/2)) < TILE_SIZE * 1.5:
            interactables.append({'rect': pygame.Rect(fx * TILE_SIZE, fy * TILE_SIZE, TILE_SIZE, TILE_SIZE), 'tip': tr('tooltip', f"Press {get_key_name('interact')}\nto go Down/Up" if t.get('is_stair') else f"Press {get_key_name('interact')} or RMB\nto Open/Close")})

    for obj in find_nearby_containers(game):
        if getattr(obj, 'item_type', '') != 'vehicle' and (getattr(obj, 'item_type', '') in ['container', 'maptile_container', 'corpse'] or type(obj).__name__ == 'Corpse') and screen_rect.colliderect(obj.rect):
            interactables.append({'rect': obj.rect, 'tip': tr('tooltip', f"Press {get_key_name('interact')} to inspect\nor use the Nearby modal")})

    tooltip_to_draw = None
    focused_tip = None 
    for item in interactables:
        world_rect = item['rect']
        if target_world_rect and world_rect == target_world_rect: focused_tip = item['tip']
        box_rect = pygame.Rect(0, 0, 20, 20)
        box_rect.center = (((world_rect.centerx + offset_x) * zoom) + GAME_OFFSET_X + game.viewport_left_offset, ((world_rect.top + offset_y) * zoom) - 5)
        pygame.draw.rect(game.game_screen, (0, 0, 0), box_rect)
        pygame.draw.rect(game.game_screen, (255, 255, 255), box_rect, 1)
        game.game_screen.blit(font_12.render("!", False, (255, 255, 255)), font_12.render("!", False, (255, 255, 255)).get_rect(center=box_rect.center))
        if box_rect.collidepoint(mouse_pos): tooltip_to_draw = item['tip']

    # --- RENDER INTERACTION TOOLTIPS (drawn on top of world, under modals) ---
    if tooltip_to_draw:
        _draw_tt(game, tooltip_to_draw, mouse_pos[0] + 15, mouse_pos[1] + 15, dynamic_h=dynamic_h)
    
    # This display the tooltip on top of the player belt 
    #if focused_tip and focused_tip != tooltip_to_draw:
    #    _draw_tt(game, focused_tip, game.viewport_left_offset + (game.dynamic_w // 2), dynamic_h - 130, center_align=True)
    #

    # --- LAYER 2: UI Buttons & Basic HUD ---
    if game.game_state in ['PLAYING', 'PAUSED']:
        view_left, view_right = game.viewport_left_offset, game.viewport_left_offset + game.dynamic_w
        game.pause_button_rect = draw_pause_button(game.game_screen, view_left, view_right, dynamic_h)
        
        # --- NEW: Menu HUD Toggle Button (Placed to the left of the Pause button) ---
        game.menu_hud_button_rect = pygame.Rect(
            game.pause_button_rect.x + 25,
            game.pause_button_rect.y,
            game.pause_button_rect.width,
            game.pause_button_rect.height
        )
        
        
        
        if getattr(game, 'assets', None) and game.assets.get('menu_hud_icon'):
            icon_rect = game.assets['menu_hud_icon'].get_rect(center=game.menu_hud_button_rect.center)
            game.game_screen.blit(game.assets['menu_hud_icon'], icon_rect)
            
        # Conditionally render the other left-side HUD buttons
        show_hud_menus = getattr(game, 'show_hud_menus', False)
        
        if show_hud_menus:
            game.status_button_rect = draw_status_button(game.game_screen, view_left, view_right, dynamic_h)
            game.inventory_button_rect = draw_inventory_button(game.game_screen, view_left, view_right, dynamic_h)
            game.nearby_button_rect = draw_nearby_button(game.game_screen, view_left, view_right, dynamic_h)
            game.gear_button_rect = draw_gear_button(game.game_screen, view_left, view_right, dynamic_h)
            game.slots_button_rect = draw_slots_button(game.game_screen, view_left, view_right, dynamic_h)
            game.messages_button_rect = draw_messages_button(game.game_screen, view_left, view_right, dynamic_h)
            game.crafting_button_rect = draw_crafting_button(game.game_screen, view_left, view_right, dynamic_h)
            game.help_button_rect = draw_help_button(game.game_screen, view_left, view_right, dynamic_h)
        else:
            game.status_button_rect = None
            game.inventory_button_rect = None
            game.nearby_button_rect = None
            game.gear_button_rect = None
            game.slots_button_rect = None
            game.messages_button_rect = None
            game.crafting_button_rect = None
            game.help_button_rect = None

        # Build the tooltips 
        for rect, label in [
            (game.pause_button_rect, tr('ui', f"Pause and Save (F2)")), 
            (game.menu_hud_button_rect, tr('ui', "Toggle UI Menus (SHIFT+M)")),
            (getattr(game, 'status_button_rect', None), tr('ui', f"Player Status ({get_key_name('toggle_status')})")), 
            (getattr(game, 'inventory_button_rect', None), tr('ui', f"Inventory ({get_key_name('toggle_inventory')})")), 
            (getattr(game, 'gear_button_rect', None), tr('ui', f"Gear ({get_key_name('toggle_gear')})")), 
            (getattr(game, 'slots_button_rect', None), tr('ui', f"Slots Overview ({get_key_name('toggle_slots')})")), 
            (getattr(game, 'nearby_button_rect', None), tr('ui', f"Nearby ({get_key_name('toggle_nearby')})")), 
            (getattr(game, 'messages_button_rect', None), tr('ui', f"Messages ({get_key_name('toggle_messages')})")), 
            (getattr(game, 'crafting_button_rect', None), tr('ui', f"Crafting ({get_key_name('toggle_crafting')})")), 
            (getattr(game, 'help_button_rect', None), tr('ui', "Help and Tutorial (?)"))
        ]:
            if rect and rect.collidepoint(mouse_pos):
                text_surf = font_12.render(label, True, WHITE)
                tip_x, tip_y = min(mouse_pos[0] + 10, GAME_WIDTH - text_surf.get_width() - 21), min(mouse_pos[1] + 10, GAME_HEIGHT - text_surf.get_height() - 21)
                pygame.draw.rect(game.game_screen, (0, 0, 0, 220), pygame.Rect(tip_x, tip_y, text_surf.get_width() + 16, text_surf.get_height() + 16))
                pygame.draw.rect(game.game_screen, WHITE, pygame.Rect(tip_x, tip_y, text_surf.get_width() + 16, text_surf.get_height() + 16), 1)
                game.game_screen.blit(text_surf, (tip_x + 8, tip_y + 8))

    draw_belt_hud(game.game_screen, game, game.player, mouse_pos, dynamic_h)
    alert_tooltip = draw_player_alerts(game.game_screen, game.player)
    if alert_tooltip: game.hovered_item = alert_tooltip

    # --- LAYER 3: Modals (Sits on top of Buttons and HUD) ---
    top_tooltip = None
    game.hovered_tab_tooltip = None
    game.modal_buttons = []
    topmost_modal_id = game.modals[-1]['id'] if game.modals else None

    for modal in game.modals:
        modal['is_active'] = (modal['id'] == topmost_modal_id)
        if modal['type'] == 'status': game.modal_buttons.extend(draw_status_modal(game.game_screen, game.player, modal, game.assets, game.zombies_killed, mouse_pos, game))
        elif modal['type'] == 'inventory':
            tooltip, *buttons = draw_inventory_modal(game.game_screen, game, game.player, modal, game.assets, mouse_pos)
            top_tooltip = tooltip or top_tooltip
            game.modal_buttons.extend(buttons)
        elif modal['type'] == 'gear': game.modal_buttons.extend(draw_gear_modal(game.game_screen, game, game.player, modal, game.assets, mouse_pos))
        elif modal['type'] == 'container': game.modal_buttons.extend(draw_container_view(game.game_screen, game, modal['item'], modal, game.assets, mouse_pos))
        elif modal['type'] == 'nearby': game.modal_buttons.extend(draw_nearby_modal(game.game_screen, game, modal, game.assets, mouse_pos))
        elif modal['type'] == 'slots': game.modal_buttons.extend(draw_slots_modal(game.game_screen, game, game.player, modal, game.assets, mouse_pos))
        elif modal['type'] == 'messages':
            result = draw_messages_modal(game.game_screen, game, modal, game.assets)
            if len(result) == 4:
                if result[2]: game.modal_buttons.append(result[2])
                if result[3]: game.modal_buttons.append(result[3])
                if result[1]: game.modal_buttons.extend(result[1])
            else:
                if result[1]: game.modal_buttons.extend(result[1]) 
        elif modal['type'] == 'text':
            _, close_button = draw_text_modal(game.game_screen, game, modal, game.assets)
            if close_button: game.modal_buttons.extend(close_button)
        elif modal['type'] == 'mobile': game.modal_buttons.extend(draw_mobile_modal(game.game_screen, game, modal, game.assets))
        elif modal['type'] == 'vehicle': game.modal_buttons.extend(draw_vehicle_modal(game.game_screen, game, modal, game.assets, mouse_pos))
        elif modal['type'] == 'big_map': game.modal_buttons.extend(draw_big_map_modal(game.game_screen, game, modal, game.assets))
        elif modal['type'] == 'npc_dialog': game.modal_buttons.extend(draw_npc_dialog_modal(game.game_screen, modal, game))
        elif modal['type'] == 'help': 
            _, close_button = draw_help_modal(game.game_screen, game, modal, game.assets)
            if close_button: game.modal_buttons.extend(close_button)
        elif modal['type'] == 'crafting':
            if 'instance' not in modal: modal['instance'] = CraftingModal(game.game_screen, modal, game.assets, game)
            modal['instance'].surface = game.game_screen
            _, *buttons = modal['instance'].draw()
            game.modal_buttons.extend(buttons)

    # --- LAYER 4: Overlays & Tooltips (Absolute Top) ---
    highlighted_rect, highlighted_allowed = None, False
    if (game.is_dragging and game.dragged_item) or (game.drag_candidate and game.drag_candidate[0]):
        preview_item = game.dragged_item if game.is_dragging else game.drag_candidate[0]
        for modal in reversed(game.modals):
            if modal['type'] == 'inventory':
                if modal.get('active_tab', 'Inventory') == 'Inventory':
                    for i in range(len(game.player.belt)):
                        slot = get_belt_slot_rect_in_modal(i, modal['position'])
                        if slot.collidepoint(mouse_pos):
                            highlighted_rect, highlighted_allowed = slot, preview_item.item_type
                            break
                    if highlighted_rect: break
                    for i in range(5):
                        slot = get_inventory_slot_rect(i, modal['position'])
                        if slot.collidepoint(mouse_pos):
                            highlighted_rect, highlighted_allowed = slot, True
                            break
                    if highlighted_rect: break
            elif modal['type'] == 'gear':
                if 'gear_slot_rects' in modal:
                    for slot_name, slot_rect in modal['gear_slot_rects'].items():
                        if slot_rect.collidepoint(mouse_pos):
                            highlighted_rect = slot_rect
                            item_slot = 'hands' if getattr(preview_item, 'slot', None) == 'hand' else getattr(preview_item, 'slot', None)
                            is_util_slot = slot_name in ['util', 'util2', 'util3']
                            is_container = getattr(preview_item, 'item_type', '') == 'container'
                            highlighted_allowed = (item_slot == slot_name) or (is_util_slot and (is_container or item_slot == 'util'))
                            break
                if highlighted_rect: break
            elif modal['type'] == 'container':
                cont = modal['item']
                for i in range(min(cont.capacity, len(cont.inventory) + 16)):
                    slot = get_container_slot_rect(modal['position'], i)
                    if slot.collidepoint(mouse_pos):
                        highlighted_rect, highlighted_allowed = slot, (len(cont.inventory) < cont.capacity) or (i < len(cont.inventory))
                        break
                if highlighted_rect: break
            elif modal['type'] == 'slots':
                for slot_data in modal.get('slot_rects', []):
                    if slot_data['rect'].collidepoint(mouse_pos):
                        highlighted_rect = slot_data['rect']
                        highlighted_allowed = (len(slot_data['container'].inventory) < slot_data['container'].capacity) or (slot_data['index'] < len(slot_data['container'].inventory))
                        break
                if highlighted_rect: break

        if not highlighted_rect:
            for i in range(5):
                slot = get_belt_hud_slot_rect(i, game=game, dynamic_h=dynamic_h)
                if slot.collidepoint(mouse_pos):
                    highlighted_rect, highlighted_allowed = slot, preview_item.item_type
                    break

        if highlighted_rect:
            overlay = pygame.Surface((highlighted_rect.width, highlighted_rect.height), pygame.SRCALPHA)
            overlay.fill((50, 220, 50, 80) if highlighted_allowed else (220, 50, 50, 80))
            game.game_screen.blit(overlay, highlighted_rect.topleft)
            pygame.draw.rect(game.game_screen, YELLOW if highlighted_allowed else RED, highlighted_rect, 2)

        if preview_item and getattr(preview_item, 'image', None):
            img = pygame.transform.scale(preview_item.image, (int(highlighted_rect.height * 0.9) if highlighted_rect else 40, int(highlighted_rect.height * 0.9) if highlighted_rect else 40))
            game.game_screen.blit(img, img.get_rect(topleft=(mouse_pos[0] - game.drag_offset[0], mouse_pos[1] - game.drag_offset[1])))
        elif preview_item:
            rect_w, rect_h = (int(highlighted_rect.width * 0.8), int(highlighted_rect.height * 0.8)) if highlighted_rect else (40, 40)
            s = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            s.fill((*preview_item.color, 180))
            game.game_screen.blit(s, (mouse_pos[0] - rect_w//2, mouse_pos[1] - rect_h//2))

    if top_tooltip:
        tip_rect, item, frac, bar_color = top_tooltip['rect'], top_tooltip['item'], top_tooltip['frac'], top_tooltip['bar']
        tip_s = pygame.Surface((tip_rect.width, tip_rect.height), pygame.SRCALPHA)
        tip_s.fill((10, 10, 10, 220))
        game.game_screen.blit(tip_s, tip_rect.topleft)
        pygame.draw.rect(game.game_screen, WHITE, tip_rect, 1)
        game.game_screen.blit(font_12.render(f"{tr('item', item.name)}", True, WHITE), (tip_rect.x + 8, tip_rect.y + 6))
        game.game_screen.blit(font_12.render(f"Type: {item.item_type}", True, GRAY), (tip_rect.x + 8, tip_rect.y + 26))
        bar_x, bar_y, bar_w, bar_h = tip_rect.x + 8, tip_rect.y + 42, tip_rect.width - 16, 10
        pygame.draw.rect(game.game_screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(game.game_screen, bar_color, (bar_x, bar_y, int(max(0.0, min(1.0, frac)) * bar_w), bar_h))
        pygame.draw.rect(game.game_screen, WHITE, (bar_x, bar_y, bar_w, bar_h), 1)

    if getattr(game, 'hovered_tab_tooltip', None):
        _draw_tt(game, game.hovered_tab_tooltip, mouse_pos[0] + 15, mouse_pos[1] + 15)

    # --- LAYER 5: Combat HUD (Reticle & Ammo) ---
    if getattr(game.player, 'is_aiming', False):
        pygame.mouse.set_visible(False) 
        if game.assets.get('aim_reticle'):
            scale_mult = 2.5 + (game.player.current_aim_factor * (getattr(game.player.active_weapon, 'distance', 10) / 1.5 if game.player.active_weapon and game.player.active_weapon.item_type == 'weapon_ranged' else 5))
            ret_img = pygame.transform.scale(game.assets.get('aim_reticle'), (max(1, int(game.assets.get('aim_reticle').get_width() * scale_mult)), max(1, int(game.assets.get('aim_reticle').get_height() * scale_mult)),))
            rect = ret_img.get_rect(center=mouse_pos)
            game.game_screen.blit(ret_img, rect)

            if game.player.active_weapon and game.player.active_weapon.item_type == 'weapon_ranged':
                ammo_in_gun = getattr(game.player.active_weapon, 'load', 0) or 0
                ammo_type = getattr(game.player.active_weapon, 'ammo_type', None)
                
                def _count_in_list(item_list):
                    count = 0
                    for item in item_list:
                        if not item: continue
                        if item.name == ammo_type:
                            count += getattr(item, 'load', 1) or 1
                        if hasattr(item, 'inventory') and item.inventory:
                            count += _count_in_list(item.inventory)
                    return count
                
                reserve_ammo = 0
                if ammo_type:
                    reserve_ammo = _count_in_list(game.player.belt) + _count_in_list(game.player.inventory) + _count_in_list(game.player.clothes.values())
                
                max_cap = getattr(game.player.active_weapon, 'capacity', 1) or 1
                text_color = (255, 50, 50) if ammo_in_gun == 0 else ((255, 200, 50) if (ammo_in_gun / max_cap) <= 0.25 else (255, 255, 255))
                text_surf = font_12.render(f"{int(ammo_in_gun)} / {int(reserve_ammo)}", True, text_color)
                bg_rect = text_surf.get_rect(topleft=(min(rect.right + 12, game.game_screen.get_width() - 5 - text_surf.get_width() - 12) if rect.right + 12 + text_surf.get_width() + 12 > game.game_screen.get_width() - 5 else rect.right + 12, rect.centery - text_surf.get_height() // 2))
                pill = pygame.Surface(bg_rect.inflate(12, 6).size, pygame.SRCALPHA)
                pygame.draw.rect(pill, (0, 0, 0, 160), pill.get_rect(), border_radius=4)
                pygame.draw.rect(pill, (150, 150, 150, 100), pill.get_rect(), 1, border_radius=4)
                game.game_screen.blit(pill, bg_rect.inflate(12, 6).topleft)
                game.game_screen.blit(text_surf, bg_rect)
    else:
        if getattr(game, 'item_to_place', None):
            pygame.mouse.set_visible(False)
            item = getattr(game, 'item_to_place')['item']
            in_range = ((game.screen_to_world(mouse_pos)[0] - game.player.rect.centerx)**2 + (game.screen_to_world(mouse_pos)[1] - game.player.rect.centery)**2) <= (TILE_SIZE * 1.5) ** 2
            if getattr(item, 'image', None):
                game.game_screen.blit(item.image, item.image.get_rect(center=mouse_pos))
                tint = pygame.Surface(item.image.get_rect(center=mouse_pos).size, pygame.SRCALPHA)
                tint.fill((0, 255, 0, 80) if in_range else (255, 0, 0, 80))
                game.game_screen.blit(tint, item.image.get_rect(center=mouse_pos).topleft)
            else:
                pygame.draw.rect(game.game_screen, getattr(item, 'color', WHITE), pygame.Rect(mouse_pos[0]-8, mouse_pos[1]-8, 16, 16))
                pygame.draw.rect(game.game_screen, (0, 255, 0) if in_range else (255, 0, 0), pygame.Rect(mouse_pos[0]-8, mouse_pos[1]-8, 16, 16), 2)
        else:
            pygame.mouse.set_visible(True)
            pygame.mouse.set_cursor(game.assets.get('aim_cursor') if (pygame.key.get_pressed()[pygame.K_LCTRL] or pygame.key.get_pressed()[pygame.K_RCTRL]) else (game.assets.get('custom_cursor') or pygame.cursors.arrow))

    if hasattr(game, 'clock'):
        fps_surf = font_12.render(f"FPS: {int(game.clock.get_fps())} | Build: {getattr(core.data.config, 'GAME_VERSION', 'Unknown')}", False, (255, 255, 255))
        game.game_screen.blit(fps_surf, fps_surf.get_rect(bottomright=(game.game_screen.get_width() - 5, game.game_screen.get_height() - 5)))