import os
import csv
import tkinter as tk
from tkinter import Toplevel, ttk
from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
from image_player import ImageViewer
from player_constants import FAV_PATH, FOLDER_LOGS, SCREENSHOTS_FOLDER

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaPlayer")
        self.root.configure(bg="black")
        self.root.geometry("900x600")
        self.play_images = False
        self.play_folder = False
        self.center_window()
        self.create_widgets()
        self._keybinding()

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_coordinate = (screen_width - 900) // 2
        y_coordinate = (screen_height - 600) // 2
        self.root.geometry(f"900x600+{x_coordinate}+{y_coordinate}")

    def _keybinding(self):
        # Bind Enter key to on_enter_pressed method
        self.entry.bind('<Return>', self.on_enter_pressed)
        self.search_entry.bind('<Return>', self.on_search_pressed)
        # self.root.bind('<Double-1>', self.on_double_click)
        self.file_table.bind('<Double-1>', self.on_double_click)
        self.file_table.bind('<Return>', self.on_double_click)
        self.entry.bind("<Control-Return>", self.random_play)
        self.search_entry.bind("<Control-Return>", self.random_play)


    def create_widgets(self):
        # Create heading label
        self.heading_label = tk.Label(self.root, text="Random Media Player", bg="black", fg="red", font=("Open Sans", 44, "bold"))
        self.heading_label.pack(side="top", pady=(10, 5))

        # Create search frame
        self.input_frame = tk.Frame(self.root, bg="black")
        self.input_frame.pack(side="top", pady=(15, 5))

        # Create search bar
        self.entry = tk.Entry(self.input_frame, bg="white", fg="black", width=60, bd=6, relief=tk.FLAT, font=("Arial", 12))
        self.entry.pack(side="left", padx=(10, 5), pady=5)

        # Create enter button
        self.enter_button = tk.Button(self.input_frame, text="Get", command=self.on_enter_pressed, bg="green", fg="black", font=("Arial", 12, "bold"),width=10, bd=4, relief=tk.RAISED)
        self.enter_button.pack(side="left", padx=(0, 10), pady=5)

        # Create search frame
        self.search_frame = tk.Frame(self.root, bg="black")
        self.search_frame.pack(side="top", pady=(0, 10))

        # Create search bar
        self.search_entry = tk.Entry(self.search_frame, bg="white", fg="black", width=30, bd=3, relief=tk.FLAT, font=("Arial", 12))
        self.search_entry.pack(side="left", padx=(10, 5), pady=0)

        # Create search button
        self.search_button = tk.Button(self.search_frame, text="Search", command=self.on_search_pressed, bg="gray", fg="black", font=("Arial", 12, "bold"),width=10, bd=0.5, relief=tk.RAISED)
        self.search_button.pack(side="left", padx=(0, 5), pady=0)

        self.show_caps = tk.Button(self.search_frame, text="Caps", command=self.display_caps, bg="green", fg="black", font=("Arial", 12, "bold"),width=7, bd=0.5, relief=tk.RAISED)
        self.show_caps.pack(side="left", padx=(0, 5), pady=0)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Open Sans", 16, "bold"))

        # Create file table
        self.file_table = ttk.Treeview(self.root, columns=("File Name", "Folder Path"), show="headings")
        self.file_table.heading("File Name", text="File Name")
        self.file_table.heading("Folder Path", text="Folder Path")
        self.file_table.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        # change the width to have scroller with the window
        self.file_table.column("File Name", width=400)  # Align columns to center
        self.file_table.column("Folder Path", width=400)  # Align columns to center

        # Set alternate colors for even and odd rows
        self.file_table.tag_configure("evenrow", background="#333333", foreground="white", font=("Arial", 10))  # Dark gray background
        self.file_table.tag_configure("oddrow", background="#555555", foreground="white", font=("Arial", 10))  # Light gray background
        # self.file_table.tag_configure("evenrow", font=("Arial", 20))

        # Create vertical scrollbar
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.file_table.yview)
        self.scrollbar.pack(side="right", fill="y")

        # Configure Treeview to use vertical scrollbar
        self.file_table.configure(yscrollcommand=self.scrollbar.set)

    def update_entry_text(self, text):
        self.entry.delete(0, tk.END)  # Clear the current text in the entry
        self.entry.insert(0, text)    # Insert the new text

    def list_files(self, directory):
        # self.file_table.delete(*self.file_table.get_children())
        file_list = []
        self.file_path = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # tags = ("evenrow",) if idx % 2 == 0 else ("oddrow",)  # Apply alternate colors to rows
                # self.file_table.insert("", tk.END, values=(file, file_path), tags=tags)
                file_list.append((file, file_path))
                self.file_path.append(file_path)
        self.insert_to_table(file_list)

    def file_path_tuple(self, files: list):
        """converts the video paths list to list of tuples contaiting filenaem, filepath"""
        temp_files = []
        for file in files:
            temp_files.append((os.path.basename(file),file))
        return temp_files

    def insert_to_table(self, files: list):
        self.file_table.delete(*self.file_table.get_children())
        for idx, (file, file_path) in enumerate(files):
            tags = ("evenrow",) if idx % 2 == 0 else ("oddrow",)  # Apply alternate colors to rows
            self.file_table.insert("", tk.END, values=(file, file_path), tags=tags)

    def on_enter_pressed(self, event=None):
        folder_path_string = self.entry.get()
        vf_loader = VideoFileLoader()
        self.play_folder = False
        try:
            if folder_path_string == "play favs":
                favs = FavoritesManager()
                self.video_files = sorted(favs.get_favorites())
            elif folder_path_string == "show paths":
                self.play_folder = True
                with open(FOLDER_LOGS, "r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    self.folders = list(set((row["Folder Path"], row["Csv Path"]) for row in reader))
                self.video_files = []
                # print(self.folders)
                
                    # print(reader)
                # folder_path_string = input("Enter folder path(s) or Your Favs: ").strip()
                # self.video_files = vf_loader.start_here(folder_path_string)
            else:
                self.video_files = vf_loader.start_here(folder_path_string)
        except ImportError as e:
            print(f"An Import Error Occurred: {e}")
            self.video_files = vf_loader.get_videos_from_paths(folder_paths=folder_path_string.split(","))
        except Exception as e:
            print(f"An Unknown Error Occurred {e}")
            return
        if not self.play_folder:
            print(f"Total Videos Found: {len(self.video_files)}")
            self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
        elif self.play_folder:
            print(f"Total Folders in Search History: {len(self.folders)}")
            self.insert_to_table(sorted(self.folders))

    def on_search_pressed(self, event=None):
        query = self.search_entry.get().lower()
        self.file_table.delete(*self.file_table.get_children())
        file_list = []
        try:
            search_files = self.image_files if self.play_images else self.video_files
            for file in search_files:
                if query in file.lower():  # Check if query matches file name
                    file_name = os.path.basename(file)
                    file_list.append((file_name, file))
            print(f"Total Files for {query}: {len(file_list)}")
            self.insert_to_table(sorted(file_list))
        except AttributeError as e:
            print("No videos found to search from.")
            print(f"An Exception is raised {e}")
        except Exception as e:
            print(f"An Error {e} Occurred")

    def on_double_click(self, event=None):
        item = self.file_table.selection()[0]
        file_path = self.file_table.item(item, "values")[1]
        if self.play_folder:
            folder_path = self.file_table.item(item, "values")[0]
            self.play_folder = False
            vf_load = VideoFileLoader()
            self.video_files = vf_load.start_here(file_path)
            print(f"Total Videos Found in {folder_path}: {len(self.video_files)}")
            self.update_entry_text(folder_path)
            self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
        elif self.play_images:
            viewer_window = Toplevel(self.root)
            viewer_window.title("Image Viewer")
            self.play_images = False
            image_viewer_width = 900
            image_viewer_height = 600
            # ImageViewer instance with the specified width and height
            ImageViewer(viewer_window, self.image_files,index=self.image_files.index(file_path), width=image_viewer_width, height=image_viewer_height)

        else:
            self.files = sorted(self.get_files_from_table())
            # if self.video_files:
            if self.files:
                print(f"Total Videos Found: {len(self.files)}")
                app = MediaPlayerApp(self.files, current_file=file_path,random_select=True)
                app.update_video_progress()
                app.mainloop()
            else:
                print("No video files found in the specified folder path(s).")

    def random_play(self, event=None):
        self.on_enter_pressed()
        self.files = sorted(self.get_files_from_table())
        if self.files:
            app = MediaPlayerApp(self.files, random_select=True)
            app.update_video_progress()
            app.mainloop()
        else:
            print("No video files found in the specified folder path(s).")

    def get_files_from_table(self):
        """
        Get file paths from the file_table.
        Returns a list of file paths.
        """
        file_paths = []
        for item in self.file_table.get_children():
            file_path = self.file_table.item(item, "values")[1]
            file_paths.append(file_path)
        return file_paths
    
    def display_caps(self):
        self.play_images = True
        self.image_files = VideoFileLoader.load_image_files()
        self.update_entry_text(SCREENSHOTS_FOLDER)
        self.insert_to_table(self.file_path_tuple(self.image_files))

        
if __name__ == "__main__":
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()