# 👁️ Ghoul Cyber — Theme Studio

**🇬🇧 English** | [🇵🇱 Polski](README.pl.md)

Build your own **rEFInd** boot screen in a few minutes: pick a theme, tune it with a **live preview**, then build or install it with one click. Theme Studio is the app for the [**Ghoul Cyber rEFInd theme**](https://github.com/Dismonder/refind-theme-ghoul-cyber) — 18 OLED themes, a builder that draws your screen for your own PC and an installer that works on any major Linux and on Windows.

![Theme Studio](docs/screenshot-en.png)

---

## ⬇️ Download and run

Get **`ghoul-cyber-theme-studio-<version>.zip`** from [Releases](https://github.com/Dismonder/ghoul-cyber-theme-studio/releases/latest) — it already contains the theme engine and all themes.

| System | Start |
| :--- | :--- |
| **Windows** | Install [Python 3](https://www.python.org/downloads/) (tick *Add to PATH*), then double-click **`ThemeStudio.bat`** — Pillow is installed on first start. |
| **Linux** | `./theme-studio.sh` — needs Python 3 and Tk (`sudo pacman -S tk` · `sudo apt install python3-tk` · `sudo dnf install python3-tkinter` · `sudo zypper install python3-tk`). Missing packages for building are installed automatically. |

From git (the engine is a submodule):

```bash
git clone --recursive https://github.com/Dismonder/ghoul-cyber-theme-studio.git
cd ghoul-cyber-theme-studio
python3 theme_studio.py
```

---

## ✨ What it does

- **Themes** on the left, a live preview of the final rEFInd screen on the right (it redraws a moment after every change).
- **Install** tab: **BUILD** (package in `theme/dist/ghoul-cyber`) or **BUILD & INSTALL** (straight into rEFInd), plus a **dry run** that only shows what would happen. Live log; questions from the installer are answered in the field under the log.
  - **Linux:** asks for your sudo password in its own dialog; installs missing packages with your package manager and even **installs rEFInd** if you don't have it yet.
  - **Windows:** asks for administrator rights (UAC), finds the EFI partition that really holds rEFInd, gives it a temporary drive letter and removes it afterwards.
- **Layout / Elements / Behaviour / Menu entries** tabs — every option of the theme as a form with explanations: resolution, tile sizes, how many system tiles are visible, scroll arrows, HUD texts and rows, tile numbers and their order, tools in the bottom row, timeout, default system, your own menu entries…
- **Fail-safe:** invalid values are shown in red and block building, the last valid settings are never overwritten, and any failure while installing rolls every file back (`refind.conf` also keeps a timestamped `.bak`).
- Settings are saved automatically; **Import / Export** shares a whole look as one file.
- **Language:** English, or Polish when your system is in Polish — switch with **PL | EN** in the top-right corner. Force it with `GHOUL_LANG=en` / `GHOUL_LANG=pl`.
- Without Tk it falls back to a text menu.

---

## 🔗 How it fits together

```
ghoul-cyber-theme-studio/        ← this repository (the app)
├── theme_studio.py              Theme Studio
├── studio_i18n.py               Polish / English texts
└── theme/                       git submodule → refind-theme-ghoul-cyber
    ├── build_and_deploy_theme.py   builder + installer (also usable from the command line)
    ├── themes/                     the 17 alternative themes
    └── …
```

The submodule is pinned to a tested version of the theme. To try the newest theme engine: `git submodule update --remote theme`.

---

## 🎭 Fan art

17 of the 18 themes are unofficial, non-commercial fan art inspired by popular anime and games — not affiliated with or endorsed by their creators or rights holders; all characters and trademarks belong to their owners. Theme Studio marks them as *FAN ART*. See [`theme/themes/FAN-ART.md`](https://github.com/Dismonder/refind-theme-ghoul-cyber/blob/main/themes/FAN-ART.md).

## 📜 License

**GHOUL CYBER PROTECTIVE LICENSE (GCPL-1.0)** — © 2026 Dismonder. Free for personal use; the author's name and signature must stay intact. Full text in [LICENSE](LICENSE).
