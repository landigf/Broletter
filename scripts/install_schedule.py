#!/usr/bin/env python3
"""
install_schedule.py — Install macOS LaunchAgent for nightly newsletter + morning reminder.

Creates two LaunchAgents:
1. Nightly newsletter generation at 11 PM
2. Morning reminder at login/wake (RunAtLoad) — pings Telegram so you see it on the bus

No persistent listener needed — feedback is fetched from Telegram right before generating.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

NEWSLETTER_DIR = Path(__file__).parent.parent.resolve()
VENV_PYTHON = NEWSLETTER_DIR / ".venv" / "bin" / "python"
BOOTSTRAP_PY = NEWSLETTER_DIR / "scripts" / "launch_main.py"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"


def _find_stable_python() -> Path:
    """Find a Python interpreter path that survives Homebrew upgrades.

    Problem: sys._base_executable resolved via .resolve() gives a path like
    /opt/homebrew/Cellar/python@3.13/3.13.7/.../python3.13 — this breaks
    when `brew upgrade python` bumps the version (3.13.7 → 3.13.12 etc.).

    Solution: prefer the stable /opt/homebrew/bin/python3.X symlink, which
    Homebrew always keeps pointing at the current Cellar version.
    Fallback: shutil.which('python3'), then sys.executable.
    """
    # The venv records which interpreter created it — use that version
    venv_python = NEWSLETTER_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        # Read the version from the venv's python
        try:
            result = subprocess.run(
                [str(venv_python), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                capture_output=True, text=True, check=True,
            )
            ver = result.stdout.strip()
        except Exception:
            ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    else:
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Prefer stable Homebrew symlink (survives `brew upgrade`)
    homebrew_stable = Path(f"/opt/homebrew/bin/python{ver}")
    if homebrew_stable.exists():
        return homebrew_stable

    # Fallback: /usr/local/bin (Intel Mac Homebrew or python.org install)
    usrlocal = Path(f"/usr/local/bin/python{ver}")
    if usrlocal.exists():
        return usrlocal

    # Fallback: whatever is on PATH
    found = shutil.which(f"python{ver}") or shutil.which("python3")
    if found:
        return Path(found)

    # Last resort: sys executable (may be a pyenv shim, but better than nothing)
    return Path(getattr(sys, "_base_executable", sys.executable))


BASE_PYTHON = _find_stable_python()

GENERATE_LABEL = "com.botletter.generate"
REMINDER_LABEL = "com.botletter.reminder"
SYNC_LABEL = "com.botletter.sync"

# Legacy labels to clean up
LEGACY_LABELS = [
    "com.Broletter.generate",
    "com.Broletter.reminder",
    "com.Broletter.sync",
    "com.gennaro.newsletter.generate",
    "com.gennaro.newsletter.reminder",
    "com.gennaro.newsletter.sync",
    "com.gennaro.newsletter.listener",
]


def get_env_vars() -> dict[str, str]:
    """Collect required env vars."""
    env = {}
    for key in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN"):
        val = os.environ.get(key, "")
        if not val:
            print(f"❌ {key} not set in environment. Set it first.")
            sys.exit(1)
        env[key] = val
    env["PYTHONUNBUFFERED"] = "1"
    env["PATH"] = ":".join(
        [
            str(BASE_PYTHON.parent),
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]
    )
    return env


def write_plist(label: str, args: list[str], env: dict, calendar: dict | None = None, keep_alive: bool = False, run_at_load: bool = False, interval_seconds: int | None = None):
    """Write a LaunchAgent plist file."""
    plist_path = LAUNCH_AGENTS_DIR / f"{label}.plist"

    env_xml = ""
    for k, v in env.items():
        env_xml += f"""\
            <key>{k}</key>
            <string>{v}</string>
"""

    args_xml = ""
    for a in args:
        args_xml += f"            <string>{a}</string>\n"

    schedule_xml = ""
    if calendar:
        schedule_xml = """\
        <key>StartCalendarInterval</key>
        <dict>
"""
        for k, v in calendar.items():
            schedule_xml += f"""\
            <key>{k}</key>
            <integer>{v}</integer>
"""
        schedule_xml += "        </dict>"
    elif interval_seconds:
        schedule_xml = f"""\
        <key>StartInterval</key>
        <integer>{interval_seconds}</integer>"""

    keepalive_xml = ""
    if keep_alive:
        keepalive_xml = """\
        <key>KeepAlive</key>
        <true/>"""

    runatload_xml = ""
    if run_at_load:
        runatload_xml = """\
        <key>RunAtLoad</key>
        <true/>"""

    plist = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}\
    </array>
    <key>WorkingDirectory</key>
    <string>{NEWSLETTER_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
{env_xml}\
    </dict>
    {schedule_xml}
    {keepalive_xml}
    {runatload_xml}
    <key>StandardOutPath</key>
    <string>/tmp/{label}.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/{label}.err</string>
</dict>
</plist>
"""

    plist_path.write_text(plist)
    return plist_path


