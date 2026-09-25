import stat
from pathlib import Path

from music_intake.core import Config, IntakeEngine


def test_quiet_autotag_skip_uses_filename_fallback(tmp_path: Path) -> None:
    album = tmp_path / "downloads" / "Artist" / "Album"
    album.mkdir(parents=True)
    source = album / "01 - Artist - Song.flac"
    source.write_bytes(b"audio")
    fake = tmp_path / "beet"
    fake.write_text("""#!/usr/bin/env python3
import pathlib, shutil, sys
if '--noautotag' not in sys.argv:
    print('Skipping.')
    raise SystemExit(0)
src = pathlib.Path(sys.argv[-1])
config = pathlib.Path(sys.argv[sys.argv.index('-c') + 1])
shutil.copytree(src, config.parent / src.name, dirs_exist_ok=True)
""")
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
    config = Config(album.parent.parent, tmp_path / "library", tmp_path / "status.json", beet=str(fake))
    assert IntakeEngine(config).process_group(album, [source])
    assert (config.library / "Album" / source.name).exists()
