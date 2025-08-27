import tkinter as tk
from player_constants import Colors
from tooltips import ToolTip

class VideoProgressBar(tk.Canvas):
    def __init__(self, parent, set_position_callback, bg="#222", trimmed_segments=None, height=20, highlightthickness=0):
        super().__init__(parent, bg=bg, highlightthickness=highlightthickness, height=height, cursor="arrow")
        self.parent = parent
        self.set_position_callback = set_position_callback
        self.trimmed_segments = trimmed_segments or []

        self.handle = None
        self.dragging = False
        self.last_pos_str = ""
        self.current_time = 0
        self.tooltip = ToolTip(self, wraplength=100, position="above")
        self._file = ""

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)

    def _on_resize(self, event):
        self.redraw()

    def set_trimmed_segments(self, segments, total_duration=None):
        self.trimmed_segments = segments
        self.redraw(total_duration=total_duration)
    
    def redraw(self, total_duration=None):
        """Alternative: Use a vertical line as position indicator"""
        if not self.parent:
            return
        if not hasattr(self.parent, "progress_bar"):
            return

        
        self.delete("all")
        width = max(1, self.winfo_width())
        height = self.winfo_height()

        bar_y1, bar_y2 = 5, 11

        self.create_rectangle(0, bar_y1, width, bar_y2, fill="#444444", outline="")
        
        total_duration = None
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000

        if total_duration and self.current_time > 0:
            progress_width = int((self.current_time / total_duration) * width)
            self.create_rectangle(0, bar_y1, progress_width, bar_y2, fill=Colors.RED_PROGRESS_BAR, outline="")


        if total_duration and self.trimmed_segments:
            for start, end in self.trimmed_segments:
                x1 = int((start / total_duration) * width)
                x2 = int((end / total_duration) * width)
                self.create_rectangle(x1, bar_y1, x2, bar_y2, fill=Colors.WARNING_ORANGE, stipple="gray50", outline="")
                self.create_line(x1, bar_y1, x1, bar_y2, fill=Colors.WARNING_ORANGE, width=2)
                self.create_line(x2, bar_y1, x2, bar_y2, fill=Colors.WARNING_ORANGE, width=2)

        if total_duration:
            handle_x = int((self.current_time / total_duration) * width)
            self.handle = self.create_line(
                handle_x, bar_y1 - 3, handle_x, bar_y2 + 3, 
                fill=Colors.PLAIN_RED, width=3
            )
            # self.draw_last_position(total_duration, width, bar_y1, bar_y2)
            
    def draw_last_position(self, total_duration, width, bar_y1, bar_y2):
        if hasattr(self, "_last_seconds") and self._last_seconds and total_duration:
            if 0 < self._last_seconds < total_duration:
                last_x = int((self._last_seconds / total_duration) * width)
                self.create_line(last_x, bar_y1, last_x, bar_y2, fill=Colors.PLAIN_BLACK, width=2)
            return

        if not self.last_pos_str or (self._file != self.parent.current_file):
            if hasattr(self.parent, "watch_history_logger") and hasattr(self.parent, "current_file"):
                self.last_pos_str = self.parent.watch_history_logger.get_last_position(self.parent.current_file)
                self._file = self.parent.current_file

        if self.last_pos_str:
            try:
                parts = [int(float(x)) for x in self.last_pos_str.split(":")]

                if len(parts) == 2:
                    h, m, s = 0, parts[0], parts[1]
                elif len(parts) == 3:
                    h, m, s = parts
                else:
                    raise ValueError(f"Unexpected time format: {self.last_pos_str}")

                self._last_seconds = h * 3600 + m * 60 + s

                if 0 < self._last_seconds < total_duration:
                    last_x = int((self._last_seconds / total_duration) * width)
                    self.create_line(last_x, bar_y1, last_x, bar_y2, fill=Colors.PLAIN_BLACK, width=2)

                print(self.last_pos_str)

            except Exception as e:
                print(f"Error parsing last position '{self.last_pos_str}': {e}")
                self._last_seconds = None


            
    def update_progress(self, total_duration=None):
        """Update the handle according to the video playback."""
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            try:
                total_duration = self.parent.media_player.get_length() / 1000
                if total_duration > 0 and not self.dragging:
                    self.current_time = min(max(0, self.parent.media_player.get_time()/1000), total_duration)
                    self.redraw(total_duration=total_duration)
            except Exception as e:
                print(f"Error updating progress: {e}")

    def on_motion(self, event):
        """Show tooltip with time at hovered position."""
        width = self.winfo_width()
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000
            if total_duration > 0:
                hovered_time = (event.x / width) * total_duration
                # Format as hh:mm:ss
                hours, remainder = divmod(int(hovered_time), 3600)
                mins, secs = divmod(remainder, 60)
                time_str = f"{hours:02}:{mins:02}:{secs:02}"
                self.tooltip.show_tooltip(event.x_root + 20, event.y_root - 10, time_str)
            else:
                self.tooltip.hide_tooltip()
        else:
            self.tooltip.hide_tooltip()

    def on_leave(self, event):
        self.tooltip.hide_tooltip()

    def move_handle(self, x):
        """Move handle to x and update video position"""
        width = self.winfo_width()
        x = max(0, min(x, width))  # clamp
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000
            if total_duration > 0:
                self.current_time = (x / width) * total_duration
                if self.set_position_callback:
                    self.set_position_callback(self.current_time)
                self.redraw()

    def on_click(self, event):
        self.dragging = True
        self.move_handle(event.x)

    def on_drag(self, event):
        if self.dragging:
            self.move_handle(event.x)

    def on_release(self, event):
        self.dragging = False