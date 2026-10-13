import pygame
import os

# --- CONFIGURATION ---
OUTPUT_PATH = './ui_crt_overlay.png'
IMAGE_SIZE = (1280, 720)  # Native game resolution (can also be scaled by pygame)
LINE_SPACING = 3          # Draws a scanline every 3rd pixel (set to 2 for tighter lines)
LINE_ALPHA = 45           # Subtle opacity (0-255). 40-50 provides a retro look without muddying UI text

def generate_ui_scanlines():
    output_dir = os.path.dirname(OUTPUT_PATH)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    pygame.init()

    width, height = IMAGE_SIZE
    surface = pygame.Surface(IMAGE_SIZE, pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))  # Start completely transparent

    scanline_color = (0, 0, 0, LINE_ALPHA)

    # Draw pure, uniform scanlines across the height
    for y in range(0, height, LINE_SPACING):
        pygame.draw.line(surface, scanline_color, (0, y), (width, y), 1)

    pygame.image.save(surface, OUTPUT_PATH)
    print(f"Successfully generated clean UI CRT scanlines at: {OUTPUT_PATH}")
    pygame.quit()

if __name__ == "__main__":
    generate_ui_scanlines()