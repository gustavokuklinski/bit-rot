import pygame
from core.data.config import *

# [NEW] Global variable to store the game instance
_game_instance = None

# [NEW] Initialization function called by Game
def init_messages(game):
    global _game_instance
    _game_instance = game

# [NEW] Helper to resolve arguments for backward compatibility
def _resolve_args(arg1, arg2):
    """
    - If arg1 is the Game object, return (arg1, arg2) [Old Syntax]
    - If arg1 is text, return (_game_instance, arg1) [New Syntax]
    """
    if hasattr(arg1, 'message_logs'):
        return arg1, arg2
    return _game_instance, arg1

# [UPDATED] Message functions use _resolve_args
def display_message(arg1, arg2=None):
    game, text = _resolve_args(arg1, arg2)
    if game:
        game.message_logs['All'].append(text)

def display_message_player(arg1, arg2=None):
    game, text = _resolve_args(arg1, arg2)
    if game:
        game.message_logs['All'].append(text)
        game.message_logs['Player'].append(text)

def display_message_chat(arg1, arg2=None):
    game, text = _resolve_args(arg1, arg2)
    if game:
        game.message_logs['All'].append(text)
        game.message_logs['Chat'].append(text)

def display_message_zombie(arg1, arg2=None):
    game, text = _resolve_args(arg1, arg2)
    if game:
        game.message_logs['All'].append(text)
        game.message_logs['Zombie'].append(text) 