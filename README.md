![BitRot logo](https://raw.githubusercontent.com/gustavokuklinski/bit-rot/refs/heads/main/game/icons/logo.png)

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
# Nuitka
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./game/icons/favicon.ico --output-dir=./build bit-rot.py # Compile the Game
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./game/icons/favicon.ico --output-dir=./build editor.py # Compile map editor
```
