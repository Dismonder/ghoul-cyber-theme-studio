#!/usr/bin/env python3
"""Ghoul Cyber Theme Studio - build your own rEFInd boot screen: pick a theme,
tune layout, elements and behaviour with a live preview, install in one click.

Author: Dismonder
Copyright: (c) 2026 Dismonder. All rights reserved.
License: Ghoul Cyber Protective License (GCPL-1.0) - see LICENSE

Run:  python3 theme_studio.py
Settings are auto-saved to boot-config.json (only when valid), so the plain
command-line installer uses exactly what you see here. On Linux the install
runs build_and_deploy_theme.py and asks for the sudo password in a small
window (SUDO_ASKPASS). On Windows it builds the package in dist/ghoul-cyber.
"""

from __future__ import annotations

import base64
import io
import json
import os
import platform
import queue
import stat
import subprocess
import sys
import tempfile
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path

from studio_i18n import current_language, group_name, option_help, option_label, save_language, t

ROOT = Path(__file__).resolve().parent
# The engine (installer, builder and themes) is the refind-theme-ghoul-cyber
# repository: the theme/ submodule of the Theme Studio repository, or this very
# folder when the app is run from a checkout of the theme itself.
ENGINE = ROOT / "theme" if (ROOT / "theme" / "build_and_deploy_theme.py").is_file() else ROOT
BUILDER = ENGINE / "build_and_deploy_theme.py"
THEMES_DIR = ENGINE / "themes"
CONFIG_PATH = ENGINE / "boot-config.json"   # the builder reads it from next to itself
DEFAULT_THEME = "ghoul-cyber"
ASKPASS_FLAG = "--askpass"
IS_LINUX = platform.system() == "Linux"

BG = "#050506"
PANEL = "#0d0d10"
PANEL_HI = "#16161b"
TEXT = "#e6e6ea"
DIM = "#8a8a94"
OK = "#7CFF3A"
BAD = "#FF4D4D"


@dataclass(frozen=True)
class ThemeInfo:
    key: str
    name: str
    description: str
    accent: str
    preview: Path | None


def read_json(path: Path):
    """JSON from a file, or None if it is missing, broken or not UTF-8."""
    try:
        if path.stat().st_size > 1_000_000:
            return None
        return json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError, RecursionError):
        return None


def load_themes() -> list[ThemeInfo]:
    """The original theme first, then every themes/<name>/theme.json."""
    themes = [
        ThemeInfo(
            DEFAULT_THEME,
            "Ghoul Cyber",
            "The original: ghoul eye, skull and blood-red cyberpunk HUD.",
            "#FF003C",
            ENGINE / "full_bootloader_preview_1080p.png",
        )
    ]
    if THEMES_DIR.is_dir():
        for folder in sorted(THEMES_DIR.iterdir()):
            config_path = folder / "theme.json"
            if not config_path.is_file():
                continue
            config = read_json(config_path)
            if not isinstance(config, dict):
                continue  # a broken theme folder must never break the studio
            preview = folder / "preview.jpg"
            themes.append(
                ThemeInfo(
                    folder.name,
                    str(config.get("name", folder.name)),
                    ("FAN ART · " if config.get("fan_art") else "") + str(config.get("description", "")),
                    str(config.get("accent", "#FF003C")),
                    preview if preview.is_file() else None,
                )
            )
    return themes


def build_command(theme: str, *, install: bool, dry_run: bool, config: Path | None) -> list[str]:
    command = [sys.executable, "-u", str(BUILDER), "--theme", theme]
    command += ["--config", str(config)] if config else ["--no-config"]
    if not install:
        command.append("--build-only")
    elif not IS_LINUX:
        command.append("--install")  # Linux installs by default
    if dry_run:
        command.append("--dry-run")
    return command


def write_askpass_wrapper() -> Path:
    """sudo needs an executable without arguments; point it back at us."""
    folder = Path(tempfile.mkdtemp(prefix="ghoul-studio-"))
    if os.name == "nt":
        wrapper = folder / "askpass.cmd"
        wrapper.write_text(f'@"{sys.executable}" "{Path(__file__).resolve()}" {ASKPASS_FLAG} %*\r\n')
    else:
        wrapper = folder / "askpass.sh"
        wrapper.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{Path(__file__).resolve()}" {ASKPASS_FLAG} "$@"\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    return wrapper


def run_askpass(prompt: str) -> int:
    """Password window used by sudo -A. Prints the password on stdout."""
    import tkinter as tk

    lang = current_language()
    root = tk.Tk()
    root.title("Ghoul Cyber - sudo")
    root.configure(bg=BG)
    root.resizable(False, False)
    root.attributes("-topmost", True)
    result: dict[str, str | None] = {"value": None}

    tk.Label(root, text=t("askpass.title", lang), bg=BG, fg=TEXT,
             font=("TkDefaultFont", 12, "bold")).pack(padx=24, pady=(20, 4), anchor="w")
    tk.Label(root, text=prompt.strip() or t("askpass.prompt", lang), bg=BG, fg=DIM).pack(padx=24, anchor="w")
    entry = tk.Entry(root, show="•", width=34, bg=PANEL_HI, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("TkDefaultFont", 12))
    entry.pack(padx=24, pady=12, ipady=6)

    def accept(_event=None):
        result["value"] = entry.get()
        root.destroy()

    buttons = tk.Frame(root, bg=BG)
    buttons.pack(padx=24, pady=(0, 20), fill="x")
    tk.Button(buttons, text=t("askpass.cancel", lang), command=root.destroy, bg=PANEL_HI, fg=TEXT,
              relief="flat", padx=14, pady=6, activebackground=PANEL).pack(side="right")
    tk.Button(buttons, text=t("askpass.ok", lang), command=accept, bg="#FF003C", fg="white",
              relief="flat", padx=20, pady=6, activebackground="#c4002e").pack(side="right", padx=8)
    entry.bind("<Return>", accept)
    root.bind("<Escape>", lambda _e: root.destroy())
    entry.focus_force()
    root.mainloop()
    if result["value"] is None:
        return 1
    sys.stdout.write(result["value"] + "\n")
    return 0


