# generate_fog.py
import pygame
import random
import math
import os

OUTPUT_PATH = './fog_texture.png'
IMAGE_SIZE = (800, 800)
NUM_CLOUDS = 240

def generate_fog_texture():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    pygame.init()

    w, h = IMAGE_SIZE
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    for _ in range(NUM_CLOUDS):
        cx = random.randint(0, w)
        cy = random.randint(0, h)
        radius = random.randint(60, 140)
        base_alpha = random.randint(15, 35)

        # Soft radial gradient circle
        cloud_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for r in range(radius, 0, -4):
            alpha = int(base_alpha * (1.0 - (r / radius) ** 1.5))
            color = (210, 220, 230, alpha)
            pygame.draw.circle(cloud_surf, color, (radius, radius), r)

        # Draw with seamless 9-way toroidal wrap
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                surface.blit(cloud_surf, (cx + ox - radius, cy + oy - radius), special_flags=pygame.BLEND_RGBA_ADD)

    pygame.image.save(surface, OUTPUT_PATH)
    print(f"Successfully generated seamless fog texture at: {OUTPUT_PATH}")
    pygame.quit()

if __name__ == "__main__":
    generate_fog_texture()