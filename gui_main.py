import os
import csv
import tkinter as tk
from tkinter import Toplevel, ttk
from tkinter import messagebox
from send2trash import send2trash
from logs_writer import LogManager
from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
from image_player import ImageViewer
from player_constants import FAV_PATH, FOLDER_LOGS, LOG_PATH, SCREENSHOTS_FOLDER, DELETE_FILES_CSV
from static_methods import create_csv_file, mark_for_deletion, remove_from_deletion

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
        self.logger = LogManager(LOG_PATH)
        create_csv_file(["File Path", "Delete_Status"], DELETE_FILES_CSV)
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
        
        # Bind Delete key to delete_selected_files with direct_delete=False
        self.file_table.bind('<Delete>', lambda event: self.delete_selected_files(direct_delete=False, event=event))
        
        # Bind Shift+Delete to delete_selected_files with direct_delete=True
        self.file_table.bind('<Shift-Delete>', lambda event: self.delete_selected_files(direct_delete=True, event=event))
        self.file_table.bind('<Control-Shift-Delete>', lambda event: remove_from_deletion(self.get_selected_video(), event))

    def get_selected_video(self):
        selected_item = self.file_table.selection()
        if not selected_item:
            messagebox.showinfo("No Selection", "Please select files to mark for deletion.")
            return -1
        elif len(selected_item) > 1:
            messagebox.showerror("Multiple Selected", "Select Only One File")
            return -1
        
        file_path = self.file_table.item(selected_item, "values")[2]
        return file_path
        


    def delete_selected_files(self, direct_delete=False, event=None):
        """Marks selected files from the file table for deletion."""
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
            if direct_delete:
                file_path = VideoFileLoader.normalise_path(file_path)
                send2trash(file_path)
                self.file_table.delete(item)
            mark_for_deletion(file_path, status)
            if direct_delete:
                self.logger.update_logs("[FILE DELETED]", file_path)
            else:
                self.logger.update_logs("[MARKED FOR DELETION]", file_path)

        messagebox.showinfo("Deletion Marked", f"{len(selected_items)} file(s) marked for deletion.")

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
        self.search_button = tk.Button(self.search_frame, text="Search", command=self.on_search_pressed, bg="gray", fg="black", font=("Arial", 12, "bold"),
                                       width=10, bd=0.5, relief=tk.RAISED)
        self.search_button.pack(side="left", padx=(0, 5), pady=0)

        self.show_caps = tk.Button(self.search_frame, text="CapShots", command=self.display_caps, bg="green", fg="black", font=("Arial", 12, "bold"),width=10, bd=0.5, relief=tk.RAISED)
        self.show_caps.pack(side="left", padx=(0, 5), pady=0)

        self.delete_button = tk.Button(self.search_frame, text="Delete Marked", command=self.delete_files_in_csv, bg="red", fg="black", font=("Arial", 12, "bold"))
        self.delete_button.pack(pady=10)

        self.stats_frame = tk.Frame(self.root, bg="black")
        self.stats_frame.pack(side="top", pady=0)

        self.total_files_label = tk.Label(self.stats_frame, text="Total Files: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.total_files_label.pack(side="left", padx=(10, 10))

        self.search_results_label = tk.Label(self.stats_frame, text="Search Results: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.search_results_label.pack(side="left", padx=(0, 10))

        self.total_size_label = tk.Label(self.stats_frame, text="Total Size: 0", bg="black", fg="white", font=("Arial", 12, "bold"))
        self.total_size_label.pack(side="left", padx=(0, 10))

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
                self.total_size = 0
                self.update_stats()
            
            elif folder_path_string == "show paths":
                self.play_folder = True
                with open(FOLDER_LOGS, "r", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    self.folders = list(set((row["Folder Path"], row["Csv Path"]) for row in reader))
                self.video_files = []
            
            elif folder_path_string == "show deletes":
                # Show files marked as "ToDelete"
                self.show_deletes()

            else:
                self.video_files = vf_loader.start_here(folder_path_string)
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

    def get_files_marked_for_deletion(self):
        """Retrieves files marked as 'ToDelete' from the DELETE_FILES_CSV."""
        delete_files = []
        try:
            with open(DELETE_FILES_CSV, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[1] == "ToDelete":
                        delete_files.append(row[0])  # Append the file path
        except FileNotFoundError:
            messagebox.showinfo("No Files", "No files marked for deletion.")
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

    def _on_close_player(self, player_window): # Not Working as Expecteed
        """Callback to re-enable the main window after the player window is closed."""
        player_window.destroy()  # Destroy the player window
        self.root.wm_attributes("-disabled", False)  # Re-enable the main window

    def _on_close_viewer(self, viewer_window): # Not Working as Expecteed
        """Callback to re-enable the main window after the image viewer window is closed."""
        viewer_window.destroy()  # Destroy the viewer window
        self.root.wm_attributes("-disabled", False)  # Re-enable the main window

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

    def show_deletes(self):
        self.video_files = self.get_files_marked_for_deletion()
        self.total_files = len(self.video_files)
        self.total_size = 0  # You can calculate the size if needed
        self.update_stats()

    def delete_files_in_csv(self):
        """Deletes files marked 'ToDelete' in the CSV and updates the status to 'Deleted'."""
        # Ask for confirmation
        confirm_delete = messagebox.askyesno("Confirm Deletion", 
                                            "Are you sure you want to delete all marked files?")
        
        if not confirm_delete:
            # If the user selects 'No', they can choose to view the files marked for deletion
            show_deletes = messagebox.askyesno("View Deletes", 
                                            "Do you want to view the files marked for deletion instead?")
            if show_deletes:
                self.show_deletes()  # Assumes you have a method to show the 'ToDelete' files
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
            return

        rows = []
        
        # Open and read the CSV file
        try:
            with open(DELETE_FILES_CSV, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                rows = list(reader)  # Read all rows into a list
        except FileNotFoundError:
            messagebox.showwarning("File Not Found", "The deletion list CSV file was not found.")
            return

        # Iterate over the rows and check the "Delete_Status"
        for row in rows:
            file_path = row["File Path"]
            status = row["Delete_Status"]
            
            if status == "ToDelete":
                try:
                    send2trash(file_path)  # Move the file to the recycle bin
                    row["Delete_Status"] = "Deleted"  # Update status to 'Deleted'
                    print(f"{file_path} has been deleted.")
                    self.logger.update_logs('[FILE DELETED]', file_path)
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
                    self.logger.error_logs(f'Error Deleting This File: {e}')

        # Write the updated rows back to the CSV
        with open(DELETE_FILES_CSV, mode='w', newline='', encoding='utf-8') as file:
            fieldnames = ["File Path", "Delete_Status"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # Write the header
            writer.writeheader()
            
            # Write all the updated rows
            writer.writerows(rows)

        messagebox.showinfo("Deletion Complete", "All 'ToDelete' files have been deleted and moved to the recycle bin.")

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

        
if __name__ == "__main__":
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()