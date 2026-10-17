# core/systems/world_area.py
"""Decides whether two entities live in the same chunk + layer.

The map filename already encodes the layer ('map_L2_3_1_map.csv'), so comparing
filenames compares chunk AND layer at once.
"""

def get_area_key(entity, game):
    """Returns the map filename an entity lives in ('' if unknown)."""
    if entity is None:
        return ''
    # Dedicated server: all chunks are simulated at once, each entity carries its own map_filename
    if getattr(game, 'is_dedicated', False):
        return getattr(entity, 'map_filename', '') or ''
    # Listen-server host: remote players report their own map
    if type(entity).__name__ == 'RemotePlayer':
        return getattr(entity, 'map_filename', '') or ''
    # Everything else on a host (host player, zombies, npcs...) lives in the host's loaded map
    return getattr(getattr(game, 'map_manager', None), 'current_map_filename', '') or ''


def _layer_of(entity, game):
    if entity is not None and entity is getattr(game, 'player', None):
        return getattr(game, 'current_layer_index', 1)
    return getattr(entity, 'layer', 1)


def is_same_area(a, b, game):
    ka, kb = get_area_key(a, game), get_area_key(b, game)
    if ka and kb:
        return ka == kb
    # Legacy / unknown map: fall back to the old layer-only comparison
    return _layer_of(a, game) == _layer_of(b, game)