import tkinter as tk

class ToolTip:
    def __init__(self, widget, text="", wraplength=200):
        self.widget = widget
        self.text = text
        self.wraplength = wraplength
        self.tooltip_window = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, event=None):
        self.show_tooltip(event.x_root + 20, event.y_root + 10, self.text)

    def _on_leave(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self, x, y, text):
        """Show tooltip at given screen coords with given text."""
        self.text = text
        if self.tooltip_window or not self.text:
            return

        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            tw,
            text=self.text,
            background="lightyellow",
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
