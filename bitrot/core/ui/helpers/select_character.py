# core/ui/helpers/select_character.py

import os
import random
import pygame
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from faker import Faker

import core.data.config
from core.data.config import (
    GAME_WIDTH, GAME_HEIGHT, UI_SCALE, TILE_SIZE, WHITE, GRAY, DARK_GRAY,
    GRAY_60, GRAY_80, GREEN, RED, YELLOW, font_16, font_14, font_12,
    SPRITE_PATH, BASE_DIR, get_writable_dir
)
from core.data.localization import tr
from core.entities.item.item import Item
from core.entities.item.item_data import ITEM_TEMPLATES
from core.entities.item.item_factory import get_tinted_sprite, CLOTHING_COLORS
from core.ui.tooltip import draw_tooltip
from core.ui.helpers.trait_config_loader import TRAIT_DEFINITIONS

fake = Faker()
_cloth_item_cache = {}
_base_player_sprite = None
_char_preview_cache = {}
_logo_cache = None

# Strictly allow ONLY these generic clothes to be tinted
TINTABLE_CLOTHES = {"tshirt", "pants", "jacket", "shoes", "sneakers"}

HAIR_STYLES = ['Bald', 'Mowalk', 'Cut', 'Crew', 'Long']
NATURAL_HAIR_COLORS = [
    (50, 50, 50),     # Black
    (90, 50, 30),     # Dark Brown
    (139, 69, 19),    # Chestnut Brown
    (220, 200, 70),   # Blonde
    (180, 80, 40),    # Ginger / Auburn
    (150, 150, 150)   # Gray
]

def _get_logo_image(width):
    """Loads, scales, and caches the game logo."""
    global _logo_cache
    if _logo_cache is not None and _logo_cache.get_width() == width:
        return _logo_cache

    logo_path = os.path.join(BASE_DIR, "data.rot", "icons", "logo.png")
    if os.path.exists(logo_path):
        try:
            raw = pygame.image.load(logo_path).convert_alpha()
            scale_factor = width / raw.get_width()
            target_h = int(raw.get_height() * scale_factor)
            _logo_cache = pygame.transform.scale(raw, (width, target_h))
            return _logo_cache
        except Exception as e:
            print(f"[SelectCharacter] Error loading logo: {e}")
    return None


def load_player_builds():
    """Dynamically loads player build classes from the XML files."""
    classes = []
    builds_dir = os.path.join(BASE_DIR, "data.rot", "lib", "data", "player_builds")
    
    
        
    for filename in os.listdir(builds_dir):
        if filename.endswith(".xml"):
            filepath = os.path.join(builds_dir, filename)
            try:
                tree = ET.parse(filepath)
                root = tree.getroot()
                if root.tag == "player_build":
                    cid = root.get('id', 'unknown')
                    
                    name_node = root.find('name')
                    name = name_node.get('value') if name_node is not None else "Unknown"
                    
                    sub_node = root.find('subtitle')
                    subtitle = sub_node.get('value') if sub_node is not None else ""
                    
                    desc_node = root.find('description')
                    desc = desc_node.get('value') if desc_node is not None else ""
                    
                    accent = (255, 255, 255)
                    color_node = root.find('color')
                    if color_node is not None:
                        color_str = color_node.get('value', '(255, 255, 255)')
                        try:
                            # Safely parse "(R, G, B)"
                            parts = color_str.strip("() ").split(',')
                            accent = tuple(int(p.strip()) for p in parts)
                        except ValueError:
                            pass
                            
                    clothes = []
                    clothes_node = root.find('clothes')
                    if clothes_node is not None:
                        for cloth in clothes_node.findall('cloth'):
                            cname = cloth.get('name')
                            if cname: clothes.append(cname)
                            
                    items = []
                    items_node = root.find('items')
                    if items_node is not None:
                        for item in items_node.findall('item'):
                            iname = item.get('name')
                            if iname: items.append(iname)
                            
                    classes.append({
                        'id': cid,
                        'name': name,
                        'subtitle': subtitle,
                        'description': desc,
                        'accent': accent,
                        'clothes': clothes,
                        'items': items
                    })
            except Exception as e:
                print(f"[SelectCharacter] Error loading build {filename}: {e}")
                
    if not classes:
        print("[SelectCharacter] No valid XML builds found.")
       
        
    # Sort them by name to keep the UI consistent
    classes.sort(key=lambda x: x['name'])
    return classes

# Initialize the classes directly
CHARACTER_CLASSES = load_player_builds()

# Baseline thematic colors ONLY for Tshirt, Pants, Jacket, Shoes, Sneakers
DEFAULT_TINTABLE_COLORS = {
    'rsf': {'feet': (50, 50, 50), 'legs': (50, 50, 50), 'arms': (139, 69, 19)},
    'civilian': {'feet': (220, 50, 50), 'body': (50, 150, 220)},
    'doctor': {'feet': (50, 50, 50), 'body': (50, 180, 200)}
}

