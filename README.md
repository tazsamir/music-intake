# Music Intake

A small Python 3.12 daemon that watches a download tree, waits until audio files stop changing, groups tracks by album directory, and asks [Beets](https://beets.io/) to copy them into an organized music library. Confident metadata matches are imported automatically; if that import cannot complete, it retries safely without autotagging, preserving filename metadata. Sources are never moved or deleted.

## Quick start

```sh
cp .env.example .env
mkdir -p downloads music state
docker compose up --build -d
docker compose ps
cat state/status.json
```

Place completed downloads under `downloads/`, ideally as `Artist/Album/tracks`. Nested trees are scanned recursively. Supported formats are FLAC, MP3, M4A, AAC, OGG, Opus, WAV, AIFF, ALAC, and WMA.

Run one scan outside Docker with Python 3.12+:

```sh
python -m pip install -e . beets
DOWNLOADS_PATH=./downloads LIBRARY_PATH=./music STATUS_FILE=./state/status.json \
  music-intake --once
```

## Configuration

| Variable | Default | Purpose |
|---|---:|---|
| `DOWNLOADS_PATH` | `/downloads` | Read-only completed-download tree |
| `LIBRARY_PATH` | `/music` | Beets-managed destination |
| `STATUS_FILE` | `/state/status.json` | Atomic JSON status/health record |
| `SCAN_INTERVAL` | `60` | Seconds between scans |
| `STABLE_OBSERVATIONS` | `3` | Consecutive unchanged scans required |
| `PUID` / `PGID` | `1000` | Container process UID and GID |
| `BEET_EXECUTABLE` | `beet` | Beets executable, mainly for testing |

The download mount is read-only in Compose. Beets is configured with `copy: yes` and `move: no`; this app never deletes originals.

## Permissions and NFS

Set `PUID` and `PGID` to a numeric identity that can read downloads and write both library and state mounts (check with `id`). For NFS, use numeric IDs shared by client and server, grant that identity write access to the export, and avoid relying on container-root because `root_squash` commonly maps it to nobody. The entrypoint only changes ownership of `/state`; it does not recursively alter media mounts.

## Navidrome / Jellyfin

Mount the same output directory read-only in the media server. Example additions to an existing Compose deployment:

```yaml
services:
  navidrome:
    volumes:
      - ./music:/music:ro
  jellyfin:
    volumes:
      - ./music:/media/music:ro
```

Point Navidrome's music folder to `/music`, or add `/media/music` as a Jellyfin music library. The applications do not need access to downloads or state.

## Safety and legal use

Use this only for media you own or are authorized to copy. It does not download music and does not bypass access controls. Review your jurisdiction's copyright rules.

## Limitations

- Album grouping follows the immediate parent directory; poorly structured downloads may become separate imports.
- Stability uses size and modification time across scans, not downloader-specific completion events.
- Beets' quiet mode skips uncertain autotag matches; the fallback imports without autotagging and relies on filenames/tags.
- Processed paths are remembered in memory for the current daemon run. Existing library content and Beets' database prevent normal duplicate copies, but replacing a source while the daemon runs requires a restart.
- Artwork and fingerprint lookup depend on Beets plugins and network/service availability; core intake remains local.

## Development

```sh
python -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
.venv/bin/ruff check src tests
python -m compileall -q src
```

CI runs tests, lint/syntax checks, Compose validation, and an image build. Licensed under the [MIT License](LICENSE).
