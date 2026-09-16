# sound_manager.py
import pygame
import os
import random
import math 
from core.data.config import *
import core.data.config

CATEGORY_TO_CONFIG_ATTR = {
    'ambient': 'VOLUME_ATMOSPHERIC',
    'ambience': 'VOLUME_ATMOSPHERIC',
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
    'animals': 'VOLUME_ANIMAL',
    'radio': 'VOLUME_ITEMS',
    'ui': 'VOLUME_ITEMS'
}

class SoundManager:
    def __init__(self):
        self.sounds = {}
        # 1024 buffer size prevents buffer underrun/drops without latency
        if not pygame.mixer.get_init():
            pygame.mixer.pre_init(22050, -16, 2, 1024)
            pygame.mixer.init()
        pygame.mixer.set_num_channels(128)
        
        # Channels 0..3: Dedicated for ambient loops (day, night, rain, cave)
        # Channels 4..15: Dedicated for critical/priority sounds (weapons, hits, radio, notifications)
        # Channels 16..127: Dynamic channels for entity/spatial sounds
        pygame.mixer.set_reserved(16)
        
        self.ambient_channels = [0, 1, 2, 3]
        self.critical_channels = list(range(4, 16))
        self.current_critical_idx = 0

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
    def get_max_audible_distance(game, subdir="", name=""):
        """
        Only plays environment sounds within the player's view radius plus a small margin.
        Explosions and heavy gunfire carry across the chunk.
        """
        if not game or not hasattr(game, 'player') or not game.player:
            return float('inf')

        name_lower = (name or "").lower()
        if any(k in name_lower for k in ('explode', 'explosion', 'bomb', 'grenade', 'blast')):
            return GAME_WIDTH * 0.85

        # Dynamic view radius from world time, weather, and health
        view_radius = getattr(game, 'player_view_radius', 12 * TILE_SIZE)
        tile_margin = 4 * TILE_SIZE  # 4 tiles (~64px) buffer
        return view_radius + tile_margin

    @staticmethod
    def calculate_spatial_audio(source_pos, player_pos, max_dist, base_volume, zoom_mult, vol_mod):
        dx = source_pos[0] - player_pos[0]
        dy = source_pos[1] - player_pos[1]
        distance = math.hypot(dx, dy)

        if distance >= max_dist:
            return 0.0, 0.0

        # Smooth S-curve (cosine) fade: 1.0 near player -> 0.0 at max_dist
        norm_dist = max(0.0, min(1.0, distance / max_dist))
        volume_falloff = 0.5 * (1.0 + math.cos(math.pi * norm_dist))

        final_volume = min(1.0, base_volume * volume_falloff * zoom_mult * vol_mod)
        if final_volume <= 0.001:
            return 0.0, 0.0

        # Equal-power circular stereo panning
        pan_range = TILE_SIZE * 15
        pan_factor = max(-1.0, min(1.0, dx / pan_range))
        angle = (pan_factor + 1.0) * (math.pi / 4.0)
        
        left_vol = min(1.0, max(0.0, final_volume * math.cos(angle)))
        right_vol = min(1.0, max(0.0, final_volume * math.sin(angle)))
        
        return left_vol, right_vol

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
            
            # Prevent uncontrolled cache growth
            if len(self.sounds) > 250:
                keys_to_del = [k for k in self.sounds if '_pitch_' in k]
                for k in keys_to_del[:50]:
                    del self.sounds[k]
                    
            self.sounds[pitched_key] = pitched_sound
            return pitched_sound
        except (ImportError, Exception):
            return base_sound

    def play_sound(self, name, subdir=None, game=None, source_pos=None, base_volume=1.0, loops=0, pitch_variance=0.0, force=False, is_critical=False, fade_ms=0):
        if not name: 
            return None
            
        sound_key = f"{subdir}/{name}" if subdir else name
        name_lower = name.lower()
        subdir_lower = (subdir or "").lower()

        volume_modifier = self.get_volume_modifier(subdir)
        if volume_modifier <= 0.0 or base_volume <= 0.0:
            return None

        # VIP routing for explosives/guns
        if not is_critical and any(k in name_lower for k in ('explode', 'explosion', 'bomb', 'grenade', 'blast', 'shot', 'gun', 'fire')):
            is_critical = True
            force = True

        # Check distance early for spatial sounds to avoid wasting channel/loading resources
        is_player = False
        if game and source_pos and game.player:
            is_player = (subdir_lower == 'player') or (
                source_pos == game.player.rect.center and subdir_lower not in ('zombie', 'zombies', 'npc', 'npcs', 'animal', 'animals', 'map', 'vehicles', 'vehicle')
            )
            if not is_player:
                dx = source_pos[0] - game.player.rect.centerx
                dy = source_pos[1] - game.player.rect.centery
                dist = math.hypot(dx, dy)
                max_dist = self.get_max_audible_distance(game, subdir=subdir_lower, name=name_lower)
                if dist >= max_dist:
                    return None

        # Load sound
        if sound_key not in self.sounds:
            sound_path = os.path.join(subdir, name) if subdir else name
            if not self.load_sound(sound_key, sound_path):
                return None
                
        sound = self.sounds[sound_key]
        if pitch_variance > 0:
            pitch_factor = round(random.uniform(1.0 - pitch_variance, 1.0 + pitch_variance) * 20) / 20.0
            sound = self.get_pitched_sound(sound_key, sound, pitch_factor)

        zoom_multiplier = self.calculate_zoom_multiplier(game)

        # Select playback channel safely
        channel = None
        is_ambient_loop = (loops == -1 and any(k in subdir_lower for k in ('ambient', 'ambience', 'weather', 'cave', 'atmosphere')))
        
        if is_ambient_loop:
            # Pick from dedicated ambient channels (0..3)
            for ch_idx in self.ambient_channels:
                c = pygame.mixer.Channel(ch_idx)
                if not c.get_busy():
                    channel = c
                    break
            if not channel:
                channel = pygame.mixer.Channel(self.ambient_channels[0])
        elif is_critical:
            # Pick from critical channels (4..15) without stealing ambient channels
            for ch_idx in self.critical_channels:
                c = pygame.mixer.Channel(ch_idx)
                if not c.get_busy():
                    channel = c
                    break
            if not channel:
                channel = pygame.mixer.Channel(self.critical_channels[self.current_critical_idx])
                self.current_critical_idx = (self.current_critical_idx + 1) % len(self.critical_channels)
        else:
            # Dynamic general SFX channel (16..127)
            channel = pygame.mixer.find_channel(False)
            if not channel:
                # Steal oldest non-reserved channel so sounds are never dropped
                channel = pygame.mixer.find_channel(True)

        if not channel:
            return None

        # Calculate spatial volume or standard UI volume
        if game and source_pos and game.player:
            if is_player:
                final_vol = min(1.0, base_volume * zoom_multiplier * volume_modifier)
                channel.set_volume(final_vol, final_vol)
            else:
                max_dist = self.get_max_audible_distance(game, subdir=subdir_lower, name=name_lower)
                left_vol, right_vol = self.calculate_spatial_audio(
                    source_pos, game.player.rect.center, max_dist, 
                    base_volume, zoom_multiplier, volume_modifier
                )
                if left_vol <= 0.0 and right_vol <= 0.0:
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

    def update_spatial_volume(self, channel, source_pos, game, base_volume=1.0, subdir=None, name=None):
        if not channel or not game or not game.player:
            return

        volume_modifier = self.get_volume_modifier(subdir)
        zoom_multiplier = self.calculate_zoom_multiplier(game)
        max_dist = self.get_max_audible_distance(game, subdir=subdir, name=name)

        left_vol, right_vol = self.calculate_spatial_audio(
            source_pos, game.player.rect.center, max_dist, 
            base_volume, zoom_multiplier, volume_modifier
        )
        channel.set_volume(left_vol, right_vol)