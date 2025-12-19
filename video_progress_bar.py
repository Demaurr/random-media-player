import tkinter as tk
from player_constants import Colors
from tooltips import ToolTip
from intervaltree import Interval, IntervalTree
from static_methods import format_seconds_to_str

class VideoProgressBar(tk.Canvas):
    def __init__(self, parent, set_position_callback, bg="#222", trimmed_segments=None, height=20, highlightthickness=0):
        super().__init__(parent, bg=bg, highlightthickness=highlightthickness, height=height, cursor="arrow")
        self.parent = parent
        self.set_position_callback = set_position_callback
        self.trimmed_segments = trimmed_segments or []

        self.handle = None
        self.dragging = False
        self.current_time = 0
        self.tooltip = ToolTip(self, wraplength=200, position="above")
        self._file = ""

        self._last_position_cache = {}
        self._segment_metadata = {}
        self._segment_rects = {}
        self._interval_tree = IntervalTree()
        self._hovered_rect = None

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)

    def _on_resize(self, event):
        self.redraw()

    def set_trimmed_segments(self, segments, total_duration=None, segment_metadata=None):
        self.trimmed_segments = segments
        self._segment_metadata = segment_metadata or {}

        self._interval_tree = IntervalTree()
        for start, end in self.trimmed_segments:
            note = self._segment_metadata.get((start, end), {}).get("notes", "")
            # self._interval_tree[start:end] = f"[{format_seconds_to_str(start)} - {format_seconds_to_str(end)}]\n{note}"
            self._interval_tree[start:end] = note

        self.redraw(total_duration=total_duration)

    def redraw(self, total_duration=None):
        self.delete("all")
        self._segment_rects.clear()
        self._hovered_rect = None
        width = max(1, self.winfo_width())
        bar_y1, bar_y2 = 5, 11

        self.create_rectangle(0, bar_y1, width, bar_y2, fill="#444444", outline="")
        if not total_duration and hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000

        if total_duration and self.current_time > 0:
            progress_width = int((self.current_time / total_duration) * width)
            self.create_rectangle(0, bar_y1, progress_width, bar_y2, fill=Colors.RED_PROGRESS_BAR, outline="")

        if total_duration and self.trimmed_segments:
            for start, end in self.trimmed_segments:
                x1 = int((start / total_duration) * width)
                x2 = int((end / total_duration) * width)
                rect_id = self.create_rectangle(x1, bar_y1, x2, bar_y2,
                                                fill=Colors.WARNING_ORANGE, stipple="gray50", outline="")
                self._segment_rects[rect_id] = (start, end)
                self.create_line(x1, bar_y1, x1, bar_y2, fill=Colors.WARNING_ORANGE, width=2)
                self.create_line(x2, bar_y1, x2, bar_y2, fill=Colors.WARNING_ORANGE, width=2)

        if total_duration:
            handle_x = int((self.current_time / total_duration) * width)
            self.handle = self.create_line(handle_x, bar_y1 - 3, handle_x, bar_y2 + 3,
                                           fill=Colors.PLAIN_RED, width=3)
            # self.draw_last_position(total_duration, width, bar_y1, bar_y2)

    def draw_last_position(self, total_duration, width, bar_y1, bar_y2):
        current_file = getattr(self.parent, "current_file", None)
        if not current_file or not total_duration:
            return

        if current_file in self._last_position_cache:
            last_seconds = self._last_position_cache[current_file]
        else:
            last_pos_str = ""
            if hasattr(self.parent, "watch_history_logger"):
                last_pos_str = self.parent.watch_history_logger.get_last_position(current_file)
            last_seconds = None
            if last_pos_str:
                try:
                    parts = [int(float(x)) for x in last_pos_str.split(":")]
                    if len(parts) == 2:
                        h, m, s = 0, parts[0], parts[1]
                    elif len(parts) == 3:
                        h, m, s = parts
                    else:
                        raise ValueError(f"Unexpected time format: {last_pos_str}")
                    last_seconds = h * 3600 + m * 60 + s
                    self._last_position_cache[current_file] = last_seconds
                except Exception as e:
                    print(f"Error parsing last position '{last_pos_str}': {e}")

        if last_seconds and 0 < last_seconds < total_duration:
            last_x = int((last_seconds / total_duration) * width)
            self.create_line(last_x, bar_y1, last_x, bar_y2, fill=Colors.PLAIN_BLACK, width=2)

    def update_progress(self, total_duration=None):
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            try:
                total_duration = self.parent.media_player.get_length() / 1000
                if total_duration > 0 and not self.dragging:
                    self.current_time = min(max(0, self.parent.media_player.get_time() / 1000), total_duration)
                    self.redraw(total_duration=total_duration)
            except Exception as e:
                print(f"Error updating progress: {e}")

    def on_motion(self, event):
        width = self.winfo_width()
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000
            if total_duration > 0:
                hovered_time = (event.x / width) * total_duration
                segment_content = self._get_segment_at_time(hovered_time)

                self._highlight_segment(hovered_time)

                if segment_content:
                    self.tooltip.show_tooltip(event.x_root + 20, event.y_root - 10, segment_content)
                else:
                    hours, remainder = divmod(int(hovered_time), 3600)
                    mins, secs = divmod(remainder, 60)
                    tooltip_text = f"{hours:02}:{mins:02}:{secs:02}"
                    self.tooltip.show_tooltip(event.x_root + 20, event.y_root - 10, tooltip_text)
            else:
                self.tooltip.hide_tooltip()
        else:
            self.tooltip.hide_tooltip()

    def _highlight_segment(self, time_seconds):
        if self._hovered_rect:
            start, end = self._segment_rects[self._hovered_rect]
            self.itemconfig(self._hovered_rect, fill=Colors.WARNING_ORANGE)
            self._hovered_rect = None

        intervals = self._interval_tree[time_seconds]
        if intervals:
            for rect_id, (start, end) in self._segment_rects.items():
                for interval in intervals:
                    if interval.begin == start and interval.end == end:
                        self.itemconfig(rect_id, fill=Colors.PLAIN_RED)
                        self._hovered_rect = rect_id
                        return

    def _get_segment_at_time(self, time_seconds):
        intervals = self._interval_tree[time_seconds]
        if intervals:
            content = []
            for iv in sorted(intervals):
                start_str, end_str = iv.begin, iv.end
                time_text = f"[{format_seconds_to_str(start_str)} - {format_seconds_to_str(end_str)}]\n"
                note_text = iv.data or ""
                content.append((time_text, {"foreground": "yellow", "font": ("Segoe UI", 9, "bold")}))
                content.append((note_text, {"foreground": "white", "font": ("Segoe UI", 9)}))
            return content
        return None

    def on_leave(self, event):
        if self._hovered_rect:
            self.itemconfig(self._hovered_rect, fill=Colors.WARNING_ORANGE)
            self._hovered_rect = None
        self.tooltip.hide_tooltip()

    def move_handle(self, x):
        width = self.winfo_width()
        x = max(0, min(x, width))
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000
            if total_duration > 0:
                self.current_time = (x / width) * total_duration
                if self.set_position_callback:
                    self.set_position_callback(self.current_time)
                self.redraw(total_duration=total_duration)

    def on_click(self, event):
        self.dragging = True
        self.move_handle(event.x)

    def on_drag(self, event):
        if self.dragging:
            self.move_handle(event.x)

    def on_release(self, event):
        self.dragging = False