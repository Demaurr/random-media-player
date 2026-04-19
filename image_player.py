import os
import threading
from tkinter import *
# from tkinter import messagebox
from custom_messagebox import *
from PIL import Image, ImageTk
import random
from deletion_manager import DeletionManager
from mixins import ResetMixin

class ImageViewer(ResetMixin):
    def __init__(self, master, image_files, index=0, width=1000, height=600, fullscreen=False, deletion_manager=None, favorites_manager=None):
        """
        Initializes the ImageViewer.
        Args:
            master: The parent Tkinter window.
            image_files: List of image file paths to display.
            index: The starting index in the image_files list.
            width: The width of the viewer window.
            height: The height of the viewer window.
            fullscreen: Whether to start in fullscreen mode.
            deletion_manager: An instance of DeletionManager for handling deletions.
            favorites_manager: An instance of FavoritesManager for handling favorites (optional if deletion_manager is None).
        """
        self.master = master
        self.master.geometry(f"{width}x{height}")
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.dragging = False
        self.start_x = 0
        self.start_y = 0
        self.image_files = image_files
        self.current_index = index
        self.total_files = len(image_files)
        self.icommand = "Forward"
        self.original_image = None
        self.original_image_files = list(image_files) 
        self.shuffled_image_files = []
        self.shuffle_mode = False
        self.fullscreen = fullscreen
        self.deletion_manager = deletion_manager or DeletionManager(fav_manager=favorites_manager)
        self.deletion_manager.set_parent_window(self.master)
        self.master.attributes("-fullscreen", self.fullscreen)

        self.status_label = Label(master, text="", bg="black", fg="lime", font=("Segoe UI", 12, "bold"))
        self.status_label.pack(side="bottom", fill="x")
        self.canvas = Canvas(master, bg='black', highlightthickness=0, width=width, height=height)
        self.canvas.pack(fill=BOTH, expand=YES)

        self.master.after(100, self._load_image_threaded)
        self.bind_keys()
        self.center_window(width=width, height=height)

    def toggle_shuffle(self, event=None):
        self.shuffle_mode = not self.shuffle_mode

        if self.shuffle_mode:
            current_image = self.image_files[self.current_index]
            self.shuffled_image_files = list(self.original_image_files)
            random.shuffle(self.shuffled_image_files)
            self.image_files = self.shuffled_image_files
            self.current_index = self.image_files.index(current_image)
            self.show_status("🔀 Shuffle ON")
        else:
            current_image = self.image_files[self.current_index]
            self.image_files = self.original_image_files
            self.current_index = self.image_files.index(current_image)
            self.show_status("➡️ Shuffle OFF")

        self._load_image_threaded()

    def show_status(self, message, duration=2000):
        self.status_label.config(text=message)
        self.master.after(duration, lambda: self.status_label.config(text=""))

    def bind_keys(self):
        self.master.bind("<Left>", self.prev_image)
        self.master.bind("<Right>", self.next_image)
        self.master.bind("<Control-KeyPress-Right>", self.to_end)
        self.master.bind("<Control-KeyPress-Left>", self.to_start)
        self.master.bind("<Escape>", self.close_window)
        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-F>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-f>", self.toggle_fullscreen)
        self.master.bind("<Control-plus>", self.zoom_in)
        self.master.bind("<Control-minus>", self.zoom_out)
        self.master.bind("<Control-equal>", self.zoom_in)
        self.master.bind("<Control-0>", self.reset_zoom)
        self.master.bind("<r>", self.rotate_clockwise)
        self.master.bind("<R>", self.rotate_counterclockwise)
        self.master.bind("<Control-r>", self.rotate_clockwise)
        self.master.bind("<Control-R>", self.rotate_counterclockwise)
        self.master.bind("<Control-0>", self.reset_rotation)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.master.bind("<Up>", self.scroll_up)
        self.master.bind("<Down>", self.scroll_down)
        self.master.bind("<s>", self.toggle_shuffle)
        self.master.bind("<S>", self.toggle_shuffle)
        self.master.bind("<Delete>", self.set_to_delete)
        self.master.bind("<BackSpace>", self.remove_from_delete)
        self.master.bind("<Control-c>", self.copy_image_path)
        self.master.bind("<Control-C>", self.copy_image_path)

    def close_window(self, event=None):
        self.reset_window()
        self.master.destroy()

    def reset_window(self):
        self.reset(exclude=[
            "master",
            "frame",
            "label"
        ], deep=True)

    def to_end(self, event=None):
        self.current_index = len(self.image_files) - 1
        self._load_image_threaded()

    def to_start(self, event=None):
        self.current_index = 0
        self._load_image_threaded()

    def center_window(self, width, height):
        self.master.update_idletasks()
        # width = self.master.winfo_width()
        # height = self.master.winfo_height()
        width=width
        height=height
        x_offset = (self.master.winfo_screenwidth() - width) // 2
        y_offset = (self.master.winfo_screenheight() - height) // 2
        self.master.geometry(f"{width}x{height}+{x_offset}+{y_offset}")

    def _load_image_threaded(self):
        def worker():
            try:
                image_path = self.image_files[self.current_index]
                img = Image.open(image_path)

                self.original_image = img.copy()
                self.scale_factor = 1.0
                self.rotation_angle = 0

                self.canvas.after(0, self.display_image)
            except Exception as e:
                print(f"Image can't load due to error: {e}")
                if self.icommand == "Forward" and self.current_index + 1 < len(self.image_files):
                    self.current_index += 1
                    self._load_image_threaded()
                elif self.icommand == "Backward" and self.current_index - 1 >= 0:
                    self.current_index -= 1
                    self._load_image_threaded()

        threading.Thread(target=worker, daemon=True).start()

    def display_image(self):
        try:
            image = self.original_image.copy()
            if self.rotation_angle != 0:
                image = image.rotate(self.rotation_angle, expand=True)

            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            image_ratio = image.width / image.height
            canvas_ratio = canvas_width / canvas_height

            if image_ratio > canvas_ratio:
                fit_width = canvas_width
                fit_height = int(canvas_width / image_ratio)
            else:
                fit_height = canvas_height
                fit_width = int(canvas_height * image_ratio)

            final_width = int(fit_width * self.scale_factor)
            final_height = int(fit_height * self.scale_factor)

            if final_width > 0 and final_height > 0:
                image = image.resize((final_width, final_height), Image.Resampling.LANCZOS)
                self.photo = ImageTk.PhotoImage(image)
                x_offset = (canvas_width - final_width) // 2
                y_offset = (canvas_height - final_height) // 2
                self.canvas.delete("all")
                self.canvas.create_image(x_offset, y_offset, anchor=NW, image=self.photo)
                self.canvas.image = self.photo

            self.update_title()

        except Exception as e:
            print(f"Error displaying image: {e}")
            showerror(self.master, "Error", f"Error displaying image: {e}")

    def update_title(self):
        image_path = self.image_files[self.current_index]
        zoom_level = round(self.scale_factor * 100)
        image_name = os.path.basename(image_path)
        title_parts = [
            f"[{self.current_index + 1}/{self.total_files}] {image_name}",
            f"Zoom: {zoom_level}%"
        ]
        if self.rotation_angle != 0:
            title_parts.append(f"Rotation: {self.rotation_angle}°")
        self.master.title(" - ".join(title_parts))

    def rotate_clockwise(self, event=None):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.display_image()

    def rotate_counterclockwise(self, event=None):
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.display_image()

    def reset_rotation(self, event=None):
        self.rotation_angle = 0
        self.display_image()

    def reset_zoom(self, event=None):
        self.scale_factor = 1.0
        self.display_image()

    def next_image(self, event=None):
        if self.current_index < len(self.image_files) - 1:
            self.icommand = "Forward"
            self.current_index += 1
            self._load_image_threaded()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.icommand = "Backward"
            self.current_index -= 1
            self._load_image_threaded()

    def scroll_up(self, event=None):
        self.canvas.move("all", 0, 10)

    def scroll_down(self, event=None):
        self.canvas.move("all", 0, -10)

    def toggle_fullscreen(self, event=None):
        self.master.attributes("-fullscreen", not self.master.attributes("-fullscreen"))
        self.master.after(100, self.display_image)

    def zoom_in(self, event=None):
        self.scale_factor *= 1.1
        self.display_image()

    def zoom_out(self, event=None):
        self.scale_factor /= 1.1
        self.display_image()

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

    def set_to_delete(self, event=None):
        image_path = self.image_files[self.current_index]
        self.deletion_manager.mark_for_deletion(image_path)
        self.show_status(f"Marked for deletion: {os.path.basename(image_path)}")
    
    def remove_from_delete(self, event=None):
        image_path = self.image_files[self.current_index]
        self.deletion_manager.remove_from_deletion(image_path)
        self.show_status(f"Removed from deletion: {os.path.basename(image_path)}")

    def copy_image_path(self, event=None):
        try:
            image_path = self.image_files[self.current_index]
            abs_path = os.path.abspath(image_path)

            self.master.clipboard_clear()
            self.master.clipboard_append(abs_path)
            self.master.update()

            self.show_status("📋 Absolute path copied")
        except Exception as e:
            showerror(self.master, "Error", f"Failed to copy path: {e}")


    # def add_to_favorites(self, event=None):
        # image_path = self.image_files[self.current_index]
        # self.favorites.add_to_favorites(image_path)
        # self.update_title()

    # def remove_from_favorites(self, event=None):
        # image_path = self.image_files[self.current_index]
        # self.favorites.remove_from_favorites(image_path)
        # self.update_title()