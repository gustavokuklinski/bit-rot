import argparse
from core.game import Game
from editor.editor import editor


def main():
    parser = argparse.ArgumentParser(description="Launch Bitrot or the Editor.")
    parser.add_argument(
        "--editor",
        action="store_true",
        help="Open the level editor instead of the game.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enter debug mode to accept instant-launch world/player/item flags.",
    )
    parser.add_argument(
        "--world",
        type=str,
        default=None,
        help="Path to JSON world template.",
    )
    parser.add_argument(
        "--player",
        type=str,
        default=None,
        help="Path to JSON player template.",
    )
    parser.add_argument(
        "--weather",
        type=str,
        default=None,
        help="Starting weather (CLEAR, RAIN, FOG, RAIN_FOG).",
    )
    parser.add_argument(
        "--time",
        type=str,
        default=None,
        help="Starting world time (e.g. 22:00).",
    )
    parser.add_argument(
        "--spawn-item",
        action="append",
        default=[],
        dest="spawn_items",
        help="Path to item XML to spawn in player inventory (repeatable).",
    )
    parser.add_argument(
        "--spawn-cloth",
        action="append",
        default=[],
        dest="spawn_clothes",
        help="Path to cloth XML to spawn in player inventory (repeatable).",
    )
    args = parser.parse_args()

    if args.editor:
        app = editor()
    elif args.debug:
        debug_config = {
            "debug": True,
            "world": args.world,
            "player": args.player,
            "weather": args.weather,
            "time": args.time,
            "spawn_items": args.spawn_items,
            "spawn_clothes": args.spawn_clothes,
        }
        app = Game(debug_config=debug_config)
    else:
        app = Game()

    app.run()

if __name__ == "__main__":
    main()