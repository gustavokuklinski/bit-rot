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
        if 'All' not in game.message_logs:
            game.message_logs['All'] = []
        game.message_logs['All'].append(text)

        # Check if text is a radio transmission or broadcast
        from core.data.radio_manager import RadioManager
        radio_stations = list(RadioManager.STATIONS.keys()) if hasattr(RadioManager, 'STATIONS') else []

        is_radio = str(text).startswith("[Radio ") or any(str(text).startswith(st + ":") for st in radio_stations)
        if is_radio:
            if 'Radio' not in game.message_logs:
                game.message_logs['Radio'] = []
            game.message_logs['Radio'].append(text)