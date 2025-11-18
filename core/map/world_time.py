import pygame
import math
from data.config import *
from core.messages import display_message

class WorldTime:
    def __init__(self, game):
        self.game = game
        
        # State machine: DAY, TRANSITION_TO_NIGHT, NIGHT, TRANSITION_TO_DAY
        self.state = "DAY" 
        
        # --- NEW CONFIGURATION ---
        # Total length of a full 24h game day in real milliseconds
        # 180000 ms = 3 minutes per day. Adjust as needed in config or here.
        self.day_length_ms = TIME_DAYLENGTH # Example: 5 minutes per game day
        
        self.game_time_ms = 0 # 0 to day_length_ms
        
        # Define key times (0.0 to 24.0)
        self.sunrise_hour = TIME_SUNRISE_HR  # 5:30 AM
        self.sunset_hour = TIME_SUNSET_HR  # 17:30 (5:30 PM)
        self.transition_duration_hours = TIME_TRANSITION_HR # How long the fade lasts in game-hours
        
        # Calculate start time (6 AM = 6.0)
        start_hour = TIME_START_HR
        self.game_time_ms = (start_hour / 24.0) * self.day_length_ms

        self.last_update_time = pygame.time.get_ticks()
        
        self.day_count = 0 # Track full days survived

        # Visual settings
        self.day_radius = BASE_PLAYER_VIEW_RADIUS * 1.5
        self.night_radius = BASE_PLAYER_VIEW_RADIUS * 0.5
        self.day_ambient = 255 
        self.night_ambient = 255 - MAX_DARKNESS_OPACITY 

        # Set initial values
        self.game.player_view_radius = self.day_radius
        self.current_ambient_light = self.day_ambient 
        self.current_hour = int(start_hour)
        
        # Helper to track state changes to avoid spamming messages
        self._last_state = self.state


    def update(self):
        """Runs the day/night state machine based on specific clock times."""
        current_real_time = pygame.time.get_ticks()
        delta_time = current_real_time - self.last_update_time
        self.last_update_time = current_real_time
        
        # Advance game time
        self.game_time_ms += delta_time
        
        # Check for day wrap
        if self.game_time_ms >= self.day_length_ms:
            self.game_time_ms %= self.day_length_ms
            self.day_count += 1
            
        # Calculate current game hour (0.0 - 24.0)
        exact_hour = (self.game_time_ms / self.day_length_ms) * 24.0
        self.current_hour = int(exact_hour)
        
        # Determine State and Fade Factor (0.0 = Night, 1.0 = Day)
        # We want:
        # Night: 18:30 to 05:30 (approx, after transition)
        # Sunrise: 05:30 to 06:30
        # Day: 06:30 to 17:30
        # Sunset: 17:30 to 18:30
        
        fade = 0.0 # Default to full night
        new_state = "NIGHT"
        
        # Dawn Transition (5:30 to 6:30)
        if self.sunrise_hour <= exact_hour < (self.sunrise_hour + self.transition_duration_hours):
            new_state = "TRANSITION_TO_DAY"
            # Progress 0.0 to 1.0
            progress = (exact_hour - self.sunrise_hour) / self.transition_duration_hours
            fade = self.ease_in_out(progress)
            
        # Day (6:30 to 17:30)
        elif (self.sunrise_hour + self.transition_duration_hours) <= exact_hour < self.sunset_hour:
            new_state = "DAY"
            fade = 1.0
            
        # Dusk Transition (17:30 to 18:30)
        elif self.sunset_hour <= exact_hour < (self.sunset_hour + self.transition_duration_hours):
            new_state = "TRANSITION_TO_NIGHT"
            # Progress 0.0 to 1.0
            progress = (exact_hour - self.sunset_hour) / self.transition_duration_hours
            fade = 1.0 - self.ease_in_out(progress) # Fade out
            
        # Night (18:30 to 5:30)
        else:
            new_state = "NIGHT"
            fade = 0.0

        self.state = new_state
        
        # Apply Visuals based on 'fade' (0.0 = Night, 1.0 = Day)
        self.game.player_view_radius = self.lerp(self.night_radius, self.day_radius, fade)
        self.current_ambient_light = self.lerp(self.night_ambient, self.day_ambient, fade)

        # Handle State Change Messages
        if self.state != self._last_state:
            if self.state == "TRANSITION_TO_NIGHT":
                display_message(self.game, "Dusk falls...")
            elif self.state == "NIGHT":
                display_message(self.game, "It is now Night.")
            elif self.state == "TRANSITION_TO_DAY":
                display_message(self.game, "The sky lightens...")
            elif self.state == "DAY":
                display_message(self.game, "It is now Day.")
            self._last_state = self.state

    def lerp(self, a, b, t):
        """Linearly interpolates between a and b by t."""
        return a + (b - a) * t

    def ease_in_out(self, t):
        """A smooth sine-based easing function for 0.0 <= t <= 1.0."""
        return (math.sin((t * math.pi) - (math.pi / 2)) + 1) / 2