def _launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
    )


def _unload_plist(plist: Path):
    domain = f"gui/{os.getuid()}"
    _launchctl("bootout", domain, str(plist))
    _launchctl("unload", str(plist))


def _load_plist(plist: Path):
    domain = f"gui/{os.getuid()}"
    result = _launchctl("bootstrap", domain, str(plist))
    if result.returncode == 0:
        return

    legacy = _launchctl("load", str(plist))
    if legacy.returncode == 0:
        return

    raise RuntimeError(
        f"launchctl failed for {plist.name}\n"
        f"bootstrap: {result.stderr.strip() or result.stdout.strip()}\n"
        f"load: {legacy.stderr.strip() or legacy.stdout.strip()}"
    )


def main():
    print("📅 Installing newsletter schedule...\n")

    if not VENV_PYTHON.exists():
        print(f"❌ Virtual env not found at {VENV_PYTHON}")
        print("   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt")
        sys.exit(1)
    if not BOOTSTRAP_PY.exists():
        print(f"❌ Bootstrap script not found at {BOOTSTRAP_PY}")
        sys.exit(1)
    if not BASE_PYTHON.exists():
        print(f"❌ Base Python not found at {BASE_PYTHON}")
        sys.exit(1)

    env = get_env_vars()
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    python = str(BASE_PYTHON)
    bootstrap_py = str(BOOTSTRAP_PY)

    # Unload existing (ignore errors) — includes legacy labels.
    for label in (GENERATE_LABEL, REMINDER_LABEL, SYNC_LABEL, *LEGACY_LABELS):
        plist = LAUNCH_AGENTS_DIR / f"{label}.plist"
        if plist.exists():
            _unload_plist(plist)
            if label in LEGACY_LABELS:
                plist.unlink()
                print(f"🗑  Removed legacy agent: {label}")

    # 1. Nightly newsletter generation at 11 PM + RunAtLoad fallback
    #    Fetches pending feedback from Telegram, then generates & sends.
    #    RunAtLoad catches missed 11 PM runs (Mac was asleep).
    #    Idempotent: skips if already generated+sent, retries send if generated but not sent.
    gen_path = write_plist(
        GENERATE_LABEL,
        [python, bootstrap_py, "generate"],
        env,
        calendar={"Hour": 23, "Minute": 0},
        run_at_load=True,
    )
    _load_plist(gen_path)
    print(f"✅ Nightly generation (11 PM + retry at wake) → {gen_path}")

    # 2. Periodic sync — fetches & processes Telegram commands every 5 min
    #    Handles /add_interest, /add_topic, /config etc. and replies.
    #    Also answers callback queries (reaction buttons) so users don't see a spinner.
    #    Single HTTP call, <1s, negligible battery.
    sync_path = write_plist(
        SYNC_LABEL,
        [python, bootstrap_py, "sync"],
        env,
        interval_seconds=300,  # 5 minutes
    )
    _load_plist(sync_path)
    print(f"✅ Command sync (every 5 min) → {sync_path}")

    # 3. Morning reminder — checks every 30 min + at login
    #    Sends a short Telegram ping so you see the newsletter on the bus.
    #    The remind command has a 5 AM–2 PM guard, so it only actually sends
    #    during morning hours. Outside that window it silently skips.
    rem_path = write_plist(
        REMINDER_LABEL,
        [python, bootstrap_py, "remind"],
        env,
        interval_seconds=1800,  # 30 minutes — morning guard handles the rest
        run_at_load=True,
    )
    _load_plist(rem_path)
    print(f"✅ Morning reminder (at wake/login) → {rem_path}")

    print("\nDone! Flow:")
    print("  🌙 11 PM — fetches your feedback, generates tomorrow's newsletter, sends it")
    print("  ☀️  Wake  — pings you on Telegram: 'your newsletter is waiting'")
    print("  🚌  Bus   — read it, tap reactions")
    print("  🔄  Every 30 min — processes /add_interest, /config etc. and replies")
    print("\nNo background processes. Zero battery impact when Mac is asleep.")
    print(f"\nLogs:")
    print(f"  /tmp/{GENERATE_LABEL}.log")
    print(f"  /tmp/{SYNC_LABEL}.log")
    print(f"  /tmp/{REMINDER_LABEL}.log")
    print("\nTo uninstall:")
    print(f"  launchctl unload {gen_path}")
    print(f"  launchctl unload {rem_path}")
    print(f"  launchctl unload {sync_path}")


if __name__ == "__main__":
    main()
