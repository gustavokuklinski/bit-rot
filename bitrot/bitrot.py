#from core.game import Game
#
#def main():
#    game = Game()
#    game.run()

#if __name__ == '__main__':
#    main()

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
    args = parser.parse_args()

    if args.editor:
        app = editor()
    else:
        app = Game()

    app.run()


if __name__ == "__main__":
    main()