<p align="center">
  <img src="https://raw.githubusercontent.com/gustavokuklinski/bit-rot/refs/heads/main/bitrot/data.rot/icons/logo.png" alt="Bit Rot Logo" width="400"><br /><br />

  <img src="https://img.shields.io/badge/license-BSD%203%20Clause-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platform">
</p>

# 🧟 Bit Rot

**Bit Rot** is a zombie survivor game where you fight, survive, and navigate through a post-apocalyptic island overrun by the undead.

---

## 📋 Minimum Requirements

Before diving in, ensure your system meets the following minimum specifications:

| Component | Minimum Specification |
| :--- | :--- |
| **RAM** | 1 GB |
| **Processor** | Intel Core i3 or Apple Silicon M-series |
| **Video** | Intel HD Graphics 3000 |
| **OS** | Ubuntu/Debian, Windows 7, or macOS |
| **Software** | Python 3.14 |
| **Resolution** | 1280x720 |
| **Disk Space** | 500 MB |

---

## 🚀 Quick Start with Rot Engine Scripts

For the fastest setup, use the included engine scripts:

**Linux / Mac**

```bash
# Pre-install: Set execute permissions for all scripts
$ chmod +x BITROT.sh scripts/*.sh

# Launch the game engine
$ ./BITROT.sh

# Launch the game
$ ./BITROT.sh shell
```

**Windows**

Double click on: `BITROT.bat`

```shell
# Open CMD or Powershell
C:\bit-rot\> BITROT.bat
```

---

## 🛠️ Manual Installation (Virtual Environment)

If you prefer to set things up manually, follow these steps:

### 1. Create and activate a virtual environment
```bash
$ python3 -m venv .venv
$ source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
$ pip install -r requirements.txt
```

### 3. Clean cache files (optional)
```bash
$ chmod +x scripts/clean.sh
$ ./clean.sh
```

---

## 🎮 Run Locally

Once installed, run the game or the editor:

```bash
# Play the game
$ python bitrot/bitrot.py

# Open the level editor
$ python bitrot/editor.py
```

---

## 📦 Building Executables

You can compile the game into standalone executables (`.bin`, `.exe`, or `.app`) using either Nuitka or PyInstaller.

### 🛠️ Option 1: Using Nuitka (Recommended for Performance)
Compile the game using [Nuitka](https://nuitka.net/).

#### 🐧 Linux
```bash
# Build the game (packed into a single file)
$ nuitka --onefile --include-data-dir=./bitrot/game=game ./bitrot/bitrot.py

# Build the editor (packed into a single file)
$ nuitka --onefile --include-data-dir=./bitrot/game=game ./bitrot/editor.py

# Alternative: Output build artifacts to a specific directory
$ nuitka --onefile --output-dir=./build ./bitrot/bitrot.py
$ nuitka --onefile --output-dir=./build ./bitrot/editor.py
```

#### 🪟 Windows
```bash
# Build the game with a custom icon and no console window
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --output-dir=./build ./bitrot/bitrot.py

# Build the editor with a custom icon and no console window
$ nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --output-dir=./build ./bitrot/editor.py
```

#### 🍎 macOS
```bash
# Build the game as an application bundle
$ nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/bitrot.py

# Build the editor as an application bundle
$ nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/editor.py
```

> **⚠️ Note:** Windows Defender may flag the executable as a false positive due to Nuitka's packaging method. This is normal—you can safely add an exception.

---

### 🛠️ Option 2: Using PyInstaller
If you prefer [PyInstaller](https://pyinstaller.org/), follow these steps. First, install the package:
```bash
$ pip install pyinstaller
```

#### 🐧 Linux & 🍎 macOS
```bash
# Build the game
$ pyinstaller --onefile --add-data "bitrot/game:game" bitrot/bitrot.py

# Build the editor
$ pyinstaller --onefile --add-data "bitrot/game:game" bitrot/editor.py
```

#### 🪟 Windows
```bash
# Build the game (no console, custom icon)
$ pyinstaller --onefile --noconsole --add-data "bitrot/game;game" --icon=./bitrot/data.rot/icons/favicon.ico bitrot/bitrot.py

# Build the editor (no console, custom icon)
$ pyinstaller --onefile --noconsole --add-data "bitrot/game;game" --icon=./bitrot/data.rot/icons/favicon.ico bitrot/editor.py
```

*Note: PyInstaller outputs the final executable in the `dist/` folder.*

---

## 🤝 Contributing

We welcome community contributions! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a Pull Request.

If you use Generative AI to assist with your code, remember to include the mandatory **AI tags** (e.g., `[DeepSeek-R1] [Code]`) in your PR description.

---

## 📄 License

This project is released under a **source-available license** with **All Rights Reserved**. You may fork it and submit Pull Requests, but you **may not** re-upload, redistribute, or claim the code as your own. See the [LICENSE](LICENSE) file for full details.

---

## 🔐 Security

For security concerns or vulnerability reports, please review our [Security Policy](SECURITY.md). **We are not responsible for broken code or damage on any machine**—use this software at your own risk.

---

## 👤 Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By interacting with the community, you agree to abide by its terms.

---

## 📬 Contact

The best way to reach us is through [GitHub Issues](https://github.com/gustavokuklinski/bit-rot/issues) or [Discord](https://discord.gg/SK4s7V6mEZ).

---

**Survive. Adapt. Fight the Rot. 🧟**