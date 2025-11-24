#!/usr/bin/env python3
import curses
import os
import time
from pathlib import Path
import vlc


################################################################################
# list_dir() → shows folders/files in sorted order for browsing.
# collect_mp3s() → walks a folder tree and grabs .mp3 files.
# AudioPlayer → wraps VLC:
  # holds queue
  # play/pause/next/prev
  # progress
# draw_ui() → paints the terminal window.
# main() → event loop:
  # reads keys
  # updates state
  # triggers playback
################################################################################


AUDIO_EXTS = {".mp3"}

# >>> NEW: Your music root
MUSIC_ROOT = Path("/Users/andrewpearce/Google Drive/My Drive/music")

################################################################################
# Return a sorted list of directory entries for UI display.
# - Attempts to list all entries (files and directories) in the given path.
# - If access is denied (PermissionError), returns an empty list.
# - Directories are sorted alphabetically (case-insensitive) and appear first.
# - Files are sorted alphabetically (case-insensitive) and appear after directories.
# - The result is a single list: [sorted dirs..., sorted files...].
# Args:
#   path (Path): The directory to list.
# Returns:
#   List[Path]: Sorted list of Path objects (dirs first, then files).
def list_dir(path: Path):
  try:
    entries = list(path.iterdir())
  except PermissionError:
    return []
  dirs = sorted([e for e in entries if e.is_dir()], key=lambda p: p.name.lower())
  mp3_files = sorted([e for e in entries if e.is_file() and e.suffix.lower() in AUDIO_EXTS], key=lambda p: p.name.lower())
  files = sorted([e for e in entries if e.is_file()], key=lambda p: p.name.lower())
  return dirs + mp3_files

################################################################################
# Recursively collects all MP3 files from the given folder and its subdirectories.
# - Traverses the directory tree using os.walk.
# - For each file found, checks if its extension matches AUDIO_EXTS (e.g., ".mp3").
# - Adds matching files as Path objects to a list.
# - Returns a list of Path objects, sorted alphabetically (case-insensitive) by filename.
def collect_mp3s(folder: Path):
  """Recursively collect mp3 files, sorted A-Z0-9."""
  files = []
  for root, _, fnames in os.walk(folder):
    for f in fnames:
      p = Path(root) / f
      if p.suffix.lower() in AUDIO_EXTS:
        files.append(p)
  return sorted(files, key=lambda p: p.name.lower())

################################################################################
class AudioPlayer:
    def __init__(self):
        self.instance = vlc.Instance("--no-video", "--quiet")
        self.player = self.instance.media_player_new()
        self.queue = []
        self.idx = -1
        self.paused = False

    def set_queue(self, files):
        self.queue = files
        self.idx = 0 if files else -1

    def current(self):
        if 0 <= self.idx < len(self.queue):
            return self.queue[self.idx]
        return None

    def play_current(self):
        cur = self.current()
        if not cur:
            return
        media = self.instance.media_new(str(cur))
        self.player.set_media(media)
        self.player.play()
        self.paused = False

    def toggle_pause(self):
        if self.player.is_playing():
            self.player.pause()
            self.paused = True
        else:
            if self.paused:
                self.player.pause()
            else:
                self.play_current()
            self.paused = False

    def next(self):
        if not self.queue:
            return
        self.idx = (self.idx + 1) % len(self.queue)
        self.play_current()

    def prev(self):
        if not self.queue:
            return
        self.idx = (self.idx - 1) % len(self.queue)
        self.play_current()

    def progress(self):
        """Return (pos_seconds, length_seconds) or (0,0)."""
        try:
            pos_ms = self.player.get_time()
            len_ms = self.player.get_length()
            if pos_ms < 0 or len_ms < 0:
                return 0, 0
            return pos_ms / 1000.0, len_ms / 1000.0
        except Exception:
            return 0, 0

