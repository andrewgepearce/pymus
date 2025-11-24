#!/usr/bin/env python3
import curses
import os
import time
from pathlib import Path
import vlc

AUDIO_EXTS = {".mp3"}

MUSIC_ROOT = Path("/Users/andrewpearce/Google Drive/My Drive/music")

def list_dir(path: Path):
    """Return sorted entries for left pane: dirs first, then MP3 files only."""
    try:
        entries = list(path.iterdir())
    except PermissionError:
        return []

    dirs = sorted([e for e in entries if e.is_dir()], key=lambda p: p.name.lower())
    mp3_files = sorted(
        [e for e in entries if e.is_file() and e.suffix.lower() in AUDIO_EXTS],
        key=lambda p: p.name.lower()
    )
    return dirs + mp3_files

def collect_mp3s(folder: Path):
    """Recursively collect mp3 files, sorted A-Z0-9 by filename."""
    files = []
    for root, _, fnames in os.walk(folder):
        for f in fnames:
            p = Path(root) / f
            if p.suffix.lower() in AUDIO_EXTS:
                files.append(p)
    return sorted(files, key=lambda p: p.name.lower())

def apply_filter(entries, text: str):
    """Filter entries by substring (case-insensitive) on name."""
    if not text:
        return entries
    t = text.lower()
    return [e for e in entries if t in e.name.lower()]

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

    def play_index(self, i: int):
        if not self.queue:
            return
        self.idx = max(0, min(i, len(self.queue) - 1))
        self.play_current()

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
    
    def add_to_queue(self, files):
        """Append files to the queue; start playing if idle."""
        if not files:
            return

        was_empty = (len(self.queue) == 0)
        self.queue.extend(files)

        # If nothing was queued/playing before, start from first added item
        if was_empty:
            self.idx = 0
            self.play_current()

    def remove_index(self, i: int):
        """Remove item at index i from queue, adjusting playback index safely."""
        if not (0 <= i < len(self.queue)):
            return

        removing_current = (i == self.idx)

        removed = self.queue.pop(i)

        if not self.queue:
            # Queue now empty
            self.idx = -1
            self.player.stop()
            return

        if removing_current:
            # If we removed the playing track, keep idx at same position
            # (now pointing at next track if it exists, else previous)
            if i >= len(self.queue):
                self.idx = len(self.queue) - 1
            else:
                self.idx = i
            self.play_current()
        else:
            # If removed something before current, shift idx left
            if i < self.idx:
                self.idx -= 1

    def move_index(self, i: int, direction: int):
        """
        Move item at index i up/down by 1.
        direction = -1 (up) or +1 (down)
        """
        j = i + direction
        if not (0 <= i < len(self.queue)) or not (0 <= j < len(self.queue)):
            return

        # Swap items
        self.queue[i], self.queue[j] = self.queue[j], self.queue[i]

        # Keep current track pointing to same file
        if self.idx == i:
            self.idx = j
        elif self.idx == j:
            self.idx = i


def clamp(n, lo, hi):
    return max(lo, min(n, hi))

def ensure_visible(cursor, top, height, total):
    """Adjust top so cursor is visible within window height."""
    if total <= height:
        return 0
    if cursor < top:
        return cursor
    if cursor >= top + height:
        return cursor - height + 1
    return top

