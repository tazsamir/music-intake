from pathlib import Path

from music_intake.core import is_supported_audio, parse_filename


def test_filename_parser_extracts_track_artist_and_title() -> None:
    parsed = parse_filename(Path("03 - Massive Attack - Teardrop.flac"))
    assert parsed.track == 3
    assert parsed.artist == "Massive Attack"
    assert parsed.title == "Teardrop"


def test_filename_parser_falls_back_safely_for_plain_name() -> None:
    parsed = parse_filename(Path("Unknown Song.mp3"))
    assert parsed.track is None
    assert parsed.artist == "Unknown Artist"
    assert parsed.title == "Unknown Song"


def test_extension_filter_is_case_insensitive() -> None:
    assert is_supported_audio(Path("song.FLAC"))
    assert is_supported_audio(Path("song.m4a"))
    assert not is_supported_audio(Path("cover.jpg"))
