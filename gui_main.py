import os
import tkinter as tk
from tkinter import ttk
from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
from player_constants import FAV_PATH

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaPlayer")
        self.root.configure(bg="black")
        self.root.geometry("900x600")
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
        # self.root.bind('<Double-1>', self.on_double_click)
        self.file_table.bind('<Double-1>', self.on_double_click)
        self.file_table.bind('<Return>', self.on_double_click)

    def create_widgets(self):
        # Create heading label
        self.heading_label = tk.Label(self.root, text="Random Media Player", bg="black", fg="red", font=("Open Sans", 40, "bold"))
        self.heading_label.pack(side="top", pady=(10, 5))

        # Create search frame
        self.search_frame = tk.Frame(self.root, bg="black")
        self.search_frame.pack(side="top", pady=20)

        # Create search bar
        self.entry = tk.Entry(self.search_frame, bg="white", fg="black", width=60, bd=6, relief=tk.FLAT, font=("Arial", 12))
        self.entry.pack(side="left", padx=(10, 5), pady=5)

        # Create enter button
        self.enter_button = tk.Button(self.search_frame, text="Get", command=self.on_enter_pressed, bg="red", fg="black", font=("Arial", 12, "bold"),width=10, bd=4, relief=tk.RAISED)
        self.enter_button.pack(side="left", padx=(0, 10), pady=5)

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

    def list_files(self, directory):
        # self.file_table.delete(*self.file_table.get_children())
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                # tags = ("evenrow",) if idx % 2 == 0 else ("oddrow",)  # Apply alternate colors to rows
                # self.file_table.insert("", tk.END, values=(file, file_path), tags=tags)
                file_list.append((file, file_path))
        self.insert_to_table(file_list)

    def file_path_tuple(self, files: list):
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
        try:
            if folder_path_string == "play favs":
                favs = FavoritesManager()
                self.video_files = sorted(favs.get_favorites())
            elif folder_path_string == "show favs":
                with open(FAV_PATH, "r", encoding="utf-8") as file:
                    reader = file.readlines()
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
        print(f"Total Videos Found: {len(self.video_files)}")
        self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))

    def on_double_click(self, event=None):
        item = self.file_table.selection()[0]
        file_path = self.file_table.item(item, "values")[1]
        if self.video_files:
            print(f"Total Videos Found: {len(self.video_files)}")
            app = MediaPlayerApp(self.video_files, current_file=file_path,random_select=True)
            app.update_video_progress()
            app.mainloop()
        else:
            print("No video files found in the specified folder path(s).")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()