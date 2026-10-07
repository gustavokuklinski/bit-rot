# core/events/mouse_context_submenus.py

import pygame
from core.data.config import WHITE, GRAY
from core.data.localization import tr
from core.data.recipe_manager import RecipeManager
from core.entities.item.item_helpers import does_allow_liquid, get_container_available_liquid, item_allows_belt, is_valid_send_to_container
from core.events.mouse_drag_utils import check_container_weight_limit, check_recursive_containment
from core.ui.crafting_common import get_recipe_status_details, is_recipe_relevant_to_item

HAIR_STYLES = ['Bald', 'Mowalk', 'Cut', 'Crew', 'Long']

def build_equip_submenu(clicked_item, click_source, game):
    sub_opts = []
    display_map = {}
    replace_map = {}
    item_type = getattr(clicked_item, 'item_type', '') or ''
    is_liquid = getattr(clicked_item, 'liquid', False)

    # Strictly check allow_belt: if False, do NOT allow belt slots
    can_go_belt = not is_liquid and item_allows_belt(clicked_item)

    if can_go_belt and click_source != 'belt':
        for b_idx in range(len(game.player.belt)):
            slot_key = f"belt_{b_idx}"
            sub_opts.append(slot_key)
            existing = game.player.belt[b_idx]
            if existing:
                display_map[slot_key] = f"{tr('ui', 'Belt')} {b_idx + 1}"
                replace_map[slot_key] = existing.name
            else:
                display_map[slot_key] = f"{tr('ui', 'Belt')} {b_idx + 1} ({tr('ui', 'Empty')})"

    if item_type in ('cloth', 'container') and not is_liquid:
        slot = getattr(clicked_item, 'slot', None)
        if slot == 'hand':
            slot = 'hands'
        
        gear_slots = []
        if slot in ('util', 'util1', 'util2', 'util3') or (item_type == 'container' and not slot):
            gear_slots = ['util', 'util2', 'util3']
        elif slot:
            gear_slots = [slot]
            
        for s in gear_slots:
            if s in game.player.clothes_slots or s in ('util', 'util2', 'util3'):
                sub_opts.append(s)
                existing = game.player.clothes.get(s)
                
                s_label = s
                if s == 'util': s_label = "Util 1"
                elif s == 'util2': s_label = "Util 2"
                elif s == 'util3': s_label = "Util 3"
                else: s_label = s.capitalize()
                
                if existing:
                    display_map[s] = tr('ui', s_label)
                    replace_map[s] = existing.name
                else:
                    display_map[s] = f"{tr('ui', s_label)} ({tr('ui', 'Empty')})"

    if sub_opts:
        return {
            'label': 'Equip',
            'sub': sub_opts,
            'display_names': display_map,
            'replacing': replace_map
        }
    return None

