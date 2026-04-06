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
        pygame.mixer.set_num_channels(128) # 32 simultaneous sounds

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

    def get_pitched_sound(self, sound_key, base_sound, pitch_factor):
        """
        Dynamically resamples the sound array to shift the pitch and caches it.
        """
        if pitch_factor == 1.0:
            return base_sound
            
        pitched_key = f"{sound_key}_pitch_{pitch_factor:.2f}"
        
        if pitched_key in self.sounds:
            return self.sounds[pitched_key]
            
        try:
            import numpy as np
            import pygame.sndarray
            
            # Extract the raw sound data array
            snd_array = pygame.sndarray.array(base_sound)
            
            # Resample the array to change speed/pitch
            indices = np.round(np.arange(0, len(snd_array), pitch_factor)).astype(int)
            indices = indices[indices < len(snd_array)]
            
            pitched_array = snd_array[indices]
            
            # Ensure the array is memory-contiguous (required by pygame.sndarray)
            pitched_array = np.ascontiguousarray(pitched_array)
            
            pitched_sound = pygame.sndarray.make_sound(pitched_array)
            self.sounds[pitched_key] = pitched_sound
            return pitched_sound
            
        except ImportError:
            print("Notice: 'numpy' is required for pitch shifting. Playing default sound.")
            return base_sound
        except Exception as e:
            print(f"Warning: Failed to shift pitch for {sound_key}: {e}")
            return base_sound

    def play_sound(self, name, subdir=None, game=None, source_pos=None, base_volume=1.0, loops=0, pitch_variance=0.0):
        """
        Plays a sound by its name. Loads it if not already loaded.
        'pitch_variance' applies a random +/- pitch shift (e.g., 0.15 for slight variation).
        """
        if not name: 
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

        

        # --- NEW: Pitch Variation ---
        if pitch_variance > 0:
            # Calculate a random pitch factor
            raw_pitch = random.uniform(1.0 - pitch_variance, 1.0 + pitch_variance)
            # Round to nearest 0.05 so we don't cache hundreds of nearly identical variations
            pitch_factor = round(raw_pitch * 20) / 20.0 
            sound = self.get_pitched_sound(sound_key, sound, pitch_factor)

        zoom_multiplier = 1.0 # Default if no game object
        if game:
            MAX_ZOOM_VOLUME = 1.0 
            MIN_ZOOM_VOLUME = 0.3 
            current_zoom = max(core.data.config.FAR_ZOOM, min(game.zoom_level, core.data.config.NEAR_ZOOM))
            if (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM) != 0:
                zoom_progress = (current_zoom - core.data.config.FAR_ZOOM) / (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM)
            else:
                zoom_progress = 1.0 
            zoom_multiplier = MIN_ZOOM_VOLUME + (zoom_progress * (MAX_ZOOM_VOLUME - MIN_ZOOM_VOLUME))

        channel = pygame.mixer.find_channel()
        if not channel:
            return
        
        # --- Spatial Audio Logic ---
        volume_modifier = core.data.config.VOLUME_ATMOSPHERIC
        if subdir and subdir.lower() in ['ambient', 'background', 'weather']:
            volume_modifier = core.data.config.VOLUME_BACKGROUND

        if game and source_pos and game.player:
            player_pos = game.player.rect.center
            dx = source_pos[0] - player_pos[0]
            dy = source_pos[1] - player_pos[1]
            distance = math.hypot(dx, dy)

            max_dist = GAME_WIDTH / 2 
            if distance > max_dist:
                return 

            volume_falloff = (1.0 - (distance / max_dist)) ** 2
            
            # MULTIPLY by volume_modifier
            final_volume = base_volume * volume_falloff * zoom_multiplier * volume_modifier

            pan_range = TILE_SIZE * 10 
            pan_factor = max(-1.0, min(1.0, dx / pan_range))
            
            left_vol = 0.0
            right_vol = 0.0

            if pan_factor < 0: 
                left_vol = final_volume
                right_vol = final_volume * (1.0 + pan_factor) 
            else: 
                right_vol = final_volume
                left_vol = final_volume * (1.0 - pan_factor) 
            
            channel.set_volume(left_vol, right_vol)
            
        else:
            # MULTIPLY by volume_modifier
            final_ui_volume = base_volume * zoom_multiplier * volume_modifier
            channel.set_volume(final_ui_volume, final_ui_volume)
    
        channel.play(sound, loops=loops)
        return channel
    
    def play_music(self, path, volume=1.0, loops=-1):
        """
        Plays background music using pygame.mixer.music (streaming).
        """
        try:
            # ---> NEW: Force absolute path for Android <---
            # Strip './' if the caller included it to prevent path joining issues
            if path.startswith('./'):
                path = path[2:]
                
            # If the path isn't already absolute, make it absolute using BASE_DIR
            if not os.path.isabs(path):
                path = os.path.join(core.data.config.BASE_DIR, path)

            if os.path.exists(path):
                pygame.mixer.music.load(path)
                
                # APPLY the Music Volume Setting
                final_music_volume = volume * core.data.config.VOLUME_MUSIC
                pygame.mixer.music.set_volume(final_music_volume)
                
                pygame.mixer.music.play(loops)
            else:
                print(f"Warning: Music file not found at '{path}'")
        except pygame.error as e:
            print(f"Warning: Could not load music '{path}': {e}")