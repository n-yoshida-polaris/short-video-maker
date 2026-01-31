from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from typing import List


DEFAULT_CHANNELS_DIR = os.path.join(os.getcwd(), "channels")


def find_yaml_files(channels_dir: str) -> List[str]:
    patterns = ["*.yaml", "*.yml"]
    files: List[str] = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(channels_dir, p)))
    # Stable order
    files.sort()
    return files


def run_channel(yaml_path: str, limit: int | None = None, python_exe: str | None = None) -> int:
    py = python_exe or sys.executable
    cmd = [py, "-m", "svmu.main", "--config", yaml_path]
    if limit is not None:
        cmd += ["--limit", str(limit)]

    print(f"\n[RUN] Channel: {os.path.basename(yaml_path)} -> {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except FileNotFoundError as e:
        print(f"[ERROR] Python not found or command failed to start: {e}")
        return 127


def main():
    parser = argparse.ArgumentParser(description="Run ShortVideoMaker for multiple channels (YAML per channel)")
    parser.add_argument("--channels-dir", default=DEFAULT_CHANNELS_DIR, help="Directory containing *.yaml per channel")
    parser.add_argument("--limit", type=int, default=None, help="Optional per-channel row limit")
    parser.add_argument("--dry-run", action="store_true", help="List YAMLs without running")

    args = parser.parse_args()

    channels_dir = os.path.abspath(args.channels_dir)
    if not os.path.isdir(channels_dir):
        print(f"[WARN] Channels directory not found: {channels_dir}")
        print("Create it and put one YAML per channel. Using config.yaml.example as a baseline.")
        return

    yaml_files = find_yaml_files(channels_dir)
    if not yaml_files:
        print(f"[INFO] No YAML files found in {channels_dir}. Nothing to run.")
        return

    print(f"[INFO] Found {len(yaml_files)} channel YAML(s).")
    for y in yaml_files:
        print(f" - {os.path.basename(y)}")

    if args.dry_run:
        print("[DRY-RUN] Completed listing. Exiting without running.")
        return

    failed = 0
    for y in yaml_files:
        code = run_channel(y, limit=args.limit)
        if code != 0:
            failed += 1
            print(f"[ERROR] Channel failed: {os.path.basename(y)} (exit={code})")
        else:
            print(f"[OK] Channel completed: {os.path.basename(y)}")

    print(f"\n[SUMMARY] Total: {len(yaml_files)}, OK: {len(yaml_files)-failed}, NG: {failed}")
    # Return non-zero if any failed (useful for CI/cron monitoring)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
