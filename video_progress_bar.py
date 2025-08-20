import tkinter as tk

class VideoProgressBar(tk.Canvas):
    def __init__(self, parent, set_position_callback, bg="#222", trimmed_segments=None, height=40, highlightthickness=0):
        super().__init__(parent, bg=bg, highlightthickness=highlightthickness, height=height)
        self.parent = parent
        self.set_position_callback = set_position_callback
        self.trimmed_segments = trimmed_segments or []

        self.handle = None
        self.handle_radius = 6
        self.dragging = False
        self.current_time = 0

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self.redraw()

    def set_trimmed_segments(self, segments, total_duration=None):
        self.trimmed_segments = segments
        self.redraw(total_duration=total_duration)
    
    def redraw(self, total_duration=None):
        """Alternative: Use a vertical line as position indicator"""
        if not hasattr(self.parent, "progress_bar"):
            return
        
        self.delete("all")
        width = max(1, self.winfo_width())
        height = self.winfo_height()

        bar_y1, bar_y2 = 10, 25

        self.create_rectangle(0, bar_y1, width, bar_y2, fill="#444", outline="")

        total_duration = None
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            total_duration = self.parent.media_player.get_length() / 1000

        if total_duration and self.trimmed_segments:
            for start, end in self.trimmed_segments:
                x1 = int((start / total_duration) * width)
                x2 = int((end / total_duration) * width)
                self.create_line(x1, 5, x2, 5, fill="#FF9800", width=3, dash=(5,2))
                self.create_line(x1, 2, x1, 8, fill="#FF9800", width=2)
                self.create_line(x2, 2, x2, 8, fill="#FF9800", width=2)

        if total_duration and self.current_time > 0:
            progress_width = int((self.current_time / total_duration) * width)
            self.create_rectangle(0, bar_y1, progress_width, bar_y2, fill="#666", outline="")

        if total_duration:
            handle_x = int((self.current_time / total_duration) * width)
            self.handle = self.create_line(
                handle_x, bar_y1, handle_x, bar_y2, 
                fill="red", width=3
            )

    def update_progress(self):
        """Update the handle according to the video playback."""
        if hasattr(self.parent, "media_player") and self.parent.media_player:
            try:
                total_duration = self.parent.media_player.get_length() / 1000
                if total_duration > 0 and not self.dragging:
                    self.current_time = min(max(0, self.parent.media_player.get_time()/1000), total_duration)
                    self.redraw()
            except Exception as e:
                print(f"Error updating progress: {e}")

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