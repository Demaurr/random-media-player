import tkinter as tk

class VolumeBar(tk.Scale):
    """
    VolumeBar class represents a volume control widget for a media player.

    Inherits from:
        tk.Scale: tkinter widget for selecting a numerical value within a range.

    Args:
        master (tk.Tk | tk.Frame): The parent widget or frame to which this VolumeBar belongs.
        media_player: The media player object whose volume will be controlled by this VolumeBar.
        **kwargs: Additional keyword arguments to configure the VolumeBar.

    Attributes:
        media_player: The media player object whose volume is controlled by this VolumeBar.

    Methods:
        set_volume(self, volume): Sets the volume of the associated media player.

    Example:
        # Create a Tkinter window
        root = tk.Tk()

        # Create a media player instance (replace ... with your media player object)
        media_player = ...

        # Create a VolumeBar instance and pack it into the window
        volume_bar = VolumeBar(root, media_player, bg='white', fg='blue')  # Customize colors here
        volume_bar.pack()

        # Start the Tkinter event loop
        root.mainloop()
    """

    def __init__(self, master, media_player, **kwargs):
        """
        Initializes the VolumeBar widget with the specified parameters and default settings.

        Args:
            master (tk.Tk | tk.Frame): The parent widget or frame to which this VolumeBar belongs.
            media_player: The media player object whose volume will be controlled by this VolumeBar.
            **kwargs: Additional keyword arguments to configure the VolumeBar.
        """
        kwargs.setdefault("bg", "black")
        kwargs.setdefault("fg", "#2196F3")  # blue
        kwargs.setdefault("troughcolor", "#222")
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("sliderrelief", tk.FLAT)
        kwargs.setdefault("activebackground", "#2196F3")
        kwargs.setdefault("bd", 1)
        kwargs.setdefault("font", ("Segoe UI", 10, "bold"))
        super().__init__(
            master,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=200,
            command=self.set_volume,
            **kwargs,
        )
        self.set(50)  # Set initial volume to 50%
        self.media_player = media_player

    def set_volume(self, volume):
        """
        Sets the volume of the associated media player.

        Args:
            volume (int | float | str): The volume level to set, ranging from 0 to 100.
                If a string is passed, it is expected to be a numerical representation of the volume level.
        """
        self.media_player.audio_set_volume(int(volume))