def is_tintable_cloth(item_name):
    """Checks if an item is strictly Tshirt, Pants, Jacket, Shoes, or Sneakers."""
    if not item_name: return False
    return item_name.lower().strip() in TINTABLE_CLOTHES

def _get_base_player_sprite():
    """Loads and caches the default 16x16 base player sprite."""
    global _base_player_sprite
    if _base_player_sprite is not None:
        return _base_player_sprite
    path = os.path.join(SPRITE_PATH, "player", "player.png")
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            _base_player_sprite = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            return _base_player_sprite
        except Exception as e:
            print(f"[SelectCharacter] Error loading base player sprite: {e}")
    _base_player_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    _base_player_sprite.fill((50, 100, 200))
    return _base_player_sprite


def _find_cloth_item(name):
    """Safely retrieves a clothing item instance with common alias fallbacks."""
    if name in _cloth_item_cache:
        return _cloth_item_cache[name]

    item = Item.create_from_name(name)
    _cloth_item_cache[name] = item
    return item


def _get_candidate_head_equips():
    """Finds all casual head equips (caps, beanies, hats) for builds without head gear."""
    if not ITEM_TEMPLATES:
        Item.load_item_templates()

    candidates = []
    for name, tmpl in ITEM_TEMPLATES.items():
        if tmpl.get('type') == 'cloth':
            props = tmpl.get('properties', {})
            slot = props.get('slot', {}).get('value') or tmpl.get('slot')
            if slot == 'head' and not name.startswith("Empty"):
                candidates.append(name)

    light_heads = [h for h in candidates if 'helmet' not in h.lower() and 'baret' not in h.lower()]
    return light_heads if light_heads else (candidates if candidates else ["Baseball Cap", "Beanie"])


def init_class_dynamic_gear():
    """Generates random hair, hair colors, and head equipment for builds without head equips."""
    gear = {}
    head_candidates = _get_candidate_head_equips()

    for c in CHARACTER_CLASSES:
        cid = c['id']
        clothes_list = list(c['clothes'])

        # Check if already has a head item
        has_head = False
        for it_name in clothes_list:
            it = _find_cloth_item(it_name)
            if it and getattr(it, 'slot', '') == 'head':
                has_head = True
                break

        added_head = None
        if not has_head and head_candidates:
            added_head = random.choice(head_candidates)
            clothes_list.append(added_head)

        hair_style = random.choice(HAIR_STYLES)
        clothes_list.insert(0, hair_style)

        gear[cid] = {
            'clothes': clothes_list,
            'hair': hair_style,
            'added_head': added_head,
            'hair_color': random.choice(NATURAL_HAIR_COLORS)
        }
    return gear


def init_class_colors(dynamic_gear=None, randomize=False):
    """Initializes colors ONLY for Tshirt, Pants, Jacket, Shoes, Sneakers, and Hair."""
    colors = {}
    for c in CHARACTER_CLASSES:
        cid = c['id']
        base = DEFAULT_TINTABLE_COLORS.get(cid, {}).copy()

        # Fetch actual clothes for this class to verify which ones are tintable
        all_gear = c['clothes']
        if dynamic_gear and cid in dynamic_gear:
            all_gear = dynamic_gear[cid]['clothes']

        # Determine which slots contain tintable clothes
        tintable_slots = set()
        for it_name in all_gear:
            if is_tintable_cloth(it_name):
                it = _find_cloth_item(it_name)
                if it and getattr(it, 'slot', None):
                    tintable_slots.add(it.slot)

        if randomize:
            for slot in tintable_slots:
                base[slot] = random.choice(CLOTHING_COLORS)
        else:
            # Ensure every tintable slot has a color assigned
            for slot in tintable_slots:
                if slot not in base:
                    base[slot] = random.choice(CLOTHING_COLORS)

        # Hair color
        if dynamic_gear and cid in dynamic_gear:
            base['hair'] = dynamic_gear[cid]['hair_color']
        else:
            base['hair'] = random.choice(NATURAL_HAIR_COLORS)

        colors[cid] = base
    return colors


def generate_random_traits():
    """Generates balanced 4 traits: exactly 2 positive and 2 negative traits, excluding professions."""
    available = {k: v for k, v in TRAIT_DEFINITIONS.items() if not v.get('is_profession', False)}
    if not available:
        return []

    pos_traits = [k for k, v in available.items() if v.get('cost', 0) > 0]
    neg_traits = [k for k, v in available.items() if v.get('cost', 0) < 0]

    chosen = []
    disabled = set()

    random.shuffle(pos_traits)
    random.shuffle(neg_traits)

    # 1. Roll 2 Positive Traits
    for t_id in pos_traits:
        if len([t for t in chosen if available[t].get('cost', 0) > 0]) >= 2:
            break
        if t_id not in disabled:
            chosen.append(t_id)
            disabled.add(t_id)
            for c in available[t_id].get('conflicts', []):
                disabled.add(c)

    # 2. Roll 2 Negative Traits
    for t_id in neg_traits:
        if len([t for t in chosen if available[t].get('cost', 0) < 0]) >= 2:
            break
        if t_id not in disabled:
            chosen.append(t_id)
            disabled.add(t_id)
            for c in available[t_id].get('conflicts', []):
                disabled.add(c)

    return chosen


