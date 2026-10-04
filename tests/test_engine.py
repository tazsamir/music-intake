import json
import stat
from pathlib import Path

from music_intake.core import (
    Config,
    IntakeEngine,
    StabilityTracker,
    album_key,
    build_beet_command,
)


def test_stability_requires_unchanged_observations(tmp_path: Path) -> None:
    song = tmp_path / "song.flac"
    song.write_bytes(b"first")
    tracker = StabilityTracker(required_observations=2)
    assert not tracker.observe(song)
    song.write_bytes(b"changed-size")
    assert not tracker.observe(song)
    assert tracker.observe(song)


def test_album_classification_groups_tracks_by_parent() -> None:
    assert album_key(Path("Artist/Album/01 - A.flac")) == Path("Artist/Album")
    assert album_key(Path("loose.mp3")) == Path(".")


def test_beet_command_is_safe_and_noninteractive(tmp_path: Path) -> None:
    command = build_beet_command("/usr/bin/beet", tmp_path / "Album", tmp_path / "library")
    assert command == [
        "/usr/bin/beet", "-c", str(tmp_path / "library" / ".beets-config.yaml"),
        "import", "--quiet", str(tmp_path / "Album"),
    ]
    assert build_beet_command(
        "/usr/bin/beet", tmp_path / "Album", tmp_path / "library", autotag=False
    )[-2:] == ["--noautotag", str(tmp_path / "Album")]


def test_failed_beets_import_preserves_source_and_sets_error(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    album = downloads / "Artist" / "Album"
    album.mkdir(parents=True)
    source = album / "01 - Artist - Song.flac"
    source.write_bytes(b"audio")
    config = Config(downloads, tmp_path / "library", tmp_path / "state.json", beet="false")
    engine = IntakeEngine(config)
    result = engine.process_group(album, [source])
    assert not result
    assert source.exists()
    state = json.loads(config.status_file.read_text())
    assert state["status"] == "error"


def test_fake_beet_integration_copies_album_into_library(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    album = downloads / "Portishead" / "Dummy"
    album.mkdir(parents=True)
    source = album / "01 - Portishead - Mysterons.flac"
    source.write_bytes(b"owned audio")
    fake = tmp_path / "beet"
    fake.write_text("""#!/usr/bin/env python3
import pathlib, shutil, sys
src = pathlib.Path(sys.argv[-1])
config = pathlib.Path(sys.argv[sys.argv.index('-c') + 1])
dest = config.parent / src.name
shutil.copytree(src, dest, dirs_exist_ok=True)
""")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    config = Config(downloads, tmp_path / "library", tmp_path / "state.json", beet=str(fake))
    assert IntakeEngine(config).process_group(album, [source])
    copied = config.library / "Dummy" / source.name
    assert copied.read_bytes() == b"owned audio"
    assert source.exists()


def test_beets_database_is_stored_in_persistent_state(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    album = downloads / "Artist" / "Album"
    album.mkdir(parents=True)
    source = album / "01 - Artist - Song.flac"
    source.write_bytes(b"audio")
    config = Config(downloads, tmp_path / "library", tmp_path / "state" / "status.json", beet="true")
    assert IntakeEngine(config).process_group(album, [source])
    beets_config = (config.library / ".beets-config.yaml").read_text()
    assert f"library: {tmp_path / 'state' / 'library.db'}" in beets_config
