# Bit Rot
Bit Rot is a zombie survivor game.

**Basic controls**:
- **W/A/S/D**: Walk
- **SHIFT + R-Click**: Shoot/Attack
- **R-Click + Drag**: Place on Belt/Backpack or Drop
- **L-Click**: Opens menu 
- **1/2/3/4/5**: Equip/Use item from Belt

- **E**: Get item from floor
- **R**: Reload weapon

- **I**: Opens inventory and belt
- **H**: Opens Status

----

**Mapping**
- **P**: Player spawn
- **Z**: Zombie spawn
- **I**: Item map spawn

**How Map Transitions Work**
The system treats the numbers in the map filenames (map_TOP_RIGHT_BOTTOM_LEFT.csv) as Connection IDs. A connection is made between two maps if they have a matching ID on opposite sides.

For example, to make a connection from the right side of one map to the left side of another, you would name your files like this:

1. First Map (Origin): map_0_1_0_0.csv
    * This filename indicates a connection on its right side with an ID of 1.

2. Second Map (Destination): map_0_0_0_1.csv
    * This filename indicates a connection on its left side with an ID of 1.

When the player walks off the right edge of map_0_1_0_0.csv, the system will search for a map with a matching 1 on its left side, find map_0_0_0_1.csv, and load it, placing the player on the left edge of the new map.

You can create chains of maps this way:
* map_0_1_0_0.csv (right connection 1)
* map_0_2_0_1.csv (left connection 1, right connection 2)
* map_0_0_0_2.csv (left connection 2)

This would create a chain of three maps you can walk through from left to right and back.

For spawning and background the maps must have a:
* map_0_1_0_0_spawn.csv
* map_0_1_0_0_ground.csv

----

**Hacking the game**

Install system wide
```python
$ sudo apt install python3-pygame
$ python3 bit-rot.py
```

Install on virtual environment
```python
$ python3 -m venv .venv
$ source .venv/bin/activate
$ python bit-rot.py
```

----

**Credits**
Tiles: https://opengameart.org/content/1-bit-pack