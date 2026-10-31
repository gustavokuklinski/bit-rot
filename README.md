<p align="center">
  <img src="https://raw.githubusercontent.com/gustavokuklinski/bit-rot/refs/heads/main/bitrot/data.rot/icons/logo.png" alt="Bit Rot Logo" width="400">
</p>

<p align="center">
    <a href="https://github.com/gustavokuklinski/bit-rot/stargazers"><img src="https://img.shields.io/github/stars/gustavokuklinski/bit-rot?style=flat-square&color=f59e0b&label=Stars" alt="GitHub stars" /></a>
    <a href="https://github.com/gustavokuklinski/bit-rot/releases/"><img src="https://img.shields.io/github/downloads/gustavokuklinski/bit-rot/total?style=flat-square&color=8b5cf6&label=Downloads" alt="Total downloads" /></a>
    <a href="https://github.com/gustavokuklinski/bit-rot/releases/latest"><img src="https://img.shields.io/github/v/tag/gustavokuklinski/bit-rot?&style=flat-square&color=10b981&label=Build" alt="Tag release" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache 2.0-blue?style=flat-square" alt="ISC license" /></a><br />
    <a href="https://discord.gg/JC9hMgh3nF"><img src="https://img.shields.io/badge/Discord-%235865F2.svg?&logo=discord&style=flat-square&logoColor=white&label=Community" alt="Discord community" /></a>
    <a href="https://gustavokuklinski.itch.io/bit-rot/purchase"><img src="https://img.shields.io/badge/itch.io-%23FF0B34.svg?logo=Itch.io&style=flat-square&label=Download&logoColor=white" alt="Download Bit Rot" /></a>
</p>

<p align="center">
  <b>Support the Game</b><br />
  <a href='https://ko-fi.com/I2I61MH19A' target='_blank'><img src='https://shields.io/badge/ko--fi-Donate-ff5f5f?logo=ko-fi&style=for-the-badge' alt='Buy Me a Coffee at ko-fi.com' /></a>
  <a href='https://www.paypal.com/donate/?hosted_button_id=2LJ6J5V9XLBKQ' target='_blank'><img src='https://shields.io/badge/paypal-donate-blue?logo=paypal&style=for-the-badge' alt='PayPal Donation' /></a>
  <a href='https://etherscan.io/address/0x1c03c13e6Ea32d3Db9F9ABDeE610779D1547F92A' target='_blank'><img src='https://img.shields.io/badge/Ethereum-Donate-blue?style=for-the-badge&logo=ethereum' alt='Donate Ethereum' /></a>
  <br />
  <small><i>Donations will help to make the project reach Steam. All donors will get a Steam Key of the game.</i></small>
</p>

# Bit Rot

**Bit Rot** is a zombie survivor game where you fight, survive, and navigate through a post-apocalyptic island overrun by the undead.

---

