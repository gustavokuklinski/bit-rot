# core/android_handler.py
import os
import pygame

def is_android():
    """Centralized check for Android environment to keep code DRY."""
    return 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_BOOTLOGO' in os.environ

def get_android_writable_dir():
    """Returns the safe private storage path for Android saves."""
    return os.environ.get('ANDROID_PRIVATE', '/data/org.bit.rot/files')

def hook_pygame_for_android(game):
    """
    Extracts the massive Pygame monkey-patching logic meant for Android 
    touch inputs and virtual controllers, keeping core/game.py clean.
    """

    if getattr(pygame, '_mobile_patched', False): return
    pygame._mobile_patched = True
    
    orig_event_get = pygame.event.get
    orig_flip = pygame.display.flip
    orig_update = pygame.display.update
    orig_mouse_get_pos = pygame.mouse.get_pos
    orig_mouse_get_pressed = pygame.mouse.get_pressed
    orig_key_get_pressed = pygame.key.get_pressed
    
    def patched_event_get(*args, **kwargs):
        events = orig_event_get(*args, **kwargs)
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        
        if is_virtual:
            game.virtual_controller.update_cursor(game)
            
        if not hasattr(game, '_touch_scroll_accum'):
            game._touch_scroll_accum = 0.0

        processed = []
        for event in events:
            if is_virtual:
                if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
                    game.virtual_controller.process_event(event, game)
                    
                # Fix: Drop ALL native mouse events on mobile. 
                # Our injected events are perfectly simulated and handled below.
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
                    continue 
                processed.append(event)
            else:
                if event.type == pygame.FINGERDOWN:
                    sw, sh = pygame.display.get_surface().get_size()
                    pygame.mouse.set_pos((int(event.x * sw), int(event.y * sh)))
                    processed.append(event)
                elif event.type == pygame.FINGERMOTION:
                    game._touch_scroll_accum -= (event.dy * 60)
                    if abs(game._touch_scroll_accum) >= 1.0:
                        ticks = int(game._touch_scroll_accum)
                        game._touch_scroll_accum -= ticks
                        processed.append(pygame.event.Event(pygame.MOUSEWHEEL, {'x': 0, 'y': -ticks, 'flipped': False}))
                    processed.append(event)
                else:
                    processed.append(event)
                    
        # --- FIX: Inject virtual events safely directly into the Python event queue ---
        if is_virtual and hasattr(game.virtual_controller, 'injected_events'):
            processed.extend(game.virtual_controller.injected_events)
            game.virtual_controller.injected_events.clear()
            
        return processed

    def patched_mouse_get_pos():
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        if is_virtual and hasattr(game.virtual_controller, 'v_mouse_x'):
            return (int(game.virtual_controller.v_mouse_x), int(game.virtual_controller.v_mouse_y))
        return orig_mouse_get_pos()

    def patched_mouse_get_pressed(*args, **kwargs):
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        if is_virtual and hasattr(game.virtual_controller, 'btn_click'):
            left_click = game.virtual_controller.btn_click.get('pressed', False) or getattr(game.virtual_controller, 'ui_pressed', False)
            right_click = game.virtual_controller.btn_aim.get('state', False)
            return (left_click, False, right_click)
        return orig_mouse_get_pressed(*args, **kwargs)

    def patched_key_get_pressed():
        orig_keys = orig_key_get_pressed()
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        
        if is_virtual and hasattr(game.virtual_controller, 'btn_run'):
            run_state = game.virtual_controller.btn_run.get('state', False)
            int_state = game.virtual_controller.btn_interact.get('pressed', False)
            
            if run_state or int_state:
                class VirtualKeyWrapper:
                    def __getitem__(self, key):
                        if run_state and key in (pygame.K_LSHIFT, pygame.K_RSHIFT): return 1
                        if int_state and key == pygame.K_e: return 1
                        try:
                            return orig_keys[key]
                        except Exception:
                            return 0
                            
                    def __len__(self):
                        return len(orig_keys)
                        
                    def __iter__(self):
                        for i in range(len(orig_keys)):
                            yield self.__getitem__(i)
                            
                    def __bool__(self):
                        return True
                        
                    def __contains__(self, key):
                        return self.__getitem__(key) == 1
                
                return VirtualKeyWrapper()
        return orig_keys
        
    def patched_flip():
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        if is_virtual:
            surf = pygame.display.get_surface()
            if surf: game.virtual_controller.draw(surf)
        orig_flip()

    def patched_update(*args, **kwargs):
        is_virtual = getattr(game, 'virtual_controller', None) and getattr(game.virtual_controller, 'enabled', False)
        if is_virtual:
            surf = pygame.display.get_surface()
            if surf: game.virtual_controller.draw(surf)
        orig_update(*args, **kwargs)
        
    pygame.event.get = patched_event_get
    pygame.mouse.get_pos = patched_mouse_get_pos
    pygame.mouse.get_pressed = patched_mouse_get_pressed
    pygame.key.get_pressed = patched_key_get_pressed
    pygame.display.flip = patched_flip
    pygame.display.update = patched_update

    game._get_scaled_mouse_pos = patched_mouse_get_pos