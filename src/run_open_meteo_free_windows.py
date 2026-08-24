#!/usr/bin/env python3
"""Reanuda la extracción en ventanas diarias gratuitas hasta completarla."""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "results/open_meteo_extraction/free_window_runner_status.json"
LOG = ROOT / "results/open_meteo_extraction/free_window_runner.log"
PID = ROOT / "results/open_meteo_extraction/free_window_runner.pid"
EXPECTED_PARTS = 171


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def next_daily_window(now: datetime) -> datetime:
    tomorrow = (now + timedelta(days=1)).date()
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(minutes=5)


def append_log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"{utc_now().isoformat()} {message}\n")


def write_status(state: str, **extra) -> None:
    parts = len(list((ROOT / "data/processed/open_meteo_daily/parts").glob("*.parquet")))
    payload = {"timestamp_utc": utc_now().isoformat(), "state": state,
               "pid": os.getpid(), "completed_parts": parts, "expected_parts": EXPECTED_PARTS, **extra}
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wait_until(target: datetime) -> None:
    while True:
        remaining = (target - utc_now()).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 60))


def run_command(command: list[str]) -> int:
    append_log("RUN " + " ".join(command))
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if completed.stdout:
        append_log("STDOUT " + completed.stdout.strip().replace("\n", " | "))
    if completed.stderr:
        append_log("STDERR " + completed.stderr.strip().replace("\n", " | "))
    append_log(f"EXIT {completed.returncode}")
    return completed.returncode


def main() -> None:
    PID.parent.mkdir(parents=True, exist_ok=True)
    if PID.exists():
        try:
            existing = int(PID.read_text().strip())
            os.kill(existing, 0)
            raise SystemExit(f"Ya existe un reanudador activo con PID {existing}.")
        except (ValueError, ProcessLookupError):
            pass
    PID.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    try:
        while True:
            parts = len(list((ROOT / "data/processed/open_meteo_daily/parts").glob("*.parquet")))
            if parts >= EXPECTED_PARTS:
                write_status("auditing")
                code = run_command(["python", "src/audit_open_meteo_historical_extraction.py"])
                write_status("complete" if code == 0 else "audit_failed", audit_exit_code=code)
                return
            target = next_daily_window(utc_now())
            write_status("waiting_next_daily_window", next_attempt_utc=target.isoformat())
            append_log(f"WAIT until {target.isoformat()} ({parts}/{EXPECTED_PARTS} parts)")
            wait_until(target)
            write_status("extracting")
            code = run_command(["python", "src/extract_open_meteo.py", "--execute"])
            if code == 0:
                continue
            append_log("Extraction paused; next retry will use the next daily free window.")
    finally:
        PID.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
