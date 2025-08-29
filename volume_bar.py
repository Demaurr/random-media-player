import tkinter as tk
from player_constants import Colors
from tooltips import ToolTip

class VolumeBar(tk.Canvas):
    def __init__(self, parent, media_player, bg="#222", height=20, width=100, highlightthickness=0):
        super().__init__(parent, bg=bg, highlightthickness=highlightthickness, height=height, width=width, cursor="arrow")
        self.parent = parent
        self.media_player = media_player
        self.current_volume = 50
        self.max_volume = 200

        self.handle = None
        self.dragging = False
        self.tooltip = ToolTip(self, wraplength=100, position="above")

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)

        self.redraw()

    def _on_resize(self, event):
        self.redraw()

    def redraw(self):
        """Draw the volume bar based on current volume level"""
        self.delete("all")
        width = max(1, self.winfo_width())
        height = self.winfo_height()

        bar_y1, bar_y2 = 5, height - 5

        self.create_rectangle(0, bar_y1, width, bar_y2, fill="#444444", outline="")

        progress_width = int((self.current_volume / self.max_volume) * width)
        self.create_rectangle(0, bar_y1, progress_width, bar_y2, fill=Colors.ORANGE, outline="")

        handle_x = progress_width
        self.handle = self.create_line(
            handle_x, bar_y1 - 3, handle_x, bar_y2 + 3,
            fill=Colors.PLAIN_ORANGE, width=3
        )

        self.create_text(
            width // 2, (bar_y1 + bar_y2) // 2,
            text=f"{self.current_volume}%",
            fill=Colors.PLAIN_WHITE if self.current_volume < 95 else Colors.BLACK, font=("Segoe UI", 9, "bold")
        )


    def update_volume(self, volume=None):
        """Update bar to reflect volume (from player or given value)"""
        if volume is not None:
            self.current_volume = max(0, min(self.max_volume, int(volume)))
        self.media_player.audio_set_volume(self.current_volume)
        self.redraw()

    def move_handle(self, x):
        """Move handle and set volume"""
        width = self.winfo_width()
        x = max(0, min(x, width))
        self.current_volume = int((x / width) * self.max_volume)
        self.media_player.audio_set_volume(self.current_volume)
        self.redraw()

    def on_click(self, event):
        self.dragging = True
        self.move_handle(event.x)

    def on_drag(self, event):
        if self.dragging:
            self.move_handle(event.x)

    def on_release(self, event):
        self.dragging = False

    def on_motion(self, event):
        """Show tooltip with volume at hovered position."""
        width = self.winfo_width()
        hovered_volume = int((event.x / width) * self.max_volume)
        self.tooltip.show_tooltip(event.x_root, event.y_root - 25, f"{hovered_volume}%")

    def on_leave(self, event):
        self.tooltip.hide_tooltip()
