<p align="center">
  <img src="https://raw.githubusercontent.com/gustavokuklinski/bit-rot/refs/heads/main/bitrot/data.rot/icons/logo.png" alt="Bit Rot Logo" width="400"><br /><br />

  <img src="https://img.shields.io/badge/license-BSD%203%20Clause-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Platform">
</p>

# 🧟 Bit Rot

**Bit Rot** is a zombie survivor game where you fight, survive, and navigate through a post-apocalyptic island overrun by the undead.

---

## 📖 Table of Contents
- [📋 Minimum Requirements](#-minimum-requirements)
- [🎮 Controls and Keybinds](#-controls-and-keybinds)
- [🚀 Using the Rot Engine](#-using-the-rot-engine)
  - [Interactive Mode (TUI)](#interactive-mode-tui)
  - [Command Line Mode (CLI)](#command-line-mode-cli)
- [🛠️ Manual Installation](#-manual-installation-virtual-environment)
- [📦 Building Executables](#-building-executables)
- [🔑 Windows Signing and Certificates](#-windows-signing-and-certificates)
- [☁️ Cloud Builds (GitHub Actions)](#-cloud-builds-github-actions)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [🔐 Security](#-security)
- [👤 Code of Conduct](#-code-of-conduct)
- [📬 Contact](#-contact)

---

## 📋 Minimum Requirements

Before diving in, ensure your system meets the following minimum specifications:

| Component | Minimum Specification |
| :--- | :--- |
| **RAM** | 1 GB |
| **Processor** | Intel Core i3 or Apple Silicon M-series |
| **Video** | Intel HD Graphics 3000 |
| **OS** | Ubuntu/Debian, Windows 7, or macOS |
| **Software** | git, python3.11 |
| **Resolution** | 1280x720 |
| **Disk Space** | 500 MB |

---

## 🎮 Controls and Keybinds

| Action               | Keyboard / Mouse      | Joystick (Xbox-style) | Joystick Compatible |
| :------------------- | :-------------------- | :-------------------- | :-----------------: |
| **Move Up**          | `W`                   | `D-Pad Up`            | ✅                   |
| **Move Down**        | `S`                   | `D-Pad Down`          | ✅                   |
| **Move Left**        | `A`                   | `D-Pad Left`          | ✅                   |
| **Move Right**       | `D`                   | `D-Pad Right`         | ✅                   |
| **Run**              | `Left Shift`          | `B Button`            | ✅                   |
| **Interact**         | `E`                   | `A Button`            | ✅                   |
| **Reload**           | `R`                   | `X Button`            | ✅                   |
| **Vehicle Engine**   | `Q`                   | `Y Button`            | ✅                   |
| **Shove**            | `Space`               | `LB (Left Bumper)`    | ✅                   |
| **Pause**            | `F2/Esc`              | `Start`               | ✅                   |
| **Toggle Modals**    | `Tab`                 | `RB (Right Bumper)`   | ✅                   |
| **Reset Modals**     | `F4`                  | `Back`                | ✅                   |
| **Shoot**            | `Left Click`          | `RT (Right Trigger)`  | ✅                   |
| **Aim Trigger**      | `Right Click/Control` | `LT (Left Trigger)`   | ✅                   |
| **Fullscreen**       | `F11`                 | —                     | ❌                   |
| **Chat**             | `T`                   | —                     | ❌                   |
| **Toggle Inventory** | `I`                   | —                     | ❌                   |
| **Toggle Crafting**  | `C`                   | —                     | ❌                   |
| **Toggle Status**    | `H`                   | —                     | ❌                   |
| **Toggle Gear**      | `G`                   | —                     | ❌                   |
| **Toggle Nearby**    | `N`                   | —                     | ❌                   |
| **Toggle Messages**  | `M`                   | —                     | ❌                   |
| **Toggle Slots**     | `Y`                   | —                     | ❌                   |


*Controllers can be edited `data.rot/save/config/keybinds.xml` XML file*

---

## 🚀 Using the Rot Engine

The **Rot Engine** scripts (`BITROT.sh` and `BITROT.bat`) are the primary control centers for the project. They act as wrappers for the specialized scripts located in the `./scripts/` directory.

### 🏁 Getting Started
**Linux / macOS:**
```bash
$ chmod +x BITROT.sh scripts/*.sh
$ ./BITROT.sh
```

**Windows:**
Simply double-click `BITROT.bat` or run it via CMD:
```cmd
C:\bit-rot\> BITROT.bat
```

### 🕹️ Interactive Mode (TUI)
If you run the scripts without any arguments, you will enter the **Interactive ASCII Menu**:
1. **Play BitRot**: Launches the game.
2. **Editor**: Launches the level editor.
3. **Clean Project**: Deletes cache, build folders, or resets `data.rot`.
4. **Build Executable**: Automates the Nuitka compilation and signing process.

### ⌨️ Command Line Mode (CLI)
| Command | Description | Linux/Mac | Windows |
| :--- | :--- | :--- | :--- |
| `shell` | Launches the game | `./BITROT.sh shell` | `BITROT.bat shell` |
| `shell --editor` | Launches the editor | `./BITROT.sh shell --editor` | `BITROT.bat shell --editor` |
| `clean` | Cleans project files | `./BITROT.sh clean --full` | `BITROT.bat clean --full` |
| `build` | Compiles the game | `./BITROT.sh build --linux` / `--macos` | `BITROT.bat build --windows` |

---

## 🛠️ Manual Installation (Virtual Environment)

If you prefer to set things up manually for development:

### 1. Create and activate a virtual environment
```bash
$ python3 -m venv .venv
$ source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
$ pip install -r requirements.txt
```

---

## 📦 Building Executables

We use [Nuitka](https://nuitka.net/) to compile Python code into machine-code executables for maximum performance.

### ⚡ Automatic Build (Recommended)
The easiest way to build is using the Rot Engine wrappers. These scripts handle dependencies, icons, and signing automatically.

- **Windows**: `BITROT.bat build --windows` (triggers `./scripts/build.bat`)
- **macOS**: `./BITROT.sh build --macos` (triggers `./scripts/build.sh`)
- **Linux (Standalone)**: `./BITROT.sh build --linux` (triggers `./scripts/build.sh`)

#### 🐧 Generating a Linux AppImage
For a truly portable "single-file" experience on Linux, you can build an **AppImage**. This packages the standalone build into a read-only filesystem that runs on most distributions.

**1. Install `appimagetool`:**
```bash
$ wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool
$ chmod +x appimagetool
$ sudo mv appimagetool /usr/local/bin/
```

**2. Build the AppImage:**
```bash
./BITROT.sh build --appimage
```
*This will create a `.AppImage` file in the project root that can be shared and executed immediately.*

---

### 🛠️ Manual Build (Raw Commands)
If you prefer to run the compilation manually or customize the build flags, use the following commands. Ensure you have `nuitka` installed via pip.

#### 🐧 Linux
```bash
# Build the game as a standalone directory
$ nuitka --standalone --include-data-dir=./bitrot/data.rot=data.rot --output-dir=./build ./bitrot/bitrot.py

# Build the editor as a standalone directory
$ nuitka --standalone --include-data-dir=./bitrot/data.rot=data.rot --output-dir=./build ./bitrot/editor.py
```

#### 🪟 Windows
```bash
# Build the game with a custom icon and no console window
$ nuitka --standalone --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --output-dir=./build ./bitrot/bitrot.py

# Build the editor with a custom icon and no console window
$ nuitka --standalone --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --output-dir=./build ./bitrot/editor.py
```

#### 🍎 macOS
```bash
# Build the game as an application bundle
$ nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/bitrot.py

# Build the editor as an application bundle
$ nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/editor.py
```

*This process will create a `build/` directory containing the standalone executable and all required dependencies.*

---

## 🔑 Windows Signing and Certificates

Windows Defender often flags unsigned Python executables as "Trojan" or "Unknown Malware." To prevent this, Bit Rot binaries are digitally signed.

### 🛠️ Local Signing Requirements
To build and sign binaries locally on Windows, you must have the **Windows SDK** installed (specifically `signtool.exe`).

### ⚙️ How the Process Works
When you run `BITROT.bat build --windows` (which executes `./scripts/build.bat`), the engine performs these steps automatically:
1. **Certificate Generation**: It runs `python bitrot/tools/windows_certificate.py cert.pfx` to create a local self-signed certificate.
2. **Compilation**: Nuitka compiles the `.py` files into `.exe`.
3. **Binary Signing**: The engine locates `signtool.exe` (x64) and signs the binaries using the generated `.pfx` certificate and a secure password.

**Manual Signing Command (Example):**
```cmd
signtool sign /f cert.pfx /p "bitrot&Certificate@Windows912026" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "build\bitrot.dist\bitrot.exe"
```

---

## ☁️ Cloud Builds (GitHub Actions)

If you don't have the Windows SDK or Nuitka installed locally, you can use our **GitHub Actions Pipeline** to build the project in the cloud.

### 🚀 How to trigger a build:
1. Go to the **Actions** tab in this GitHub repository.
2. Select the **"Build Project"** workflow from the left sidebar.
3. Click the **"Run workflow"** dropdown.
4. Select your target platform (Windows, Linux, or macOS).
5. Click **Run workflow**.

### 📦 Downloading the Build:
Once the process is complete, GitHub will upload the compiled binaries as **Artifacts**. You can find them at the bottom of the specific Action run summary.

**Note for Maintainers:** The GitHub Action uses **Repository Secrets** to store the certificate password and signing keys, ensuring that the public releases are signed without exposing sensitive passwords in the code.

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