"""Theme Studio translations (Polish / English) and language detection.

Author: Dismonder
Copyright: (c) 2026 Dismonder. All rights reserved.
License: Ghoul Cyber Protective License (GCPL-1.0) - see LICENSE

Polish is used only when the system UI language is Polish; everything else
gets English. GHOUL_LANG=pl|en overrides both the detection and the choice
saved from the PL | EN switch (studio-settings.json next to this file).
"""

from __future__ import annotations

import json
import locale
import os
import sys
import tempfile
import warnings
from pathlib import Path

LANGUAGES = ("pl", "en")
DEFAULT_LANGUAGE = "en"
SETTINGS_PATH = Path(__file__).resolve().parent / "studio-settings.json"


# ---- detection ---------------------------------------------------------
def _is_polish(value: str) -> bool:
    value = value.strip().lower()
    return value.startswith("pl") or value.startswith("polish")


def _windows_ui_language() -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError, ValueError):
        return None
    if not langid:
        return None
    return "pl" if langid & 0x3FF == 0x15 else "en"


def _locale_language() -> str | None:
    candidates = []
    try:
        candidates.append(locale.getlocale()[0])
    except (ValueError, TypeError, AttributeError):
        pass
    getdefaultlocale = getattr(locale, "getdefaultlocale", None)  # deprecated, gone in newer Pythons
    if getdefaultlocale is not None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                candidates.append(getdefaultlocale()[0])
        except (ValueError, TypeError, AttributeError):
            pass
    for name in candidates:
        if name:
            return "pl" if _is_polish(name) else "en"
    return None


def detect_language() -> str:
    """'pl' when the system UI language is Polish, otherwise 'en'. Never raises."""
    try:
        override = os.environ.get("GHOUL_LANG", "").strip().lower()
        if override in LANGUAGES:
            return override
        for name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
            value = os.environ.get(name, "").strip()
            if value and value.split(".")[0].upper() not in {"C", "POSIX"}:
                return "pl" if _is_polish(value) else "en"
        return _windows_ui_language() or _locale_language() or DEFAULT_LANGUAGE
    except Exception:  # noqa: BLE001 - detection is best effort
        return DEFAULT_LANGUAGE


# ---- saved preference ----------------------------------------------------
def _read_settings() -> dict | None:
    try:
        if SETTINGS_PATH.stat().st_size > 64_000:
            return None
        data = json.loads(SETTINGS_PATH.read_bytes().decode("utf-8-sig"))
    except Exception:  # noqa: BLE001 - a broken settings file must never matter
        return None
    return data if isinstance(data, dict) else None


def load_language() -> str | None:
    """The language picked with the PL | EN switch, or None."""
    settings = _read_settings()
    value = settings.get("language") if settings else None
    return value if value in LANGUAGES else None


def save_language(lang: str) -> bool:
    """Remember the choice (atomic write). False if it could not be saved."""
    if lang not in LANGUAGES:
        return False
    settings = _read_settings() or {}
    settings["language"] = lang
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=".studio-settings-", suffix=".tmp", dir=SETTINGS_PATH.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(settings, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, SETTINGS_PATH)
        return True
    except OSError:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return False


def current_language() -> str:
    """GHOUL_LANG override, else the saved choice, else the detected language."""
    override = os.environ.get("GHOUL_LANG", "").strip().lower()
    if override in LANGUAGES:
        return override
    return load_language() or detect_language()


