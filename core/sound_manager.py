import pygame
import os
import random
import math 
from core.data.config import *
import core.data.config

class SoundManager:
    def __init__(self):
        """
        Initializes the SoundManager.
        Sounds will be loaded on-demand.
        """
        self.sounds = {}
        # We still pre-init the mixer for better performance
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32) # 32 simultaneous sounds

    def load_sound(self, name, sound_path):
        """
        Loads a single sound from a path and stores it.
        Returns True on success, False on failure.
        """
        if name in self.sounds:
            return True # Already loaded
        
        # Use SOUND_PATH from config
        full_path = os.path.join(SOUND_PATH, sound_path)
        
        try:
            sound = pygame.mixer.Sound(full_path)
            self.sounds[name] = sound
            return True
        except pygame.error as e:
            print(f"Warning: Could not load sound '{name}' from '{full_path}': {e}")
            return False

    # [START MODIFICATION]
    def play_sound(self, name, subdir=None, game=None, source_pos=None, base_volume=1.0, loops=0):
        """
        Plays a sound by its name. Loads it if not already loaded.
        'subdir' specifies the subfolder within SOUND_PATH (e.g., 'zombie' or 'items').
        'game' and 'source_pos' are used to calculate spatial audio.
        """
    # [END MODIFICATION]
        
        if not name: # Don't try to play None or empty string
            return
            
        sound_key = name
        if subdir:
            sound_key = f"{subdir}/{name}"

        if sound_key not in self.sounds:
            sound_path = name
            if subdir:
                sound_path = os.path.join(subdir, name)
            
            if not self.load_sound(sound_key, sound_path):
                print(f"Warning: Sound '{name}' could not be found or loaded from {sound_path}.")
                return
                
        sound = self.sounds[sound_key]


        zoom_multiplier = 1.0 # Default if no game object
        if game:
            # 1. Define our desired volume range
            MAX_ZOOM_VOLUME = 1.0 # At nearest zoom (e.g., 2.0)
            MIN_ZOOM_VOLUME = 0.3 # At farthest zoom (e.g., 0.5)
            
            # 2. Get the current zoom level (clamped)
            current_zoom = max(core.data.config.FAR_ZOOM, min(game.zoom_level, core.data.config.NEAR_ZOOM))
            
            # 3. Calculate how far 'current_zoom' is through the zoom range (0.0 to 1.0)
            if (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM) != 0:
                zoom_progress = (current_zoom - core.data.config.FAR_ZOOM) / (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM)
            else:
                zoom_progress = 1.0 # Avoid division by zero
            
            # 4. Map this progress to our volume range
            # When zoom_progress is 0 (far), multiplier is 0.2
            # When zoom_progress is 1 (near), multiplier is 1.0
            zoom_multiplier = MIN_ZOOM_VOLUME + (zoom_progress * (MAX_ZOOM_VOLUME - MIN_ZOOM_VOLUME))


        channel = pygame.mixer.find_channel()
        if not channel:
            return
        
        # --- Spatial Audio Logic ---
        # We only apply spatial audio if we know *where* the sound is and *who* is listening.
        if game and source_pos and game.player:
            player_pos = game.player.rect.center
            dx = source_pos[0] - player_pos[0]
            dy = source_pos[1] - player_pos[1]
            distance = math.hypot(dx, dy)

            # 1. Volume Falloff
            # Sounds fade to nothing at about half the game screen's width
            max_dist = GAME_WIDTH / 2 
            if distance > max_dist:
                return # Too far to hear

            # Use a quadratic falloff (more natural)
            volume_falloff = (1.0 - (distance / max_dist)) ** 2
            # final_volume = base_volume * volume_falloff
            final_volume = base_volume * volume_falloff * zoom_multiplier

            # 2. Panning (Stereo)
            # How far left/right a sound needs to be to be fully panned
            pan_range = TILE_SIZE * 10 # e.g., 10 tiles
            
            # Get pan_factor: -1.0 (full left) to 1.0 (full right)
            pan_factor = max(-1.0, min(1.0, dx / pan_range))
            
            left_vol = 0.0
            right_vol = 0.0

            if pan_factor < 0: # Sound is to the left
                left_vol = final_volume
                right_vol = final_volume * (1.0 + pan_factor) # (1.0 + -1.0) = 0.0
            else: # Sound is to the right
                right_vol = final_volume
                left_vol = final_volume * (1.0 - pan_factor) # (1.0 - 1.0) = 0.0
            
            channel.set_volume(left_vol, right_vol)
            
        else:
            # --- Non-Spatial (UI/Player) Sound ---
            # Play centered at the requested base volume
            # channel.set_volume(base_volume, base_volume)
            final_ui_volume = base_volume * zoom_multiplier
            channel.set_volume(final_ui_volume, final_ui_volume)
        
        # 3. Play
        channel.play(sound, loops=loops)

        return channel