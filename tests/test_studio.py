"""Theme Studio tests: it starts in both languages and survives random input.

Needs a display (on a headless Linux run it under xvfb-run) and the theme/
submodule (git clone --recursive).
"""
from __future__ import annotations

import importlib
import json
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ROUNDS = int(os.environ.get("FUZZ_ROUNDS", "15"))
SEED = int(os.environ.get("FUZZ_SEED", str(random.randrange(1 << 30))))
TYPED = ["", " ", '"', "\\", "{", "}", "\n", "\x00", "死神核", "🔥", "-5", "1e999", "nan", "inf", "0",
         "3,5", "600", "abc", "12345678901234567890", "a" * 500, "#FF003C", "#GGGGGG"]


_ROOT = None


def studio_env(test: unittest.TestCase):
    """One shared Tk root per test run (re-creating Tk is flaky on Windows)."""
    global _ROOT
    try:
        import tkinter as tk
        if _ROOT is None:
            _ROOT = tk.Tk()
            _ROOT.withdraw()
    except Exception as exc:  # noqa: BLE001 - no display
        test.skipTest(f"no Tk display: {exc}")
    reset(_ROOT)
    import theme_studio as ts
    importlib.reload(ts)
    sys.path.insert(0, str(ts.ENGINE))
    import build_and_deploy_theme as builder
    return tk, _ROOT, ts, builder


def reset(root) -> None:
    """Cancel the Studio's pending timers, then remove its widgets."""
    for job in root.tk.splitlist(root.tk.call("after", "info")):
        root.after_cancel(job)
    for child in root.winfo_children():
        child.destroy()
    root.update()


def tearDownModule():
    if _ROOT is not None:
        _ROOT.destroy()


class StudioTests(unittest.TestCase):
    def test_engine_is_found(self):
        import theme_studio as ts
        self.assertTrue(ts.BUILDER.is_file(), f"theme engine missing - clone with --recursive ({ts.BUILDER})")
        self.assertTrue(ts.THEMES_DIR.is_dir())

    def test_starts_in_both_languages(self):
        for lang in ("en", "pl"):
            os.environ["GHOUL_LANG"] = lang
            tk, root, ts, builder = studio_env(self)
            with tempfile.TemporaryDirectory() as raw:
                ts.CONFIG_PATH = Path(raw) / "boot-config.json"
                errors: list[str] = []
                root.report_callback_exception = lambda *exc: errors.append(repr(exc[1]))
                try:
                    studio = ts.Studio(root, ts.load_themes(), builder)
                    root.report_callback_exception = lambda *exc: errors.append(repr(exc[1]))
                    for i in range(studio.notebook.index("end")):
                        studio.notebook.select(i)
                        root.update()
                    tabs = [studio.notebook.tab(i, "text") for i in range(studio.notebook.index("end"))]
                    self.assertIn("Install" if lang == "en" else "Instalacja", tabs)
                finally:
                    reset(root)
                self.assertEqual(errors, [])
        os.environ.pop("GHOUL_LANG", None)

    def test_random_input_never_breaks_the_studio(self):
        tk, root, ts, builder = studio_env(self)
        rng = random.Random(f"{SEED}-studio")
        crashes: list[str] = []
        root.report_callback_exception = lambda *exc: crashes.append(repr(exc[1]))
        print(f"\n[fuzz] seed={SEED} rounds={ROUNDS}")
        with tempfile.TemporaryDirectory() as raw:
            ts.CONFIG_PATH = Path(raw) / "boot-config.json"
            try:
                studio = ts.Studio(root, ts.load_themes(), builder)
                root.report_callback_exception = lambda *exc: crashes.append(repr(exc[1]))
                specs = {spec.key: spec for spec in builder.OPTION_SPECS}
                for i in range(ROUNDS * 8):
                    key = rng.choice(list(studio.fields))
                    spec, field = specs[key], studio.fields[key]
                    if spec.kind in {"int", "float", "text", "color", "choice"}:
                        value = rng.choice(TYPED)
                    elif spec.kind == "bool":
                        value = rng.choice([True, False])
                    elif spec.kind in {"multi", "order"}:
                        value = tuple(c for c in spec.choices if rng.random() < 0.5)
                    elif spec.kind == "lines":
                        value = tuple(rng.choice(TYPED) for _ in range(rng.randrange(0, 6)))
                    else:
                        continue
                    with self.subTest(case=i, key=key, value=repr(value)[:60], seed=SEED):
                        field["set"](value)
                        studio.on_change()
                        root.update()
                        if not studio.errors and ts.CONFIG_PATH.exists():
                            saved = json.loads(ts.CONFIG_PATH.read_text(encoding="utf-8"))
                            self.assertEqual(builder.validate_options(saved)[1], [])
            finally:
                reset(root)
        self.assertEqual(crashes, [])


if __name__ == "__main__":
    unittest.main()