## 📖 Table of Contents
- [Minimum Requirements](#minimum-requirements)
- [Controls and Keybinds](#controls-and-keybinds)
- [Install and Play](#install-and-play)
- [Building Executables](#building-executables)
- [Windows Signing and Certificates](#windows-signing-and-certificates)
- [Cloud Builds](#cloud-builds)
- [Contact](#contact)

---

## Minimum Requirements

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

## Controls and Keybinds

| Action               | Keyboard / Mouse      | Joystick (Xbox-style) | Joystick Compatible |
| :------------------- | :-------------------- | :-------------------- | :-----------------: |
| **Move Up**          | `W`                   | `D-Pad Up`            | ✓                   |
| **Move Down**        | `S`                   | `D-Pad Down`          | ✓                   |
| **Move Left**        | `A`                   | `D-Pad Left`          | ✓                   |
| **Move Right**       | `D`                   | `D-Pad Right`         | ✓                   |
| **Run**              | `Left Shift`          | `B Button`            | ✓                   |
| **Interact**         | `E`                   | `A Button`            | ✓                   |
| **Reload**           | `R`                   | `X Button`            | ✓                   |
| **Vehicle Engine**   | `Q`                   | `Y Button`            | ✓                   |
| **Shove**            | `Space`               | `LB (Left Bumper)`    | ✓                   |
| **Shoot**            | `Left Click`          | `RT (Right Trigger)`  | ✓                   |
| **Aim Trigger**      | `Right Click/Control` | `LT (Left Trigger)`   | ✓                   |

---

| Modals               | Keyboard / Mouse      | Joystick (Xbox-style) | Joystick Compatible |
| :------------------- | :-------------------- | :-------------------- | :-----------------: |
| **Toggle Modals**    | `Tab`                 | `RB (Right Bumper)`   | ✓                   |
| **Open Chat**        | `T`                   | —                     | —                   |
| **Toggle Crafting**  | `C`                   | —                     | —                   |
| **Toggle Help**      | `F1`                  | —                     | —                   |
| **Pause and Save**   | `F2/Esc`              | `Start`               | ✓                   |
| **Toggle UI Menus**  | `F3`                  | `Back`                | ✓                   |
| **Reset Modals**     | `F4`                  | `Back`                | ✓                   |
| **Toggle Status**    | `F5`                  | —                     | —                   |
| **Toggle Inventory** | `F6`                  | —                     | —                   |
| **Toggle Gear**      | `F7`                  | —                     | —                   |
| **Toggle Nearby**    | `F8`                  | —                     | —                   |
| **Toggle Slots**     | `F9`                  | —                     | —                   |
| **Toggle Messages**  | `F10`                 | —                     | —                   |
| **Fullscreen**       | `F11`                 | —                     | —                   |


*Controllers can be edited `data.rot/save/config/keybinds.xml` XML file*

---

## Install and Play

Prepare development:

### 1. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Play
```bash
python bitrot/bitrot.py
```

---

## Building Executables

We use [Nuitka](https://nuitka.net/) to compile Python code into machine-code executables for maximum performance.

---

### Manual Build (Raw Commands)
If you prefer to run the compilation manually or customize the build flags, use the following commands. Ensure you have `nuitka` installed via pip.

#### Linux
```bash
# Build the game as a standalone directory
nuitka --onefile --assume-yes-for-downloads --output-dir=./build --output-filename=bitrot.bin --static-libpython=yes --include-data-dir=bitrot/data.rot=data.rot bitrot/bitrot.py

# Build the editor as a standalone directory
nuitka --onefile --assume-yes-for-downloads --output-dir=./build --output-filename=bitrot.bin --static-libpython=yes --include-data-dir=bitrot/data.rot=data.rot bitrot/editor.py
```

#### Windows
```bash
# Build the game with a custom icon and no console window
nuitka --onefile --assume-yes-for-downloads --output-dir=./build --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --include-data-dir=./bitrot/data.rot=data.rot bitrot/bitrot.py

# Build the editor with a custom icon and no console window
nuitka --onefile --assume-yes-for-downloads --output-dir=./build --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --include-data-dir=./bitrot/data.rot=data.rot bitrot/editor.py
```

#### macOS
```bash
# Build the game as an application bundle
nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/bitrot.py

# Build the editor as an application bundle
nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --output-dir=./build ./bitrot/editor.py
```

*This process will create a `build/` directory containing the standalone executable and all required dependencies.*

---

## Windows Signing and Certificates

Windows Defender often flags unsigned Python executables as "Trojan" or "Unknown Malware." To prevent this, Bit Rot binaries are digitally signed.

### Local Signing Requirements
To build and sign binaries locally on Windows, you must have the **Windows SDK** installed (specifically `signtool.exe`).

**Signing Command:**
```cmd
signtool sign /f cert.pfx /p "bitrot&Certificate@Windows912026" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "build\bitrot.dist\bitrot.exe"
```

---

## Cache cleaner (`__pycache__`)

Cache cleanup for Linux

```bash
find ./bitrot -type d -name "__pycache__" -exec rm -rf {} +
```

## Cloud Builds

If you don't have the Windows SDK or Nuitka installed locally, you can use our **GitHub Actions Pipeline** to build the project in the cloud.

### How to trigger a build:
1. Go to the **Actions** tab in this GitHub repository.
2. Select the **"Build Project"** workflow from the left sidebar.
3. Click the **"Run workflow"** dropdown.
4. Select your target platform (Windows, Linux, or macOS).
5. Click **Run workflow**.

| Linux | MacOS | Windows |
| :--- | :--- | :--- |
| <a href="https://github.com/gustavokuklinski/bit-rot/actions/workflows/bitrot-linux.yml"><img src="https://img.shields.io/github/actions/workflow/status/gustavokuklinski/bit-rot/bitrot-linux.yml?branch=main&style=flat-square&label=Linux" alt="GH Action" /></a> | <a href="https://github.com/gustavokuklinski/bit-rot/actions/workflows/bitrot-macos.yml"><img src="https://img.shields.io/github/actions/workflow/status/gustavokuklinski/bit-rot/bitrot-macos.yml?branch=main&style=flat-square&label=MacOS" alt="GH Action" /></a> | <a href="https://github.com/gustavokuklinski/bit-rot/actions/workflows/bitrot-windows.yml"><img src="https://img.shields.io/github/actions/workflow/status/gustavokuklinski/bit-rot/bitrot-windows.yml?branch=main&style=flat-square&label=Windows" alt="GH Action" /></a> |

### Downloading the Build:
Once the process is complete, GitHub will upload the compiled binaries as **Artifacts**. You can find them at the bottom of the specific Action run summary.

**Note for Maintainers:** The GitHub Action uses **Repository Secrets** to store the certificate password and signing keys, ensuring that the public releases are signed without exposing sensitive passwords in the code.

---

## Contact

The best way to reach us is through [GitHub Discussions](https://github.com/gustavokuklinski/bit-rot/discussions) or [Discord](https://discord.gg/SK4s7V6mEZ).

---
**Survive. Adapt. Fight the Rot.**