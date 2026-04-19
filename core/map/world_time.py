# core/map/world_time.py

import pygame
import math
import random 
from core.data.config import *
import core.data.config
from core.messages import display_message
from core.data.localization import tr

class WorldTime:
    def __init__(self, game):
        self.game = game
        
        self.state = "DAY" 
        self.day_length_ms = core.data.config.TIME_DAYLENGTH 
        self.game_time_ms = 0 
        
        self.sunrise_hour = core.data.config.TIME_SUNRISE_HR  
        self.sunset_hour = core.data.config.TIME_SUNSET_HR  
        self.transition_duration_hours = core.data.config.TIME_TRANSITION_HR 
        
        start_hour = core.data.config.TIME_START_HR
        self.game_time_ms = (start_hour / 24.0) * self.day_length_ms

        self.last_update_time = pygame.time.get_ticks()
        self.day_count = 0 

        self.day_radius = core.data.config.BASE_PLAYER_VIEW_RADIUS * 1.5
        self.night_radius = core.data.config.BASE_PLAYER_VIEW_RADIUS * 1.0
        self.day_ambient = 255 
        self.night_ambient = 255 - core.data.config.MAX_DARKNESS_OPACITY 

        self.game.player_view_radius = self.day_radius
        self.current_ambient_light = self.day_ambient 
        self.current_hour = int(start_hour)
        
        self._last_state = self.state

        self.weather = "CLEAR"
        self.weather_timer = random.randint(60000, 180000)

        # --- AMBIENCE AUDIO CHANNELS ---
        self.day_channel = None
        self.night_channel = None
        self.rain_channel = None
        self.cave_channel = None
        self._initial_sounds_played = False

    def stop_all_sounds(self):
        """Stops all ambient sounds immediately."""
        if self.day_channel:
            self.day_channel.stop()
            self.day_channel = None
        if self.night_channel:
            self.night_channel.stop()
            self.night_channel = None
        if self.rain_channel:
            self.rain_channel.stop()
            self.rain_channel = None
        if self.cave_channel:
            self.cave_channel.stop()
            self.cave_channel = None
        self._initial_sounds_played = False

    def update(self):
        # Play initial sounds if needed when the game first starts
        if not self._initial_sounds_played and hasattr(self.game, 'sound_manager'):
            if self.game.current_layer_index == 2:
                self.cave_channel = self.game.sound_manager.play_sound("cave.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
            else:
                if self.state in ["DAY", "TRANSITION_TO_DAY"]:
                    self.day_channel = self.game.sound_manager.play_sound("day.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
                elif self.state in ["NIGHT", "TRANSITION_TO_NIGHT"]:
                    self.night_channel = self.game.sound_manager.play_sound("night.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
                
                if self.weather == "RAIN":
                    self.rain_channel = self.game.sound_manager.play_sound("rain.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
            self._initial_sounds_played = True

        # --- LAYER 2 LOGIC (Indoors/Cave) ---
        if self.game.current_layer_index == 2:
            # Stop outdoor ambience when going indoors/underground (layer 2)
            if self.day_channel:
                self.day_channel.fadeout(1000)
                self.day_channel = None
            if self.night_channel:
                self.night_channel.fadeout(1000)
                self.night_channel = None
            if self.rain_channel:
                self.rain_channel.fadeout(1000)
                self.rain_channel = None
                
            # Start cave ambience
            if not self.cave_channel and hasattr(self.game, 'sound_manager'):
                self.cave_channel = self.game.sound_manager.play_sound("cave.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)

            self.state = "NIGHT"
            self.current_ambient_light = self.night_ambient
            self.game.player_view_radius = self.night_radius
            
            current_real_time = pygame.time.get_ticks()
            base_delta = current_real_time - self.last_update_time
            multiplier = self.game.fast_forward_speed if getattr(self.game, 'is_fast_forwarding', False) else 1.0
            self.game_time_ms += base_delta * multiplier
            self.last_update_time = current_real_time
            if self.game_time_ms >= self.day_length_ms:
                self.game_time_ms %= self.day_length_ms
                self.day_count += 1
            return

        # --- LAYER 1 LOGIC (Outdoors) ---
        # Stop cave ambience when returning outside
        if self.cave_channel:
            self.cave_channel.fadeout(1000)
            self.cave_channel = None

        # Resume rain sound if we came back to layer 1 and it's raining
        if self.weather == 'RAIN' and not self.rain_channel and hasattr(self.game, 'sound_manager'):
            self.rain_channel = self.game.sound_manager.play_sound("rain.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
            
        # Ensure correct day/night ambience resumes after leaving cave
        if self.state in ["DAY", "TRANSITION_TO_DAY"] and not self.day_channel and hasattr(self.game, 'sound_manager'):
            self.day_channel = self.game.sound_manager.play_sound("day.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
        elif self.state in ["NIGHT", "TRANSITION_TO_NIGHT"] and not self.night_channel and hasattr(self.game, 'sound_manager'):
            self.night_channel = self.game.sound_manager.play_sound("night.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)

        current_real_time = pygame.time.get_ticks()
        base_delta = current_real_time - self.last_update_time
        multiplier = self.game.fast_forward_speed if getattr(self.game, 'is_fast_forwarding', False) else 1.0
        delta_time = base_delta * multiplier
        
        self.last_update_time = current_real_time
        self.game_time_ms += delta_time
        
        # Weather update
        if self.game.current_layer_index != 2:
            self.weather_timer -= delta_time
            if self.weather_timer <= 0:
                if self.weather == 'CLEAR':
                    self.weather = 'RAIN'
                    display_message(tr('msg', "It started raining."))
                    self.weather_timer = random.randint(30000, 90000)
                    if hasattr(self.game, 'sound_manager') and not self.rain_channel:
                        self.rain_channel = self.game.sound_manager.play_sound("rain.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=2000)
                else:
                    self.weather = 'CLEAR'
                    display_message(tr('msg', "The rain stopped."))
                    self.weather_timer = random.randint(90000, 240000)
                    if self.rain_channel:
                        self.rain_channel.fadeout(2000)
                        self.rain_channel = None

        if self.game_time_ms >= self.day_length_ms:
            self.game_time_ms %= self.day_length_ms
            self.day_count += 1

            z_mult = core.data.config.ZOMBIE_MULTIPLIER * self.day_count
            
            core.data.config.ZOMBIES_PER_SPAWN *= z_mult
            core.data.config.ZOMBIE_INFECTION_CHANCE *= z_mult
            
            if hasattr(self.game.player, 'saved_detection_radius') and self.game.player.saved_detection_radius is not None:
                self.game.player.saved_detection_radius *= z_mult
            else:
                core.data.config.ZOMBIE_DETECTION_RADIUS *= z_mult
            
            print(f"Day {self.day_count} Complete. Difficulty Increased (x{z_mult})!")
            display_message(self.game, f"{tr('msg', 'The horde grows stronger... (Day')} {self.day_count})")
            
            
        exact_hour = (self.game_time_ms / self.day_length_ms) * 24.0
        self.current_hour = int(exact_hour)
        
        fade = 0.0 
        new_state = "NIGHT"
        
        if self.sunrise_hour <= exact_hour < (self.sunrise_hour + self.transition_duration_hours):
            new_state = "TRANSITION_TO_DAY"
            progress = (exact_hour - self.sunrise_hour) / self.transition_duration_hours
            fade = self.ease_in_out(progress)
            
        elif (self.sunrise_hour + self.transition_duration_hours) <= exact_hour < self.sunset_hour:
            new_state = "DAY"
            fade = 1.0
            
        elif self.sunset_hour <= exact_hour < (self.sunset_hour + self.transition_duration_hours):
            new_state = "TRANSITION_TO_NIGHT"
            progress = (exact_hour - self.sunset_hour) / self.transition_duration_hours
            fade = 1.0 - self.ease_in_out(progress) 
            
        else:
            new_state = "NIGHT"
            fade = 0.0

        self.state = new_state
        
        self.game.player_view_radius = self.lerp(self.night_radius, self.day_radius, fade)
        self.current_ambient_light = self.lerp(self.night_ambient, self.day_ambient, fade)

        # Calculate how long one in-game hour is in milliseconds
        one_hour_ms = self.day_length_ms / 24.0

        if self.weather == 'RAIN':
            self.current_ambient_light = max(float(self.night_ambient), self.current_ambient_light * 0.70)
            self.game.player_view_radius *= 0.90 
        elif self.weather == 'CLEAR' and self.weather_timer <= one_hour_ms:
            # Progressively darken as the storm approaches
            # progress goes from 0.0 (exactly 1 hour away) to 1.0 (rain is starting right now)
            progress = 1.0 - (self.weather_timer / one_hour_ms)
            
            # Smoothly interpolate towards the RAIN multipliers (0.70 for light, 0.90 for view)
            storm_light_factor = self.lerp(1.0, 0.70, progress)
            storm_view_factor = self.lerp(1.0, 0.90, progress)
            
            self.current_ambient_light = max(float(self.night_ambient), self.current_ambient_light * storm_light_factor)
            self.game.player_view_radius *= storm_view_factor

        # --- TRANSITION LOGIC ---
        if self.state != self._last_state:
            if self.state == "TRANSITION_TO_NIGHT":
                display_message(self.game, tr('msg', "Dusk falls..."))
                
                # Fade out day, fade in night
                if self.day_channel:
                    self.day_channel.fadeout(4000)
                    self.day_channel = None
                if not self.night_channel and hasattr(self.game, 'sound_manager'):
                    self.night_channel = self.game.sound_manager.play_sound("night.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=4000)
                    
            elif self.state == "NIGHT":
                display_message(self.game, tr('msg', "It is now Night."))
                
            elif self.state == "TRANSITION_TO_DAY":
                display_message(self.game, tr('msg', "The sky lightens..."))
                # Fade out night, fade in day
                if self.night_channel:
                    self.night_channel.fadeout(4000)
                    self.night_channel = None
                if not self.day_channel and hasattr(self.game, 'sound_manager'):
                    self.day_channel = self.game.sound_manager.play_sound("day.ogg", "ambience", loops=-1, base_volume=1.0, is_critical=True, fade_ms=4000)
                    
            elif self.state == "DAY":
                display_message(self.game, tr('msg', "It is now Day."))
                
            self._last_state = self.state

    def lerp(self, a, b, t):
        return a + (b - a) * t

    def ease_in_out(self, t):
        return (math.sin((t * math.pi) - (math.pi / 2)) + 1) / 2