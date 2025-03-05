from datetime import datetime, timedelta
import os
import csv
from pprint import pprint
import tkinter as tk
from tkinter import Toplevel, ttk
from tkinter import messagebox
from tkinter import filedialog
from logs_writer import LogManager
from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
from deletion_manager import DeletionManager
from file_manager import FileManager
from image_player import ImageViewer
from player_constants import FILES_FOLDER, REPORTS_FOLDER, WATCHED_HISTORY_LOG_PATH, FOLDER_LOGS, LOG_PATH, SCREENSHOTS_FOLDER, DELETE_FILES_CSV
from static_methods import create_csv_file, ensure_folder_exists, normalise_path, get_file_size
from get_aspects import VideoProcessor
import cProfile

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaPlayer")
        self.root.configure(bg="black")
        self.root.geometry("900x600")
        self.play_images = False
        self.play_folder = False
        self.total_files = 0
        self.total_size = 0
        self.total_search_results = 0
        self.total_duration_watched = 0.0
        self.search_size = 0

        # Instantiate DeletionManager
        ensure_folder_exists(FILES_FOLDER)
        ensure_folder_exists(SCREENSHOTS_FOLDER)
        ensure_folder_exists(REPORTS_FOLDER)
        self.deletion_manager = DeletionManager()
        self.fav_manager = FavoritesManager()
        self.logger = LogManager(LOG_PATH)
        self.video_processor = VideoProcessor
        create_csv_file(["File Path", "Delete_Status", "File Size", "Modification Time"], DELETE_FILES_CSV)
        self.center_window()
        self.create_widgets()
        self._keybinding()
        self.create_context_menu()

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
        self.file_table.bind('<Double-1>', self.on_double_click)

        # context menu on right-click
        self.file_table.bind("<Button-3>", self.on_right_click)

        self.file_table.bind('<Return>', self.on_double_click)
        self.entry.bind("<Control-Return>", self.random_play)
        self.search_entry.bind("<Control-Return>", self.random_play)
        
        # Bind Delete key to delete_selected_files with direct_delete=False
        self.file_table.bind('<Delete>', lambda event: self.delete_selected_files(direct_delete=False, event=event))

        # Move the Selected Items in a Folder
        self.file_table.bind('<Control-m>', self.move_selected_files)
        self.file_table.bind('<Control-M>', self.move_selected_files)

        # Adding Files to Favorites from the Main Gui
        self.file_table.bind('<Control-d>', self.remove_from_favorites)
        self.file_table.bind('<Control-D>', self.remove_from_favorites)
        self.file_table.bind('<Control-f>', self.add_to_favorites)
        self.file_table.bind('<Control-F>', self.add_to_favorites)

        
        # Bind Shift+Delete to delete_selected_files with direct_delete=True
        # self.file_table.bind('<Shift-Delete>', lambda event: self.delete_selected_files(direct_delete=True, event=event))
        self.file_table.bind('<Control-Shift-Delete>', lambda event: self.remove_from_deletion(self.get_selected_video(), event))

    def get_selected_video(self):
        selected_item = self.file_table.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select files to mark for deletion.")
            return -1
        file_path = []
        for selection in selected_item:
            file_path.append(self.file_table.item(selection, "values")[2])
        return file_path
    
    def remove_from_favorites(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Select a File To Remove from Favs.")
            return
        fav_manager = FavoritesManager()
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if fav_manager.check_favorites(file_path):  # Move the selected file
                    fav_manager.delete_from_favorites(file_path)  # Optionally remove from table after moving
                else:
                    messagebox.showerror("Removal Failed", f"Failed to remove file: {file_path} from Favorites.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred in Favorites Removal: {e}")
                continue

        messagebox.showinfo("File Removed From Favorites", f"{len(selected_items)} unfavorited successfully.")

    def add_to_favorites(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Select a File To Add-To Favs.")
            return
        
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to add {len(selected_items)} file(s) to Favorites?")
        if not confirm:
            return
        
        fav_manager = FavoritesManager()
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if not fav_manager.check_favorites(file_path):  # Move the selected file
                    fav_manager.add_to_favorites(file_path)
                else:
                    messagebox.showerror("Addition Failed", f"Failed to Add file: {file_path} To Favorites.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred while Adding {file_path} To Favorites: {e}")
                continue

        messagebox.showinfo("File(s) Added To Favorites", f"{len(selected_items)} file(s) Added-To Favorites successfully.")

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Move", command=self.move_selected_files)  # Add Move option
        self.context_menu.add_command(label="Move to Recycle Bin", command=self.delete_selected_files)
        # self.context_menu.add_separator()
        # self.context_menu.add_command(label="Properties", command=self.show_properties)

    def move_selected_files(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to move.")
            return

        dest_folder = filedialog.askdirectory(title="Select Destination Folder")
        if not dest_folder:
            return
        file_manager = FileManager()  # Create an instance of FileManager
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            try:
                if file_manager.move_file(file_path, dest_folder):  # Move the selected file
                    self.file_table.delete(item)  # Optionally remove from table after moving
                else:
                    messagebox.showerror("Move Failed", f"Failed to move file: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

        messagebox.showinfo("Move Complete", f"{len(selected_items)} file(s) moved successfully.")
        


    def delete_selected_files(self, direct_delete=False, event=None):
        """Marks selected files from the file table for deletion or deletes them directly."""
        selected_items = self.file_table.selection()
        status = "ToDelete"
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to mark for deletion.")
            return
        if direct_delete:
            status = "Deleted"

        confirm_message = "mark" if not direct_delete else "delete"
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to {confirm_message} {len(selected_items)} file(s)?")
        if not confirm:
            return

        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            self.deletion_manager.mark_for_deletion(file_path, status)
        
        # Use the DeletionManager to handle deletion or marking
        if direct_delete:
            self.deletion_manager.delete_files_in_csv(skip_confirmation=True)
        
        messagebox.showinfo("Deletion Marked", f"{len(selected_items)} file(s) marked for deletion.")

    def remove_from_deletion(self, file, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to move.")
            return
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            try:
                self.deletion_manager.remove_from_deletion(file_path)      
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")
        messagebox.showinfo("Removed Marked", f"{len(selected_items)} file(s) removed from deletion list.")

    def delete_files_in_csv(self):
        """Deletes files marked as 'ToDelete' using the DeletionManager."""
        self.deletion_manager.delete_files_in_csv()

    @staticmethod
    def convert_bytes(bytes_size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0
        size = float(bytes_size)

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1

        return f"{size:.2f} {units[index]}"


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
        self.search_button = tk.Button(self.search_frame, text="Search", command=self.on_search_pressed, bg="gray", fg="black", font=("Arial", 10, "bold"),
                                       width=10, bd=0.5, relief=tk.RAISED)
        self.search_button.pack(side="left", padx=(0, 5), pady=0)

        self.filter_favs = tk.Button(self.search_frame, text="Favs", command=self.check_update_favs, bg="green", fg="black", font=("Arial", 10, "bold"), bd=0.5, relief=tk.RAISED)
        self.filter_favs.pack(side="left", pady=0)

        self.delete_button = tk.Button(self.search_frame, text="Del-All", command=self.delete_files_in_csv, bg="red", fg="white", font=("Arial", 10, "bold"), bd=0.5, relief=tk.RAISED)
        self.delete_button.pack(side="left", padx=5, pady=5)

        self.refresh_deleted = tk.Button(self.search_frame, text="Refresh-Del", command=self.refresh_deletions, bg="red", fg="white", font=("Arial", 10, "bold"),bd=0.5, relief=tk.RAISED)
        self.refresh_deleted.pack(side="left", pady=5, padx=(0,5))

        self.show_caps = tk.Button(self.search_frame, text="Snaps", command=self.display_caps, bg="green", fg="black", font=("Arial", 10, "bold"), bd=0.5, relief=tk.RAISED)
        self.show_caps.pack(side="left", pady=0)

        self.show_verticals = tk.Button(self.search_frame, text="V", command=self.get_verticals, bg="white", fg="black", font=("Arial", 10, "bold"), bd=0.7, relief=tk.RAISED)
        self.show_verticals.pack(side="left", padx=5, pady=0)

        self.show_horizontals = tk.Button(self.search_frame, text="L", command=self.get_horizontals, bg="white", fg="black", font=("Arial", 10, "bold"), bd=0.7, relief=tk.RAISED)
        self.show_horizontals.pack(side="left", padx=0, pady=0)

        self.stats_frame = tk.Frame(self.root, bg="black")
        self.stats_frame.pack(side="top", pady=0)

        self.total_files_label = tk.Label(self.stats_frame, text="Total Files: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.total_files_label.pack(side="left", padx=(10, 10))

        self.search_results_label = tk.Label(self.stats_frame, text="Search Results: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.search_results_label.pack(side="left", padx=(0, 10))

        self.total_size_label = tk.Label(self.stats_frame, text="Total Size: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.total_size_label.pack(side="left", padx=(0, 10))

        self.search_size_label = tk.Label(self.stats_frame, text="S-Size: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.search_size_label.pack(side="left", padx=(0, 10))

        self.total_duration_label = tk.Label(self.stats_frame, text="Durations: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.total_duration_label.pack(side="left", padx=(10, 10))

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Open Sans", 16, "bold"))

        # Create file table
        self.file_table = ttk.Treeview(self.root, columns=("#", "File Name", "Folder Path"), show="headings")
        self.file_table.heading("#", text="#")
        self.file_table.heading("File Name", text="File Name")
        self.file_table.heading("Folder Path", text="Folder Path")
        self.file_table.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        # change the width to have scroller with the window
        self.file_table.column("#", width=30)  # Align columns to center
        self.file_table.column("File Name", width=370)  # Align columns to center
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

    def update_stats(self):
            self.total_files_label.config(text=f"Total Files: {self.total_files}")
            self.total_size_label.config(text=f"Total Size: {self.total_size}")
            self.search_results_label.config(text=f"Search Results: {self.total_search_results}")
            self.total_duration_label.config(text=f"Durations (hours): {self.total_duration_watched}")
            self.search_size_label.config(text=f"S-Size: {self.search_size}")

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
            self.file_table.insert("", tk.END, values=(idx, file, file_path), tags=tags)

    def on_enter_pressed(self, event=None):
        folder_path_string = self.entry.get()
        vf_loader = VideoFileLoader()
        self.play_folder = False
        try:
            if folder_path_string == "play favs":
                favs = FavoritesManager()
                self.video_files = sorted(favs.get_favorites())
                self.total_files = len(self.video_files)
                self.total_size = self.convert_bytes(favs.total_size)
                self.update_stats()
            
            elif folder_path_string == "show paths":
                self.play_folder = True
                with open(FOLDER_LOGS, "r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)

                    self.folders = list(set((normalise_path(row["Folder Path"]), normalise_path(row["Csv Path"])) for row in reader if os.path.isdir(row["Folder Path"])))
                self.video_files = []
            
            elif folder_path_string == "show deletes":
                # Show files marked as "ToDelete"
                self.show_deletes()
            
            elif folder_path_string == "show deleted":
                # Show files marked as "ToDelete"
                self.show_deletes(deleted=True)

            elif folder_path_string == "show history":
                self.video_files = self.get_history_files()
                self.total_files = len(self.video_files)
                self.update_stats()
                self.total_duration_watched = 0

            else:
                self.video_files = vf_loader.start_here(normalise_path(folder_path_string))
                self.total_size = self.convert_bytes(vf_loader.total_size_in_bytes)
                self.total_files = len(self.video_files)
                self.update_stats()
        
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

    def refresh_deletions(self):
        self.deletion_manager.check_deleted()
        self.show_deletes(deleted=True)
        self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))


    def on_right_click(self, event):
        """ Handle right-click to open context menu """
        # Check if the file is already selected
        item = self.file_table.identify_row(event.y)
        
        if item not in self.file_table.selection():
            # If the item is not part of the current selection, keep the old selection
            self.file_table.selection_set(item)

        self.selected_item = item
        try:
            self.context_menu.post(event.x_root, event.y_root)
        except IndexError:
            pass
    
    def get_files_marked_for_deletion(self):
        """Retrieves files marked as 'ToDelete' from the DELETE_FILES_CSV."""
        delete_files = []
        self.total_size = 0
        try:
            with open(DELETE_FILES_CSV, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[1] == "ToDelete":
                        delete_files.append(row[0])  # Append the file path
                        if row[2] != "N/A":
                            self.total_size += float(row[2])
        except FileNotFoundError:
            messagebox.showinfo("No Files", "No files marked for deletion.")
        self.total_size = self.convert_bytes(self.total_size)
        return delete_files
    
    def get_files_deleted(self):
        """Retrieves files marked as 'Deleted' from the DELETE_FILES_CSV."""
        delete_files = []
        self.total_size = 0
        try:
            with open(DELETE_FILES_CSV, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[1] == "Deleted":
                        delete_files.append(row[0])  # Append the file path
                        if row[2] != "N/A":
                            self.total_size += float(row[2])
        except FileNotFoundError:
            messagebox.showinfo("No Files", "No files marked for deletion.")
        self.total_size = self.convert_bytes(self.total_size)
        return delete_files

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
            if query == '':
                self.search_size = self.total_size
            elif not self.entry.get() in ["show deleted"]:
                self.update_search_size([file[1] for file in file_list])
            self.total_search_results = len(file_list)
            self.update_stats()
            self.insert_to_table(sorted(file_list))
        except AttributeError as e:
            print("No videos found to search from.")
            print(f"An Exception is raised {e}")
            messagebox.showerror("Attribute Error", f"Error in Search Pressed: {e}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            messagebox.showerror("Error", f"Exception in Search Pressed: {e}")

    def on_filter_fav(self, event=None):
        files = self.get_files_from_table()
        favs = self.fav_manager
        if files:
            files = [normalise_path(file) for file in files if favs.check_favorites(file)]
            self.total_search_results = len(files)
            self.update_search_size(files)
            self.insert_to_table(self.file_path_tuple(files))
            self.update_stats()

    def check_update_favs(self, event=None):
        files = self.file_path_tuple(self.get_files_from_table())
        favs = self.fav_manager.get_favorites_by_name()
        fav_files = []
        if files:
            for file in files:
                if file[0] in favs.keys() and file[1] in favs.values():
                    fav_files.append(file)
                elif file[0] in favs.keys():
                    self.fav_manager.add_to_favorites(normalise_path(file[1]))
                    fav_files.append(file)
            self.total_search_results = len(fav_files)
            self.update_search_size([file[1] for file in fav_files])
            self.insert_to_table(fav_files)
            self.update_stats()
                    


    def on_double_click(self, event=None):
        try:
            item = self.file_table.selection()[0]
            file_path = self.file_table.item(item, "values")[2]
            if self.play_folder:
                folder_path = self.file_table.item(item, "values")[1]
                vf_load = VideoFileLoader()
                self.play_folder = False
                self.play_images = False
                self.video_files = vf_load.start_here(file_path)
                self.total_size = self.convert_bytes(vf_load.total_size_in_bytes)
                self.total_files = len(self.video_files)
                self.update_stats()
                print(f"Total Videos Found in {folder_path}: {len(self.video_files)}")
                self.update_entry_text(folder_path)
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
            
            elif self.play_images:
                # Disable the main window
                # self.root.wm_attributes("-disabled", True)
                viewer_window = Toplevel(self.root)
                viewer_window.title("Image Viewer")
                image_viewer_width = 900
                image_viewer_height = 600
                image_files = self.get_files_from_table()

                # Create ImageViewer instance with the specified width and height
                ImageViewer(viewer_window, image_files, index=image_files.index(file_path), width=image_viewer_width, height=image_viewer_height)
                
                # Re-enable the main window when the image viewer window is closed
                # viewer_window.protocol("WM_DELETE_WINDOW", lambda: self._on_close_viewer(viewer_window))

            else:
                self.files = sorted(self.get_files_from_table())
                print(f"Total Videos Found: {len(self.files)}")
                if self.files:
                    # Disable the main window
                    # self.root.wm_attributes("-disabled", True)
                    self.play_images = False
                    app = MediaPlayerApp(self.files, current_file=file_path, random_select=True)
                    app.update_video_progress()
                    
                    # Re-enable the main window when the player window is closed
                    # app.protocol("WM_DELETE_WINDOW", lambda: self._on_close_player(app))

                    # Start the media player loop
                    app.mainloop()
                else:
                    print("No video files found in the specified folder path(s).")
        
        except IndexError as e:
            messagebox.showerror("Error", f"{e}")

    def update_search_size(self, file_list):
        self.search_size = 0
        size = 0
        for file in file_list:
             size += get_file_size(file)

        self.search_size = self.convert_bytes(size)

    def get_verticals(self):
        try:
            file_list = self.get_files_from_table()
            # pprint(file_list)
            # video_processor = VideoProcessor(file_list)
            video_processor = self.video_processor(file_list)
            verticals = video_processor.get_vertical_videos()
            print(f"Total Verticals Files: {len(verticals)}")
            self.total_search_results = len(verticals)
            self.update_search_size(verticals)
            self.update_stats()
            self.insert_to_table(self.file_path_tuple(sorted(verticals)))
            messagebox.showinfo("Total Files Found", f"Total Vertical Videos Found: {self.total_search_results}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            messagebox.showerror("Error", f"Exception in Getting Vertical Pressed: {e}")

    def get_horizontals(self):
        try:
            file_list = self.get_files_from_table()
            # pprint(file_list)
            # video_processor = VideoProcessor(file_list)
            video_processor = self.video_processor(file_list)
            horizontals = video_processor.get_horizontal_videos()
            print(f"Total Verticals Files: {len(horizontals)}")
            self.total_search_results = len(horizontals)
            self.update_search_size(horizontals)
            self.update_stats()
            self.insert_to_table(self.file_path_tuple(sorted(horizontals)))
            messagebox.showinfo("Total Files Found", f"Total Vertical Videos Found: {self.total_search_results}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            messagebox.showerror("Error", f"Exception in Getting Vertical Pressed: {e}")

    # def _on_close_player(self, player_window): # Not Working as Expecteed
    #     """Callback to re-enable the main window after the player window is closed."""
    #     player_window.destroy() 
    #     self.root.wm_attributes("-disabled", False)

    # def _on_close_viewer(self, viewer_window): # Not Working as Expecteed
    #     """Callback to re-enable the main window after the image viewer window is closed."""
    #     viewer_window.destroy()  
    #     self.root.wm_attributes("-disabled", False)  # Re-enable the main window

    def random_play(self, event=None):
        self.on_enter_pressed()
        self.files = sorted(self.get_files_from_table())
        if self.files:
            # self.root.wm_attributes("-disabled", True)
            app = MediaPlayerApp(self.files, random_select=True)
            app.update_video_progress()
            # app.protocol("WM_DELETE_WINDOW", lambda: self._on_close_player(app))
            app.mainloop()
        else:
            print("No video files found in the specified folder path(s).")

    def show_deletes(self, deleted=False):
        self.video_files = self.get_files_marked_for_deletion() if not deleted else self.get_files_deleted()
        self.total_files = len(self.video_files)
        self.update_stats()

    def get_history_files(self, days=30):
        file_path = WATCHED_HISTORY_LOG_PATH
        thirty_days_ago = datetime.now() - timedelta(days=days)
        
        unique_file_names = set()
        self.total_duration_watched = 0  # Initialize total duration watched in seconds
        row_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                row_count += 1
                
                # Parse the date from the 'Date Watched' column
                try:
                    date_watched = datetime.strptime(row['Date Watched'], '%Y-%m-%d %H:%M:%S')  # Adjust format if needed
                except ValueError:
                    print(f"Warning: Invalid date format in row {row_count}. Skipping.")
                    continue
                
                # Only calculate for rows watched within the last 'days' days
                if date_watched >= thirty_days_ago:
                    # Parse and accumulate the duration watched in seconds
                    try:
                        duration_watched = self.calculate_duration_in_seconds(row['Duration Watched'])
                        self.total_duration_watched += duration_watched
                    except ValueError:
                        print(f"Warning: Invalid duration format in row {row_count}. Skipping.")
                        continue
                    
                    # Add the file name to the unique set
                    unique_file_names.add(row['File Name'])
                
                # Print progress every 1000 rows
                if row_count % 1000 == 0:
                    print(f"Processed {row_count} rows...")

        
        self.total_duration_watched = round(self.total_duration_watched / 3600, 2)
        print(f"Total rows processed: {row_count}")
        print(f"Total duration watched in the last {days} days: {self.total_duration_watched:.2f} hours")
        
        return unique_file_names

    def calculate_duration_in_seconds(self, duration_str):
        """
        Convert a duration string (e.g., '00:10.8' or '00:00:10.8') to seconds.
        """
        if '.' in duration_str:
            duration_parts = duration_str.split('.')
            if ':' in duration_parts[0]:
                # Handles the case where format is HH:MM:SS.microseconds
                time_part = datetime.strptime(duration_parts[0], '%H:%M:%S')
            else:
                # Handles the case where format is MM:SS.microseconds
                time_part = datetime.strptime(duration_parts[0], '%M:%S')
            
            # Calculate the total time in seconds with microseconds converted to decimal seconds
            seconds = time_part.hour * 3600 + time_part.minute * 60 + time_part.second + float(f"0.{duration_parts[1]}")
        else:
            if ':' in duration_str:
                # Handles the case where format is HH:MM:SS
                time_part = datetime.strptime(duration_str, '%H:%M:%S')
            else:
                # Handles the case where format is MM:SS
                time_part = datetime.strptime(duration_str, '%M:%S')
            
            # Convert the total time to seconds
            seconds = time_part.hour * 3600 + time_part.minute * 60 + time_part.second
        
        return seconds
        

    def get_files_from_table(self):
        """
        Get file paths from the file_table.
        Returns a list of file paths.
        """
        file_paths = []
        for item in self.file_table.get_children():
            file_path = self.file_table.item(item, "values")[2]
            file_paths.append(file_path)
        return file_paths
    
    
    def display_caps(self):
        self.play_images = True
        self.image_files = VideoFileLoader.load_image_files()
        self.update_entry_text(SCREENSHOTS_FOLDER)
        self.insert_to_table(self.file_path_tuple(self.image_files))

        
def run_app():
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()

if __name__ == "__main__":
    # cProfile.run('run_app()')
    run_app()