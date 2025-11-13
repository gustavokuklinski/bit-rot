![BitRot logo](https://raw.githubusercontent.com/gustavokuklinski/bit-rot/refs/heads/main/game/sprites/ui/logo.png)

# Bit Rot

Bit Rot is a zombie survivor game.

**Hacking the game**

Install on virtual environment
```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python main.py # Play the game
$ python editor.py # Map editor
```

Build executable system target

```shell
$ pyinstaller --onefile --noconsole --icon=./game/icons/favicon.ico main.py # Compile the Game
$ pyinstaller --onefile --noconsole --icon=./game/icons/favicon.ico editor.py # Compile map editor
```

----

**Basic controls**:
- **W/A/S/D**: Walk
- **SHIFT + W/A/S/D**: Run
- **CTRL + L-Click**: Shoot/Attack
- **SHIFT + L-Click + Drag**: Get only one item from stack
- **L-Click + Drag**: Place or Drop
- **R-Click**: Opens menu 
- **1/2/3/4/5**: Equip and use item from Belt

- **E**: Get item from floor, open/close door
- **R**: Reload weapon or item

- **I**: Opens Inventory and Belt
- **H**: Open Status
- **N**: Open Nearby
- **M**: Open Messages

- **F2**: Pause game

- **MOUSE SCROLL**: Zoom in/Zoom out
- **-/=**: Keyboard Zoom in/Zoom out
