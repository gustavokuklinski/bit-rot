import pygame
import os
import random
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
        pygame.mixer.set_num_channels(8) # 8 simultaneous sounds

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

    def play_sound(self, name, subdir=None, volume=1.0, loops=0, pan_variance=0.1, volume_variance=0.1):
        """
        Plays a sound by its name. Loads it if not already loaded.
        'subdir' specifies the subfolder within SOUND_PATH (e.g., 'zombie' or 'items').
        """
        
        if not name: # Don't try to play None or empty string
            return
            
        # Use a unique key for the dictionary, e.g., "zombie/zombie_hit.ogg"
        sound_key = name
        if subdir:
            sound_key = f"{subdir}/{name}"

        # --- On-Demand Loading ---
        if sound_key not in self.sounds:
            # Construct the relative path from SOUND_PATH
            sound_path = name
            if subdir:
                sound_path = os.path.join(subdir, name)
            
            if not self.load_sound(sound_key, sound_path):
                print(f"Warning: Sound '{name}' could not be found or loaded from {sound_path}.")
                return # Can't play a sound that doesn't exist
                
        sound = self.sounds[sound_key]

        # Find a free channel
        channel = pygame.mixer.find_channel()
        if not channel:
            return

        # --- Randomization for non-repetitive sound ---
        
        # 1. Randomize Panning
        # -1.0 is full left, 1.0 is full right.
        # We'll pan slightly left or right.
        base_pan = 0.5 # Center
        pan_left = max(0.0, base_pan - pan_variance)
        pan_right = min(1.0, base_pan + pan_variance)
        random_pan = random.uniform(pan_left, pan_right)
        
        # channel.set_volume(LEFT, RIGHT)
        channel.set_volume(random_pan, 1.0 - random_pan)
        
        # 2. Randomize Volume
        # We vary the sound's *base* volume by the variance.
        min_vol = max(0.0, volume - volume_variance)
        max_vol = min(1.0, volume + volume_variance)
        random_volume = random.uniform(min_vol, max_vol)
        
        # Apply the randomized volume to the sound itself before playing
        sound.set_volume(random_volume)

        # 3. Play
        channel.play(sound, loops=loops)