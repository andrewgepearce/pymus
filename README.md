# pymus

Terminal-first MP3 player with a split-pane ncurses UI. Browse your music folders on the left, manage a play queue on the right, and control playback with a handful of single-letter shortcuts. Playback uses VLC via `python-vlc`, ID3 tags are read with `mutagen`, and the current queue is persisted to `~/.pymus/playlist.json` so you can pick up where you left off.

## What it does

- Browses a root music folder (defaults to `/Users/andrewpearce/Google Drive/My Drive/music`, falls back to `~` if missing).
- Shows folders first, then MP3 files (only `.mp3` files are considered).
- Builds a play queue from a single track or an entire folder (recursively) and plays through VLC.
- Reads ID3 tags to show `Artist — Title (Album)` when available.
- Provides a two-pane ncurses UI with keyboard controls for navigation, queue management, and playback.
- Saves the queue and current index to `~/.pymus/playlist.json` when you exit; reloads it next launch (no autoplay).

## Keyboard controls

Left pane (browser):

- `j/k` or `↓/↑` move; `PgDown/PgUp` jump a page.
- `Enter` opens a folder or starts playing the selected track (queues the whole folder).
- `s` queue + start playing the selected folder (recursive) or current track.
- `a` append the selected folder (recursive) or track to the queue without interrupting playback.
- `/` start search mode on the current folder (type to filter; `Enter` accept, `Esc` cancel, `Backspace` delete, `Ctrl+U` clear).
- `b` go up one directory.

Right pane (queue):

- `Tab` switch focus between panes.
- `Enter` or `s` play the highlighted queued track.
- `x` or `Delete` remove the highlighted track.
- `u` / `d` move the highlighted track up/down one slot.
- `c` clear the entire queue.

Global playback:

- `Space` pause/resume.
- `n` next track; `p` previous track.
- `q` or `Esc` quit (queue is saved).

Notes: the UI needs at least ~120×12 characters; if the terminal is smaller, a resize warning is shown. The now-playing line is centered at the bottom and shows ID3 info when available.

## Requirements

- Python ≥ 3.10
- VLC installed on your system (for `python-vlc` to find `libvlc`).
- macOS/Linux terminal with ncurses support.
- MP3 files in your music library.

## Installation

### Fast path with pipx (recommended for an isolated CLI install)

```bash
pipx install .
# later, after pulling changes:
pipx reinstall .
```

### Standard pip install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install .
```

Run with:

```bash
pymus
```

## Development workflow

The repository includes a Makefile with common tasks:

```bash
make install-dev   # create .venv + editable install with dev deps
make run           # run pymus from the venv
make format        # black
make lint          # ruff
make check         # black --check + ruff
make build         # produce wheel + sdist in dist/
make clean         # remove venv + build artifacts + caches
```

All targets are safe to rerun; the venv is kept in `.venv`.

## Building release artifacts

If you prefer the raw tools:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel build
python -m build     # creates dist/*.whl and dist/*.tar.gz
```

## How playback works under the hood

- The left pane lists directories first, then `.mp3` files in the current folder. Folder queuing is recursive (`os.walk`).
- ID3 metadata is read via `mutagen.easyid3`; results are cached in-memory per session.
- VLC is driven through `python-vlc`; playback state (position/length) is polled for a simple progress bar.
- Queue state is kept in memory and persisted on exit to `~/.pymus/playlist.json`; invalid/missing entries are filtered out on load.
- The default music root is `MUSIC_ROOT` in `src/pymus/cli.py`; edit that constant if your library lives elsewhere.

## Troubleshooting

- **VLC not found**: install VLC from your package manager or <https://www.videolan.org/>, ensuring `libvlc` is on the library path.
- **No audio**: verify your output device in VLC and that `python-vlc` can play other files.
- **Terminal too small**: resize to at least 120 columns; the app will not render below that.
- **Different music folder**: adjust `MUSIC_ROOT` in `src/pymus/cli.py` and reinstall/editable install.

## Uninstall

- `pipx uninstall pymus` (pipx install)
- `pip uninstall pymus` (standard pip)

## License

MIT; see `LICENSE`.