# ---- UI strings ----------------------------------------------------------
TEXT: dict[str, dict[str, str]] = {
    "pl": {
        "window.title": "Ghoul Cyber - Theme Studio",
        "header.mode_linux": "Linux: instalacja przez sudo",
        "header.mode_windows": "Windows: instalacja przez UAC",
        "header.lang_tip": "Język interfejsu",
        "lang.busy_title": "Theme Studio",
        "lang.busy": "Poczekaj, aż budowanie się zakończy (albo je przerwij), zanim zmienisz język.",
        "ui_error": "Wystąpił nieoczekiwany błąd, ale nic nie zostało zmienione:\n\n{exc}",
        "list.themes": "MOTYWY [{count}]",
        "tab.install": "Instalacja",
        "install.dry_run": "Próba na sucho (pokaż, co by się stało)",
        "install.build_install": "ZBUDUJ I ZAINSTALUJ",
        "install.build": "ZBUDUJ",
        "install.stop": "Przerwij",
        "install.hint": "Wybierz motyw, dopasuj ustawienia w zakładkach i kliknij przycisk.",
        "install.answer": "Odpowiedź dla instalatora >",
        "install.remove": "Usuń rEFInd",
        "settings.reset": "Przywróć domyślne",
        "settings.import": "Importuj…",
        "settings.export": "Eksportuj…",
        "field.enabled": "włączone",
        "field.pick_color": "Wybierz…",
        "field.from_theme": "Z motywu",
        "order.no_number": "(bez numeru)",
        "order.auto": "automatycznie (wg wpisów menu i wykrytych systemów)",
        "order.up": "▲ W górę",
        "order.down": "▼ W dół",
        "order.toggle": "Numer wł./wył.",
        "entries.col_label": "Nazwa",
        "entries.col_card": "Kafelek",
        "entries.col_loader": "Loader EFI",
        "entries.col_volume": "Wolumin",
        "entries.off": " (wył.)",
        "entries.add": "Dodaj wpis",
        "entries.edit": "Edytuj",
        "entries.remove": "Usuń",
        "entry.title": "Wpis menu rEFInd",
        "entry.label": "Nazwa w menu",
        "entry.label_hint": "np. Windows 11 Gaming",
        "entry.card": "Kafelek (ikona)",
        "entry.card_hint": "wygląd kafelka z motywu",
        "entry.loader": "Ścieżka loadera EFI",
        "entry.loader_hint": "np. \\EFI\\Microsoft\\Boot\\bootmgfw.efi",
        "entry.volume": "Wolumin (opcjonalnie)",
        "entry.volume_hint": "PARTUUID lub etykieta partycji; puste = ten sam dysk",
        "entry.options": "Opcje (opcjonalnie)",
        "entry.options_hint": "parametry dla jądra Linux, np. quiet splash",
        "entry.disabled": "Wyłączony (zostaje w pliku, nie pokazuje się)",
        "entry.error_title": "Wpis menu",
        "entry.cancel": "Anuluj",
        "entry.save": "Zapisz wpis",
        "form.invalid": "{key}: niepoprawna wartość",
        "config.errors": "{name}: {count} błędów, użyto domyślnych",
        "config.unreadable": "Nie wczytano {name}: {exc}",
        "config.saved": "✔ zapisano w {name}",
        "config.not_saved": "✖ nie zapisano: {exc}",
        "config.exported": "✔ wyeksportowano {name}",
        "reset.title": "Przywróć domyślne",
        "reset.question": "Przywrócić wszystkie ustawienia do domyślnych?",
        "file.settings": "Ustawienia",
        "file.export_name": "moj-bootloader.json",
        "import.title": "Import",
        "import.too_big": "plik jest za duży (ponad 1 MB)",
        "import.unreadable": "Nie można odczytać pliku:\n{exc}",
        "import.fixed": "Wczytano z poprawkami (błędne wartości zastąpiono domyślnymi):\n\n",
        "preview.rendering": "⟳ renderuję podgląd…",
        "preview.unavailable": "podgląd niedostępny: {error}",
        "status.fix_errors": "Popraw błędy w ustawieniach przed instalacją.",
        "status.start_failed": "Nie udało się uruchomić instalatora: {exc}",
        "status.building_install": "Buduję i instaluję motyw {name}... (4K trwa kilka minut)",
        "status.building": "Buduję motyw {name}... (4K trwa kilka minut)",
        "status.stopped": "Przerwano - nic nie zostało zmienione na partycji EFI.",
        "status.dry_run_done": "Próba na sucho zakończona - nic nie zostało zmienione.",
        "status.installed": "Gotowe. Motyw zainstalowany w rEFInd - zrestartuj komputer.",
        "status.built": "Gotowe. Motyw zbudowany w {path}.",
        "status.failed": "Błąd (kod {code}) - szczegóły w logu. Poprzednia konfiguracja rEFInd została zachowana.",
        "status.removing": "Usuwam rEFInd z menu rozruchu i partycji EFI...",
        "status.removed": "Gotowe. rEFInd usunięty - komputer uruchomi Windowsa bezpośrednio.",
        "status.secure_boot": "Secure Boot jest włączony - wyłącz go w BIOS-ie i kliknij ponownie ZBUDUJ I ZAINSTALUJ.",
        "remove.title": "Usuń rEFInd",
        "remove.question": ("Usunąć rEFInd zainstalowany przez Theme Studio (wpis w menu rozruchu, folder "
                            "EFI\\refind i motyw)? Windows będzie znów startował bezpośrednio."),
        "firmware.title": "Secure Boot",
        "firmware.question": ("rEFInd nie wystartuje przy włączonym Secure Boot. Jeśli komputer używa BitLockera, program już go wstrzymał.\n\n"
                              "Uruchomić teraz komputer ponownie prosto do ustawień BIOS/UEFI? "
                              "Zapisz najpierw otwarte pliki.\n\nTam ustaw Secure Boot na Disabled, zapisz "
                              "(zwykle F10) i po starcie Windowsa kliknij ponownie ZBUDUJ I ZAINSTALUJ."),
        "firmware.failed": ("Nie udało się uruchomić ponownie do BIOS-u:\n{exc}\n\nWejdź do BIOS-u ręcznie "
                            "(zwykle F2, F10, Del albo Esc zaraz po włączeniu)."),
        "log.stopped": "\n[przerwano]\n",
        "askpass.title": "Autoryzacja administratora",
        "askpass.prompt": "Hasło sudo:",
        "askpass.cancel": "Anuluj",
        "askpass.ok": "OK",
        "text.title": "Ghoul Cyber - wybór motywu (tryb tekstowy)",
        "text.advanced": "Ustawienia zaawansowane: edytuj {config} (sprawdź: python3 {builder} --check-config)",
        "text.prompt": "Numer motywu (p<numer> = podgląd, q = wyjście): ",
        "main.no_tkinter": "Brak tkinter - na CachyOS/Arch: sudo pacman -S tk  (uruchamiam tryb tekstowy)",
        "main.no_builder": "Nie można załadować instalatora ({exc}). Na CachyOS/Arch: sudo pacman -S python-pillow",
        "main.no_display": "Brak środowiska graficznego ({exc}) - tryb tekstowy.",
    },
    "en": {
        "window.title": "Ghoul Cyber - Theme Studio",
        "header.mode_linux": "Linux: installs via sudo",
        "header.mode_windows": "Windows: installs via UAC",
        "header.lang_tip": "Interface language",
        "lang.busy_title": "Theme Studio",
        "lang.busy": "Wait for the build to finish (or stop it) before switching the language.",
        "ui_error": "An unexpected error occurred, but nothing was changed:\n\n{exc}",
        "list.themes": "THEMES [{count}]",
        "tab.install": "Install",
        "install.dry_run": "Dry run (show what would happen)",
        "install.build_install": "BUILD AND INSTALL",
        "install.build": "BUILD",
        "install.stop": "Stop",
        "install.hint": "Pick a theme, adjust the settings in the tabs and click the button.",
        "install.answer": "Answer for the installer >",
        "install.remove": "Remove rEFInd",
        "settings.reset": "Restore defaults",
        "settings.import": "Import…",
        "settings.export": "Export…",
        "field.enabled": "enabled",
        "field.pick_color": "Pick…",
        "field.from_theme": "From theme",
        "order.no_number": "(no number)",
        "order.auto": "automatic (from menu entries and detected systems)",
        "order.up": "▲ Up",
        "order.down": "▼ Down",
        "order.toggle": "Number on/off",
        "entries.col_label": "Name",
        "entries.col_card": "Tile",
        "entries.col_loader": "EFI loader",
        "entries.col_volume": "Volume",
        "entries.off": " (off)",
        "entries.add": "Add entry",
        "entries.edit": "Edit",
        "entries.remove": "Remove",
        "entry.title": "rEFInd menu entry",
        "entry.label": "Menu name",
        "entry.label_hint": "e.g. Windows 11 Gaming",
        "entry.card": "Tile (icon)",
        "entry.card_hint": "tile artwork from the theme",
        "entry.loader": "EFI loader path",
        "entry.loader_hint": "e.g. \\EFI\\Microsoft\\Boot\\bootmgfw.efi",
        "entry.volume": "Volume (optional)",
        "entry.volume_hint": "PARTUUID or partition label; empty = same disk",
        "entry.options": "Options (optional)",
        "entry.options_hint": "Linux kernel parameters, e.g. quiet splash",
        "entry.disabled": "Disabled (kept in the file, not shown)",
        "entry.error_title": "Menu entry",
        "entry.cancel": "Cancel",
        "entry.save": "Save entry",
        "form.invalid": "{key}: invalid value",
        "config.errors": "{name}: {count} errors, defaults used",
        "config.unreadable": "Could not load {name}: {exc}",
        "config.saved": "✔ saved to {name}",
        "config.not_saved": "✖ not saved: {exc}",
        "config.exported": "✔ exported {name}",
        "reset.title": "Restore defaults",
        "reset.question": "Restore all settings to their defaults?",
        "file.settings": "Settings",
        "file.export_name": "my-bootloader.json",
        "import.title": "Import",
        "import.too_big": "the file is too large (over 1 MB)",
        "import.unreadable": "Cannot read the file:\n{exc}",
        "import.fixed": "Loaded with corrections (invalid values replaced with defaults):\n\n",
        "preview.rendering": "⟳ rendering preview…",
        "preview.unavailable": "preview unavailable: {error}",
        "status.fix_errors": "Fix the errors in the settings before installing.",
        "status.start_failed": "Could not start the installer: {exc}",
        "status.building_install": "Building and installing the {name} theme... (4K takes a few minutes)",
        "status.building": "Building the {name} theme... (4K takes a few minutes)",
        "status.stopped": "Stopped - nothing was changed on the EFI partition.",
        "status.dry_run_done": "Dry run finished - nothing was changed.",
        "status.installed": "Done. Theme installed in rEFInd - restart your computer.",
        "status.built": "Done. Theme built in {path}.",
        "status.failed": "Error (code {code}) - see the log for details. The previous rEFInd configuration was kept.",
        "status.removing": "Removing rEFInd from the boot menu and the EFI partition...",
        "status.removed": "Done. rEFInd removed - the PC starts Windows directly again.",
        "status.secure_boot": "Secure Boot is on - turn it off in the BIOS and click BUILD AND INSTALL again.",
        "remove.title": "Remove rEFInd",
        "remove.question": ("Remove the rEFInd that Theme Studio installed (boot menu entry, the "
                            "EFI\\refind folder and the theme)? Windows will start directly again."),
        "firmware.title": "Secure Boot",
        "firmware.question": ("rEFInd will not start while Secure Boot is on. If this PC uses BitLocker, it has already been paused.\n\n"
                              "Restart now straight into the BIOS/UEFI settings? Save your open files first.\n\n"
                              "There set Secure Boot to Disabled, save (usually F10) and once Windows is back "
                              "click BUILD AND INSTALL again."),
        "firmware.failed": ("Could not restart into the BIOS:\n{exc}\n\nOpen the BIOS yourself "
                            "(usually F2, F10, Del or Esc right after power-on)."),
        "log.stopped": "\n[stopped]\n",
        "askpass.title": "Administrator authorization",
        "askpass.prompt": "sudo password:",
        "askpass.cancel": "Cancel",
        "askpass.ok": "OK",
        "text.title": "Ghoul Cyber - theme picker (text mode)",
        "text.advanced": "Advanced settings: edit {config} (check: python3 {builder} --check-config)",
        "text.prompt": "Theme number (p<number> = preview, q = quit): ",
        "main.no_tkinter": "tkinter is missing - on CachyOS/Arch: sudo pacman -S tk  (starting text mode)",
        "main.no_builder": "Cannot load the installer ({exc}). On CachyOS/Arch: sudo pacman -S python-pillow",
        "main.no_display": "No graphical environment ({exc}) - text mode.",
    },
}


