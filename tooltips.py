import tkinter as tk
from player_constants import Colors

class ToolTip:
    def __init__(self, widget, text="", wraplength=200, skipbindings=False, position="below"):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tooltip_window = None
        self.position = position.lower() if position in ("above", "below") else "below"
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        if self.position == "above":
            y = event.y_root - 10
        else:
            y = event.y_root + 10
        self.show_tooltip(event.x_root + 20, y, self.text)

    def _on_leave(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self, x, y, text):
        """Show tooltip at given screen coords with given text."""
        self.text = text
        if self.tooltip_window:
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            label = self.tooltip_window.winfo_children()[0]
            label.config(text=self.text)
            return

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            background=Colors.PLAIN_BLACK,
            foreground=Colors.PLAIN_WHITE,
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            wraplength=self.wraplength,
            justify="left"
        )
        label.pack(ipadx=5, ipady=2)

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
