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

        # Increase the maximum number of simultaneous channels
        pygame.mixer.set_num_channels(128)
        
        # Reserve the first 16 channels (IDs 0 to 15) for critical sounds 
        # find_channel() will now only look at channels 16 through 255.
        pygame.mixer.set_reserved(16)
        
        # Keep track of which reserved channel to use next (Round-robin)
        self.current_reserved_channel = 0
        self.max_reserved_channels = 16


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

    def play_sound(self, name, subdir=None, game=None, source_pos=None, base_volume=1.0, loops=0, pitch_variance=0.0, force=False, is_critical=False):
        """
        Plays a sound by its name.
        'is_critical' routes the sound to a protected reserved channel so it never drops.
        """
        if not name: 
            return
            
        sound_key = name
        if subdir:
            sound_key = f"{subdir}/{name}"

        name_lower = name.lower()
        subdir_lower = subdir.lower() if subdir else ""

        # --- VIP Routing for Explosives / Guns ---
        if not is_critical and any(k in name_lower for k in ['explode', 'explosion', 'bomb', 'grenade', 'blast', 'shot', 'gun', 'fire']):
            is_critical = True
            force = True

        # --- Re-Balanced Horde Dampening ---
        is_zombie = 'zombie' in subdir_lower or 'zombie' in name_lower
        
        if is_zombie:
            # Light dampening so the XML config remains the dominant volume controller
            if any(k in name_lower for k in ['groan', 'moan', 'idle', 'wander', 'alert']):
                base_volume *= 0.5  
                
        if 'step' in name_lower or 'walk' in name_lower:
            if pitch_variance == 0.0:
                pitch_variance = 0.35  
            
            if is_zombie:
                base_volume *= 0.3  # Reduced from 95% reduction to a moderate 70% reduction
            
            # NOTE: Player and NPC steps are no longer dampened here. 
            # They will play at 100% of whatever the XML and entity script requests.

        if sound_key not in self.sounds:
            sound_path = name
            if subdir:
                sound_path = os.path.join(subdir, name)
            
            if not self.load_sound(sound_key, sound_path):
                if 'step' not in name_lower:
                    print(f"Warning: Sound '{name}' could not be found or loaded from {sound_path}.")
                return
                
        sound = self.sounds[sound_key]

        if pitch_variance > 0:
            raw_pitch = random.uniform(1.0 - pitch_variance, 1.0 + pitch_variance)
            pitch_factor = round(raw_pitch * 20) / 20.0 
            sound = self.get_pitched_sound(sound_key, sound, pitch_factor)

        zoom_multiplier = 1.0 
        if game:
            MAX_ZOOM_VOLUME = 1.0 
            MIN_ZOOM_VOLUME = 0.75 
            current_zoom = max(core.data.config.FAR_ZOOM, min(game.zoom_level, core.data.config.NEAR_ZOOM))
            if (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM) != 0:
                zoom_progress = (current_zoom - core.data.config.FAR_ZOOM) / (core.data.config.NEAR_ZOOM - core.data.config.FAR_ZOOM)
            else:
                zoom_progress = 1.0 
            zoom_multiplier = MIN_ZOOM_VOLUME + (zoom_progress * (MAX_ZOOM_VOLUME - MIN_ZOOM_VOLUME))

        channel = None
        if is_critical:
            for i in range(self.max_reserved_channels):
                c = pygame.mixer.Channel(i)
                if not c.get_busy():
                    channel = c
                    break
            if not channel:
                if force:
                    channel = pygame.mixer.Channel(self.current_reserved_channel)
                    self.current_reserved_channel = (self.current_reserved_channel + 1) % self.max_reserved_channels
                else:
                    channel = pygame.mixer.find_channel(False)
        else:
            channel = pygame.mixer.find_channel(force)

        if not channel:
            return
        
        # Pull master volume from XML config
        volume_modifier = core.data.config.VOLUME_BACKGROUND
        if subdir_lower in ['ambient', 'weather', 'cave', 'atmosphere', 'environment']:
            volume_modifier = core.data.config.VOLUME_ATMOSPHERIC
        elif subdir_lower in ['music']:
            volume_modifier = core.data.config.VOLUME_MUSIC

        if game and source_pos and game.player:
            player_pos = game.player.rect.center
            dx = source_pos[0] - player_pos[0]
            dy = source_pos[1] - player_pos[1]
            distance = math.hypot(dx, dy)

            max_dist = GAME_WIDTH * 0.6 
            if distance > max_dist:
                return 

            # --- Re-Balanced Distance Falloff ---
            # Brought the exponent down from 3.5 to 2.0 (Inverse-Square Law).
            # Sounds will carry further and feel more natural as you move away.
            volume_falloff = max(0.01, math.pow(max(0.0, 1.0 - (distance / max_dist)), 2.0))
            
            final_volume = base_volume * volume_falloff * zoom_multiplier * volume_modifier
            final_volume = min(1.0, final_volume) 

            pan_range = TILE_SIZE * 15 
            pan_factor = max(-1.0, min(1.0, dx / pan_range))
            
            angle = (pan_factor + 1.0) * math.pi / 4.0
            left_vol = final_volume * math.cos(angle)
            right_vol = final_volume * math.sin(angle)
            
            channel.set_volume(left_vol, right_vol)
            
        else:
            final_ui_volume = base_volume * zoom_multiplier * volume_modifier
            final_ui_volume = min(1.0, final_ui_volume) 
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