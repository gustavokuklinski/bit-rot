import pygame
import random
import os

# --- CONFIGURATION ---
# Make sure this path matches where your game expects the file
OUTPUT_PATH = './rain_overlay.png' 
IMAGE_SIZE = (800, 800)  # Square size; your game will scale it to screen
RAIN_COLOR = (180, 200, 255, 120) # Light blue-ish, semi-transparent
NUM_STREAKS = 800             # Density of rain

def generate_rain_texture():
    # Ensure the directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    pygame.init()
    
    # Create a surface with an alpha channel (transparent)
    surface = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0)) # Fully transparent background

    width, height = IMAGE_SIZE

    for _ in range(NUM_STREAKS):
        # Random position and length
        x = random.randint(0, width)
        y = random.randint(0, height)
        length = random.randint(5, 15)
        thickness = random.randint(1, 2)
        
        # Slight diagonal angle for a more natural look
        angle_x = 2 
        
        # To make it SEAMLESS:
        # We draw the rain streak, and then we draw it again 
        # offset by the height of the image.
        # This ensures that if a drop starts at the bottom, it "continues" at the top.
        
        start_pos = (x, y)
        end_pos = (x + angle_x, y + length)
        
        # Main streak
        pygame.draw.line(surface, RAIN_COLOR, start_pos, end_pos, thickness)
        
        # Seamless wrap-around (Bottom to Top)
        pygame.draw.line(surface, RAIN_COLOR, (x, y - height), (x + angle_x, y + length - height), thickness)
        
        # Seamless wrap-around (Top to Bottom)
        pygame.draw.line(surface, RAIN_COLOR, (x, y + height), (x + angle_x, y + length + height), thickness)

    # Save as PNG
    pygame.image.save(surface, OUTPUT_PATH)
    print(f"Successfully generated seamless rain overlay at: {OUTPUT_PATH}")
    pygame.quit()

if __name__ == "__main__":
    generate_rain_texture()