def draw_ui(stdscr, cwd, entries, left_cursor, left_top,
            player, right_cursor, right_top, focus, status_msg,
            filter_text, search_mode):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    mid = w // 2

    header = f"NCurses Music Player  |  Folder: {cwd}"
    stdscr.addnstr(0, 0, header, w - 1, curses.A_REVERSE)

    if search_mode:
        help_line = "SEARCH MODE: type to filter | Enter=accept | Esc=cancel | BS=delete | Ctrl+U=clear"
    else:
        help_line = "Tab=switch pane | Enter=open/play | s=queue/play folder | a=append | /=search | Right: x/delete=delete d=move down u=move up | Space=pause | n/p=next/prev | b=back | q=quit"
    stdscr.addnstr(h - 1, 0, help_line, w - 1, curses.A_REVERSE)

    list_h = h - 3

    # --- Left pane (browser) ---
    left_w = mid - 1
    filt = f" /{filter_text}" if filter_text else ""
    mode = " [SEARCH]" if search_mode else ""
    left_title = f" Browser{filt}{mode} "
    left_attr = curses.A_BOLD | (curses.A_STANDOUT if focus == "left" else 0)
    stdscr.addnstr(1, 0, left_title.ljust(left_w), left_w, left_attr)

    for i in range(list_h - 1):
        idx = left_top + i
        if idx >= len(entries):
            break
        e = entries[idx]
        name = e.name + ("/" if e.is_dir() else "")
        attr = curses.A_BOLD if e.is_dir() else curses.A_NORMAL
        if idx == left_cursor and focus == "left" and not search_mode:
            attr |= curses.A_REVERSE
        stdscr.addnstr(2 + i, 0, name.ljust(left_w)[:left_w], left_w, attr)

    # Divider
    for y in range(1, h - 1):
        stdscr.addch(y, mid - 1, "|")

    # --- Right pane (queue) ---
    right_x = mid
    right_w = w - mid
    right_title = f" Queue ({len(player.queue)}) "
    right_attr = curses.A_BOLD | (curses.A_STANDOUT if focus == "right" else 0)
    stdscr.addnstr(1, right_x, right_title.ljust(right_w), right_w, right_attr)

    queue = player.queue
    for i in range(list_h - 1):
        idx = right_top + i
        if idx >= len(queue):
            break
        track = queue[idx]
        name = track.name
        attr = curses.A_NORMAL
        if idx == player.idx:
            attr |= curses.A_BOLD
        if idx == right_cursor and focus == "right":
            attr |= curses.A_REVERSE
        stdscr.addnstr(2 + i, right_x, name.ljust(right_w)[:right_w], right_w, attr)
  
    #
    # --- Now Playing + Progress Bar (keep existing functionality)
    #
    cur = player.current()
    np_line = f"Now Playing: {cur.name if cur else '-'}"
    stdscr.addnstr(h - 3, 0, np_line, w - 1)

    pos, length = player.progress()

    def fmt_mmss(t):
        t = max(0, int(t))
        m = t // 60
        s = t % 60
        return f"{m}:{s:02d}"
    if length > 0:
        bar_w = max(10, w - 30)
        filled = int((pos / length) * bar_w)
        bar = "[" + "#" * filled + "-" * (bar_w - filled) + "]"
        time_line = f"{bar} {fmt_mmss(pos)} / {fmt_mmss(length)}"
    else:
        time_line = "[----------] 0:00 / 0:00"

    stdscr.addnstr(h - 3, max(0, w - len(time_line) - 1), time_line, len(time_line))

    #
    # --- New permanent playback-status line (centered + dim)
    #
    if cur:
        status_line = f"Playing: {cur.name}"
    else:
        status_line = " -- nothing being played ---"

    # centre horizontally
    x = max(0, (w - len(status_line)) // 2)

    stdscr.addnstr(h - 2, x, status_line, len(status_line), curses.A_DIM)

    if status_msg:
        stdscr.addnstr(h - 4, 0, status_msg, w - 1, curses.A_DIM)

    stdscr.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)

    cwd = MUSIC_ROOT if MUSIC_ROOT.exists() else Path.home()

    all_entries = list_dir(cwd)
    filter_text = ""
    entries = apply_filter(all_entries, filter_text)

    focus = "left"

    left_cursor = 0
    left_top = 0

    right_cursor = 0
    right_top = 0

    status_msg = ""
    player = AudioPlayer()

    last_tick = time.time()

    # Search mode state
    search_mode = False
    filter_before_search = ""

    while True:
        if player.queue and player.player.get_state() == vlc.State.Ended:
            player.next()

        if focus != "right" and player.idx >= 0:
            right_cursor = player.idx

        now = time.time()
        if now - last_tick > 0.03:
            h, w = stdscr.getmaxyx()
            list_h = h - 3
            left_top = ensure_visible(left_cursor, left_top, list_h - 1, len(entries))
            right_top = ensure_visible(right_cursor, right_top, list_h - 1, len(player.queue))
            draw_ui(
                stdscr, cwd, entries, left_cursor, left_top,
                player, right_cursor, right_top, focus, status_msg,
                filter_text, search_mode
            )
            last_tick = now

        key = stdscr.getch()
        if key == -1:
            continue

        status_msg = ""

        # --- SEARCH MODE HANDLING (left pane only) ---
        if search_mode:
            # Esc cancels search and restores previous filter
            if key == 27:
                search_mode = False
                filter_text = filter_before_search
                entries = apply_filter(all_entries, filter_text)
                left_cursor, left_top = 0, 0
                continue

            # Enter accepts current filter and exits search mode
            if key in (curses.KEY_ENTER, 10, 13):
                search_mode = False
                continue

            # Backspace deletes
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if filter_text:
                    filter_text = filter_text[:-1]
                    entries = apply_filter(all_entries, filter_text)
                    left_cursor, left_top = 0, 0
                continue

            # Ctrl+U clears
            if key == 21:
                filter_text = ""
                entries = all_entries
                left_cursor, left_top = 0, 0
                continue

            # Printable chars add to filter (no reserved keys here)
            if 32 <= key <= 126:
                filter_text += chr(key)
                entries = apply_filter(all_entries, filter_text)
                left_cursor, left_top = 0, 0
            continue

        # --- NORMAL MODE HANDLING ---

        ########################################################################
        # Quit
        if key in (ord("q"), 27):
            break
        ############################################################################
        # Start search mode
        elif key == ord("/") and focus == "left":
            search_mode = True
            filter_before_search = filter_text
            filter_text = ""  # fresh search each time
            entries = all_entries
            left_cursor, left_top = 0, 0

        ########################################################################
        # Switch pane
        elif key == 9:  # Tab
            focus = "right" if focus == "left" else "left"
            
        ########################################################################
        # Up/Down
        elif key in (curses.KEY_DOWN, ord("j")):
            if focus == "left":
                left_cursor = clamp(left_cursor + 1, 0, max(0, len(entries) - 1))
            else:
                right_cursor = clamp(right_cursor + 1, 0, max(0, len(player.queue) - 1))
        
        ########################################################################
        elif key in (curses.KEY_UP, ord("k")):
            if focus == "left":
                left_cursor = clamp(left_cursor - 1, 0, max(0, len(entries) - 1))
            else:
                right_cursor = clamp(right_cursor - 1, 0, max(0, len(player.queue) - 1))
        
        ########################################################################
        # Page Down / Page Up
        elif key == curses.KEY_NPAGE:
            h, w = stdscr.getmaxyx()
            list_h = h - 3
            page = max(1, list_h - 1)
            if focus == "left":
                left_cursor = clamp(left_cursor + page, 0, max(0, len(entries) - 1))
            else:
                right_cursor = clamp(right_cursor + page, 0, max(0, len(player.queue) - 1))

        ########################################################################
        elif key == curses.KEY_PPAGE:
            h, w = stdscr.getmaxyx()
            list_h = h - 3
            page = max(1, list_h - 1)
            if focus == "left":
                left_cursor = clamp(left_cursor - page, 0, max(0, len(entries) - 1))
            else:
                right_cursor = clamp(right_cursor - page, 0, max(0, len(player.queue) - 1))

        ########################################################################
        # Enter
        elif key in (curses.KEY_ENTER, 10, 13):
            if focus == "left":
                if not entries:
                    continue
                sel = entries[left_cursor]
                if sel.is_dir():
                    cwd = sel
                    all_entries = list_dir(cwd)
                    filter_text = ""
                    entries = all_entries
                    left_cursor, left_top = 0, 0
                else:
                    mp3s = collect_mp3s(cwd)
                    player.set_queue(mp3s)
                    try:
                        player.idx = mp3s.index(sel)
                    except ValueError:
                        player.idx = 0
                    player.play_current()
                    right_cursor = player.idx
                    status_msg = f"Playing {sel.name}"
            else:
                if player.queue:
                    player.play_index(right_cursor)
                    status_msg = f"Playing {player.current().name}"

        ########################################################################
        # 's' to queue/play folder
        elif key == ord("s"):
            if focus == "left":
                if not entries:
                    continue
                sel = entries[left_cursor]
                if sel.is_dir():
                    mp3s = collect_mp3s(sel)
                    player.set_queue(mp3s)
                    if mp3s:
                        player.play_current()
                        right_cursor = player.idx
                        status_msg = f"Queued {len(mp3s)} MP3s from {sel.name}/"
                    else:
                        status_msg = f"No MP3s found in {sel.name}/"
                else:
                    mp3s = collect_mp3s(cwd)
                    player.set_queue(mp3s)
                    try:
                        player.idx = mp3s.index(sel)
                    except ValueError:
                        player.idx = 0
                    player.play_current()
                    right_cursor = player.idx
                    status_msg = f"Playing {sel.name}"
            else:
                if player.queue:
                    player.play_index(right_cursor)
                    status_msg = f"Playing {player.current().name}"

        ########################################################################
        # 'a' = APPEND behaviour
        elif key == ord("a"):
            if focus == "left":
                if not entries:
                    continue
                sel = entries[left_cursor]

                if sel.is_dir():
                    # Folder: append all MP3s in folder (recursive)
                    mp3s = collect_mp3s(sel)
                    if mp3s:
                        player.add_to_queue(mp3s)
                        status_msg = f"Appended {len(mp3s)} MP3s from {sel.name}/"
                    else:
                        status_msg = f"No MP3s found in {sel.name}/"

                else:
                    # File: append only this MP3
                    player.add_to_queue([sel])
                    status_msg = f"Appended {sel.name}"

                # Update queue cursor if player is already playing something
                if player.idx >= 0:
                    right_cursor = player.idx

            else:
                # Right pane: pressing 'a' does nothing (safe no-op)
                status_msg = ""

        ########################################################################
        # Back directory
        elif key == ord("b"):
            parent = cwd.parent
            if parent != cwd:
                cwd = parent
                all_entries = list_dir(cwd)
                filter_text = ""
                entries = all_entries
                left_cursor, left_top = 0, 0
        
        ########################################################################
        # Playback controls
        elif key == ord(" "):
            player.toggle_pause()

        ########################################################################
        # Next track
        elif key == ord("n"):
            player.next()
            right_cursor = player.idx

        ########################################################################
        # Previous track
        elif key == ord("p"):
            player.prev()
            right_cursor = player.idx
            
        ########################################################################
        # Delete selected queue item (right pane)
        elif (key in (curses.KEY_DC, 330) or key == ord("x")) and focus == "right":
            if player.queue:
                player.remove_index(right_cursor)
                # Clamp cursor to new queue size
                right_cursor = clamp(right_cursor, 0, max(0, len(player.queue) - 1))
                status_msg = "Deleted item from queue"

        ########################################################################
        # Move selected item DOWN (right pane)
        elif key == ord("d") and focus == "right":
            if player.queue and right_cursor < len(player.queue) - 1:
                player.move_index(right_cursor, +1)
                right_cursor += 1
                status_msg = "Moved item down"

        ########################################################################
        # Move selected item UP (right pane)
        elif key == ord("u") and focus == "right":
            if player.queue and right_cursor > 0:
                player.move_index(right_cursor, -1)
                right_cursor -= 1
                status_msg = "Moved item up"


    player.player.stop()

if __name__ == "__main__":
    curses.wrapper(main)
