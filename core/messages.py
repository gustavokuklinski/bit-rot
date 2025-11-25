import pygame
from core.data.config import *

def display_message(game, text):
    """Global message (appears in All)."""
    # Add to All
    game.message_logs['All'].append(text)

def display_message_player(game, text):
    """Player specific message."""
    game.message_logs['All'].append(text)
    game.message_logs['Player'].append(text)

def display_message_chat(game, text):
    """Chat specific message."""
    game.message_logs['All'].append(text)
    game.message_logs['Chat'].append(text)

def display_message_zombie(game, text):
    """Zombie specific message."""
    game.message_logs['All'].append(text)
    game.message_logs['Zombie'].append(text)