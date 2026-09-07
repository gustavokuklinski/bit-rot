import pygame
import random
import os

# --- CONFIGURATION ---
OUTPUT_PATH = './crt_overlay.png' 
IMAGE_SIZE = (800, 800) 
SCANLINE_COLOR = (0, 0, 0, 60)    # Dark, semi-transparent lines
NOISE_COLOR = (255, 255, 255, 20) # Very faint white noise

def generate_crt_texture():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    pygame.init()
    
    surface = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0)) 

    width, height = IMAGE_SIZE

    # 1. Create Scanlines
    # We draw a line every 3 pixels to create the CRT look
    for y in range(0, height, 3):
        pygame.draw.line(surface, SCANLINE_COLOR, (0, y), (width, y), 1)

    # 2. Add subtle static noise
    for _ in range(2000):
        rx = random.randint(0, width - 1)
        ry = random.randint(0, height - 1)
        surface.set_at((rx, ry), NOISE_COLOR)

    pygame.image.save(surface, OUTPUT_PATH)
    print(f"Successfully generated CRT overlay at: {OUTPUT_PATH}")
    pygame.quit()

if __name__ == "__main__":
    generate_crt_texture()