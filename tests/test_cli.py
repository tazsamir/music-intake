from pathlib import Path

from music_intake.cli import config_from_env
from music_intake.core import IntakeEngine


def test_environment_configures_paths_and_timing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DOWNLOADS_PATH", str(tmp_path / "in"))
    monkeypatch.setenv("LIBRARY_PATH", str(tmp_path / "out"))
    monkeypatch.setenv("STATUS_FILE", str(tmp_path / "status.json"))
    monkeypatch.setenv("PROCESSED_FILE", str(tmp_path / "processed.json"))
    monkeypatch.setenv("SCAN_INTERVAL", "17")
    monkeypatch.setenv("STABLE_OBSERVATIONS", "3")
    config, interval = config_from_env()
    assert config.downloads == tmp_path / "in"
    assert config.library == tmp_path / "out"
    assert config.processed_file == tmp_path / "processed.json"
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


def test_processed_files_survive_daemon_restart(monkeypatch, tmp_path: Path) -> None:
    album = tmp_path / "in" / "Artist" / "Album"
    album.mkdir(parents=True)
    song = album / "01 - Artist - Song.flac"
    song.write_bytes(b"audio")
    env = {
        "DOWNLOADS_PATH": str(tmp_path / "in"),
        "LIBRARY_PATH": str(tmp_path / "out"),
        "STATUS_FILE": str(tmp_path / "state" / "status.json"),
        "PROCESSED_FILE": str(tmp_path / "state" / "processed.json"),
        "STABLE_OBSERVATIONS": "1",
    }
    config, _ = config_from_env(env)
    first = IntakeEngine(config)
    first_calls = []
    monkeypatch.setattr(first, "process_group", lambda group, files: first_calls.append(group) or True)
    assert first.scan_once() == 1
    assert first_calls == [album]

    second = IntakeEngine(config)
    second_calls = []
    monkeypatch.setattr(second, "process_group", lambda group, files: second_calls.append(group) or True)
    assert second.scan_once() == 0
    assert second_calls == []


def test_changed_processed_file_is_imported_again(monkeypatch, tmp_path: Path) -> None:
    album = tmp_path / "in" / "Artist" / "Album"
    album.mkdir(parents=True)
    song = album / "01 - Artist - Song.flac"
    song.write_bytes(b"first")
    env = {
        "DOWNLOADS_PATH": str(tmp_path / "in"),
        "LIBRARY_PATH": str(tmp_path / "out"),
        "STATUS_FILE": str(tmp_path / "state" / "status.json"),
        "PROCESSED_FILE": str(tmp_path / "state" / "processed.json"),
        "STABLE_OBSERVATIONS": "1",
    }
    config, _ = config_from_env(env)
    first = IntakeEngine(config)
    monkeypatch.setattr(first, "process_group", lambda group, files: True)
    assert first.scan_once() == 1

    song.write_bytes(b"changed audio")
    second = IntakeEngine(config)
    calls = []
    monkeypatch.setattr(second, "process_group", lambda group, files: calls.append(group) or True)
    assert second.scan_once() == 1
    assert calls == [album]
