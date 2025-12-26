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
        self.show_tooltip(event.x_root + 20, y, self.text, prefer_above=(self.position == "above"))

    def _on_leave(self, event=None):
        self.hide_tooltip()

    def show_tooltip(self, x, y, content, prefer_above=False):
        """Show tooltip at given screen coords, adjusting to stay visible on screen."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        self.tooltip_window = tw

        if isinstance(content, str):
            label = tk.Label(
                tw,
                text=content,
                background=Colors.PLAIN_BLACK,
                foreground=Colors.PLAIN_WHITE,
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                wraplength=self.wraplength,
                justify="left"
            )
            label.pack(ipadx=5, ipady=2)
        else:
            text_widget = tk.Text(
                tw,
                background=Colors.PLAIN_BLACK,
                foreground=Colors.PLAIN_WHITE,
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                wrap="word",
                width=45,
            )
            text_widget.pack(ipadx=5, ipady=2)
            text_widget.configure(state="normal")

            for t, style in content:
                tag_name = f"tag_{len(text_widget.tag_names())}"
                text_widget.insert("end", t, (tag_name,))
                text_widget.tag_configure(tag_name, **style)

            # lines = int(text_widget.index("end-1c").split(".")[0])
            # text_widget.configure(height=min(lines, 15))
            text_widget.configure(height=5)
            text_widget.configure(state="disabled")

        tw.update_idletasks()
        width = tw.winfo_reqwidth()
        height = tw.winfo_reqheight()

        screen_width = tw.winfo_screenwidth()
        screen_height = tw.winfo_screenheight()

        if x + width > screen_width:
            x = screen_width - width - 5
        if x < 0:
            x = 5

        if y + height > screen_height:
            y = y - height - 30 
        elif y < 0:
            y = 5

        # if y + height > screen_height:
        #     y = screen_height - height - 5
        # if y < 0:
        #     y = 5

        tw.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