def build_send_to_submenu(clicked_item, click_source, click_container_item, game):
    sub_opts = []
    display_map = {}
    tooltip_map = {}
    is_liquid = getattr(clicked_item, 'liquid', False)

    if click_source != 'inventory' and not is_liquid:
        sub_opts.append('Inventory')
        display_map['Inventory'] = tr('ui', 'Inventory')
        tooltip_map['Inventory'] = f"{tr('ui', 'Send to')} {tr('ui', 'Inventory')}"

    # Belt destination check: strictly blocked if allow_belt="false"
    can_go_belt = not is_liquid and item_allows_belt(clicked_item)
    if click_source != 'belt' and can_go_belt and any(b is None for b in game.player.belt):
        sub_opts.append('Belt')
        display_map['Belt'] = tr('ui', 'Belt')
        tooltip_map['Belt'] = f"{tr('ui', 'Send to')} {tr('ui', 'Belt')}"

    candidate_containers = []
    for m in getattr(game, 'modals', []):
        if m.get('type') == 'container' and m.get('item'):
            if is_valid_send_to_container(m['item']):
                candidate_containers.append((m['item'], tr('ui', 'Open Container')))
        elif m.get('type') == 'vehicle' and m.get('vehicle'):
            candidate_containers.append((m['vehicle'], tr('ui', 'Vehicle Trunk')))

    for nearby_obj in game.find_nearby_containers():
        if is_valid_send_to_container(nearby_obj) and hasattr(nearby_obj, 'inventory') and nearby_obj.inventory is not None:
            is_ground = (getattr(nearby_obj, 'item_type', '') == 'ground')
            is_closed_maptile = (
                getattr(nearby_obj, 'item_type', '') == 'maptile_container' 
                and not getattr(nearby_obj, 'is_opened', False)
            )
            is_locked_veh = (
                getattr(nearby_obj, 'item_type', '') == 'vehicle' 
                and hasattr(nearby_obj, 'has_key_access') 
                and not nearby_obj.has_key_access(game.player)
            )
            if not is_ground and not is_closed_maptile and not is_locked_veh:
                candidate_containers.append((nearby_obj, tr('ui', 'Nearby Container')))

    for i, b_item in enumerate(game.player.belt):
        if b_item and is_valid_send_to_container(b_item) and getattr(b_item, 'inventory', None) is not None:
            candidate_containers.append((b_item, f"{tr('ui', 'Belt')} > {tr('ui', 'Slot')} {i+1}"))
    for i_item in game.player.inventory:
        if i_item and is_valid_send_to_container(i_item) and getattr(i_item, 'inventory', None) is not None:
            candidate_containers.append((i_item, tr('ui', 'Inventory')))
    for slot_k, c_item in game.player.clothes.items():
        if c_item and is_valid_send_to_container(c_item) and getattr(c_item, 'inventory', None) is not None:
            candidate_containers.append((c_item, f"{tr('ui', 'Gear')} > {str(slot_k).capitalize()}"))

    seen_c_keys = set()
    for c, loc_str in candidate_containers:
        if c is clicked_item: continue
        if click_container_item and c is click_container_item: continue
        if not is_valid_send_to_container(c): continue
        if check_recursive_containment(clicked_item, c): continue

        c_key = str(getattr(c, 'id', id(c)))
        if c_key in seen_c_keys: continue

        if getattr(c, 'item_type', '') == 'maptile_container' and not getattr(c, 'is_opened', False):
            continue
        if getattr(c, 'item_type', '') == 'vehicle' and hasattr(c, 'has_key_access') and not c.has_key_access(game.player):
            continue

        c_cap = getattr(c, 'capacity', 0)
        if c_cap is None or c_cap <= 0:
            continue

        # Enforce container weight capacity!
        if not check_container_weight_limit(c, clicked_item):
            continue

        c_allows_liquid = does_allow_liquid(c)
        if is_liquid and not c_allows_liquid: continue
        if not is_liquid and c_allows_liquid: continue
        if is_liquid and get_container_available_liquid(c) <= 0: continue

        can_fit = (len(getattr(c, 'inventory', [])) < c_cap)
        if not can_fit and getattr(clicked_item, 'is_stackable', lambda: False)():
            for inv_it in getattr(c, 'inventory', []):
                if hasattr(inv_it, 'can_stack_with') and inv_it.can_stack_with(clicked_item):
                    if (getattr(inv_it, 'load', 0) or 0) < (getattr(inv_it, 'capacity', 1) or 1):
                        can_fit = True
                        break

        if can_fit:
            seen_c_keys.add(c_key)
            sub_opts.append(c_key)
            c_name = getattr(c, 'name', tr('ui', 'Container'))
            
            if c_allows_liquid:
                max_l = getattr(c, 'max_liquid', None)
                cur_l = int(sum(getattr(x, 'load', 1) or 1 for x in getattr(c, 'inventory', []) if getattr(x, 'liquid', False)))
                display_map[c_key] = f"{c_name} ({cur_l}/{max_l or '?'})"
            else:
                display_map[c_key] = f"{c_name}"

            tooltip_map[c_key] = f"{tr('ui', 'Location:')} {loc_str}"

    if sub_opts:
        return {
            'label': 'Send to',
            'sub': sub_opts,
            'display_names': display_map,
            'tooltips': tooltip_map
        }
    return None

def build_remove_fuel_submenu(game):
    sub_opts = []
    display_map = {}
    tooltip_map = {}
    
    containers_with_loc = []
    for i, b_item in enumerate(game.player.belt):
        if b_item and getattr(b_item, 'item_type', '') in ['container', 'cloth'] and getattr(b_item, 'inventory', None) is not None:
            containers_with_loc.append((b_item, f"Belt > Slot {i+1}"))
    for i_item in game.player.inventory:
        if i_item and getattr(i_item, 'item_type', '') in ['container', 'cloth'] and getattr(i_item, 'inventory', None) is not None:
            containers_with_loc.append((i_item, "Inventory"))
    for slot, c_item in game.player.clothes.items():
        if c_item and getattr(c_item, 'item_type', '') in ['container', 'cloth'] and getattr(c_item, 'inventory', None) is not None:
            containers_with_loc.append((c_item, f"Gear > {str(slot).capitalize()}"))
            
    for c, loc_str in containers_with_loc:
        if not getattr(c, 'allow_liquid', False): 
            continue
        
        c_id = str(getattr(c, 'id', c.name))
        liquid_qty = 0
        liquid_name = ""
        
        if getattr(c, 'allow_liquid', False):
            for inside_item in getattr(c, 'inventory', []):
                if getattr(inside_item, 'liquid', False):
                    liquid_qty += getattr(inside_item, 'load', 1) or 1
                    liquid_name = inside_item.name
        
        max_liq_str = f"/{c.max_liquid}" if getattr(c, 'max_liquid', None) is not None else ""
        if liquid_qty > 0:
            display_str = f"{c.name} ({int(liquid_qty)}{max_liq_str} {liquid_name} {tr('ui', 'units')})"
        elif getattr(c, 'allow_liquid', False):
            display_str = f"{c.name} (0{max_liq_str} {tr('ui', 'Empty')})"
        else:
            display_str = c.name
            
        if c_id not in sub_opts:
            sub_opts.append(c_id)
            display_map[c_id] = display_str
            tooltip_map[c_id] = f"{tr('ui', 'Location:')} {loc_str}"
                
    return {
        'label': 'Remove fuel to', 
        'sub': sub_opts, 
        'display_names': display_map, 
        'tooltips': tooltip_map
    }

