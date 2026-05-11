import pygame
from core.data.config import *
from core.ui.modals import BaseModal

class Tabs:
    def __init__(self, surface, modal, tabs_data, assets):
        self.surface = surface
        self.modal = modal
        self.tabs_data = tabs_data
        self.assets = assets
        self.base_modal = BaseModal(surface, modal, assets, "") # assets and title are not needed here
        self.tab_rects = []

        # Ensure initial active tab is set correctly
        if 'active_tab' not in self.modal or self.modal['active_tab'] not in {tab['label'] for tab in self.tabs_data}:
            self.modal['active_tab'] = self.tabs_data[0]['label'] if self.tabs_data else None

    def _load_tab_icons(self):
        for tab in self.tabs_data:
            if 'icon_loaded' in tab and tab['icon_loaded']: # Avoid reloading/rescaling
                 continue
            try:
                if 'icon' in tab and isinstance(tab['icon'], pygame.Surface):
                    # If icon surface is passed directly, scale it
                    tab['icon'] = pygame.transform.scale(tab['icon'], (24, 24))
                elif 'icon_path' in tab:
                    # Load from path if path is provided
                    img = pygame.image.load(tab['icon_path']).convert_alpha()
                    tab['icon'] = pygame.transform.scale(img, (24, 24))
                else:
                    tab['icon'] = None
                tab['icon_loaded'] = True # Mark as loaded
            except Exception as e:
                print(f"Error loading tab icon: {e}")
                tab['icon'] = None
                tab['icon_loaded'] = False # Mark as failed

    def draw(self, game=None, mouse_pos=None):
        # Update base_modal's position to reflect the current modal's position
        self.base_modal.modal_x = self.modal['position'][0]
        self.base_modal.modal_y = self.modal['position'][1]
        self.base_modal.modal_w = self.modal['rect'].width
        self.base_modal.modal_h = self.modal['rect'].height

        self._load_tab_icons() # Ensure icons are loaded/scaled
        self.tab_rects = []

        if not self.tabs_data: # Handle case with no tabs
             self.modal['tab_rects'] = [] # Store empty list
             return

        # Calculate tab widths dynamically to ensure they fill the space
        total_tabs = len(self.tabs_data)
        current_x = self.base_modal.modal_x
        tab_height = 30 # Hardcoded tab height

        current_active_label = self.modal.get('active_tab', 'NONE SET')

        # 1. Calculate Rects First
        for i, tab in enumerate(self.tabs_data):
            # Calculate width for this specific tab
            tab_width = self.base_modal.modal_w // total_tabs
            if i < self.base_modal.modal_w % total_tabs:
                tab_width += 1

            tab_rect = pygame.Rect(current_x, self.base_modal.modal_y + self.base_modal.header_h, tab_width, tab_height)
            self.tab_rects.append(tab_rect)
            current_x += tab_width

        # 2. Draw Inactive Tabs
        for i, tab in enumerate(self.tabs_data):
            if tab['label'] != current_active_label:
                # Check for drag highlight
                is_drag_target = False
                if game and game.dragged_item and mouse_pos and self.tab_rects[i].collidepoint(mouse_pos):
                    is_drag_target = True
                
                self._draw_single_tab(tab, self.tab_rects[i], is_active=False, is_drag_target=is_drag_target)

        # 3. Draw Active Tab (Last, so it stays on top)
        for i, tab in enumerate(self.tabs_data):
            if tab['label'] == current_active_label:
                # Check for drag highlight (even active tabs can be drop targets)
                is_drag_target = False
                if game and game.dragged_item and mouse_pos and self.tab_rects[i].collidepoint(mouse_pos):
                    is_drag_target = True

                self._draw_single_tab(tab, self.tab_rects[i], is_active=True, is_drag_target=is_drag_target)

        # Store calculated rects for click detection
        self.modal['tab_rects'] = self.tab_rects

    def _draw_single_tab(self, tab, rect, is_active, is_drag_target=False):
        if is_active: 
            pygame.draw.rect(self.surface, GRAY_60, rect) # Active color
        else:
            pygame.draw.rect(self.surface, DARK_GRAY, rect) # Inactive color
        
        # Draw Border
        if is_drag_target:
             pygame.draw.rect(self.surface, YELLOW, rect, 2) # Highlight
        else:
             pygame.draw.rect(self.surface, WHITE, rect, 1) # Normal Border

        # Draw icon or fallback text
        if tab.get('icon'): 
            icon_rect = tab['icon'].get_rect(center=rect.center)
            self.surface.blit(tab['icon'], icon_rect)
        else:
            # Fallback to text if icon fails to load or not provided
            text = font_14.render(tab['label'], True, WHITE)
            text_rect = text.get_rect(center=rect.center)
            self.surface.blit(text, text_rect)

    def handle_input(self):
        # This method is no longer needed as input will be handled in mouse.py
        pass

    # check_click is kept but might not be used directly by handle_mouse_down anymore
    def check_click(self, scaled_mouse_pos):
        for i, tab_rect in enumerate(self.tab_rects):
            if tab_rect.collidepoint(scaled_mouse_pos):
                if i < len(self.tabs_data): # Ensure index is valid
                    self.modal['active_tab'] = self.tabs_data[i]['label']
                    return True
        return False