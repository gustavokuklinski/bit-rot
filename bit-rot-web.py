import pygame
import asyncio
from core.game import Game

# 2. Create an async main function
async def main():
    game = Game()
    await game.run()

if __name__ == '__main__':
    asyncio.run(main())