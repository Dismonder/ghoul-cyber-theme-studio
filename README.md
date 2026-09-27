# Ghoul Cyber – Theme Studio

**🇬🇧 English** | [🇵🇱 Polski](README.pl.md)

> **Build your own rEFInd boot screen in a few minutes: pick one of 18 themes, tune it with a live preview, then build or install it with one click — on Linux and Windows.**

[![Latest release](https://img.shields.io/github/v/release/Dismonder/ghoul-cyber-theme-studio?style=for-the-badge&logo=github&label=Release)](https://github.com/Dismonder/ghoul-cyber-theme-studio/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Dismonder/ghoul-cyber-theme-studio/total?style=for-the-badge&label=Downloads)](https://github.com/Dismonder/ghoul-cyber-theme-studio/releases)
[![Theme engine](https://img.shields.io/badge/Engine-Ghoul%20Cyber%20rEFInd%20theme-FF003C?style=for-the-badge&logo=github)](https://github.com/Dismonder/refind-theme-ghoul-cyber)
[![License](https://img.shields.io/badge/License-GCPL--1.0-orange?style=for-the-badge)](LICENSE)

![Linux](https://img.shields.io/badge/Linux-any%20major%20distro-FCC624?style=flat-square&logo=linux&logoColor=black)
![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6?style=flat-square&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-English%20%7C%20Polski-555?style=flat-square)

![Theme Studio](docs/screenshot-en.png)

---

## ☕ Support the Author

If Theme Studio saved you an evening of editing `refind.conf` by hand, or you simply like how your boot screen looks now — you can buy me a virtual coffee:

[![Buy me a coffee on BuyCoffee.to](https://img.shields.io/badge/BuyCoffee.to-Buy%20a%20coffee%20(BLIK)-37AC49?style=for-the-badge&logo=buy-me-a-coffee&logoColor=white)](https://buycoffee.to/dismonder)
[![Support on Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/dismonder)
[![Become a Patron on Patronite](https://img.shields.io/badge/Patronite-Become%20a%20Patron-EC1D24?style=for-the-badge)](https://patronite.pl/Dismonder)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-Dismonder-EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/Dismonder)

- 🌍 **[Ko-fi.com/dismonder](https://ko-fi.com/dismonder)** – international support (PayPal / cards, 0% platform fee).
- 🐙 **[GitHub Sponsors (Dismonder)](https://github.com/sponsors/Dismonder)** – GitHub's own sponsorship program.
- 🇵🇱 **[BuyCoffee.to/dismonder](https://buycoffee.to/dismonder)** – quick coffee in PLN (BLIK, card, Apple Pay / Google Pay).
- 🏆 **[Patronite.pl/Dismonder](https://patronite.pl/Dismonder)** – monthly patronage / subscription.

---

## ⬇️ Download and run

Get **`ghoul-cyber-theme-studio-<version>.zip`** from **[Releases](https://github.com/Dismonder/ghoul-cyber-theme-studio/releases/latest)** — it already contains the theme engine and all 18 themes.

| System | Start |
| :--- | :--- |
| **Windows 10 / 11** | Install [Python 3](https://www.python.org/downloads/) (tick *Add to PATH*), then double-click **`ThemeStudio.bat`** — Pillow is installed on first start. |
| **Linux** | `./theme-studio.sh` — needs Python 3 and Tk (`sudo pacman -S tk` · `sudo apt install python3-tk` · `sudo dnf install python3-tkinter` · `sudo zypper install python3-tk`). Everything else is installed automatically. |

From git (the engine is a submodule, so clone recursively):

```bash
git clone --recursive https://github.com/Dismonder/ghoul-cyber-theme-studio.git
cd ghoul-cyber-theme-studio
python3 theme_studio.py
```

---

## ✨ Features

| | |
| :--- | :--- |
| 🎨 **18 themes** | The original Ghoul Cyber plus 17 alternative OLED themes, each with its own artwork, OS cards and accent colour. |
| 👀 **Live preview** | The final rEFInd screen redraws a moment after every change — tiles, tools row, HUD, numbering, arrows. |
| 🧩 **Every option as a form** | Resolution, tile sizes, how many system tiles are visible at once, scroll arrows, HUD texts and hardware rows, tile numbers and their order, tools in the bottom row, timeout, default system, your own menu entries. Explanations under every field. |
| 🛠️ **Build or install in one click** | **BUILD** makes the package, **BUILD & INSTALL** puts it straight into rEFInd, **dry run** only shows what would happen. Live log; the installer's questions are answered right in the app. |
| 🐧 **Any major Linux** | pacman, apt, dnf, zypper, xbps, apk. Asks for your sudo password in its own window, installs what is missing — **even rEFInd itself** — and adds EFI Shell and MemTest86+ to the tools row. |
| 🪟 **Windows** | Asks for administrator rights (UAC), finds the EFI partition that really holds rEFInd, gives it a temporary drive letter and removes it afterwards. |
| 🛡️ **Fail-safe** | Invalid values are shown in red and block building, the last valid settings are never overwritten, any failure while installing rolls every file back and `refind.conf` keeps a timestamped `.bak`. |
| 🌍 **English / Polski** | Follows your system language; switch with **PL \| EN** in the top-right corner (`GHOUL_LANG=en` / `pl` to force it). |
| 💾 **Share a look** | Settings save automatically; **Import / Export** shares a whole setup as one file. |

### The result — the real rEFInd

Installed by Theme Studio, photographed in a UEFI virtual machine: your systems numbered, nine working tools with one shared frame, scroll arrows when not every system fits.

![rEFInd with a Theme Studio theme](docs/refind-result.png)

---

## 👤 Author & Signature

- **Author / Creator:** **Dismonder**
- **Theme engine:** [Dismonder/refind-theme-ghoul-cyber](https://github.com/Dismonder/refind-theme-ghoul-cyber)
- **Releases:** [Releases](https://github.com/Dismonder/ghoul-cyber-theme-studio/releases)
- **Copyright:** © 2026 Dismonder. All Rights Reserved.
- **License:** [Ghoul Cyber Protective License (GCPL-1.0)](LICENSE)

---

## 📜 License Summary

Theme Studio is part of the Ghoul Cyber project and is covered by the same protective license, **GCPL-1.0 (Ghoul Cyber Protective License)**:

✅ **You MAY:**
- Download, install and use Theme Studio free of charge on your own devices.
- Modify the files and settings for your own private use.

❌ **You may NOT:**
- **REDISTRIBUTE IT UNDER YOUR OWN NAME:** publishing, sharing or re-uploading it under your own name, initials, nickname or brand, or presenting it as your own work, is strictly prohibited.
- **REMOVE THE AUTHOR'S DETAILS:** removing or obscuring the `Dismonder` signature, copyright notices or the license file is prohibited.
- **USE IT COMMERCIALLY:** selling it, charging for it, or bundling it into paid packages without the author's written permission is prohibited.

The full, legally binding license text in Polish and English is in the [LICENSE](LICENSE) file.

---

## 🔗 How it fits together

```
ghoul-cyber-theme-studio/        ← this repository (the app)
├── theme_studio.py              Theme Studio
├── studio_i18n.py               English / Polish texts
├── ThemeStudio.bat              Windows launcher
├── theme-studio.sh              Linux launcher
└── theme/                       git submodule → refind-theme-ghoul-cyber
    ├── build_and_deploy_theme.py   builder + installer (also usable from the command line)
    └── themes/                     the 17 alternative themes
```

The submodule is pinned to a tested version of the theme engine. Try the newest one with `git submodule update --remote theme`.

---

## 🎭 Fan art

17 of the 18 themes are unofficial, non-commercial fan art inspired by popular anime and games — not affiliated with or endorsed by their creators or rights holders; all characters and trademarks belong to their owners. Theme Studio marks them as *FAN ART*. Rights holders can request removal through an issue — see [`FAN-ART.md`](https://github.com/Dismonder/refind-theme-ghoul-cyber/blob/main/themes/FAN-ART.md).

---

## 🧪 Tests

```bash
python3 -m pytest tests                       # Linux without a display: xvfb-run -a python3 -m pytest tests
FUZZ_ROUNDS=200 python3 -m pytest tests       # heavier random-input run (replay with FUZZ_SEED=…)
```

Every release is built by GitHub Actions: tests, then the ready-to-run archive with `SHA256SUMS.txt`.
