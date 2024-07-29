import os
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk, ImageSequence


class ImageViewer:
    def __init__(self, master, image_files, index=0, width=800, height=600):
        self.master = master
        self.scale_factor = 1.0
        self.dragging = False
        self.start_x = 0
        self.start_y = 0
        self.image_files = image_files
        self.current_index = index
        self.total_files = len(image_files)

        self.canvas = Canvas(master, bg='black', highlightthickness=0, width=width, height=height)
        self.canvas.pack(fill=BOTH, expand=YES)
        
        self.load_image()

        self.master.bind("<Left>", self.prev_image)
        self.master.bind("<Right>", self.next_image)
        self.master.bind("<Escape>", self.toggle_fullscreen)
        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-F>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-f>", self.toggle_fullscreen)
        self.master.bind("<Control-plus>", self.zoom_in)
        self.master.bind("<Control-minus>", self.zoom_out)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<Control-KeyPress-Right>", self.to_end)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.master.bind("<Up>", self.scroll_up)
        self.master.bind("<Down>", self.scroll_down)
        self.center_window()

    def to_end(self, event=None):
        self.current_index = len(self.image_files) - 1
        self.load_image()

    def center_window(self):
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x_offset = (self.master.winfo_screenwidth() - width) // 2
        y_offset = (self.master.winfo_screenheight() - height) // 2
        self.master.geometry(f"{width}x{height}+{x_offset}+{y_offset}")

    def load_image(self):
        image_path = self.image_files[self.current_index]
        image = Image.open(image_path)

        # Resize the image to fit the window size while maintaining the aspect ratio
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        image.thumbnail((canvas_width, canvas_height))

        image = image.resize((int(image.width * self.scale_factor), int(image.height * self.scale_factor)), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)

        # Calculate the position to centerize the image in the window
        image_width, image_height = image.size
        x_offset = (canvas_width - image_width) // 2
        y_offset = (canvas_height - image_height) // 2

        self.canvas.delete("all")
        self.canvas.create_image(x_offset, y_offset, anchor=NW, image=self.photo)
        self.canvas.image = self.photo

        # Update window title with image name and zoom level
        self.zoom_level = round(self.scale_factor * 100)
        self.image_name = os.path.basename(image_path)
        self.master.title(f"{self.image_name} [{self.current_index + 1} / {self.total_files}] - Zoom: {self.zoom_level}%")

    def next_image(self, event=None):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_image()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_image()

    def scroll_up(self, event=None):
        # Move the image up when the up arrow key is pressed
        self.canvas.move("all", 0, 10)

    def scroll_down(self, event=None):
        # Move the image down when the down arrow key is pressed
        self.canvas.move("all", 0, -10)

    def toggle_fullscreen(self, event=None):
        self.master.attributes("-fullscreen", not self.master.attributes("-fullscreen"))

    def zoom_in(self, event=None):
        self.scale_factor *= 1.1
        self.load_image()

    def zoom_out(self, event=None):
        self.scale_factor /= 1.1
        self.load_image()

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def on_mouse_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.dragging = True

    def on_mouse_drag(self, event):
        if self.dragging:
            delta_x = event.x - self.start_x
            delta_y = event.y - self.start_y
            self.canvas.move("all", delta_x, delta_y)
            self.start_x = event.x
            self.start_y = event.y

    def on_mouse_release(self, event):
        self.dragging = False