import pygame
import os
import random
import math  # <-- [ADD THIS]
from data.config import *

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
            final_volume = base_volume * volume_falloff

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
            channel.set_volume(base_volume, base_volume)
        
        # 3. Play
        channel.play(sound, loops=loops)

        return channel