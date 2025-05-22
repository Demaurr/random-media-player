import tkinter as tk

class VideoProgressBar(tk.Scale):
    """A custom progress bar for video playback."""

    def __init__(self, master, command, **kwargs):
        """
        Initializes the VideoProgressBar.

        Args:
            master: The master widget.
            command: The callback function to be called when the value is changed.
            **kwargs: Additional keyword arguments to configure the progress bar.
        """
        kwargs["showvalue"] = False
        kwargs.setdefault("bg", "black")
        kwargs.setdefault("fg", "#2196F3")  # blue
        kwargs.setdefault("troughcolor", "#222")
        kwargs.setdefault("activebackground", "#2196F3")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("font", ("Segoe UI", 10, "bold"))
        super().__init__(
            master,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=800,
            command=command,
            **kwargs,
        )
        self.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        """
        Handles the click event on the progress bar.

        Args:
            event: The click event.
        """
        if self.cget("state") == tk.NORMAL:
            value = (event.x / self.winfo_width()) * 100
            self.set(value)