def t(text_key: str, lang: str, /, **fmt) -> str:
    """UI string for text_key; falls back to Polish, then to the key itself."""
    text = TEXT.get(lang, {}).get(text_key)
    if text is None:
        text = TEXT["pl"].get(text_key, text_key)
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# ---- settings form (OPTION_SPECS) ------------------------------------------
GROUP_EN = {
    "Układ": "Layout",
    "Elementy": "Elements",
    "Zachowanie": "Behaviour",
    "Wpisy menu": "Menu entries",
}

# key -> (label, help); an empty help keeps the spec without a help line.
OPTION_EN: dict[str, tuple[str, str]] = {
    "layout.resolution": ("Screen resolution",
                          "Native monitor resolution. Background and icon sizes adapt automatically."),
    "layout.icon_size": ("System tile size (px)", "0 = automatic (768 px at 4K, 384 px at 1080p)."),
    "layout.tool_size": ("Tool icon size (px)", "0 = automatic (240 px at 4K)."),
    "layout.selection_scale": ("Selection frame size", "Frame relative to the tile: 1.0 = right at the edge."),
    "layout.art_scale": ("Corner artwork scale", "For themes with AI artwork. Less = more black background."),
    "layout.art_brightness": ("Artwork brightness", "0 = theme value. 1.0 = original, less = darker."),
    "layout.ui_dim": ("Dimming under the interface",
                      "How much to darken the artwork under the tiles and text (0 = not at all)."),
    "hud.accent": ("Accent color", "#RRGGBB. Empty = theme color. Recolors the frame, icons and HUD."),
    "hud.title": ("Title in the top-left corner", ""),
    "hud.title_text": ("Custom title", "Empty = the theme's title, e.g. CURSED_DOMAIN_v1.0."),
    "hud.tagline": ("Tagline in the top-right corner", ""),
    "hud.tagline_text": ("Custom tagline", ""),
    "hud.kanji": ("Vertical column of characters", ""),
    "hud.kanji_text": ("Custom characters (up to 5)", ""),
    "hud.hardware": ("Hardware info", ""),
    "hud.hardware_lines": ("Which hardware lines", ""),
    "hud.custom_lines": ("Custom lines under the hardware info", "Up to 4 lines, e.g. name, hostname, motto."),
    "hud.status_line": ("Status line with cursor", ""),
    "hud.status_text": ("Status text", ""),
    "hud.decorations": ("HUD decorations (rulers, corners)", ""),
    "hud.nav_bar": ("Key hint bar at the bottom", ""),
    "hud.scanlines": ("Scanlines (CRT effect)", ""),
    "hud.glitch": ("Glitch bars", ""),
    "hud.ghoul_overlay": ("Original Ghoul Cyber overlay",
                          "ghoul-cyber theme only. Off = HUD drawn the same way as in other themes."),
    "cards.numbers": ("Numbers on system tiles",
                      "01, 02, ... in the bottom-left corner of a tile. Off = tiles without numbers."),
    "cards.order": ("Number order",
                    "Empty = automatic: your menu entries first, then systems detected on this "
                    "computer. Tiles not on the list get no number."),
    "refind.timeout": ("Time until automatic boot (s)",
                       "0 = wait forever, -1 = boot the default system immediately."),
    "refind.default_selection": ("Default system",
                                 "Part of an entry name (e.g. CachyOS) or + = last booted. Empty = first."),
    "refind.showtools": ("Tools in the bottom row", "rEFInd shows only the ones that are actually available."),
    "refind.hideui": ("Hide rEFInd elements", ""),
    "refind.scanfor": ("Where to look for systems",
                       "Empty = rEFInd default (internal, external, optical, manual)."),
    "layout.visible_tiles": ("System tiles visible at once",
                             "0 = automatic from the tile size (3 at 4K). A number > 0 sizes the tiles so exactly "
                             "that many fit; the other systems scroll by one. 1 tile only up to 1440p."),
    "layout.scroll_arrows": ("Scroll arrows", "Arrows beside the system row when not all systems fit."),
    "refind.max_tools": ("Tools in the bottom row (max)",
                         "0 = all available. Counted in order of importance: BIOS, reboot, power off, Shell, "
                         "MemTest, about, boot order, hidden entries, the rest."),
    "refind.extra_tools": ("Add rEFInd tools",
                           "EFI Shell (Arch/CachyOS, Debian/Ubuntu) and the MemTest86+ memory test (Arch, "
                           "Debian/Ubuntu) from your distribution's packages, copied to EFI/tools. They appear in the bottom row."),
    "refind.enable_mouse": ("Mouse support", ""),
    "refind.enable_touch": ("Touchscreen support", ""),
    "refind.dont_scan_dirs": ("Skipped folders", "Comma-separated."),
    "refind.dont_scan_files": ("Skipped files", "Comma-separated."),
    "refind.max_tags": ("Max. number of systems in the menu", "0 = no limit."),
    "entries": ("Custom menu entries", "Manual rEFInd entries, e.g. a second Windows on another disk."),
}


def option_label(spec, lang: str) -> str:
    if lang == "en" and spec.key in OPTION_EN:
        return OPTION_EN[spec.key][0] or spec.label
    return spec.label


def option_help(spec, lang: str) -> str:
    if lang == "en" and spec.key in OPTION_EN and spec.help:
        return OPTION_EN[spec.key][1] or spec.help
    return spec.help


def group_name(group: str, lang: str) -> str:
    return GROUP_EN.get(group, group) if lang == "en" else group
