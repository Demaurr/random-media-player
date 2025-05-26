import os
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from PIL import Image, ImageTk, ImageSequence


class ImageViewer:
    def __init__(self, master, image_files, index=0, width=800, height=600, fullscreen=False):
        self.master = master
        self.scale_factor = 1.0
        self.rotation_angle = 0
        self.dragging = False
        self.start_x = 0
        self.start_y = 0
        self.image_files = image_files
        # self.favorites = favorites
        self.current_index = index
        self.total_files = len(image_files)
        self.icommand = "Forward"
        self.original_image = None  # Store original image for rotations
        self.fullscreen = fullscreen
        self.master.attributes("-fullscreen", self.fullscreen)
        
        self.status_label = Label(master, text="", bg="black", fg="lime", font=("Segoe UI", 12, "bold"))
        self.status_label.pack(side="bottom", fill="x")
        self.canvas = Canvas(master, bg='black', highlightthickness=0, width=width, height=height)
        self.canvas.pack(fill=BOTH, expand=YES)
        
        self.master.after(100, self.load_image)
        self.bind_keys()
        self.center_window()

    def bind_keys(self):
        """Bind all keyboard shortcuts"""
        self.master.bind("<Left>", self.prev_image)
        self.master.bind("<Right>", self.next_image)
        self.master.bind("<Control-KeyPress-Right>", self.to_end)
        self.master.bind("<Control-KeyPress-Left>", self.to_start)
        
        self.master.bind("<Escape>", self.toggle_fullscreen)
        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-F>", self.toggle_fullscreen)
        self.master.bind("<KeyPress-f>", self.toggle_fullscreen)
        self.master.bind("<Control-plus>", self.zoom_in)
        self.master.bind("<Control-minus>", self.zoom_out)
        self.master.bind("<Control-equal>", self.zoom_in)
        self.master.bind("<Control-0>", self.reset_zoom)
        
        # Rotation controls (NEW)
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
        
        # self.master.bind("<Control-f>", self.add_to_favorites)
        # self.master.bind("<Control-F>", self.add_to_favorites)
        # self.master.bind("<Control-D>", self.add_to_favorites)
        # self.master.bind("<Control-d>", self.remove_from_favorites)

    def to_end(self, event=None):
        self.current_index = len(self.image_files) - 1
        self.load_image()

    def to_start(self, event=None):
        self.current_index = 0
        self.load_image()

    def center_window(self):
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        x_offset = (self.master.winfo_screenwidth() - width) // 2
        y_offset = (self.master.winfo_screenheight() - height) // 2
        self.master.geometry(f"{width}x{height}+{x_offset}+{y_offset}")

    def load_image(self):
        try:
            image_path = self.image_files[self.current_index]
            self.original_image = Image.open(image_path)
            
            # Reset transformations when loading new image
            self.scale_factor = 1.0
            self.rotation_angle = 0
            
            self.display_image()
            
        except Exception as e:
            print(f"Image can't load due to error: {e}")
            self.next_image() if self.icommand == "Forward" else self.prev_image()

    def display_image(self):
        """Display the image with current transformations applied"""
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
            
            # Update window title
            self.update_title()
            
        except Exception as e:
            print(f"Error displaying image: {e}")

    def update_title(self):
        """Update window title with current image info"""
        image_path = self.image_files[self.current_index]
        zoom_level = round(self.scale_factor * 100)
        image_name = os.path.basename(image_path)
        title_parts = []
        
        title_parts.append(f"{image_name} [{self.current_index + 1}/{self.total_files}]")
        title_parts.append(f"Zoom: {zoom_level}%")
        
        if self.rotation_angle != 0:
            title_parts.append(f"Rotation: {self.rotation_angle}°")
        
        self.master.title(" - ".join(title_parts))

    def rotate_clockwise(self, event=None):
        """Rotate image 90 degrees clockwise"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.display_image()

    def rotate_counterclockwise(self, event=None):
        """Rotate image 90 degrees counterclockwise"""
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.display_image()

    def reset_rotation(self, event=None):
        """Reset rotation to 0 degrees"""
        self.rotation_angle = 0
        self.display_image()

    def reset_zoom(self, event=None):
        """Reset zoom to 100%"""
        self.scale_factor = 1.0
        self.display_image()

    def next_image(self, event=None):
        if self.current_index < len(self.image_files) - 1:
            self.icommand = "Forward"
            self.current_index += 1
            self.load_image()

    def prev_image(self, event=None):
        if self.current_index > 0:
            self.icommand = "Backward"
            self.current_index -= 1
            self.load_image()

    def scroll_up(self, event=None):
        self.canvas.move("all", 0, 10)

    def scroll_down(self, event=None):
        self.canvas.move("all", 0, -10)

    def toggle_fullscreen(self, event=None):
        self.master.attributes("-fullscreen", not self.master.attributes("-fullscreen"))
        # Redisplay image to fit new window size
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

    # def add_to_favorites(self, event=None):
        # image_path = self.image_files[self.current_index]
        # self.favorites.add_to_favorites(image_path)
        # self.update_title()

    # def remove_from_favorites(self, event=None):
        # image_path = self.image_files[self.current_index]
        # self.favorites.remove_from_favorites(image_path)
        # self.update_title()