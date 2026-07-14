# Bit Rot

Bit Rot is a zombie survivor game.

**Minimum requirements**

**RAM:** 1 GB Ram
**Processor:** Intel Core i3, Silicon M-series
**Video:** Intel HD Graphics 3000
**OS:** Ubuntu/Debian, Windows 7, MacOS
**Resolution:** 1280x720
**Disk:** 500MB

**Hacking the game**

## Install on virtual environment
```shell
$python3 -m venv .venv$ source .venv/bin/activate
$ pip install -r requirements.txt
```

### Cache cleaning
```shell
$ chmod +x clean_cache.sh
$ ./clean_cache.sh
```

---

## Play

Run locally

```shell
$ python bitrot/bitrot.py # Play the game$ python bitrot/editor.py # Edit maps
```
 
## Play on web browser

```shell
$ pygbag bitrot/ # Open localhost:8000 (Uses the main.py default file)
```

---

## Build executables (.bin, .exe, .app):

**Linux**

```shell
# Nuitka
$ nuitka --onefile --include-data-dir=./bitrot/game=game ./bitrot/bitrot.py # Make one file packed
$ nuitka --onefile --output-dir=./build ./bitrot/bitrot.py # Compile the game
$ nuitka --onefile --output-dir=./build ./bitrot/editor.py # Compile the editor
```

**Windows**

```shell
# Nuitka
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/game/icons/favicon.ico --output-dir=./build ./bitrot/bitrot.py # Compile the game
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/game/icons/favicon.ico --output-dir=./build ./bitrot/editor.py # Compile the editor
```

Windows Defender may flag.

**MacOS**

```shell
# Nuitka
$ nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/game/icons/favicon.icns --output-dir=./build ./bitrot/bitrot.py # Compile the game
$ nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/game/icons/favicon.icns --output-dir=./build ./bitrot/editor.py # Compile the editor
```

After finish, open a terminal and type: `xattr -cr bitrot.app`

**Android**

```shell
$ buildozer -v android debug # Build APK to ./bin/
$ buildozer -v android debug deploy run logcat -s "python" # Send the APK to Device and get the full log
```