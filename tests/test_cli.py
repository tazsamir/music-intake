from pathlib import Path

from music_intake.cli import config_from_env
from music_intake.core import IntakeEngine


def test_environment_configures_paths_and_timing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "in"))
    monkeypatch.setenv("LIBRARY_PATH", str(tmp_path / "out"))
    monkeypatch.setenv("STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("SCAN_INTERVAL", "17")
    monkeypatch.setenv("STABLE_OBSERVATIONS", "3")
    config, interval = config_from_env()
    assert config.downloads == tmp_path / "in"
    assert config.library == tmp_path / "out"
    assert config.stable_observations == 3
    assert interval == 17


def test_scan_recurses_filters_and_waits_for_stability(monkeypatch, tmp_path: Path) -> None:
    album = tmp_path / "in" / "Artist" / "Album"
    album.mkdir(parents=True)
    song = album / "01 - Artist - Song.flac"
    song.write_bytes(b"audio")
    (album / "cover.jpg").write_bytes(b"image")
    config, _ = config_from_env({
        "DOWNLOADS_PATH": str(tmp_path / "in"),
        "LIBRARY_PATH": str(tmp_path / "out"),
        "STATUS_FILE": str(tmp_path / "status.json"),
        "STABLE_OBSERVATIONS": "2",
        "BEET_EXECUTABLE": "beet",
    })
    engine = IntakeEngine(config)
    calls = []
    monkeypatch.setattr(engine, "process_group", lambda group, files: calls.append((group, list(files))) or True)
    assert engine.scan_once() == 0
    assert engine.scan_once() == 1
    assert calls == [(album, [song])]
    assert engine.scan_once() == 0