def init_all_class_traits():
    """Rolls a unique balanced 4-trait combination independently for every class."""
    return {c['id']: generate_random_traits() for c in CHARACTER_CLASSES}


def _render_paper_doll(class_id, clothes_names, class_colors=None, size=(48, 48)):
    """Renders composite layered pixel art. Strictly tints ONLY hair and specified clothes."""
    colors_key = tuple(sorted((class_colors or {}).items()))
    clothes_key = tuple(clothes_names)
    cache_key = (class_id, clothes_key, colors_key, size)
    if cache_key in _char_preview_cache:
        return _char_preview_cache[cache_key]

    base = _get_base_player_sprite()
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
    if base:
        surf.blit(base, (0, 0))

    if class_id != 'custom':
        layer_order = ['hair', 'feet', 'legs', 'body', 'arms', 'hands', 'facial', 'head']
        resolved_items = []
        for name in clothes_names:
            it = _find_cloth_item(name)
            if it:
                resolved_items.append(it)

        # Check hide_cloth rules (e.g. helmets hiding hair)
        hidden_slots = set()
        for it in resolved_items:
            tmpl = ITEM_TEMPLATES.get(it.name)
            if tmpl and 'properties' in tmpl and 'hide_cloth' in tmpl['properties']:
                hidden_slots.update(tmpl['properties']['hide_cloth'])

        def _layer_rank(it):
            slot = getattr(it, 'slot', '')
            return layer_order.index(slot) if slot in layer_order else 99

        resolved_items.sort(key=_layer_rank)

        for it in resolved_items:
            slot = getattr(it, 'slot', '')
            if slot in hidden_slots:
                continue

            img = getattr(it, 'image', None)
            if img:
                color = None
                if slot == 'hair':
                    color = (class_colors or {}).get('hair')
                elif is_tintable_cloth(it.name):
                    color = (class_colors or {}).get(slot)

                # Strictly tint only if allowed and not white
                if color and color != (255, 255, 255):
                    img = get_tinted_sprite(img, it.name, color)
                surf.blit(img, (0, 0))

    scaled = pygame.transform.scale(surf, size)
    _char_preview_cache[cache_key] = scaled
    return scaled


