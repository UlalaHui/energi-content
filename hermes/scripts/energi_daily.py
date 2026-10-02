"""Hermes cron launcher (no agent): runs the Energi daily reel run with the project's Python.
Lives in %LOCALAPPDATA%\\hermes\\scripts\\ because Hermes only runs cron scripts from there.
The run sends its own Telegram messages; this prints nothing on success (silent tick)."""
import os
import subprocess
import sys

PY = r"C:\Program Files\Python311\python.exe"
RUN = r"C:\Users\User\energi-content\scripts\daily_run.py"

env = dict(os.environ, PYTHONIOENCODING="utf-8")
for extra in (r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")):
    if os.path.isdir(extra) and extra not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + os.pathsep + extra
r = subprocess.run([PY, RUN] + sys.argv[1:], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
if r.returncode != 0:
    print("Energi daily run failed:\n" + (r.stderr or r.stdout)[-1500:])
    sys.exit(1)
