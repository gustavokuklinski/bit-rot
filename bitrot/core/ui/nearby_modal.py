# core/ui/nearby_modal.py
import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.container_modal import draw_container_content
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Container
from core.data.localization import tr
from core.ui.helpers.keybinds import keybind_manager
from core.messages import display_message
from core.entities.item.item_helpers import has_app

def get_key_name(action):
    val = keybind_manager.kb_binds.get(action)
    if val is None: return ""
    if val < 0:
        btn_num = -val
        if btn_num == 1: return "LMB"
        elif btn_num == 2: return "MMB"
        elif btn_num == 3: return "RMB"
        else: return f"MB{btn_num}"
    name = pygame.key.name(val).upper()
    return name

class VirtualGroundContainer:
    def __init__(self, items):
        self.name = tr('ui', "Ground")
        self.inventory = items
        self.capacity = 20
        self.item_type = 'ground'
        self.image = None 

def _draw_closed_container_view(surface, game, container, content_rect, mouse_pos, modal):
    center_x = content_rect.centerx
    area_top = content_rect.top + 30
    area_center_y = area_top + (content_rect.height - 30) // 2
    
    if hasattr(container, 'image') and container.image:
        faded_img = container.image.copy()
        faded_img.fill((255, 255, 255, 140), special_flags=pygame.BLEND_RGBA_MULT)
        img_scaled = pygame.transform.scale(faded_img, (48, 48))
        surface.blit(img_scaled, img_scaled.get_rect(center=(center_x, area_center_y - 25)))
        
    title_surf = font_12.render(tr('ui', "Closed container"), False, WHITE)
    surface.blit(title_surf, title_surf.get_rect(center=(center_x, area_center_y + 15)))
    
    btn_w, btn_h = 130, 30
    btn_rect = pygame.Rect(center_x - btn_w // 2, area_center_y + 40, btn_w, btn_h)
    
    is_hovered = btn_rect.collidepoint(mouse_pos)
    btn_color = (60, 60, 60) if not is_hovered else (80, 80, 80)
    pygame.draw.rect(surface, btn_color, btn_rect, border_radius=4)
    pygame.draw.rect(surface, WHITE if is_hovered else GRAY, btn_rect, 1, border_radius=4)
    
    btn_txt = font_12.render(f"{tr('ui', 'Open')} [{get_key_name('interact')}]", False, YELLOW if is_hovered else WHITE)
    surface.blit(btn_txt, btn_txt.get_rect(center=btn_rect.center))
    
    mouse_pressed = pygame.mouse.get_pressed()[0]
    if is_hovered and mouse_pressed and not getattr(game, 'is_dragging', False):
        if game.player.action_timer > 0:
            display_message(tr('msg', "Busy..."))
        else:
            def do_open_container():
                if hasattr(container, 'open'):
                    container.open(game)
                    modal['active_tab'] = container.name

            # Zero timer if SD card app is installed
            if has_app(game, 'open_container_instant'):
                do_open_container()
            else:
                agility = game.player.progression.get_level('agility')
                open_time = max(0.2, 1.8 - (agility * 0.2))
                game.player.start_action(tr('ui', "Opening"), open_time, do_open_container, xp_reward=1.5)

def draw_nearby_modal(surface, game, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, tr('ui', "Nearby"))
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    raw_nearby_objects = game.find_nearby_containers()
    
    nearby_containers = []
    ground_items = []

    if raw_nearby_objects:
        for obj in raw_nearby_objects:
            is_independent_container = False
            
            if isinstance(obj, Corpse):
                is_independent_container = True
            elif hasattr(obj, 'inventory') and obj.inventory is not None:
                if getattr(obj, 'item_type', '') in ['container', 'vehicle', 'cloth', 'maptile_container']:
                    is_independent_container = True
            
            if is_independent_container:
                nearby_containers.append(obj)

            should_show_on_ground = True
            if not getattr(obj, 'item_type', None):
                should_show_on_ground = False

            if is_independent_container:
                if isinstance(obj, Corpse):
                    should_show_on_ground = False
                elif isinstance(obj, Container):
                    should_show_on_ground = False
                elif getattr(obj, 'item_type', '') == 'vehicle':
                    should_show_on_ground = False
            
            if should_show_on_ground:
                ground_items.append(obj)
    
    if ground_items:
        nearby_containers.insert(0, VirtualGroundContainer(ground_items))

    if not nearby_containers:
        modal['content_rect'] = None
        modal['tabs_data'] = []
        modal['tab_rects'] = []
        return close_button

    tabs_data = []
    current_tab_labels = set() 
    for container in nearby_containers:
        is_closed_maptile = (getattr(container, 'item_type', '') == 'maptile_container' and not getattr(container, 'is_opened', False))

        if is_closed_maptile:
            label = tr('ui', "Closed container")
            icon = None
            icon_path = None
            if hasattr(container, 'image') and container.image:
                faded_icon = container.image.copy()
                faded_icon.fill((255, 255, 255, 110), special_flags=pygame.BLEND_RGBA_MULT)
                icon = faded_icon
            else:
                icon_path = SPRITE_PATH + 'ui/inventory.png'
        elif isinstance(container, Corpse):
            label = "Corpse" 
            icon_path = SPRITE_PATH + 'zombie/dead.png'
            icon = None
        elif getattr(container, 'item_type', '') == 'ground':
            label = container.name
            icon_path = SPRITE_PATH + 'ui/ground.png' 
            icon = None
        elif hasattr(container, 'image') and container.image:
            label = container.name
            icon = container.image 
            icon_path = None
        else:
            label = container.name
            icon = None
            icon_path = None

        original_label = label
        count = 1
        while label in current_tab_labels:
            count += 1
            label = f"{original_label} ({count})"

        current_tab_labels.add(label)

        tab_info = {
            'label': label,
            'container': container
        }
        if is_closed_maptile:
            tab_info['tooltip'] = tr('ui', "Closed container")

        if icon:
            tab_info['icon'] = icon
        elif icon_path:
            tab_info['icon_path'] = icon_path

        tabs_data.append(tab_info)

    modal['tabs_data'] = tabs_data

    if modal.get('active_tab') not in current_tab_labels:
        modal['active_tab'] = tabs_data[0]['label'] if tabs_data else None

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw(game, mouse_pos) 

    active_tab_label_to_draw = modal.get('active_tab')
    active_tab_data = None
    if active_tab_label_to_draw:
        active_tab_data = next((tab for tab in tabs_data if tab['label'] == active_tab_label_to_draw), None)

    content_rect = pygame.Rect(
        modal['position'][0],
        modal['position'][1] + base_modal.header_h,
        modal['rect'].width,
        modal['rect'].height - base_modal.header_h
    )
    modal['content_rect'] = content_rect

    if active_tab_data:
        container = active_tab_data['container']
        container_modal_view = {'rect': content_rect}

        if getattr(container, 'item_type', '') == 'maptile_container' and not getattr(container, 'is_opened', False):
            _draw_closed_container_view(surface, game, container, content_rect, mouse_pos, modal)
        else:
            draw_container_content(surface, game, container, container_modal_view, assets, mouse_pos)

    return close_button