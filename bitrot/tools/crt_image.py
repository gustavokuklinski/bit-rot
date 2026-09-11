import pygame
import random
import os

# --- CONFIGURATION ---
OUTPUT_PATH = './vhs_glitch_overlay.png' 
IMAGE_SIZE = (800, 800) 

def generate_vhs_texture():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    pygame.init()
    
    width, height = IMAGE_SIZE
    surface = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0)) # Start with a fully transparent screen

    # List of RGB colors for the glitch (Red, Green, Blue)
    # The '50' at the end is the transparency (Alpha)
    glitch_colors = [
        (255, 0, 0, 50),   # Red
        (0, 255, 0, 50),   # Green
        (0, 0, 255, 50),   # Blue
        (0, 0, 0, 100)     # Dark scanline
    ]

    for y in range(0, height):
        # 1. Draw the standard dark CRT scanlines every 3rd pixel
        if y % 3 == 0:
            pygame.draw.line(surface, (0, 0, 0, 80), (0, y), (width, y), 1)

        # 2. Randomly draw a colored glitch line
        # 0.02 means there is a 2% chance for any given line to be a glitch
        if random.random() < 0.02: 
            color = random.choice(glitch_colors)
            # We draw the line. Sometimes we make it slightly offset for a "jagged" look
            offset = random.randint(-10, 10)
            pygame.draw.line(surface, color, (offset, y), (width + offset, y), 1)

    pygame.image.save(surface, OUTPUT_PATH)
    print(f"Successfully generated Simple RGB Glitch at: {OUTPUT_PATH}")
    pygame.quit()

if __name__ == "__main__":
    generate_vhs_texture()