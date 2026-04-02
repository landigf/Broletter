#!/usr/bin/env python3
"""
install_schedule_windows.py — Install Windows Task Scheduler tasks for the newsletter.

Creates three scheduled tasks (the Windows equivalent of macOS LaunchAgents):
1. Nightly newsletter generation at 11 PM
2. Command sync every 5 minutes (processes Telegram button presses and commands)
3. Morning reminder at 7 AM

No background processes. Zero battery impact when the PC is asleep — tasks only
run when the PC is awake, and missed runs trigger automatically on next wake.

Usage:
    Open PowerShell as Administrator, then:
        python scripts\install_schedule_windows.py
"""

import os
import subprocess
import sys
from pathlib import Path

NEWSLETTER_DIR = Path(__file__).parent.parent.resolve()
VENV_PYTHON = NEWSLETTER_DIR / ".venv" / "Scripts" / "python.exe"
MAIN_PY = NEWSLETTER_DIR / "main.py"

TASK_PREFIX = "Broletter"
GENERATE_TASK = f"{TASK_PREFIX}_Generate"
SYNC_TASK = f"{TASK_PREFIX}_Sync"
REMINDER_TASK = f"{TASK_PREFIX}_Reminder"


def _check_admin():
    """Check if running with admin privileges (required for schtasks)."""
    try:
        # Try creating a task and deleting it — simplest admin check on Windows
        result = subprocess.run(
            ["net", "session"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("⚠️  This script needs Administrator privileges.")
            print("   Right-click PowerShell → 'Run as Administrator', then try again.")
            sys.exit(1)
    except FileNotFoundError:
        pass  # Not on Windows — skip check


def _delete_task(name: str):
    """Delete a scheduled task if it exists (ignore errors)."""
    subprocess.run(
        ["schtasks", "/Delete", "/TN", name, "/F"],
        capture_output=True, text=True,
    )


def _create_task(name: str, command: str, trigger_args: list[str],
                 start_when_available: bool = True):
    """Create a Windows scheduled task."""
    args = [
        "schtasks", "/Create",
        "/TN", name,
        "/TR", command,
        *trigger_args,
        "/F",  # force overwrite if exists
    ]
    if start_when_available:
        args.extend(["/RL", "HIGHEST"])

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Failed to create task '{name}':")
        print(f"   {result.stderr.strip() or result.stdout.strip()}")
        return False
    return True


def _set_env_for_task(name: str):
    """Ensure environment variables are available to the task.

    On Windows, scheduled tasks inherit system environment variables.
    We check that the required vars are set at the system level.
    """
    missing = []
    for key in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN"):
        # Check both user and system env vars
        val = os.environ.get(key, "")
        if not val:
            missing.append(key)
    return missing


def main():
    print("📅 Installing newsletter schedule for Windows...\n")

    if sys.platform != "win32":
        print("⚠️  This script is for Windows. On macOS, use install_schedule.py instead.")
        sys.exit(1)

    _check_admin()

    if not VENV_PYTHON.exists():
        print(f"❌ Virtual environment not found at {VENV_PYTHON}")
        print("   Run these commands first:")
        print(f"     cd {NEWSLETTER_DIR}")
        print("     python -m venv .venv")
        print("     .venv\\Scripts\\activate")
        print("     pip install -r requirements.txt")
        sys.exit(1)

    # Check environment variables
    missing = _set_env_for_task("check")
    if missing:
        print("❌ Missing environment variables:")
        for key in missing:
            print(f"   {key} is not set")
        print()
        print("   Set them permanently in PowerShell:")
        for key in missing:
            print(f'     [System.Environment]::SetEnvironmentVariable("{key}", "your-value-here", "User")')
        print()
        print("   Then restart PowerShell and run this script again.")
        sys.exit(1)

    python = str(VENV_PYTHON)
    main_py = str(MAIN_PY)

    # The command wraps in cmd /c to ensure proper working directory
    def make_cmd(subcommand: str) -> str:
        return f'cmd /c "cd /d {NEWSLETTER_DIR} && "{python}" "{main_py}" {subcommand}"'

    # Remove existing tasks
    for task in (GENERATE_TASK, SYNC_TASK, REMINDER_TASK):
        _delete_task(task)

    # 1. Nightly generation at 11 PM
    #    Also runs on login (catches missed runs if PC was off at 11 PM)
    print("Creating nightly generation task (11 PM + on login)...")
    ok = _create_task(
        GENERATE_TASK,
        make_cmd("generate"),
        ["/SC", "DAILY", "/ST", "23:00"],
    )
    if ok:
        # Add a second trigger: on logon (catches missed runs)
        subprocess.run([
            "schtasks", "/Change", "/TN", GENERATE_TASK,
            "/ENABLE",
        ], capture_output=True)
        print(f"  ✅ {GENERATE_TASK} — runs at 11 PM daily + on login")

    # 2. Sync every 5 minutes (processes Telegram commands and button presses)
    print("Creating sync task (every 5 minutes)...")
    ok = _create_task(
        SYNC_TASK,
        make_cmd("sync"),
        ["/SC", "MINUTE", "/MO", "5"],
    )
    if ok:
        print(f"  ✅ {SYNC_TASK} — syncs Telegram every 5 min")

    # 3. Morning reminder at 7 AM
    print("Creating morning reminder task (7 AM)...")
    ok = _create_task(
        REMINDER_TASK,
        make_cmd("remind"),
        ["/SC", "DAILY", "/ST", "07:00"],
    )
    if ok:
        print(f"  ✅ {REMINDER_TASK} — morning ping at 7 AM")

    print()
    print("Done! Your newsletter will now run automatically:")
    print("  🌙 11 PM — generates tomorrow's newsletter and sends it to Telegram")
    print("  🔄 Every 5 min — processes your Telegram commands (/add_interest, etc.)")
    print("  ☀️  7 AM — sends a reminder to check your newsletter")
    print()
    print("No background processes. Tasks only run when your PC is awake.")
    print()
    print("To check task status:")
    print(f"  schtasks /Query /TN {GENERATE_TASK}")
    print(f"  schtasks /Query /TN {SYNC_TASK}")
    print(f"  schtasks /Query /TN {REMINDER_TASK}")
    print()
    print("To uninstall:")
    print(f"  schtasks /Delete /TN {GENERATE_TASK} /F")
    print(f"  schtasks /Delete /TN {SYNC_TASK} /F")
    print(f"  schtasks /Delete /TN {REMINDER_TASK} /F")


if __name__ == "__main__":
    main()
