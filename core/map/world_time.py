import pygame
import math
from data.config import *
from core.messages import display_message

class WorldTime:
    def __init__(self, game):
        self.game = game
        
        # State machine: DAY, TRANSITION_TO_NIGHT, NIGHT, TRANSITION_TO_DAY
        self.state = "DAY" 
        self.day_duration = DAY_NIGHT_CYCLE_MS
        self.night_duration = DAY_NIGHT_CYCLE_MS
        self.transition_duration = TRANSITION_DURATION_MS
        
        self.last_state_change_time = pygame.time.get_ticks()
        
        # Define the min/max values for radius and darkness
        self.day_radius = BASE_PLAYER_VIEW_RADIUS * 1.5
        self.night_radius = BASE_PLAYER_VIEW_RADIUS * 0.5
        # self.min_darkness = 0
        # self.max_darkness = MAX_DARKNESS_OPACITY
        # 
        # # Set initial values on the game object
        # self.game.player_view_radius = self.day_radius
        # self.current_darkness_overlay = self.min_darkness

        self.day_ambient = 255 # Full brightness
        # Calculate night ambient from the old darkness value
        self.night_ambient = 255 - MAX_DARKNESS_OPACITY 
        
        # Set initial values on the game object
        self.game.player_view_radius = self.day_radius
        self.current_ambient_light = self.day_ambient # New variable


    def update(self):
        """Runs the day/night state machine."""
        current_time = pygame.time.get_ticks()
        time_since_change = current_time - self.last_state_change_time

        # --- State: DAY ---
        if self.state == "DAY":
            if time_since_change > self.day_duration:
                self.state = "TRANSITION_TO_NIGHT"
                self.last_state_change_time = current_time
                display_message(self.game, "Dusk falls...")

        # --- State: TRANSITION_TO_NIGHT ---
        elif self.state == "TRANSITION_TO_NIGHT":
            if time_since_change >= self.transition_duration:
                # Transition complete
                self.state = "NIGHT"
                self.last_state_change_time = current_time
                self.game.player_view_radius = self.night_radius
                #self.current_darkness_overlay = self.max_darkness
                self.current_ambient_light = self.night_ambient
                display_message(self.game, "It is now Night.")
            else:
                # In progress, calculate fades
                progress = time_since_change / self.transition_duration
                eased_progress = self.ease_in_out(progress) # 0.0 -> 1.0

                # Lerp (linear interpolation)
                self.game.player_view_radius = self.lerp(self.day_radius, self.night_radius, eased_progress)
                #self.current_darkness_overlay = self.lerp(self.min_darkness, self.max_darkness, eased_progress)
                self.current_ambient_light = self.lerp(self.day_ambient, self.night_ambient, eased_progress)

        # --- State: NIGHT ---
        elif self.state == "NIGHT":
            if time_since_change > self.night_duration:
                self.state = "TRANSITION_TO_DAY"
                self.last_state_change_time = current_time
                display_message(self.game, "The sky lightens...")

        # --- State: TRANSITION_TO_DAY ---
        elif self.state == "TRANSITION_TO_DAY":
            if time_since_change >= self.transition_duration:
                # Transition complete
                self.state = "DAY"
                self.last_state_change_time = current_time
                self.game.player_view_radius = self.day_radius
                # self.current_darkness_overlay = self.min_darkness
                self.current_ambient_light = self.day_ambient
                display_message(self.game, "It is now Day.")
            else:
                # In progress, calculate fades
                progress = time_since_change / self.transition_duration
                eased_progress = self.ease_in_out(progress) # 0.0 -> 1.0

                # Lerp (linear interpolation)
                self.game.player_view_radius = self.lerp(self.night_radius, self.day_radius, eased_progress)
                #self.current_darkness_overlay = self.lerp(self.max_darkness, self.min_darkness, eased_progress)
                self.current_ambient_light = self.lerp(self.night_ambient, self.day_ambient, eased_progress)

    def lerp(self, a, b, t):
        """Linearly interpolates between a and b by t."""
        return a + (b - a) * t

    def ease_in_out(self, t):
        """A smooth sine-based easing function for 0.0 <= t <= 1.0."""
        return (math.sin((t * math.pi) - (math.pi / 2)) + 1) / 2