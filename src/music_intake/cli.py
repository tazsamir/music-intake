"""Command-line daemon for music intake."""

from __future__ import annotations

import argparse
import os
import time
from collections.abc import Mapping
from pathlib import Path

from .core import Config, IntakeEngine


def config_from_env(environment: Mapping[str, str] | None = None) -> tuple[Config, int]:
    env = os.environ if environment is None else environment
    config = Config(
        downloads=Path(env.get("DOWNLOADS_PATH", "/downloads")),
        library=Path(env.get("LIBRARY_PATH", "/music")),
        status_file=Path(env.get("STATUS_FILE", "/state/status.json")),
        beet=env.get("BEET_EXECUTABLE", "beet"),
        stable_observations=int(env.get("STABLE_OBSERVATIONS", "3")),
    )
    return config, int(env.get("SCAN_INTERVAL", "60"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy stable music downloads into a Beets library")
    parser.add_argument("--once", action="store_true", help="scan once and exit")
    args = parser.parse_args()
    config, interval = config_from_env()
    engine = IntakeEngine(config)
    if args.once:
        engine.scan_once()
        return
    engine._write_status("starting")
    while True:
        engine.scan_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()