def _start_with_class(game, state, class_def):
    """Initializes player data, clothes with specific colors, starter items, and starts the game."""
    final_player_data = state['base_data'].copy()
    final_player_data['name'] = state.get('player_name', "Survivor")
    final_player_data['sex'] = state['base_data'].get('sex', 'Male')

    clothes_slots = state.get('clothes_slots', ['hair', 'head', 'legs', 'feet', 'body', 'util', 'arms', 'hands', 'facial'])
    chosen_clothes = {slot: "None" for slot in clothes_slots}

    active_clothes = state.get('class_dynamic_gear', {}).get(class_def['id'], {}).get('clothes', class_def.get('clothes', []))

    for c_name in active_clothes:
        it = _find_cloth_item(c_name)
        if it:
            slot = getattr(it, 'slot', None)
            if not slot:
                nl = c_name.lower()
                if c_name in HAIR_STYLES: slot = 'hair'
                elif 'helmet' in nl or 'baret' in nl or 'beret' in nl or 'cap' in nl or 'beanie' in nl or 'hat' in nl: slot = 'head'
                elif 'boots' in nl or 'shoes' in nl or 'sneakers' in nl: slot = 'feet'
                elif 'pants' in nl or 'shorts' in nl or 'jeans' in nl: slot = 'legs'
                elif 'tshirt' in nl: slot = 'body'
                elif 'jacket' in nl: slot = 'arms'
                elif 'gloves' in nl: slot = 'hands'
                elif 'mask' in nl: slot = 'facial'
            if slot and slot in chosen_clothes:
                chosen_clothes[slot] = it.name

    final_player_data['clothes'] = chosen_clothes

    # Colors: ONLY hair and Tshirt, Pants, Jacket, Shoes, Sneakers receive custom tints
    class_colors = state.get('class_colors', {}).get(class_def['id'], {})
    final_colors = {slot: (255, 255, 255) for slot in clothes_slots}

    if 'hair' in class_colors:
        final_colors['hair'] = class_colors['hair']

    for slot, item_name in chosen_clothes.items():
        if is_tintable_cloth(item_name) and slot in class_colors:
            final_colors[slot] = class_colors[slot]

    final_player_data['clothes_colors'] = final_colors

    # Assign uniquely rolled traits
    class_traits = state.get('class_traits', {}).get(class_def['id'], [])
    final_player_data['traits'] = list(class_traits)

    # Starter Inventory Items
    starter_items = list(class_def.get('items', []))
    final_player_data['initial_loot'] = starter_items

    # Calculate starting attribute levels from traits
    final_attrs = {k: (v.copy() if isinstance(v, dict) else v) for k, v in state['base_data']['attributes'].items()}
    for t_name in final_player_data['traits']:
        t_def = TRAIT_DEFINITIONS.get(t_name, {})
        if 'starting_levels' in t_def:
            for attr, val in t_def['starting_levels'].items():
                if attr in final_attrs:
                    cur = final_attrs[attr]
                    if isinstance(cur, dict):
                        cur['level'] = cur.get('level', 0) + val
                    else:
                        final_attrs[attr] = cur + val

    final_player_data['attributes'] = final_attrs

    # World seed and preset resolution
    # World seed and preset resolution
    w_state = getattr(game, 'world_setup_state', {})
    preset_to_load = state.get('selected_config_preset') or w_state.get('selected_config_preset', 'world')

    final_mode = w_state.get('chosen_mode') or state.get('chosen_mode') or 'sandbox'
    final_player_data['game_mode'] = final_mode

    # Resolve save folder and world.xml path
    save_folder = state.get('save_folder_name') or w_state.get('save_folder_name') or getattr(game, 'current_save_folder_name', None)
    world_data = w_state.get('world_data') or state.get('world_data')

    if not save_folder and not state.get('respawn_save_folder'):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_folder = f"save_{final_mode}_{timestamp}"
        save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_folder)
        os.makedirs(save_path, exist_ok=True)
        world_xml_path = os.path.join(save_path, "world.xml")
        if not world_data:
            from core.ui.helpers.trait_config_loader import load_config_data
            world_data = load_config_data(os.path.join(DATA_PATH, "world.xml"))
        from core.ui.helpers.trait_config_loader import save_config_xml
        save_config_xml(world_data, world_xml_path)
    elif save_folder:
        save_path = os.path.join(get_writable_dir(), "data.rot", "save", "game", save_folder)
        world_xml_path = os.path.join(save_path, "world.xml")
    else:
        world_xml_path = None

    # Load its world.xml inside the folder right when character is selected
    if world_xml_path and os.path.exists(world_xml_path):
        core.data.config.load_settings(world_xml_path)

    game.current_save_folder_name = save_folder
    final_player_data['save_folder_name'] = save_folder
    final_player_data['world_xml_path'] = world_xml_path
    final_player_data['selected_config_preset'] = preset_to_load
    final_player_data['game_settings'] = world_data

    # Forward respawn folder if respawning in an existing world save
    if state.get('respawn_save_folder'):
        final_player_data['respawn_save_folder'] = state['respawn_save_folder']

    raw_seed = state.get('world_seed', "").strip()
    chunks = core.data.config.MAP_CHUNKS
    if not raw_seed.startswith(f"{chunks}-"):
        world_seed = f"{chunks}-{raw_seed}"
    else:
        world_seed = raw_seed
    final_player_data['world_seed'] = world_seed

    final_player_data['visuals'] = {'center': 'player.png', 'left': 'player_left.png', 'right': 'player_right.png'}
    final_player_data['sounds'] = {'steps': 'steps.ogg'}

    # [FIX] Attach Game Mode properly to bypass the 'sandbox' default!
    final_mode = w_state.get('chosen_mode') or state.get('chosen_mode') or 'sandbox'
    final_player_data['game_mode'] = final_mode

    game.loading_data = final_player_data
    game.game_state = 'LOADING'
    game.loading_done = False


