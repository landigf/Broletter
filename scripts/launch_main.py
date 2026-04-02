#!/usr/bin/env python3
"""
launch_main.py — run main.py from the base interpreter with venv packages added.

This avoids macOS LaunchAgent crashes in Python's venv startup path while keeping
the project dependencies isolated in .venv.
"""

from __future__ import annotations

import os
import runpy
import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"


def _find_site_packages() -> Path:
    lib_dir = VENV_DIR / "lib"
    if not lib_dir.exists():
        raise RuntimeError(f"Virtualenv lib directory not found: {lib_dir}")

    wanted = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = sorted(lib_dir.glob("python*/site-packages"))
    if not candidates:
        raise RuntimeError(f"No site-packages directory found under {lib_dir}")

    for candidate in candidates:
        if candidate.parent.name == wanted:
            return candidate
    return candidates[-1]


def main():
    if not VENV_DIR.exists():
        raise RuntimeError(f"Virtualenv not found: {VENV_DIR}")

    os.chdir(ROOT)
    os.environ.setdefault("VIRTUAL_ENV", str(VENV_DIR))
    os.environ["PATH"] = os.pathsep.join(
        [str(VENV_DIR / "bin"), os.environ.get("PATH", "")]
    ).strip(os.pathsep)

    site_packages = _find_site_packages()
    site.addsitedir(str(site_packages))

    if str(site_packages) in sys.path:
        sys.path.remove(str(site_packages))
        sys.path.insert(0, str(site_packages))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    sys.argv = [str(ROOT / "main.py"), *sys.argv[1:]]
    runpy.run_path(str(ROOT / "main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