def photo_from_image(tk, image, size: tuple[int, int]):
    """PIL image -> Tk PhotoImage (fit into size) without needing ImageTk."""
    from PIL import ImageOps

    image = ImageOps.fit(image.convert("RGB"), size)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buffer.getvalue()), format="png")


def photo_from_file(tk, path: Path | None, size: tuple[int, int]):
    from PIL import Image

    if path is None or not path.is_file():
        return photo_from_image(tk, Image.new("RGB", size, (8, 8, 10)), size)
    with Image.open(path) as source:
        return photo_from_image(tk, source, size)


class Studio:
    THUMB = (224, 126)

    def __init__(self, root, themes: list[ThemeInfo], builder, *, lang: str | None = None,
                 theme: str | None = None, rebuild: bool = False):
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk, self.bt = tk, ttk, builder
        self.lang = lang or current_language()
        self.root = root
        self.themes = themes
        self.selected = 0
        self.process: subprocess.Popen[str] | None = None
        self.stopped = False
        self.with_install = True
        self._systems = None          # detected systems, for the automatic card order
        self._order_refresh = None
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.previews: queue.Queue = queue.Queue()
        self.thumbs: list = []
        self.tiles: list = []
        self.preview_image = None
        self.preview_source = None          # last rendered PIL image
        self.preview_job = None
        self.preview_generation = 0
        self.fields: dict[str, dict] = {}   # key -> {"get": fn, "set": fn}
        self.errors: list[str] = []
        self.loading = False
        self.askpass = write_askpass_wrapper() if IS_LINUX else None
        self.scroll_areas: list = []
        self.drain_job = None

        root.title(self.t("window.title"))
        root.configure(bg=BG)
        root.report_callback_exception = self._on_ui_error
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96)
        self.thumb = (round(self.THUMB[0] * self.scale), round(self.THUMB[1] * self.scale))
        if not rebuild:  # a language switch keeps the window as the user left it
            screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{min(screen_w, round(1440 * self.scale))}x{min(screen_h - 80, round(940 * self.scale))}")
            root.minsize(round(1050 * self.scale), round(700 * self.scale))
            try:  # start maximised: the preview is the point of the app
                root.state("zoomed")
            except tk.TclError:
                try:
                    root.attributes("-zoomed", True)
                except tk.TclError:
                    pass
        self._style()

        self._build_header()
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._build_list(body)
        self._build_detail(body)
        root.bind_all("<MouseWheel>", self._on_wheel)
        root.bind_all("<Button-4>", self._on_wheel)
        root.bind_all("<Button-5>", self._on_wheel)

        saved_theme = self._load_config()
        wanted = theme or saved_theme
        start = next((i for i, info in enumerate(themes) if info.key == wanted), 0)
        self.select(start)
        self.drain_job = root.after(80, self._drain_queues)

    def t(self, text_key: str, /, **fmt) -> str:
        return t(text_key, self.lang, **fmt)

    def switch_language(self, lang: str):
        """Save the choice and rebuild the whole window in the other language."""
        from tkinter import messagebox

        if lang == self.lang:
            return
        if self.process is not None:
            messagebox.showinfo(self.t("lang.busy_title"), self.t("lang.busy"), parent=self.root)
            return
        save_language(lang)
        theme = self.themes[self.selected].key
        for job in (self.preview_job, self.drain_job):
            if job is not None:
                self.root.after_cancel(job)
        self.preview_job = self.drain_job = None
        self.preview_generation += 1  # a render still running for this instance is ignored
        for child in self.root.winfo_children():
            child.destroy()
        Studio(self.root, self.themes, self.bt, lang=lang, theme=theme, rebuild=True)

    # ---- look ---------------------------------------------------------
    def _style(self):
        ttk = self.ttk
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL_HI, background=PANEL_HI,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=PANEL_HI)
        style.map("TCombobox", fieldbackground=[("readonly", PANEL_HI)], foreground=[("readonly", TEXT)])
        style.configure("Accent.Horizontal.TProgressbar", troughcolor=PANEL, background="#FF003C",
                        bordercolor=PANEL, lightcolor="#FF003C", darkcolor="#FF003C")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=DIM, padding=(14, 6),
                        font=("Consolas", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", PANEL_HI)], foreground=[("selected", TEXT)])
        style.configure("Treeview", background=PANEL_HI, fieldbackground=PANEL_HI, foreground=TEXT,
                        rowheight=round(24 * self.scale), borderwidth=0)
        style.configure("Treeview.Heading", background=PANEL, foreground=DIM, borderwidth=0)

    def _button(self, parent, text, command, *, accent=False, **kw):
        return self.tk.Button(parent, text=text, command=command, relief="flat", cursor="hand2",
                              bg="#FF003C" if accent else PANEL_HI, fg="white" if accent else TEXT,
                              activebackground=PANEL, activeforeground=TEXT,
                              font=("Consolas", 10, "bold" if accent else "normal"), padx=12, pady=5, **kw)

    def _on_ui_error(self, exc_type, exc, tb):
        """Never let a UI glitch kill the studio: log it and keep going."""
        from tkinter import messagebox

        detail = "".join(traceback.format_exception(exc_type, exc, tb))
        print(detail, file=sys.stderr)
        messagebox.showerror("Theme Studio", self.t("ui_error", exc=exc))

    # ---- layout -------------------------------------------------------
    def _build_header(self):
        tk = self.tk
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(16, 12))
        tk.Label(header, text="0x0000_BOOT // THEME_STUDIO", bg=BG, fg=TEXT,
                 font=("Consolas", 18, "bold")).pack(side="left")
        self.header_rule = tk.Frame(self.root, bg="#FF003C", height=2)
        self.header_rule.pack(fill="x", padx=18, pady=(0, 14))
        switch = tk.Frame(header, bg=BG)
        switch.pack(side="right", padx=(14, 0))
        for i, code in enumerate(("pl", "en")):
            if i:
                tk.Label(switch, text="|", bg=BG, fg=DIM, font=("Consolas", 10)).pack(side="left")
            active = code == self.lang
            button = self._button(switch, code.upper(), lambda c=code: self.switch_language(c))
            button.configure(bg=PANEL_HI if active else BG, fg=TEXT if active else DIM, padx=8, pady=2,
                             font=("Consolas", 10, "bold" if active else "normal"))
            button.pack(side="left")
        mode = self.t("header.mode_linux") if IS_LINUX else self.t("header.mode_windows")
        tk.Label(header, text=f"rEFInd OLED  |  {mode}", bg=BG, fg=DIM,
                 font=("Consolas", 10)).pack(side="right")

    def _scroll_area(self, parent, bg=PANEL):
        """Canvas + inner frame that scrolls with the wheel under the mouse."""
        tk = self.tk
        canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=bg)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.scroll_areas.append(canvas)
        return canvas, inner

    def _on_wheel(self, event):
        widget = self.root.winfo_containing(event.x_root, event.y_root)
        while widget is not None and widget not in self.scroll_areas:
            widget = widget.master
        if widget is not None:
            delta = -1 if (getattr(event, "delta", 0) > 0 or getattr(event, "num", 0) == 4) else 1
            widget.yview_scroll(delta * 2, "units")

    def _build_list(self, parent):
        tk = self.tk
        outer = tk.Frame(parent, bg=PANEL, width=self.thumb[0] + round(44 * self.scale))
        outer.pack(side="left", fill="y")
        outer.pack_propagate(False)
        tk.Label(outer, text=self.t("list.themes", count=len(self.themes)), bg=PANEL, fg=DIM,
                 font=("Consolas", 10)).pack(anchor="w", padx=14, pady=(12, 6))
        holder = tk.Frame(outer, bg=PANEL)
        holder.pack(fill="both", expand=True, padx=(10, 0))
        self.list_canvas, inner = self._scroll_area(holder)
        for index, theme in enumerate(self.themes):
            tile = tk.Frame(inner, bg=PANEL, highlightthickness=2, highlightbackground=PANEL)
            tile.pack(fill="x", pady=6, padx=(0, 6))
            thumb = photo_from_file(tk, theme.preview, self.thumb)
            self.thumbs.append(thumb)
            image_label = tk.Label(tile, image=thumb, bg=PANEL, bd=0)
            image_label.pack()
            caption = tk.Frame(tile, bg=PANEL)
            caption.pack(fill="x")
            tk.Frame(caption, bg=theme.accent, width=10, height=10).pack(side="left", padx=(4, 8), pady=6)
            tk.Label(caption, text=theme.name, bg=PANEL, fg=TEXT,
                     font=("Consolas", 10, "bold")).pack(side="left")
            for widget in (tile, image_label, caption, *caption.winfo_children()):
                widget.bind("<Button-1>", lambda _e, i=index: self.select(i))
            self.tiles.append(tile)

    def _build_detail(self, parent):
        tk, ttk = self.tk, self.ttk
        detail = tk.Frame(parent, bg=BG)
        detail.pack(side="left", fill="both", expand=True, padx=(18, 0))

        # Bottom-up: settings notebook, info line; the live preview takes the rest.
        self.notebook = ttk.Notebook(detail)
        self.notebook.pack(side="bottom", fill="both", expand=False, pady=(8, 0))
        info = tk.Frame(detail, bg=BG)
        info.pack(side="bottom", fill="x", pady=(8, 0))
        self.preview = tk.Canvas(detail, bg=BG, highlightthickness=0, width=1, height=1)
        self.preview.pack(side="top", fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _e: self._show_preview())

        self.swatch = tk.Frame(info, bg="#FF003C", width=6, height=40)
        self.swatch.pack(side="left", padx=(0, 12))
        text_box = tk.Frame(info, bg=BG)
        text_box.pack(side="left", fill="x", expand=True)
        self.title_label = tk.Label(text_box, bg=BG, fg=TEXT, font=("Consolas", 16, "bold"), anchor="w")
        self.title_label.pack(fill="x")
        self.desc_label = tk.Label(text_box, bg=BG, fg=DIM, font=("Consolas", 9), anchor="w", justify="left")
        self.desc_label.pack(fill="x")
        self.config_status = tk.Label(info, bg=BG, fg=DIM, font=("Consolas", 9), anchor="e", justify="right")
        self.config_status.pack(side="right")

        self._build_install_tab()
        groups: dict[str, list] = {}
        for spec in self.bt.OPTION_SPECS:
            groups.setdefault(spec.group, []).append(spec)
        for group, specs in groups.items():
            self._build_settings_tab(group_name(group, self.lang), specs)

    def _tab(self, title):
        frame = self.tk.Frame(self.notebook, bg=PANEL, height=round(300 * self.scale))
        frame.pack_propagate(False)
        self.notebook.add(frame, text=title)
        return frame

    def _build_install_tab(self):
        tk, ttk = self.tk, self.ttk
        tab = self._tab(self.t("tab.install"))
        controls = tk.Frame(tab, bg=PANEL)
        controls.pack(fill="x", padx=10, pady=(10, 4))
        self.dry_run = tk.BooleanVar(value=False)
        tk.Checkbutton(controls, text=self.t("install.dry_run"), variable=self.dry_run,
                       bg=PANEL, fg=TEXT, selectcolor=PANEL_HI, activebackground=PANEL,
                       activeforeground=TEXT, font=("Consolas", 10)).pack(side="left", padx=(0, 14))
        self.action = tk.Button(controls, text=self.t("install.build_install"), command=lambda: self.install(True),
                                fg="white", relief="flat", font=("Consolas", 12, "bold"), padx=22, pady=7,
                                cursor="hand2")
        self.action.pack(side="right")
        self.build_button = self._button(controls, self.t("install.build"), lambda: self.install(False))
        self.build_button.configure(font=("Consolas", 11, "bold"), padx=18, pady=6)
        self.build_button.pack(side="right", padx=(8, 8))
        self.stop_button = self._button(controls, self.t("install.stop"), self.stop)
        self.stop_button.configure(state="disabled")
        self.stop_button.pack(side="right", padx=8)
        self.progress = ttk.Progressbar(tab, mode="indeterminate", style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=10, pady=(2, 4))
        self.status = tk.Label(tab, text=self.t("install.hint"),
                               bg=PANEL, fg=DIM, font=("Consolas", 10), anchor="w")
        self.status.pack(fill="x", padx=10)
        answer_row = tk.Frame(tab, bg=PANEL)
        answer_row.pack(side="bottom", fill="x", padx=10, pady=(0, 8))
        tk.Label(answer_row, text=self.t("install.answer"), bg=PANEL, fg=DIM,
                 font=("Consolas", 9)).pack(side="left")
        self.answer = tk.Entry(answer_row, bg=PANEL_HI, fg=TEXT, insertbackground=TEXT, relief="flat",
                               font=("Consolas", 10))
        self.answer.pack(side="left", fill="x", expand=True, padx=8, ipady=3)
        self.answer.bind("<Return>", self.send_answer)
        self.log = tk.Text(tab, bg=BG, fg=TEXT, insertbackground=TEXT, relief="flat",
                           font=("Consolas", 9), wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=6)

    # ---- settings form (generated from the builder's OPTION_SPECS) ----
    def _build_settings_tab(self, group, specs):
        tk = self.tk
        tab = self._tab(group)
        bar = tk.Frame(tab, bg=PANEL)
        bar.pack(side="bottom", fill="x", padx=10, pady=6)
        self._button(bar, self.t("settings.reset"), self.reset_defaults).pack(side="left")
        self._button(bar, self.t("settings.import"), self.import_config).pack(side="left", padx=6)
        self._button(bar, self.t("settings.export"), self.export_config).pack(side="left")
        holder = tk.Frame(tab, bg=PANEL)
        holder.pack(fill="both", expand=True, padx=(10, 0), pady=(8, 0))
        _canvas, inner = self._scroll_area(holder)
        inner.columnconfigure(1, weight=1)
        for row, spec in enumerate(specs):
            label = tk.Label(inner, text=option_label(spec, self.lang), bg=PANEL, fg=TEXT, font=("Consolas", 10, "bold"),
                             anchor="nw", justify="left", wraplength=round(260 * self.scale))
            label.grid(row=row * 2, column=0, sticky="nw", padx=(0, 16), pady=(8, 0))
            cell = tk.Frame(inner, bg=PANEL)
            cell.grid(row=row * 2, column=1, sticky="we", pady=(6, 0), padx=(0, 16))
            self.fields[spec.key] = self._make_field(cell, spec)
            help_text = option_help(spec, self.lang)
            if help_text:
                tk.Label(inner, text=help_text, bg=PANEL, fg=DIM, font=("Consolas", 8), anchor="w",
                         justify="left", wraplength=round(560 * self.scale)).grid(
                    row=row * 2 + 1, column=1, sticky="w", padx=(0, 16))

    def _make_field(self, cell, spec):
        tk, ttk = self.tk, self.ttk
        changed = lambda *_a: self.on_change()  # noqa: E731
        entry_kw = dict(bg=PANEL_HI, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Consolas", 10))
        kind = spec.kind
        if kind == "bool":
            var = tk.BooleanVar()
            tk.Checkbutton(cell, variable=var, text=self.t("field.enabled"), bg=PANEL, fg=TEXT, selectcolor=PANEL_HI,
                           activebackground=PANEL, activeforeground=TEXT, font=("Consolas", 9),
                           command=changed).pack(anchor="w")
            return {"get": var.get, "set": var.set}
        if kind in {"int", "float"}:
            var = tk.StringVar()
            step = 1 if kind == "int" else 0.05
            box = tk.Spinbox(cell, from_=spec.minimum, to=spec.maximum, increment=step, textvariable=var,
                             width=10, buttonbackground=PANEL_HI, command=changed,
                             format="%.0f" if kind == "int" else "%.2f", **entry_kw)
            box.pack(anchor="w", ipady=2)
            var.trace_add("write", changed)

            def get():
                text = var.get().strip().replace(",", ".")
                return int(float(text)) if kind == "int" else round(float(text), 3)
            return {"get": get, "set": lambda v: var.set(str(v))}
        if kind == "choice":
            var = tk.StringVar()
            combo = ttk.Combobox(cell, textvariable=var, values=spec.choices, state="readonly", width=16)
            combo.pack(anchor="w")
            combo.bind("<<ComboboxSelected>>", changed)
            return {"get": var.get, "set": var.set}
        if kind == "multi":
            flags = {}
            grid = tk.Frame(cell, bg=PANEL)
            grid.pack(anchor="w", fill="x")
            for i, choice in enumerate(spec.choices):
                flags[choice] = tk.BooleanVar()
                tk.Checkbutton(grid, text=choice, variable=flags[choice], bg=PANEL, fg=TEXT,
                               selectcolor=PANEL_HI, activebackground=PANEL, activeforeground=TEXT,
                               font=("Consolas", 9), command=changed).grid(row=i // 4, column=i % 4, sticky="w",
                                                                         padx=(0, 10))
            return {"get": lambda: tuple(c for c in spec.choices if flags[c].get()),
                    "set": lambda v: [flags[c].set(c in v) for c in spec.choices]}
        if kind in {"text", "color"}:
            var = tk.StringVar()
            row = tk.Frame(cell, bg=PANEL)
            row.pack(anchor="w", fill="x")
            tk.Entry(row, textvariable=var, width=34 if kind == "text" else 10, **entry_kw).pack(side="left", ipady=3)
            var.trace_add("write", changed)
            if kind == "color":
                swatch = tk.Frame(row, width=22, height=22, bg=PANEL_HI)
                swatch.pack(side="left", padx=8)

                def pick():
                    from tkinter import colorchooser
                    chosen = colorchooser.askcolor(color=var.get() or "#FF003C", parent=self.root)[1]
                    if chosen:
                        var.set(chosen.upper())

                def paint(*_a):
                    try:
                        swatch.configure(bg=var.get() if len(var.get()) == 7 else PANEL_HI)
                    except self.tk.TclError:
                        swatch.configure(bg=PANEL_HI)
                var.trace_add("write", paint)
                self._button(row, self.t("field.pick_color"), pick).pack(side="left")
                self._button(row, self.t("field.from_theme"), lambda: var.set("")).pack(side="left", padx=6)
            return {"get": lambda: var.get().strip(), "set": var.set}
        if kind == "lines":
            box = tk.Text(cell, height=4, width=48, wrap="none", **entry_kw)
            box.pack(anchor="w")
            box.bind("<KeyRelease>", changed)

            def set_lines(v):
                box.delete("1.0", "end")
                box.insert("1.0", "\n".join(v))
            return {"get": lambda: tuple(l for l in box.get("1.0", "end").splitlines() if l.strip()),
                    "set": set_lines}
        if kind == "entries":
            return self._make_entries_field(cell)
        if kind == "order":
            return self._make_order_field(cell, spec)
        raise ValueError(f"unsupported option kind: {kind}")

    def _make_order_field(self, cell, spec):
        """Card numbering order: automatic, or a user list (up/down, on/off)."""
        tk = self.tk
        auto = tk.BooleanVar(value=True)
        order: list[str] = []      # numbered cards, in order
        top = tk.Frame(cell, bg=PANEL)
        top.pack(anchor="w", fill="x")
        box = tk.Listbox(top, height=len(spec.choices), width=34, activestyle="none", exportselection=False,
                         bg=PANEL_HI, fg=TEXT, selectbackground="#FF003C", selectforeground="#FFFFFF",
                         relief="flat", font=("Consolas", 10))
        box.pack(side="left")
        buttons = tk.Frame(top, bg=PANEL)
        buttons.pack(side="left", padx=8, anchor="n")

        def auto_order():
            if self._systems is None:
                try:
                    self._systems = self.bt.detect_systems()
                except Exception:  # noqa: BLE001 - detection is best effort
                    self._systems = ()
            return list(self.bt.auto_card_order(self.options, self._systems))

        def rows():
            shown = auto_order() if auto.get() else order
            rest = [c for c in spec.choices if c not in shown]
            return [(c, i + 1) for i, c in enumerate(shown)] + [(c, None) for c in rest]

        last: list[tuple[str, int | None]] = []

        def refresh(keep=None):
            keep = keep or selected()
            last[:] = rows()
            box.delete(0, "end")
            for i, (card, number) in enumerate(last):
                label = self.bt.CARD_LABELS.get(card, card)
                box.insert("end", f" {number:02d}  {label}" if number else f" --  {label}  {self.t('order.no_number')}")
                if card == keep:
                    box.selection_set(i)
            box.configure(fg=DIM if auto.get() else TEXT)
            for child in buttons.winfo_children():
                if isinstance(child, tk.Button):
                    child.configure(state="disabled" if auto.get() else "normal")

        def selected():
            sel = box.curselection()
            return last[sel[0]][0] if sel and sel[0] < len(last) else None

        def move(step):
            card = selected()
            if card in order:
                i = order.index(card)
                j = max(0, min(len(order) - 1, i + step))
                order[i], order[j] = order[j], order[i]
                refresh(card)
                self.on_change()

        def toggle():
            card = selected()
            if card is None:
                return
            if card in order:
                order.remove(card)
            else:
                order.append(card)
            refresh(card)
            self.on_change()

        def switch():
            if not auto.get():
                order[:] = auto_order()
            refresh()
            self.on_change()

        tk.Checkbutton(cell, text=self.t("order.auto"), variable=auto,
                       bg=PANEL, fg=TEXT, selectcolor=PANEL_HI, activebackground=PANEL, activeforeground=TEXT,
                       font=("Consolas", 9), command=switch).pack(anchor="w", pady=(4, 0))
        self._button(buttons, self.t("order.up"), lambda: move(-1)).pack(fill="x")
        self._button(buttons, self.t("order.down"), lambda: move(1)).pack(fill="x", pady=4)
        self._button(buttons, self.t("order.toggle"), toggle).pack(fill="x")
        self._order_refresh = refresh

        def set_order(value):
            order[:] = list(value)
            auto.set(not value)
            refresh()
        return {"get": lambda: () if auto.get() else tuple(order), "set": set_order}

    def _make_entries_field(self, cell):
        tk, ttk = self.tk, self.ttk
        entries: list[dict] = []
        tree = ttk.Treeview(cell, columns=("label", "card", "loader", "volume"), show="headings", height=6)
        for col, width in (("label", 150), ("card", 90), ("loader", 260), ("volume", 150)):
            tree.heading(col, text=self.t(f"entries.col_{col}"))
            tree.column(col, width=round(width * self.scale), stretch=col == "loader")
        tree.pack(fill="x", anchor="w")
        buttons = tk.Frame(cell, bg=PANEL)
        buttons.pack(anchor="w", pady=6)

        def refresh():
            tree.delete(*tree.get_children())
            for i, e in enumerate(entries):
                tree.insert("", "end", iid=str(i), values=(
                    e["label"] + (self.t("entries.off") if e.get("disabled") else ""), e["card"], e["loader"], e["volume"]))

        def edit(index=None):
            current = dict(entries[index]) if index is not None else {
                "label": "", "card": "windows", "loader": "\\EFI\\Microsoft\\Boot\\bootmgfw.efi",
                "volume": "", "options": "", "disabled": False}
            result = self._entry_dialog(current)
            if result is None:
                return
            if index is None:
                entries.append(result)
            else:
                entries[index] = result
            refresh()
            self.on_change()

        def selected_index():
            sel = tree.selection()
            return int(sel[0]) if sel else None

        def remove():
            index = selected_index()
            if index is not None:
                del entries[index]
                refresh()
                self.on_change()

        self._button(buttons, self.t("entries.add"), lambda: edit()).pack(side="left")
        self._button(buttons, self.t("entries.edit"), lambda: selected_index() is not None and edit(selected_index())).pack(
            side="left", padx=6)
        self._button(buttons, self.t("entries.remove"), remove).pack(side="left")
        tree.bind("<Double-1>", lambda _e: selected_index() is not None and edit(selected_index()))

        def set_entries(value):
            entries[:] = [dict(e) for e in value]
            refresh()
        return {"get": lambda: tuple(dict(e) for e in entries), "set": set_entries}

    def _entry_dialog(self, current: dict):
        """Modal editor for one menu entry, validated before it is accepted."""
        tk, ttk = self.tk, self.ttk
        from tkinter import messagebox

        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("entry.title"))
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        result: dict = {"value": None}
        variables = {}
        rows = tuple((key, self.t(f"entry.{key}"), self.t(f"entry.{key}_hint"))
                     for key in ("label", "card", "loader", "volume", "options"))
        for i, (key, label, hint) in enumerate(rows):
            tk.Label(dialog, text=label, bg=BG, fg=TEXT, font=("Consolas", 10, "bold")).grid(
                row=i * 2, column=0, sticky="w", padx=16, pady=(10, 0))
            variables[key] = tk.StringVar(value=str(current.get(key, "")))
            if key == "card":
                ttk.Combobox(dialog, textvariable=variables[key], values=tuple(self.bt.ENTRY_CARDS),
                             state="readonly", width=20).grid(row=i * 2, column=1, sticky="w", padx=16, pady=(10, 0))
            else:
                tk.Entry(dialog, textvariable=variables[key], width=48, bg=PANEL_HI, fg=TEXT,
                         insertbackground=TEXT, relief="flat", font=("Consolas", 10)).grid(
                    row=i * 2, column=1, sticky="we", padx=16, pady=(10, 0), ipady=3)
            tk.Label(dialog, text=hint, bg=BG, fg=DIM, font=("Consolas", 8)).grid(
                row=i * 2 + 1, column=1, sticky="w", padx=16)
        disabled = tk.BooleanVar(value=bool(current.get("disabled")))
        tk.Checkbutton(dialog, text=self.t("entry.disabled"), variable=disabled,
                       bg=BG, fg=TEXT, selectcolor=PANEL_HI, activebackground=BG, activeforeground=TEXT,
                       font=("Consolas", 9)).grid(row=len(rows) * 2, column=1, sticky="w", padx=16, pady=8)

        def accept():
            candidate = {k: v.get().strip() for k, v in variables.items()}
            candidate["disabled"] = disabled.get()
            errors: list[str] = []
            checked = self.bt._check_entry(0, candidate, errors)
            if errors:
                messagebox.showerror(self.t("entry.error_title"), "\n".join(e.replace("entries[0].", "") for e in errors),
                                     parent=dialog)
                return
            result["value"] = checked
            dialog.destroy()

        buttons = tk.Frame(dialog, bg=BG)
        buttons.grid(row=len(rows) * 2 + 1, column=0, columnspan=2, sticky="e", padx=16, pady=(4, 16))
        self._button(buttons, self.t("entry.cancel"), dialog.destroy).pack(side="right")
        self._button(buttons, self.t("entry.save"), accept, accent=True).pack(side="right", padx=8)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        self.root.wait_window(dialog)
        return result["value"]

    # ---- options state --------------------------------------------------
    def _set_form(self, options: dict):
        self.loading = True
        try:
            for key, field in self.fields.items():
                field["set"](options[key])
        finally:
            self.loading = False

    def _read_form(self) -> tuple[dict, list[str]]:
        """Collect widget values, then run them through the builder's validator."""
        raw, problems = {}, []
        for key, field in self.fields.items():
            try:
                raw[key] = field["get"]()
            except (ValueError, OverflowError, self.tk.TclError):
                problems.append(self.t("form.invalid", key=key))
        options, errors, _warnings = self.bt.validate_options(self.bt.nest_options(raw))
        return options, problems + errors

    def _load_config(self) -> str | None:
        theme = None
        options = self.bt.default_options()
        if CONFIG_PATH.is_file():
            try:
                raw = json.loads(CONFIG_PATH.read_bytes().decode("utf-8-sig"))
                options, errors, _ = self.bt.validate_options(raw)
                theme = raw.get("theme") if isinstance(raw, dict) else None
                if errors:
                    self._set_config_status(self.t("config.errors", name=CONFIG_PATH.name, count=len(errors)), BAD)
            except (OSError, ValueError, RecursionError) as exc:
                self._set_config_status(self.t("config.unreadable", name=CONFIG_PATH.name, exc=exc), BAD)
        self.options = options
        self._set_form(options)
        return theme

    def _set_config_status(self, text, color):
        self.config_status.configure(text=text, fg=color)

    def on_change(self):
        if self.loading:
            return
        options, errors = self._read_form()
        self.errors = errors
        if errors:
            self._set_config_status("✖ " + " | ".join(errors[:2]) + (" …" if len(errors) > 2 else ""), BAD)
            self.action.configure(state="disabled")
            self.build_button.configure(state="disabled")
            return
        self.options = options
        if self._order_refresh is not None:
            self._order_refresh()  # auto order follows the menu entries
        state = "normal" if self.process is None else "disabled"
        self.action.configure(state=state)
        self.build_button.configure(state=state)
        self._save()
        self._schedule_preview()

    def _save(self):
        try:
            self.bt.save_options(self.options, CONFIG_PATH, theme=self.themes[self.selected].key)
            self._set_config_status(self.t("config.saved", name=CONFIG_PATH.name), OK)
        except OSError as exc:
            self._set_config_status(self.t("config.not_saved", exc=exc), BAD)

    def reset_defaults(self):
        from tkinter import messagebox

        if messagebox.askyesno(self.t("reset.title"), self.t("reset.question")):
            self.options = self.bt.default_options()
            self._set_form(self.options)
            self.on_change()

    def import_config(self):
        from tkinter import filedialog, messagebox

        path = filedialog.askopenfilename(filetypes=[(self.t("file.settings"), "*.json")], parent=self.root)
        if not path:
            return
        try:
            if Path(path).stat().st_size > 1_000_000:
                raise ValueError(self.t("import.too_big"))
            raw = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
        except (OSError, ValueError, RecursionError) as exc:
            messagebox.showerror(self.t("import.title"), self.t("import.unreadable", exc=exc))
            return
        options, errors, warnings = self.bt.validate_options(raw)
        if errors or warnings:
            messagebox.showwarning(self.t("import.title"), self.t("import.fixed")
                                   + "\n".join((errors + warnings)[:12]))
        self._set_form(options)
        self.on_change()

    def export_config(self):
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=self.t("file.export_name"),
                                            filetypes=[(self.t("file.settings"), "*.json")], parent=self.root)
        if path:
            self.bt.save_options(self.options, Path(path), theme=self.themes[self.selected].key)
            self._set_config_status(self.t("config.exported", name=Path(path).name), OK)

    # ---- theme selection + live preview ----------------------------------
    def select(self, index: int):
        if self.process is not None:
            return
        self.selected = index
        theme = self.themes[index]
        for i, tile in enumerate(self.tiles):
            tile.configure(highlightbackground=theme.accent if i == index else PANEL)
        self.title_label.configure(text=theme.name.upper())
        self.desc_label.configure(text=f"{theme.description}   [--theme {theme.key}]")
        self.swatch.configure(bg=theme.accent)
        self.header_rule.configure(bg=theme.accent)
        self.ttk.Style(self.root).configure("Accent.Horizontal.TProgressbar", background=theme.accent,
                                            lightcolor=theme.accent, darkcolor=theme.accent)
        self.action.configure(bg=theme.accent, activebackground=theme.accent)
        # Instant feedback from the stored preview, then the live render replaces it.
        if theme.preview:
            from PIL import Image
            with Image.open(theme.preview) as img:
                self.preview_source = img.convert("RGB")
        self._show_preview()
        if not self.errors:
            self._save()
        self._schedule_preview(delay=50)

    def _schedule_preview(self, delay=500):
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(delay, self._start_preview)

    def _start_preview(self):
        self.preview_job = None
        self.preview_generation += 1
        generation, theme, options = self.preview_generation, self.themes[self.selected].key, dict(self.options)
        self.preview.delete("busy")
        self.preview.create_text(16, 16, text=self.t("preview.rendering"), fill=DIM, anchor="nw",
                                 font=("Consolas", 10), tags="busy")

        def work():
            try:
                image = self.bt.render_preview(theme, options, width=1280)
                self.previews.put((generation, image, None))
            except Exception as exc:  # preview problems must never block the user
                self.previews.put((generation, None, exc))
        threading.Thread(target=work, daemon=True).start()

    def _show_preview(self):
        box_w, box_h = self.preview.winfo_width(), self.preview.winfo_height()
        if box_w < 50 or box_h < 50 or self.preview_source is None:
            return
        width = min(box_w, round(box_h * 16 / 9))
        self.preview_image = photo_from_image(self.tk, self.preview_source, (width, round(width * 9 / 16)))
        self.preview.delete("img")
        self.preview.create_image(box_w // 2, box_h // 2, image=self.preview_image, tags="img")
        self.preview.tag_raise("busy")

    # ---- install --------------------------------------------------------
    def _append(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def install(self, with_install: bool = True):
        if self.process is not None:
            return
        if self.errors:
            self.notebook.select(0)
            self.status.configure(text=self.t("status.fix_errors"), fg=BAD)
            return
        self._save()
        theme = self.themes[self.selected]
        self.with_install = with_install
        command = build_command(theme.key, install=with_install, dry_run=self.dry_run.get(),
                                config=CONFIG_PATH)
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        if self.askpass is not None:
            env["SUDO_ASKPASS"] = str(self.askpass)
        self.notebook.select(0)
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._append(f"$ {' '.join(command[2:])}\n")
        try:
            self.process = subprocess.Popen(
                command, cwd=ENGINE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except OSError as exc:
            self._finish(self.t("status.start_failed", exc=exc), ok=False)
            return
        self.stopped = False
        self.action.configure(state="disabled")
        self.build_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        key = "status.building_install" if with_install else "status.building"
        self.status.configure(text=self.t(key, name=theme.name), fg=TEXT)
        threading.Thread(target=self._reader, args=(self.process,), daemon=True).start()

    def _reader(self, process: subprocess.Popen[str]):
        assert process.stdout is not None
        for line in process.stdout:
            self.lines.put(line)
        process.wait()
        self.lines.put(None)

    def _drain_queues(self):
        try:
            while True:
                line = self.lines.get_nowait()
                if line is None:
                    code = self.process.returncode if self.process else -1
                    if self.stopped:
                        self._finish(self.t("status.stopped"), ok=False)
                    elif code == 0:
                        if self.dry_run.get():
                            message = self.t("status.dry_run_done")
                        elif self.with_install:
                            message = self.t("status.installed")
                        else:
                            message = self.t("status.built", path=ENGINE / "dist" / DEFAULT_THEME)
                        self._finish(message, ok=True)
                    else:
                        self._finish(self.t("status.failed", code=code), ok=False)
                else:
                    self._append(line)
        except queue.Empty:
            pass
        try:
            while True:
                generation, image, error = self.previews.get_nowait()
                if generation != self.preview_generation:
                    continue  # an older render finished after a newer one started
                self.preview.delete("busy")
                if error is not None:
                    self.preview.create_text(16, 16, text=self.t("preview.unavailable", error=error), fill=BAD,
                                             anchor="nw", font=("Consolas", 10), tags="busy")
                else:
                    self.preview_source = image
                    self._show_preview()
        except queue.Empty:
            pass
        self.drain_job = self.root.after(80, self._drain_queues)

    def _finish(self, message: str, *, ok: bool):
        self.process = None
        self.progress.stop()
        state = "normal" if not self.errors else "disabled"
        self.action.configure(state=state)
        self.build_button.configure(state=state)
        self.stop_button.configure(state="disabled")
        self.status.configure(text=message, fg=OK if ok else BAD)

    def send_answer(self, _event=None):
        text = self.answer.get()
        self.answer.delete(0, "end")
        if self.process is not None and self.process.stdin is not None:
            self._append(f"> {text}\n")
            try:
                self.process.stdin.write(text + "\n")
                self.process.stdin.flush()
            except OSError:
                pass

    def stop(self):
        if self.process is not None:
            self.stopped = True
            self.process.terminate()
            self._append(self.t("log.stopped"))


def text_menu(themes: list[ThemeInfo]) -> int:
    """Fallback when tkinter is missing: numbered menu, preview via the desktop viewer."""
    lang = current_language()
    print(t("text.title", lang))
    print(t("text.advanced", lang, config=CONFIG_PATH.name, builder=BUILDER.name))
    for index, theme in enumerate(themes, 1):
        print(f"  {index:2}. {theme.name:<16} {theme.accent}  {theme.description}")
    while True:
        raw = input(t("text.prompt", lang)).strip().lower()
        if raw == "q":
            return 0
        if raw.startswith("p") and raw[1:].isdigit() and 1 <= int(raw[1:]) <= len(themes):
            preview = themes[int(raw[1:]) - 1].preview
            if preview:
                opener = "xdg-open" if IS_LINUX else "open" if sys.platform == "darwin" else None
                if opener:
                    subprocess.Popen([opener, str(preview)])
                else:
                    os.startfile(preview)  # type: ignore[attr-defined]
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(themes):
            theme = themes[int(raw) - 1]
            config = CONFIG_PATH if CONFIG_PATH.is_file() else None
            command = build_command(theme.key, install=True, dry_run=False, config=config)
            return subprocess.call(command, cwd=ENGINE)


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == ASKPASS_FLAG:
        return run_askpass(" ".join(sys.argv[2:]))
    themes = load_themes()
    try:
        import tkinter as tk
    except ImportError:
        print(t("main.no_tkinter", current_language()))
        return text_menu(themes)
    try:
        sys.path.insert(0, str(ENGINE))
        import build_and_deploy_theme as builder
        builder._require_pillow()
    except Exception as exc:  # noqa: BLE001 - explain instead of crashing
        print(t("main.no_builder", current_language(), exc=exc))
        return text_menu(themes)
    if os.name == "nt":
        try:  # crisp rendering on HiDPI Windows instead of a blurry bitmap stretch
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(t("main.no_display", current_language(), exc=exc))
        return text_menu(themes)
    Studio(root, themes, builder)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
