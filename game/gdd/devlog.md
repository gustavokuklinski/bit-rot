## Devlog

### Dev
- [x] Create lootable containers on map
- [x] Ajust dynamic 'Nearby' lootable containers
- [x] Add the Wallet slot
- [x] Create a player view 360 radius
- [x] Ajust the walk controls: W/A goes fast, S/D goes slow
- [x] Added scrool to messages
- [x] Set the default open modals (Inventory and Nearby)
- [x] Modals have default start alignment
- [x] Modals have keybindings
- [] Show the weapon on player hand when SHIFT is pressed
- [] Nearby system shows itens on the floor
- [] Append the important player messages to Messages modal ```display_message(game, "Replace print('messages')")```
- [] Make player spawn with wallet on slot
- [] Add Saves for the current game
- [] Build day/night system (with sleep)
- [] Add player spawn choice and random spawn
- [] Build a camp system
- [] Add TCP/IP direct multiplayer
- [] Build a simple craft system (allow the player to chop trees and build a little house on the map)

### Map Editor
- [x] Allow selection of an Area
- [x] Game map size: 100x100 - Can be increased
- [] Display some map relation on boundaries in editor using the map pattern: ```map_L<NUM>_P0_<TOP>_<RIGHT>_<BOTTOM>_<LEFT>``` and add a button: ```Create new Map Section```
- [] Add a menu buttom to connect a layared map (Make it search the connection on the same map codes and place correctly)
- [] Add open/closed doors
- [] Breakable scenarios (walls, containers, doors)

### Player
- [] Add more prefessions
- [] Add more traits
- [] Create a character builder (traits and char sprite)
- [] Generate Player ID
- [] Player balance action

### Zombies
- [x] Zombies are random generated
- [x] Zombie timer respawn in config
- [] Generate Zombie ID

### Game Lore
- [] Generate a game lore based on the story
- [] Generate game map focusing on the game story
- [] Create items for the lore story (Newspaper, ID)
