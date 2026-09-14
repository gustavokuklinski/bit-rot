# sound_manager.py
import pygame
import os
import random
import math 
from core.data.config import *
import core.data.config

CATEGORY_TO_CONFIG_ATTR = {
    'ambient': 'VOLUME_ATMOSPHERIC', 
    'weather': 'VOLUME_ATMOSPHERIC', 
    'cave': 'VOLUME_ATMOSPHERIC', 
    'atmosphere': 'VOLUME_ATMOSPHERIC', 
    'environment': 'VOLUME_ATMOSPHERIC', 
    'music': 'VOLUME_MUSIC', 
    'map': 'VOLUME_MAP', 
    'items': 'VOLUME_ITEMS', 
    'item': 'VOLUME_ITEMS', 
    'vehicles': 'VOLUME_VEHICLE', 
    'vehicle': 'VOLUME_VEHICLE', 
    'player': 'VOLUME_PLAYER', 
    'zombie': 'VOLUME_ZOMBIE', 
    'zombies': 'VOLUME_ZOMBIE', 
    'npc': 'VOLUME_NPC', 
    'npcs': 'VOLUME_NPC', 
    'animal': 'VOLUME_ANIMAL', 
    'animals': 'VOLUME_ANIMAL'
}

class SoundManager:
    def __init__(self):
        self.sounds = {}
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(128)
        pygame.mixer.set_reserved(16)
        
        self.current_reserved_channel = 0
        self.max_reserved_channels = 16

    @staticmethod
    def get_volume_modifier(subdir):
        if not subdir:
            return 1.0
        attr_name = CATEGORY_TO_CONFIG_ATTR.get(subdir.lower())
        return getattr(core.data.config, attr_name, 1.0) if attr_name else 1.0

    @staticmethod
    def calculate_zoom_multiplier(game):
        if not game:
            return 1.0
        near = core.data.config.NEAR_ZOOM
        far = core.data.config.FAR_ZOOM
        zoom_range = near - far
        current_zoom = max(far, min(game.zoom_level, near))
        progress = (current_zoom - far) / zoom_range if zoom_range != 0 else 1.0
        return 0.75 + (progress * 0.25)

    @staticmethod
    def calculate_spatial_audio(source_pos, player_pos, max_dist, base_volume, zoom_mult, vol_mod, is_steep_falloff=False):
        dx = source_pos[0] - player_pos[0]
        dy = source_pos[1] - player_pos[1]
        distance = math.hypot(dx, dy)

        if distance > max_dist:
            return 0.0, 0.0

        exponent = 3.0 if is_steep_falloff else 2.0
        volume_falloff = math.pow(max(0.0, 1.0 - (distance / max_dist)), exponent)
        if not is_steep_falloff:
            volume_falloff = max(0.01, volume_falloff)

        final_volume = min(1.0, base_volume * volume_falloff * zoom_mult * vol_mod)

        pan_range = TILE_SIZE * 15
        pan_factor = max(-1.0, min(1.0, dx / pan_range))
        angle = (pan_factor + 1.0) * math.pi / 4.0
        
        return final_volume * math.cos(angle), final_volume * math.sin(angle)

    def load_sound(self, name, sound_path):
        if name in self.sounds:
            return True
        full_path = os.path.join(SOUND_PATH, sound_path)
        try:
            self.sounds[name] = pygame.mixer.Sound(full_path)
            return True
        except pygame.error as e:
            print(f"Warning: Could not load sound '{name}' from '{full_path}': {e}")
            return False

    def get_pitched_sound(self, sound_key, base_sound, pitch_factor):
        if pitch_factor == 1.0:
            return base_sound
        pitched_key = f"{sound_key}_pitch_{pitch_factor:.2f}"
        if pitched_key in self.sounds:
            return self.sounds[pitched_key]
            
        try:
            import numpy as np
            import pygame.sndarray
            
            snd_array = pygame.sndarray.array(base_sound)
            indices = np.round(np.arange(0, len(snd_array), pitch_factor)).astype(int)
            indices = indices[indices < len(snd_array)]
            pitched_array = np.ascontiguousarray(snd_array[indices])
            
            pitched_sound = pygame.sndarray.make_sound(pitched_array)
            self.sounds[pitched_key] = pitched_sound
            return pitched_sound
        except ImportError:
            return base_sound
        except Exception as e:
            print(f"Warning: Failed to shift pitch for {sound_key}: {e}")
            return base_sound

    def play_sound(self, name, subdir=None, game=None, source_pos=None, base_volume=1.0, loops=0, pitch_variance=0.0, force=False, is_critical=False, fade_ms=0):
        if not name: 
            return None
            
        sound_key = f"{subdir}/{name}" if subdir else name
        name_lower = name.lower()
        subdir_lower = subdir.lower() if subdir else ""

        volume_modifier = self.get_volume_modifier(subdir)
        if volume_modifier <= 0.0 or base_volume <= 0.0:
            return None

        # VIP routing for explosives/guns
        if not is_critical and any(k in name_lower for k in ('explode', 'explosion', 'bomb', 'grenade', 'blast', 'shot', 'gun', 'fire')):
            is_critical = True
            force = True

        # Zombie acoustic variance
        is_zombie = 'zombie' in subdir_lower or 'zombie' in name_lower
        if is_zombie:
            if any(k in name_lower for k in ('groan', 'moan', 'idle', 'wander', 'alert')):
                if random.random() > 0.5:
                    return None
                if pitch_variance == 0.0:
                    pitch_variance = 0.25
                base_volume *= random.uniform(0.3, 0.6)

        if 'step' in name_lower or 'walk' in name_lower:
            if pitch_variance == 0.0:
                pitch_variance = 0.35
            if is_zombie:
                base_volume *= 0.3

        if sound_key not in self.sounds:
            sound_path = os.path.join(subdir, name) if subdir else name
            if not self.load_sound(sound_key, sound_path):
                return None
                
        sound = self.sounds[sound_key]
        if pitch_variance > 0:
            pitch_factor = round(random.uniform(1.0 - pitch_variance, 1.0 + pitch_variance) * 20) / 20.0
            sound = self.get_pitched_sound(sound_key, sound, pitch_factor)

        zoom_multiplier = self.calculate_zoom_multiplier(game)

        # Select playback channel
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
            return None

        # Position panning / attenuation
        if game and source_pos and game.player:
            is_step = 'step' in name_lower or 'walk' in name_lower
            is_player = subdir_lower == 'player'
            max_dist = GAME_WIDTH * (0.45 if is_step and not is_player else 0.6)

            left_vol, right_vol = self.calculate_spatial_audio(
                source_pos, game.player.rect.center, max_dist, base_volume, 
                zoom_multiplier, volume_modifier, is_steep_falloff=(is_step and not is_player)
            )
            if left_vol == 0.0 and right_vol == 0.0:
                return None
            channel.set_volume(left_vol, right_vol)
        else:
            final_ui_vol = min(1.0, base_volume * zoom_multiplier * volume_modifier)
            channel.set_volume(final_ui_vol, final_ui_vol)

        channel.play(sound, loops=loops, fade_ms=fade_ms)
        return channel

    def play_music(self, path, volume=1.0, loops=-1):
        if core.data.config.VOLUME_MUSIC <= 0.0 or volume <= 0.0:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
            return
            
        try:
            if path.startswith('./'):
                path = path[2:]
            if not os.path.isabs(path):
                path = os.path.join(core.data.config.BASE_DIR, path)

            if os.path.exists(path):
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(volume * core.data.config.VOLUME_MUSIC)
                pygame.mixer.music.play(loops)
            else:
                print(f"Warning: Music file not found at '{path}'")
        except pygame.error as e:
            print(f"Warning: Could not load music '{path}': {e}")

    def update_spatial_volume(self, channel, source_pos, game, base_volume=1.0, subdir=None):
        if not channel or not game or not game.player:
            return

        volume_modifier = self.get_volume_modifier(subdir)
        zoom_multiplier = self.calculate_zoom_multiplier(game)
        max_dist = GAME_WIDTH * 0.6

        left_vol, right_vol = self.calculate_spatial_audio(
            source_pos, game.player.rect.center, max_dist, 
            base_volume, zoom_multiplier, volume_modifier
        )
        channel.set_volume(left_vol, right_vol)