# Bit Rot
Bit Rot is a zombie survivor game.

**Basic controls**:
- **W/A/S/D or arrows**: Walk
- **SHIFT + R-Click**: Shoot/Attack
- **R-Click + Drag**: Place on Belt/Backpack or Drop
- **L-Click**: Opens menu 
- **1/2/3/4/5**: Equip/Use item from Belt

- **E**: Get item from floor
- **R**: Reload weapon

- **I**: Opens inventory and belt
- **H**: Opens Status

- **F2**: Pause game
----


**Hacking the game**

Install system wide
```shell
$ sudo apt install python3-pygame
$ python3 main.py
```

Install on virtual environment
```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python main.py
```

Play on browser
```shell
$ pygbag main.py 

# Open: localhost:8000
```
----

**Credits**
Tiles: https://kenney.nl/assets/1-bit-pack