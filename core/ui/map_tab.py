import pygame
from data.config import *

def draw_map_tab(surface, game, modal, assets):
    y_offset = modal['rect'].y + 80
    x_offset = modal['rect'].x + 20
    
    text_surf = font.render("Map is not available.", True, GRAY)
    text_rect = text_surf.get_rect(centerx=modal['rect'].centerx, y=y_offset + 20)
    surface.blit(text_surf, text_rect)