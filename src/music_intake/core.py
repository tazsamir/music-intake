"""Core intake behavior."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = frozenset({".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".aiff", ".alac", ".wma"})


@dataclass(frozen=True)
class ParsedTrack:
    track: int | None
    artist: str
    title: str


@dataclass(frozen=True)
class Config:
    downloads: Path
    library: Path
    status_file: Path
    beet: str = "beet"
    stable_observations: int = 2


class StabilityTracker:
    def __init__(self, required_observations: int = 2) -> None:
        self.required_observations = required_observations
        self._seen: dict[Path, tuple[int, int, int]] = {}

    def observe(self, path: Path) -> bool:
        current = (path.stat().st_size, path.stat().st_mtime_ns)
        previous = self._seen.get(path)
        count = previous[2] + 1 if previous and previous[:2] == current else 1
        self._seen[path] = (*current, count)
        return count >= self.required_observations


def album_key(path: Path) -> Path:
    return path.parent


def build_beet_command(beet: str, source: Path, library: Path, *, autotag: bool = True) -> list[str]:
    config = library / ".beets-config.yaml"
    command = [beet, "-c", str(config), "import", "--quiet"]
    if not autotag:
        command.append("--noautotag")
    return [*command, str(source)]


class IntakeEngine:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.tracker = StabilityTracker(config.stable_observations)
        self.processed: set[Path] = set()

    def _write_status(self, status: str, **extra: object) -> None:
        self.config.status_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.config.status_file.with_suffix(".tmp")
        temporary.write_text(json.dumps({"status": status, **extra}, indent=2) + "\n")
        temporary.replace(self.config.status_file)

    def process_group(self, group: Path, files: Iterable[Path]) -> bool:
        sources = list(files)
        self.config.library.mkdir(parents=True, exist_ok=True)
        beets_config = self.config.library / ".beets-config.yaml"
        if not beets_config.exists():
            beets_config.write_text(f"directory: {self.config.library}\nimport:\n  copy: yes\n  move: no\n")
        for autotag in (True, False):
            command = build_beet_command(self.config.beet, group, self.config.library, autotag=autotag)
            try:
                completed = subprocess.run(command, check=False, capture_output=True, text=True)
            except OSError as error:
                self._write_status("error", error=str(error), source=str(group))
                return False
            skipped = "skipping." in (completed.stdout + completed.stderr).lower()
            if completed.returncode == 0 and not skipped:
                self._write_status("ok", source=str(group), files=len(sources), fallback=not autotag)
                return True
        self._write_status("error", error=completed.stderr.strip() or "beets import failed", source=str(group))
        return False

    def scan_once(self) -> int:
        groups: dict[Path, list[Path]] = {}
        if not self.config.downloads.exists():
            self._write_status("ok", message="downloads path does not exist", processed=0)
            return 0
        for path in sorted(self.config.downloads.rglob("*")):
            if path.is_file() and is_supported_audio(path) and path not in self.processed:
                groups.setdefault(path.parent, []).append(path)
        completed = 0
        for group, files in groups.items():
            if all(self.tracker.observe(path) for path in files) and self.process_group(group, files):
                self.processed.update(files)
                completed += 1
        return completed


def is_supported_audio(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def parse_filename(path: Path) -> ParsedTrack:
    stem = path.stem.strip()
    match = re.match(r"^(\d{1,3})\s*[-_.]\s*(.+?)\s+-\s+(.+)$", stem)
    if match:
        return ParsedTrack(int(match.group(1)), match.group(2).strip(), match.group(3).strip())
    return ParsedTrack(None, "Unknown Artist", stem or "Unknown Track")
