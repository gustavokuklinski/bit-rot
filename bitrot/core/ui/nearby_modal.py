import pygame
from core.data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.container_modal import draw_container_content
from core.entities.zombie.corpse import Corpse
from core.entities.item.item import Container
from core.data.localization import tr

# --- NEW: Virtual Container for grouping loose items ---
class VirtualGroundContainer:
    def __init__(self, items):
        self.name = tr('ui', "Ground")
        self.inventory = items
        self.capacity = 20 # Infinite capacity for ground view
        self.item_type = 'ground'
        self.image = None 
# -----------------------------------------------------

def draw_nearby_modal(surface, game, modal, assets, mouse_pos):
    base_modal = BaseModal(surface, modal, assets, tr('ui', "Nearby"))
    modal['rect'] = base_modal.modal_rect
    base_modal.draw_base()
    close_button = base_modal.get_buttons()

    # --- CHANGED: Filter and Group Items ---
    raw_nearby_objects = game.find_nearby_containers()
    
    nearby_containers = []
    ground_items = []

    if raw_nearby_objects:
        for obj in raw_nearby_objects:
            # Determine if this object deserves its own tab (Container/Corpse)
            is_independent_container = False
            
            if isinstance(obj, Corpse):
                is_independent_container = True
            elif hasattr(obj, 'inventory') and obj.inventory is not None:
                if getattr(obj, 'item_type', '') in ['container','vehicle', 'cloth', 'maptile_container']:
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
            # -------------------------------------
    
    # If we have loose items, create a "Ground" tab at the very beginning
    if ground_items:
        nearby_containers.insert(0, VirtualGroundContainer(ground_items))

    if not nearby_containers:
        no_containers_text = font.render("", True, WHITE)
        surface.blit(no_containers_text, (base_modal.modal_x + 10, base_modal.modal_y + base_modal.header_h + 30 + 10))
        modal['content_rect'] = None
        modal['tabs_data'] = []
        modal['tab_rects'] = []
        return close_button

    tabs_data = []
    current_tab_labels = set() 
    for container in nearby_containers:
        label = container.name 
        icon = None 
        icon_path = None 

        if isinstance(container, Corpse):
            label = "Corpse" 
            icon_path = SPRITE_PATH + 'zombie/dead.png'
        elif getattr(container, 'item_type', '') == 'ground':
            icon_path = SPRITE_PATH + 'ui/ground.png' 
        elif hasattr(container, 'image') and container.image:
             icon = container.image 

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
        draw_container_content(surface, game, container, container_modal_view, assets, mouse_pos)

    return close_button