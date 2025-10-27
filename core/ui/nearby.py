import pygame
from data.config import *
from core.ui.modals import BaseModal
from core.ui.tabs import Tabs
from core.ui.container import draw_container_content
from core.entities.corpse import Corpse

def draw_nearby_modal(surface, game, modal, assets):
    base_modal = BaseModal(surface, modal, assets, "Nearby")
    base_modal.draw_base()
    close_button, minimize_button = base_modal.get_buttons()

    if base_modal.minimized:
        modal['content_rect'] = None # No content rect when minimized
        return close_button, minimize_button

    nearby_containers = game.find_nearby_containers()

    if not nearby_containers:
        no_containers_text = font.render("No containers nearby.", True, WHITE)
        surface.blit(no_containers_text, (base_modal.modal_x + 10, base_modal.modal_y + base_modal.header_h + 30 + 10)) # Position below header+tabs
        modal['content_rect'] = None # No content rect when empty
        modal['tabs_data'] = [] # Ensure tabs_data is empty
        modal['tab_rects'] = [] # Ensure tab_rects is empty
        return close_button, minimize_button

    tabs_data = []
    current_tab_labels = set() # Keep track of valid labels for this frame
    for container in nearby_containers:
        label = container.name # Default label
        icon = None # Default icon
        icon_path = None # Default icon path

        # Determine Icon and potentially Label based on type
        if isinstance(container, Corpse):
            label = "Corpse" # Use a consistent label for corpses
            icon_path = SPRITE_PATH + 'zombie/dead.png'
        elif container.item_type == 'backpack':
            # Use specific backpack icons
            if 'large' in container.name.lower():
                icon_path = SPRITE_PATH + 'items/large_backpack.png'
            elif 'small' in container.name.lower():
                icon_path = SPRITE_PATH + 'items/small_backpack.png'
            else:
                icon_path = SPRITE_PATH + 'items/bag.png'
        elif hasattr(container, 'image'):
             # Use the container's own image if available (and not handled above)
             icon = container.image # Pass the surface directly if loaded

        # Add unique label suffix if needed (e.g., "Corpse (1)", "Corpse (2)")
        original_label = label
        count = 1
        while label in current_tab_labels:
            count += 1
            label = f"{original_label} ({count})"

        current_tab_labels.add(label)

        tab_info = {
            'label': label, # Use the potentially modified label
            'container': container
        }
        if icon:
            tab_info['icon'] = icon # Pass pre-loaded surface
        elif icon_path:
            tab_info['icon_path'] = icon_path # Pass path for Tabs class to load

        tabs_data.append(tab_info)

    modal['tabs_data'] = tabs_data # Store the generated tabs_data

    # --- VALIDATE active_tab ---
    # Ensure active_tab is valid, default to first if not set or invalid
    if modal.get('active_tab') not in current_tab_labels:
        modal['active_tab'] = tabs_data[0]['label'] if tabs_data else None
    # --- END VALIDATION ---

    # DEBUG 9: Show active tab at the START of drawing
    # print(f"--- Drawing Nearby Modal (Start): Active Tab is '{modal.get('active_tab')}' ---") # DEBUG

    tabs = Tabs(surface, modal, tabs_data, assets)
    tabs.draw() # This draws the tabs and stores 'tab_rects' in the modal dict

    active_tab_label_to_draw = modal.get('active_tab')
    active_tab_data = None
    if active_tab_label_to_draw:
        # Find the active tab data using the *potentially modified* label
        active_tab_data = next((tab for tab in tabs_data if tab['label'] == active_tab_label_to_draw), None)

    # --- DEFINE CONTENT RECT ---
    # Calculate the area below the header and tab bar for container content
    content_rect = pygame.Rect(
        modal['position'][0], # Modal X
        modal['position'][1] + base_modal.header_h, # Modal Y + Header Height + Tab Height
        modal['rect'].width, # Modal Width
        modal['rect'].height - base_modal.header_h # Remaining Height
    )
    modal['content_rect'] = content_rect # Store for find_item_at_pos and potentially drawing bg
    # --- END DEFINE ---


    if active_tab_data:
        container = active_tab_data['container']
        # Create a temporary dict containing just the rect needed by draw_container_content
        container_modal_view = {'rect': content_rect}

        # Optionally draw a background for the content area
        # pygame.draw.rect(surface, (30,30,30), content_rect) # Darker background

        # print(f"    Drawing content for container: {container.name}") # DEBUG
        draw_container_content(surface, container, container_modal_view, assets)
    # else:
        # print(f"    No active_tab_data found to draw content for '{active_tab_label_to_draw}'") # DEBUG

    return close_button, minimize_button