def draw_select_character_screen(game, state, mouse_pos):
    scale = UI_SCALE
    def S(val): return int(val * scale)

    center_x = GAME_WIDTH // 2

    # Initialize traits, dynamic gear (hair & head), colors, and identity states
    if 'class_traits' not in state or not isinstance(state.get('class_traits'), dict):
        state['class_traits'] = init_all_class_traits()
    else:
        for c in CHARACTER_CLASSES:
            if c['id'] not in state['class_traits']:
                state['class_traits'][c['id']] = generate_random_traits()

    if 'class_dynamic_gear' not in state:
        state['class_dynamic_gear'] = init_class_dynamic_gear()

    if 'class_colors' not in state:
        state['class_colors'] = init_class_colors(state['class_dynamic_gear'])

    if 'char_carousel_index' not in state:
        state['char_carousel_index'] = 0
    if 'player_name' not in state or not state['player_name']:
        state['player_name'] = fake.name_male()

    # --- 1. GAME LOGO AT THE TOP ---
    logo_w = S(240)
    logo_img = _get_logo_image(logo_w)

    top_cursor_y = S(42)
    if logo_img:
        logo_rect = logo_img.get_rect(center=(center_x, top_cursor_y + (logo_img.get_height() // 2)))
        game.game_screen.blit(logo_img, logo_rect)
        top_cursor_y = logo_rect.bottom + S(10)
    else:
        top_cursor_y = S(45)

    # --- 2. SCREEN TITLE & SUBTITLE ---
    title_text = font_16.render(tr('ui', "CHOOSE YOUR CHARACTER"), False, WHITE)
    title_rect = title_text.get_rect(center=(center_x, top_cursor_y + S(40)))
    game.game_screen.blit(title_text, title_rect)

    sub_text = font_12.render(tr('ui', "Select your origin or customize your survivor"), False, (160, 160, 160))
    sub_rect = sub_text.get_rect(center=(center_x, title_rect.bottom + S(12)))
    game.game_screen.blit(sub_text, sub_rect)

    # --- 3. IDENTITY BAR (WIDE NAME FIELD & SEX TOGGLES) ---
    id_bar_y = sub_rect.bottom + S(10)
    cur_sex = state['base_data'].get('sex', 'Male')

    start_bar_x = center_x - S(255)
    name_label = font_12.render(tr('ui', "Name:"), False, (180, 180, 180))
    game.game_screen.blit(name_label, (start_bar_x, id_bar_y + S(6)))

    # Generous Name Field Width (S(230))
    name_box_w = S(230)
    name_box = pygame.Rect(start_bar_x + S(55), id_bar_y, name_box_w, S(28))
    pygame.draw.rect(game.game_screen, (45, 45, 45), name_box, border_radius=S(4))
    pygame.draw.rect(game.game_screen, WHITE if state.get('name_input_active') else GRAY, name_box, width=1, border_radius=S(4))

    name_str = state.get('player_name', '')
    name_txt_surf = font_12.render(name_str, False, WHITE)

    # Text Clipping inside Name Box
    old_clip = game.game_screen.get_clip()
    game.game_screen.set_clip(name_box.inflate(-S(8), -S(4)))
    game.game_screen.blit(name_txt_surf, (name_box.x + S(8), name_box.centery - name_txt_surf.get_height() // 2))

    if state.get('name_input_active') and (pygame.time.get_ticks() // 500) % 2 == 0:
        cursor_x = min(name_box.right - S(6), name_box.x + S(8) + name_txt_surf.get_width() + S(2))
        pygame.draw.line(game.game_screen, WHITE, (cursor_x, name_box.y + S(5)), (cursor_x, name_box.bottom - S(5)), S(2))
    game.game_screen.set_clip(old_clip)

    # Random Name Dice Button
    dice_btn = pygame.Rect(name_box.right + S(6), id_bar_y, S(28), S(28))
    pygame.draw.rect(game.game_screen, (60, 60, 60), dice_btn, border_radius=S(4))
    dice_txt = font_12.render("*", False, YELLOW)
    game.game_screen.blit(dice_txt, dice_txt.get_rect(center=dice_btn.center))

    # Sex Toggles
    male_rect = pygame.Rect(dice_btn.right + S(25), id_bar_y, S(100), S(28))
    female_rect = pygame.Rect(male_rect.right + S(8), id_bar_y, S(100), S(28))

    pygame.draw.rect(game.game_screen, (70, 70, 70) if cur_sex == 'Male' else (35, 35, 35), male_rect, border_radius=S(4))
    pygame.draw.rect(game.game_screen, (70, 70, 70) if cur_sex == 'Female' else (35, 35, 35), female_rect, border_radius=S(4))
    pygame.draw.rect(game.game_screen, WHITE if cur_sex == 'Male' else GRAY, male_rect, 1, border_radius=S(4))
    pygame.draw.rect(game.game_screen, WHITE if cur_sex == 'Female' else GRAY, female_rect, 1, border_radius=S(4))

    m_surf = font_12.render(tr('ui', "Male"), False, WHITE)
    f_surf = font_12.render(tr('ui', "Female"), False, WHITE)
    game.game_screen.blit(m_surf, m_surf.get_rect(center=male_rect.center))
    game.game_screen.blit(f_surf, f_surf.get_rect(center=female_rect.center))

    # --- 4. CARDS CAROUSEL LAYOUT ---
    card_w = S(270)
    card_h = S(350)
    spacing = S(25)
    total_w = (card_w * 3) + (spacing * 2)
    start_x = center_x - (total_w // 2)
    card_y = id_bar_y + S(36)

    clickable_rects = {
        'cards': [],
        'back_button': None,
        'random_button': None,
        'custom_button': None,
        'prev_arrow': None,
        'next_arrow': None,
        'name_input': name_box,
        'random_name': dice_btn,
        'sex_male': male_rect,
        'sex_female': female_rect
    }

    # 6 Preset Classes (3 visible at once in carousel)
    max_carousel_idx = max(0, len(CHARACTER_CLASSES) - 3)
    carousel_idx = max(0, min(state['char_carousel_index'], max_carousel_idx))
    state['char_carousel_index'] = carousel_idx

    visible_classes = CHARACTER_CLASSES[carousel_idx : carousel_idx + 3]
    hovered_class = None

    # Navigation Arrows
    arrow_w, arrow_h = S(32), S(48)
    prev_arrow_rect = pygame.Rect(start_x - arrow_w - S(14), card_y + (card_h // 2) - (arrow_h // 2), arrow_w, arrow_h)
    next_arrow_rect = pygame.Rect(start_x + total_w + S(14), card_y + (card_h // 2) - (arrow_h // 2), arrow_w, arrow_h)

    can_prev = carousel_idx > 0
    can_next = carousel_idx < max_carousel_idx

    prev_hover = prev_arrow_rect.collidepoint(mouse_pos) and can_prev
    next_hover = next_arrow_rect.collidepoint(mouse_pos) and can_next

    pygame.draw.rect(game.game_screen, (70, 70, 70) if prev_hover else ((45, 45, 45) if can_prev else (25, 25, 25)), prev_arrow_rect, border_radius=S(5))
    pygame.draw.rect(game.game_screen, WHITE if prev_hover else ((100, 100, 100) if can_prev else (50, 50, 50)), prev_arrow_rect, 1, border_radius=S(5))
    prev_txt = font_16.render("<", False, WHITE if can_prev else (80, 80, 80))
    game.game_screen.blit(prev_txt, prev_txt.get_rect(center=prev_arrow_rect.center))

    pygame.draw.rect(game.game_screen, (70, 70, 70) if next_hover else ((45, 45, 45) if can_next else (25, 25, 25)), next_arrow_rect, border_radius=S(5))
    pygame.draw.rect(game.game_screen, WHITE if next_hover else ((100, 100, 100) if can_next else (50, 50, 50)), next_arrow_rect, 1, border_radius=S(5))
    next_txt = font_16.render(">", False, WHITE if can_next else (80, 80, 80))
    game.game_screen.blit(next_txt, next_txt.get_rect(center=next_arrow_rect.center))

    if can_prev: clickable_rects['prev_arrow'] = prev_arrow_rect
    if can_next: clickable_rects['next_arrow'] = next_arrow_rect

    # Render The 3 Visible Preset Cards
    for i, c_def in enumerate(visible_classes):
        cx = start_x + i * (card_w + spacing)
        card_rect = pygame.Rect(cx, card_y, card_w, card_h)
        is_hovered = card_rect.collidepoint(mouse_pos)

        bg_col = (45, 45, 45) if is_hovered else (32, 32, 32)
        border_col = c_def['accent'] if is_hovered else GRAY_60
        border_width = 2 if is_hovered else 1

        pygame.draw.rect(game.game_screen, bg_col, card_rect, border_radius=S(8))
        pygame.draw.rect(game.game_screen, border_col, card_rect, width=border_width, border_radius=S(8))

        # Icon Frame with Paper Doll
        icon_box_size = S(64)
        icon_box = pygame.Rect(0, 0, icon_box_size, icon_box_size)
        icon_box.center = (card_rect.centerx, card_rect.top + S(50))
        pygame.draw.rect(game.game_screen, (22, 22, 22), icon_box, border_radius=S(6))
        pygame.draw.rect(game.game_screen, border_col, icon_box, width=1, border_radius=S(6))

        c_colors = state.get('class_colors', {}).get(c_def['id'], {})
        active_clothes = state.get('class_dynamic_gear', {}).get(c_def['id'], {}).get('clothes', c_def['clothes'])

        doll_preview = _render_paper_doll(c_def['id'], active_clothes, class_colors=c_colors, size=(S(48), S(48)))
        game.game_screen.blit(doll_preview, doll_preview.get_rect(center=icon_box.center))

        # Title
        name_font = font_14 if font_16.size(c_def['name'])[0] > card_w - S(30) else font_16
        name_surf = name_font.render(tr('ui', c_def['name']), False, c_def['accent'] if is_hovered else WHITE)
        game.game_screen.blit(name_surf, name_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(96))))

        # Subtitle
        sub_c_surf = font_12.render(c_def['subtitle'], False, (180, 180, 180))
        game.game_screen.blit(sub_c_surf, sub_c_surf.get_rect(center=(card_rect.centerx, card_rect.top + S(116))))

        # Divider Line
        pygame.draw.line(
            game.game_screen, (55, 55, 55),
            (card_rect.left + S(15), card_rect.top + S(134)),
            (card_rect.right - S(15), card_rect.top + S(134)), 1
        )

        # Bullets / Summary Inside Card
        line_cursor_y = card_rect.top + S(146)

        # Each Class's Own 4 Rolled Traits (2 Positives, 2 Negatives)
        traits_header = font_12.render(tr('ui', "Traits:"), False, YELLOW)
        game.game_screen.blit(traits_header, (card_rect.left + S(18), line_cursor_y))
        line_cursor_y += S(18)

        class_traits = state['class_traits'].get(c_def['id'], [])
        for t_id in class_traits:
            t_def = TRAIT_DEFINITIONS.get(t_id, {})
            base_name = t_def.get('name', t_id.capitalize())
            cost = t_def.get('cost', 0)
            prefix = "+" if cost > 0 else "-"
            col = (130, 255, 130) if cost > 0 else (255, 130, 130)
            t_line = font_12.render(f"{prefix} {base_name}", False, col)
            game.game_screen.blit(t_line, (card_rect.left + S(22), line_cursor_y))
            line_cursor_y += S(16)

        # Starter Items summary
        if c_def.get('items'):
            line_cursor_y += S(6)
            items_str = ", ".join(c_def['items'])
            items_txt = f"Items: {items_str}"
            if font_12.size(items_txt)[0] > card_w - S(36):
                items_txt = f"Items: {len(c_def['items'])} starters"
            it_surf = font_12.render(items_txt, False, (130, 200, 255))
            game.game_screen.blit(it_surf, (card_rect.left + S(18), line_cursor_y))

        # Card Action Button (Start Game)
        btn_h = S(38)
        btn_rect = pygame.Rect(card_rect.left + S(18), card_rect.bottom - btn_h - S(14), card_rect.width - S(36), btn_h)
        
        # --- NEW: "More info" text left-aligned above the button ---
        info_text = tr('ui', "More info")
        info_dummy_surf = font_12.render(info_text, False, WHITE)
        info_rect = info_dummy_surf.get_rect(bottomleft=(btn_rect.left, btn_rect.top - S(8)))
        
        info_hovered = info_rect.collidepoint(mouse_pos)
        if info_hovered:
            hovered_class = c_def  # Trigger the tooltip
            
        info_color = YELLOW if info_hovered else (150, 150, 150)
        info_surf = font_12.render(info_text, False, info_color)
        game.game_screen.blit(info_surf, info_rect)
        
        # Draw Start Game Button (Highlight only when button is hovered)
        btn_hovered = btn_rect.collidepoint(mouse_pos)
        btn_bg = c_def['accent'] if btn_hovered else (55, 55, 55)
        btn_text_col = (10, 10, 10) if btn_hovered else WHITE
        pygame.draw.rect(game.game_screen, btn_bg, btn_rect, border_radius=S(5))

        btn_txt = font_12.render(tr('ui', "Start Game"), False, btn_text_col)
        game.game_screen.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))

        # Store btn_rect instead of card_rect for click detection
        clickable_rects['cards'].append((c_def, btn_rect))

    # --- 5. BOTTOM BAR: BACK, RANDOM, AND CUSTOM CHARACTER ---
    back_w = S(160)
    rand_w = S(180)
    custom_w = S(230)
    btn_h = S(42)
    gap = S(20)

    total_bottom_w = back_w + rand_w + custom_w + (gap * 2)
    start_bottom_x = center_x - (total_bottom_w // 2)
    bottom_y = card_y + card_h + S(36)

    # 1. Back Button
    back_rect = pygame.Rect(start_bottom_x, bottom_y, back_w, btn_h)
    is_back_hover = back_rect.collidepoint(mouse_pos)
    pygame.draw.rect(game.game_screen, (80, 80, 80) if is_back_hover else (60, 60, 60), back_rect, border_radius=S(6))
    back_txt = font_16.render(tr('ui', "Back"), False, WHITE)
    game.game_screen.blit(back_txt, back_txt.get_rect(center=back_rect.center))
    clickable_rects['back_button'] = back_rect

    # 2. Random Button (re-rolls traits for all classes + sets new random colors, hair, head equips, name & sex)
    rand_rect = pygame.Rect(back_rect.right + gap, bottom_y, rand_w, btn_h)
    is_rand_hover = rand_rect.collidepoint(mouse_pos)
    rand_bg = (0, 120, 170) if is_rand_hover else (0, 95, 140)
    pygame.draw.rect(game.game_screen, rand_bg, rand_rect, border_radius=S(6))
    rand_txt = font_16.render(tr('ui', "Random"), False, WHITE)
    game.game_screen.blit(rand_txt, rand_txt.get_rect(center=rand_rect.center))
    clickable_rects['random_button'] = rand_rect

    # 3. Custom Character Button (opens full player builder)
    custom_btn_rect = pygame.Rect(rand_rect.right + gap, bottom_y, custom_w, btn_h)
    is_custom_hover = custom_btn_rect.collidepoint(mouse_pos)
    custom_bg = (220, 160, 30) if is_custom_hover else (180, 130, 20)
    pygame.draw.rect(game.game_screen, custom_bg, custom_btn_rect, border_radius=S(6))
    custom_txt = font_16.render(tr('ui', "Custom Character"), False, WHITE)
    game.game_screen.blit(custom_txt, custom_txt.get_rect(center=custom_btn_rect.center))
    clickable_rects['custom_button'] = custom_btn_rect

    # --- 6. TOOLTIP ON HOVER (COMPACT VERTICAL LIST FORMAT) ---
    if hovered_class:
        class_traits = state['class_traits'].get(hovered_class['id'], [])
        
        # Word wrap description into ~40 character lines so tooltip never stretches wide
        desc = hovered_class['description']
        desc_lines = []
        words = desc.split(' ')
        cur = []
        for w in words:
            cur.append(w)
            if len(' '.join(cur)) > 40:
                cur.pop()
                desc_lines.append(' '.join(cur))
                cur = [w]
        if cur:
            desc_lines.append(' '.join(cur))

        tooltip_lines = list(desc_lines)
        
        tooltip_lines.append("")
        tooltip_lines.append(f"{tr('ui', 'Clothes:')}")
        
        # Show actual clothes list including hair and head equipment
        active_clothes = state.get('class_dynamic_gear', {}).get(hovered_class['id'], {}).get('clothes', hovered_class['clothes'])
        for c_name in active_clothes:
            tooltip_lines.append(f"  • {c_name}")

        if hovered_class.get('items'):
            tooltip_lines.append("")
            tooltip_lines.append(f"{tr('ui', 'Starter Items:')}")
            for it_name in hovered_class['items']:
                tooltip_lines.append(f"  • {it_name}")

        tooltip_lines.append("")
        tooltip_lines.append(tr('ui', "Traits:"))
        for t_id in class_traits:
            t_def = TRAIT_DEFINITIONS.get(t_id, {})
            t_name = t_def.get('name', t_id)
            t_cost = t_def.get('cost', 0)
            tooltip_lines.append(f"  • {t_name} ({t_cost:+})")

        t_proxy = SimpleNamespace(
            name=tr('ui', hovered_class['name']),
            tooltip_lines=tooltip_lines,
            tooltip_text=None,
            item_type=None,
            durability=None,
            defence=None,
            load=None,
            capacity=None,
            min_damage=None,
            max_damage=None,
            ammo_type=None
        )
        draw_tooltip(game.game_screen, t_proxy, (mouse_pos[0] + S(15), mouse_pos[1] + S(15)))

    return clickable_rects


def handle_select_character_events(game, state, event, mouse_pos, clickable_rects):
    # Keyboard typing for name
    if event.type == pygame.KEYDOWN:
        if state.get('name_input_active'):
            if event.key == pygame.K_BACKSPACE:
                state['player_name'] = state['player_name'][:-1]
            elif event.key == pygame.K_RETURN:
                state['name_input_active'] = False
            elif len(state['player_name']) < 24 and event.unicode.isprintable():
                state['player_name'] += event.unicode
            return

    # Mouse Wheel for Cards Carousel
    elif event.type == pygame.MOUSEWHEEL:
        cur_idx = state.get('char_carousel_index', 0)
        max_idx = max(0, len(CHARACTER_CLASSES) - 3)
        if event.y < 0:
            state['char_carousel_index'] = min(max_idx, cur_idx + 1)
        elif event.y > 0:
            state['char_carousel_index'] = max(0, cur_idx - 1)
        return

    elif event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', 1) == 1:
        # Carousel Arrow Controls
        if clickable_rects.get('prev_arrow') and clickable_rects['prev_arrow'].collidepoint(mouse_pos):
            state['char_carousel_index'] = max(0, state.get('char_carousel_index', 0) - 1)
            return

        if clickable_rects.get('next_arrow') and clickable_rects['next_arrow'].collidepoint(mouse_pos):
            max_idx = max(0, len(CHARACTER_CLASSES) - 3)
            state['char_carousel_index'] = min(max_idx, state.get('char_carousel_index', 0) + 1)
            return

        # Back Button
        if clickable_rects.get('back_button') and clickable_rects['back_button'].collidepoint(mouse_pos):
            if state.get('respawn_save_folder'):
                game.current_save_folder_name = None
                game.game_state = 'MENU'
            else:
                state['current_tab'] = 'SelectWorld'
            return

        # Random Button (rerolls traits, colors, hair, head equips, name & sex)
        if clickable_rects.get('random_button') and clickable_rects['random_button'].collidepoint(mouse_pos):
            state['class_traits'] = init_all_class_traits()
            state['class_dynamic_gear'] = init_class_dynamic_gear()
            state['class_colors'] = init_class_colors(state['class_dynamic_gear'], randomize=True)
            _char_preview_cache.clear()
            new_sex = random.choice(['Male', 'Female'])
            state['base_data']['sex'] = new_sex
            state['player_name'] = fake.name_male() if new_sex == 'Male' else fake.name_female()
            return

        # Custom Character Button (opens full player builder)
        if clickable_rects.get('custom_button') and clickable_rects['custom_button'].collidepoint(mouse_pos):
            state['current_tab'] = 'Player'
            return

        # Class Cards Click (Start Game directly with selected preset)
        for c_def, rect in clickable_rects.get('cards', []):
            if rect.collidepoint(mouse_pos):
                _start_with_class(game, state, c_def)
                return

        # Name Input Field Activation
        name_rect = clickable_rects.get('name_input')
        if name_rect and name_rect.collidepoint(mouse_pos):
            state['name_input_active'] = True
        else:
            state['name_input_active'] = False

        # Random Name Dice Button
        rand_name_rect = clickable_rects.get('random_name')
        if rand_name_rect and rand_name_rect.collidepoint(mouse_pos):
            is_male = state['base_data'].get('sex', 'Male') == 'Male'
            state['player_name'] = fake.name_male() if is_male else fake.name_female()
            return

        # Sex Toggles
        male_rect = clickable_rects.get('sex_male')
        female_rect = clickable_rects.get('sex_female')
        if male_rect and male_rect.collidepoint(mouse_pos):
            state['base_data']['sex'] = 'Male'
            return
        if female_rect and female_rect.collidepoint(mouse_pos):
            state['base_data']['sex'] = 'Female'
            return