def build_crafts_submenu(clicked_item, game):
    if not RecipeManager.RECIPES:
        RecipeManager.load_recipes()

    sub_opts = ['open_craft']
    display_map = {'open_craft': tr('ui', 'Open Craft')}
    tooltip_map = {
        'open_craft': f"{tr('tooltip', 'Open crafting menu')}\n\n{tr('msg', 'The item must be in inventory or nearby to craft')}"
    }
    color_map = {'open_craft': WHITE}

    item_name = getattr(clicked_item, 'name', '')
    game.context_menu['craft_recipes'] = {}

    craft_buckets = {
        'Craft': [],
        'Repair': [],
        'Dismantle': []
    }

    for r in RecipeManager.RECIPES:
        if not is_recipe_relevant_to_item(r, item_name):
            continue

        raw_type = getattr(r, 'craft_type', 'create').lower()
        if raw_type == 'repair':
            cat_key = 'Repair'
        elif raw_type == 'dismantle':
            cat_key = 'Dismantle'
        else:
            cat_key = 'Craft'

        can_craft, is_unlocked, missing_ings, missing_mag, missing_skills = get_recipe_status_details(game.player, game, r)
        craft_buckets[cat_key].append({
            'recipe': r,
            'can_craft': can_craft,
            'is_unlocked': is_unlocked,
            'missing_ings': missing_ings,
            'missing_mag': missing_mag,
            'missing_skills': missing_skills
        })

    global_idx = 0
    max_total_recipes = 12

    for cat_name in ['Craft', 'Repair', 'Dismantle']:
        bucket = craft_buckets[cat_name]
        if not bucket:
            continue

        bucket.sort(key=lambda d: (not d['can_craft'], d['recipe'].output_name))

        hdr_id = f"header_{cat_name.lower()}"
        sub_opts.append(hdr_id)
        display_map[hdr_id] = tr('tab', cat_name)
        color_map[hdr_id] = (255, 215, 0)

        for data in bucket:
            if global_idx >= max_total_recipes:
                break

            r = data['recipe']
            sub_key = f"recipe_{global_idx}"
            global_idx += 1

            sub_opts.append(sub_key)
            game.context_menu['craft_recipes'][sub_key] = r

            out_name = tr('item', r.output_name)
            if r.output_amount > 1:
                out_name = f"{out_name} x{r.output_amount}"

            display_map[sub_key] = f"- {out_name}"
            color_map[sub_key] = WHITE if data['can_craft'] else GRAY

            tt_lines = [
                out_name,
                f"{tr('ui', 'Type')}: {tr('tab', cat_name)}",
                ""
            ]

            if data['can_craft']:
                tt_lines.append(f"{tr('ui', 'Ready to craft')} ({r.time_required}s)")
            else:
                if data['missing_ings']:
                    tt_lines.append(f"{tr('ui', 'Ingredients')}:")
                    for m in data['missing_ings']:
                        tt_lines.append(f"- {tr('item', m['name'])} ({m['have']}/{m['needed']})")

                if data['missing_skills'] or data['missing_mag']:
                    if data['missing_ings']:
                        tt_lines.append("")
                    tt_lines.append(f"{tr('ui', 'Missing skill')}:")
                    for s in data['missing_skills']:
                        skill_name = tr('ui', s[0].capitalize())
                        tt_lines.append(f"- {skill_name} (Lv {s[2]})")
                    if data['missing_mag']:
                        tt_lines.append(f"- {tr('item', data['missing_mag'])}")

            tt_lines.append("")
            tt_lines.append(tr('msg', "The item must be in inventory or nearby to craft"))
            tooltip_map[sub_key] = "\n".join(tt_lines)

    return {
        'label': 'Crafts', 
        'sub': sub_opts, 
        'display_names': display_map, 
        'tooltips': tooltip_map, 
        'colors': color_map
    }