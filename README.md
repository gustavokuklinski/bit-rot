# Bit Rot

Bit Rot is a zombie survivor game.

**Minimum requirements**

RAM: 1 GB Ram
Processor: Intel Core i3
Video: Intel HD Graphics 3000
OS: Ubuntu/Debian, Windows 7
Resolution: 1280x720
Disk: 500MB

**Hacking the game**

Install on virtual environment
```shell
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
```

Run locally
```shell
$ python bitrot.py # Play the game
$ python editor.py # Edit maps
```

Running on web browser
```shell
$ pygbag . # Open localhost:8000 (Uses the main.py default file)
```

Build executable system target
```shell
# Nuitka
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./game/icons/favicon.ico --output-dir=./build bitrot.py # Compile the game
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./game/icons/favicon.ico --output-dir=./build editor.py # Compile the editor
```