################################################################################
def draw_ui(stdscr, cwd, entries, cursor, player, status_msg):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header = f"NCurses Music Player  |  Folder: {cwd}"
    stdscr.addnstr(0, 0, header, w - 1, curses.A_REVERSE)

    # >>> UPDATED help line
    help_line = "Enter=open folder  |  s=queue/play folder  |  Space=play/pause  n=next  p=prev  b=back  q=quit"
    stdscr.addnstr(h - 1, 0, help_line, w - 1, curses.A_REVERSE)

    list_h = h - 3
    for i in range(min(list_h, len(entries))):
        e = entries[i]
        name = e.name + ("/" if e.is_dir() else "")
        attr = curses.A_BOLD if e.is_dir() else curses.A_NORMAL
        if i == cursor:
            attr |= curses.A_STANDOUT
        stdscr.addnstr(1 + i, 0, name, w - 1, attr)

    cur = player.current()
    np_line = f"Now Playing: {cur.name if cur else '-'}"
    stdscr.addnstr(h - 2, 0, np_line, w - 1)

    pos, length = player.progress()
    if length > 0:
        bar_w = max(10, w - 30)
        filled = int((pos / length) * bar_w)
        bar = "[" + "#" * filled + "-" * (bar_w - filled) + "]"
        time_line = f"{bar} {int(pos):>4}s / {int(length):>4}s"
    else:
        time_line = "[----------]    0s /    0s"
    stdscr.addnstr(h - 2, max(0, w - len(time_line) - 1), time_line, len(time_line))

    if status_msg:
        stdscr.addnstr(h - 3, 0, status_msg, w - 1, curses.A_DIM)

    stdscr.refresh()

################################################################################
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    # >>> UPDATED start directory
    cwd = MUSIC_ROOT if MUSIC_ROOT.exists() else Path.home()
    entries = list_dir(cwd)
    cursor = 0
    status_msg = ""

    player = AudioPlayer()
    last_tick = time.time()

    while True:
        if player.queue and player.player.get_state() == vlc.State.Ended:
            player.next()

        now = time.time()
        if now - last_tick > 0.03:
            draw_ui(stdscr, cwd, entries, cursor, player, status_msg)
            last_tick = now

        key = stdscr.getch()
        if key == -1:
            continue

        status_msg = ""

        if key in (ord("q"), 27):
            break

        elif key in (curses.KEY_DOWN, ord("j")):
            cursor = min(cursor + 1, len(entries) - 1)

        elif key in (curses.KEY_UP, ord("k")):
            cursor = max(cursor - 1, 0)

        # >>> UPDATED: Enter only navigates into directory
        elif key in (curses.KEY_ENTER, 10, 13):
            if not entries:
                continue
            sel = entries[cursor]
            if sel.is_dir():
                cwd = sel
                entries = list_dir(cwd)
                cursor = 0
            elif sel.is_file():
                # Play selected file (queue all MP3s under cwd so next/prev works)
                mp3s = collect_mp3s(cwd)
                player.set_queue(mp3s)
                try:
                    player.idx = mp3s.index(sel)
                except ValueError:
                    player.idx = 0
                player.play_current()
                status_msg = f"Playing {sel.name}"

        # >>> NEW: 's' to queue/play MP3s from a directory (recursive)
        elif key == ord("s"):
            if not entries:
                continue
            sel = entries[cursor]
            if sel.is_dir():
                mp3s = collect_mp3s(sel)
                player.set_queue(mp3s)
                if mp3s:
                    player.play_current()
                    status_msg = f"Queued {len(mp3s)} MP3s from {sel.name}/"
                else:
                    status_msg = f"No MP3s found in {sel.name}/"
            elif sel.is_file():
                mp3s = collect_mp3s(cwd)
                player.set_queue(mp3s)
                try:
                    player.idx = mp3s.index(sel)
                except ValueError:
                    player.idx = 0
                player.play_current()
                status_msg = f"Playing {sel.name}"

        elif key == ord("b"):
            parent = cwd.parent
            if parent != cwd:
                cwd = parent
                entries = list_dir(cwd)
                cursor = 0

        elif key == ord(" "):
            player.toggle_pause()

        elif key == ord("n"):
            player.next()

        elif key == ord("p"):
            player.prev()

        elif key == curses.KEY_RIGHT:
            if entries and entries[cursor].is_dir():
                cwd = entries[cursor]
                entries = list_dir(cwd)
                cursor = 0

        elif key == curses.KEY_LEFT:
            parent = cwd.parent
            if parent != cwd:
                cwd = parent
                entries = list_dir(cwd)
                cursor = 0

    player.player.stop()

################################################################################  
if __name__ == "__main__":
    curses.wrapper(main)
