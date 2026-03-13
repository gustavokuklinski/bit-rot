import pygame
from core.data.config import *

# Global variable to store the game instance
_game_instance = None

# Initialization function called by Game
def init_messages(game):
    global _game_instance
    _game_instance = game

# Helper to resolve arguments for backward compatibility
def _resolve_args(arg1, arg2):
    """
    - If arg1 is the Game object, return (arg1, arg2) [Old Syntax]
    - If arg1 is text, return (_game_instance, arg1) [New Syntax]
    """
    if hasattr(arg1, 'message_logs'):
        return arg1, arg2
    return _game_instance, arg1

# --- UPDATED FUNCTIONS ---

def display_message(arg1, arg2=None):
    game, text = _resolve_args(arg1, arg2)
    if game:
        game.message_logs['All'].append(text)