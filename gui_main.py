import csv
import importlib
import os
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk

import file_loader
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
from file_loader import VideoFileLoader
from file_manager import FileManager
from get_aspects import VideoProcessor
from image_player import ImageViewer
from logs_writer import LogManager
from player_constants import (
    DELETE_FILES_CSV,
    FILES_FOLDER,
    FOLDER_LOGS,
    LOG_PATH,
    REPORTS_FOLDER,
    SCREENSHOTS_FOLDER,
    WATCHED_HISTORY_LOG_PATH,
)
from settings_manager import SettingsWindow
from static_methods import create_csv_file, ensure_folder_exists, gather_all_media, get_file_size, normalise_path
from videoplayer import MediaPlayerApp

import player_constants
# from pprint import pprint
# import cProfile

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
        self.video_files = []

        ensure_folder_exists(FILES_FOLDER)
        ensure_folder_exists(SCREENSHOTS_FOLDER)
        ensure_folder_exists(REPORTS_FOLDER)
        
        self.deletion_manager = DeletionManager()
        self.fav_manager = FavoritesManager()
        self.logger = LogManager(LOG_PATH)
        self.video_processor = VideoProcessor
        
        create_csv_file(["File Path", "Delete_Status", "File Size", "Modification Time"], DELETE_FILES_CSV)
        self.center_window(window=self.root)
        self._create_widgets()
        self._keybinding()
        self.create_context_menu()

    def center_window(self, width=900, height=600, window=None):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_coordinate = (screen_width - width) // 2
        y_coordinate = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")

    def _keybinding(self):
        self.entry.bind('<Return>', self.on_enter_pressed)
        self.search_entry.bind('<Return>', self.on_search_pressed)
        self.file_table.bind('<Double-1>', self.on_double_click)

        self.file_table.bind("<Button-3>", self.on_right_click)

        self.file_table.bind('<Return>', self.on_double_click)
        self.entry.bind("<Control-Return>", self.random_play)
        self.search_entry.bind("<Control-Return>", self.random_play)
    
        self.file_table.bind('<Delete>', lambda event: self.delete_selected_files(direct_delete=False, event=event))
        self.file_table.bind('<Control-m>', self.move_selected_files)
        self.file_table.bind('<Control-M>', self.move_selected_files)

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
        # fav_manager = FavoritesManager()
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if self.fav_manager.check_favorites(file_path):
                    self.fav_manager.delete_from_favorites(file_path)
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
        
        # fav_manager = FavoritesManager()
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if not self.fav_manager.check_favorites(file_path):
                    self.fav_manager.add_to_favorites(file_path)
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
        file_manager = FileManager()
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            try:
                if file_manager.move_file(file_path, dest_folder): 
                    self.file_table.delete(item)
                else:
                    messagebox.showerror("Move Failed", f"Failed to move file: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {e}")

        messagebox.showinfo("Move Complete", f"{len(selected_items)} file(s) moved successfully.")
        
    def treeview_sort_column(self, col, reverse):
        data = [(self.file_table.set(k, col), k) for k in self.file_table.get_children('')]
        try:
            data.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for index, (val, k) in enumerate(data):
            self.file_table.move(k, '', index)
        self.file_table.heading(col, command=lambda: self.treeview_sort_column(col, not reverse))


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
        
        # Using the DeletionManager to handle deletion or marking
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

    def on_delete_all_pressed(self, event=None):
        """Deletes files marked as 'ToDelete' using the DeletionManager."""
        entry_text = self.entry.get().strip().lower()
        if entry_text == "show deletes":
            self.deletion_manager.delete_files_in_csv()
        else:
            self.update_entry_text("show deletes")
            self.show_deletes()
            self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
            # messagebox.showinfo("Marked for Deletion", "Showing files marked for deletion. To delete all, type 'show deletes' and click 🗑 again.")

    def open_settings(self):
        def reload_constants():
            importlib.reload(player_constants)
            importlib.reload(file_loader)
            self.deletion_manager = DeletionManager()
            self.fav_manager = FavoritesManager()
            self.logger = LogManager(LOG_PATH)
        SettingsWindow(self.root, on_save_callback=reload_constants)

    @staticmethod
    def convert_bytes(bytes_size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0
        size = float(bytes_size)

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1

        return f"{size:.2f} {units[index]}"
    
    def _set_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Segoe UI", 16, "bold"), background="black", foreground="red")
        style.configure("Treeview", font=("Segoe UI", 11), rowheight=28, background="#222", fieldbackground="#222", foreground="white")
        style.map("Treeview", background=[("selected", "#8B0000")])
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=6, borderwidth=0)
        style.configure("TEntry", font=("Segoe UI", 11), padding=4)
        style.configure(
            "Modern.TCheckbutton",
            background="black",
            foreground="white",
            font=("Segoe UI", 13),
            focuscolor="",
            indicatorcolor="white",
            indicatordiameter=18,
            indicatormargin=[8, 4, 8, 4],
            padding=4,
        )
        style.map(
            "Modern.TCheckbutton",
            background=[("active", "#222"), ("selected", "#444")],
            foreground=[("active", "#4FC3F7"), ("selected", "#4FC3F7")],
        )


    def _create_widgets(self):
        """
        Create the main widgets for the GUI.
        """
        self._set_styles()
        
        self.heading_label = tk.Label(
            self.root, text="Media Analyser", bg="black", fg="red",
            font=("Segoe UI", 44, "bold"), pady=10
        )
        self.heading_label.pack(side="top", fill="x", pady=(10, 5))

        self.input_frame = tk.Frame(self.root, bg="black")
        self.input_frame.pack(side="top", fill="x", padx=20, pady=(10, 5))

        self.entry = tk.Entry(
            self.input_frame, bg="#181818", fg="white", width=50, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 13)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=5, ipady=4)

        self.enter_button = tk.Button(
            self.input_frame, text="Get", command=self.on_enter_pressed,
            bg="red", fg="white", font=("Segoe UI", 13, "bold"),
            width=10, bd=0, relief=tk.RAISED, activebackground="#b30000",
            cursor="hand2"
        )
        self.enter_button.pack(side="left", padx=(0, 0), pady=5)
        self.browse_button = tk.Button(
            self.input_frame, text="📁", command=self.browse_folder,
            bg="white", fg="black", font=("Segoe UI", 13, "bold"),
            width=3, bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.browse_button.pack(side="left", padx=(5, 0), pady=5)

        self.search_frame = tk.Frame(self.root, bg="black")
        self.search_frame.pack(side="top", fill="x", padx=20, pady=(0, 10))
        
        self.filter_favs = tk.Button(
            self.search_frame, text="★", command=self.check_update_favs,
            bg="green", fg="white", font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.filter_favs.pack(side="left", padx=(0, 5), pady=0)

        self.show_caps = tk.Button(
            self.search_frame, text="Snaps", command=self.display_caps,
            bg="green", fg="white", font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.show_caps.pack(side="left", padx=(0, 5), pady=0)

        self.show_verticals = tk.Button(
            self.search_frame, text="V", command=self.get_verticals,
            bg="black", fg="white", font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.show_verticals.pack(side="left", padx=(0,5), pady=0)

        self.show_horizontals = tk.Button(
            self.search_frame, text="L", command=self.get_horizontals,
            bg="black", fg="white", font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.show_horizontals.pack(side="left", padx=(0, 5), pady=0)
        
        self.search_entry = tk.Entry(
            self.search_frame, bg="#181818", fg="white", width=30, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0, ipady=2)

        self.search_button = tk.Button(
            self.search_frame, text="Search", command=self.on_search_pressed,
            bg="white", fg="black", font=("Segoe UI", 11, "bold"),
            width=10, bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.search_button.pack(side="left", padx=(0, 0), pady=0)

        # self.top_level_only_var = tk.BooleanVar(value=False)
        # self.top_level_only_check = ttk.Checkbutton(
        #     self.search_frame, text="🔼", variable=self.top_level_only_var,
        #     style="Modern.TCheckbutton",
        #     cursor="hand2",
        #     takefocus=0,
        # )
        # self.top_level_only_check.pack(side="left", padx=(5, 0), pady=5)

        self.top_level_only_on = False
        def toggle_top_level():
            self.top_level_only_on = not self.top_level_only_on
            if self.top_level_only_on:
                self.top_level_only_button.config(bg="#4FC3F7", fg="black", relief=tk.SUNKEN)
            else:
                self.top_level_only_button.config(bg="black", fg="white", relief=tk.RAISED)
        self.top_level_only_button = tk.Button(
            self.search_frame, text="🔼", command=toggle_top_level,
            bg="black", fg="white", font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.top_level_only_button.pack(side="left", padx=(5, 5), pady=5)

        self.delete_button = tk.Button(
            self.search_frame, text="🗑", command=self.on_delete_all_pressed,
            bg="red", fg="white", font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#b30000",
            anchor="center", cursor="hand2"
        )
        self.delete_button.pack(side="left", padx=(0,5), pady=5)

        self.refresh_button = tk.Button(
            self.search_frame, text="♻️", command=self.on_refresh_pressed,
            bg="red", fg="white", font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#b30000",
            cursor="hand2"
        )
        self.refresh_button.pack(side="left", padx=(0, 5), pady=5)
        
        self.all_media_button = tk.Button(
            self.search_frame, text="All Media", command=self.show_all_media,
            bg="blue", fg="white", font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#003366",
            cursor="hand2"
        )
        self.all_media_button.pack(side="left", padx=(0, 5), pady=0)

        self.stats_frame = tk.Frame(self.root, bg="#181818", bd=2, relief=tk.GROOVE)
        self.stats_frame.pack(side="top", fill="x", padx=20, pady=(0, 5), anchor="center")

        self.selected_files_label = tk.Label(
            self.stats_frame, text="Selected: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.selected_files_label.grid(row=0, column=0, padx=10, pady=0, sticky="ew")

        self.total_files_label = tk.Label(
            self.stats_frame, text="All Files: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.total_files_label.grid(row=0, column=1, padx=10, pady=0, sticky="ew")

        self.search_results_label = tk.Label(
            self.stats_frame, text="Search Results: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.search_results_label.grid(row=0, column=2, padx=10, pady=0, sticky="ew")

        self.total_size_label = tk.Label(
            self.stats_frame, text="Size: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.total_size_label.grid(row=0, column=3, padx=10, pady=0, sticky="ew")

        self.search_size_label = tk.Label(
            self.stats_frame, text="S-Size: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.search_size_label.grid(row=0, column=4, padx=10, pady=0, sticky="ew")

        self.total_duration_label = tk.Label(
            self.stats_frame, text="Durations: 0", bg="#181818", fg="white",
            font=("Segoe UI", 12, "bold")
        )
        self.total_duration_label.grid(row=0, column=5, padx=10, pady=0, sticky="ew")

        self._create_table()
        for i in range(6):
            self.stats_frame.grid_columnconfigure(i, weight=1)

        self.settings_button = tk.Button(
            self.root, text="⚙️", command=self.open_settings,
            bg="white", fg="gray", bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.settings_button.place(relx=1.0, x=-10, y=10, anchor="ne", width=40, height=30)

        # Currently not working
        self.stats_button = tk.Button(
            self.root, text="📊", command=self.open_media_stats,
            bg="white", fg="blue", bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.stats_button.place(relx=1.0, x=-60, y=10, anchor="ne", width=40, height=30)

        self.info_button = tk.Button(
            self.root, text="ℹ️", command=self.show_info,
            bg="white", fg="red", bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.info_button.place(relx=0.0, x=10, y=10, anchor="nw", width=40, height=30)

        # "Hovering Effects"
        def on_enter(e): e.widget.config(bg="#444")
        def on_leave(e):
            if e.widget == self.enter_button:
                e.widget.config(bg="red")
            elif e.widget == self.delete_button or e.widget["text"] == "🗑":
                e.widget.config(bg="red")
            elif e.widget == self.refresh_button or e.widget["text"] == "♻️":
                e.widget.config(bg="red")
            elif "★" in e.widget["text"] or "Snaps" in e.widget["text"]:
                e.widget.config(bg="green")
            elif "V" in e.widget["text"] or "L" in e.widget["text"]:
                e.widget.config(bg="black")
            elif e.widget == self.all_media_button:
                e.widget.config(bg="blue")
            else:
                e.widget.config(bg="white")

        for btn in [self.enter_button, self.delete_button, self.refresh_button,
                     self.filter_favs, self.show_caps, self.show_verticals, self.show_horizontals,
                     self.all_media_button]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def _create_table(self):
        table_frame = tk.Frame(self.root, bg="black")
        table_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

        self.file_table = ttk.Treeview(
            table_frame, columns=("#", "File Name", "Folder Path"), show="headings", selectmode="extended"
        )
        self.file_table.heading("#", text="#", command=lambda: self.treeview_sort_column("#", False))
        self.file_table.heading("File Name", text="File Name", command=lambda: self.treeview_sort_column("File Name", False))
        self.file_table.heading("Folder Path", text="Folder Path", command=lambda: self.treeview_sort_column("Folder Path", False))

        self.file_table.column("#", width=40, anchor="center", stretch=False)
        self.file_table.column("File Name", width=320, anchor="w")
        self.file_table.column("Folder Path", width=400, anchor="w")

        self.file_table.tag_configure("evenrow", background="#222", foreground="white")
        self.file_table.tag_configure("oddrow", background="#333", foreground="white")

        self.file_table.pack(side="left", fill="both", expand=True)

        self.file_table.bind("<<TreeviewSelect>>", self.update_selected_files_label)

        self.scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.file_table.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.file_table.configure(yscrollcommand=self.scrollbar.set)

    def update_selected_files_label(self, event=None):
        selected_count = len(self.file_table.selection())
        self.selected_files_label.config(text=f"Selected: {selected_count}")

    def show_info(self):
        if hasattr(self, "_info_window") and self._info_window.winfo_exists():
            self._info_window.lift()
            return

        self._info_window = tk.Toplevel(self.root)
        self._info_window.title("How to Use Random Media Player")
        self._info_window.configure(bg="#222")
        self._info_window.geometry("600x500")
        self._info_window.resizable(False, False)
        self._info_window.transient(self.root)
        self._info_window.grab_set()
        self.center_window(window=self._info_window, width=600, height=600)

        icon_label = tk.Label(self._info_window, text="ℹ️", font=("Segoe UI Emoji", 48), bg="#222", fg="red")
        icon_label.pack(pady=(18, 0))

        title_label = tk.Label(self._info_window, text="How to Use", font=("Segoe UI", 22, "bold"), bg="#222", fg="red")
        title_label.pack(pady=(0, 10))

        frame = tk.Frame(self._info_window, bg="#222")
        frame.pack(fill="both", expand=True, padx=18, pady=(0, 12))

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        info_text = tk.Text(
            frame, wrap="word", font=("Segoe UI", 12), bg="#181818", fg="#fff",
            bd=0, relief="flat", yscrollcommand=scrollbar.set, height=12
        )
        info_text.pack(fill="both", expand=True)
        scrollbar.config(command=info_text.yview)
        info_content = (
            "Welcome to Random Media Player!\n\n"
            "• Enter a folder path Or Browse it using '📁' and click 'Get' to list media files.\n"
            "• You can enter multiple folder paths separated by commas.\n"
            "• Use 'Search' to filter files by name.\n"
            "• Use '🔼' to search only in the top-level folder.\n"
            "• Use '★' and'Snaps' to view favorite files and screenshots taken respectively.\n"
            "• Double-click/Enter a file to play it.\n"
            "• Right-click a file for more options (move, delete).\n"
            "• Keyboard Shortcuts:\n"
            "    - Ctrl+F: Add to Favorites\n"
            "    - Ctrl+D: Remove from Favorites\n"
            "    - Ctrl+M: Move selected files\n"
            "    - Delete: Mark for deletion\n"
            "    - Ctrl+Shift+Delete: Remove from deletion list\n"
            "• You can use 'V' and 'L' buttons to filter for vertical and landscape videos.\n"
            "• Use the settings (⚙️) and stats (📊) buttons for more features.\n"
            "\nNote: to use V and L you'd have to download ffmpeg on your system.\n" \
            "Download FFmpeg from: https://ffmpeg.org/download.html\n" \
        )
        info_text.insert("1.0", info_content)
        info_text.config(state="disabled")
        close_btn = tk.Button(
            self._info_window, text="Close", command=self._info_window.destroy,
            font=("Segoe UI", 12, "bold"), bg="white", fg="#222", bd=0,
            relief="flat", activebackground="#0288D1", activeforeground="#fff",
            cursor="hand2"
        )
        close_btn.pack(pady=(0, 12))

    def browse_folder(self):
        folder_selected = filedialog.askdirectory(title="Select Folder")
        if folder_selected:
            current = self.entry.get().strip()
            if current:
                if not current.endswith(","):
                    current += ", "
                self.entry.delete(0, tk.END)
                self.entry.insert(0, f"{current}{folder_selected}")
            else:
                self.entry.delete(0, tk.END)
                self.entry.insert(0, folder_selected)

    def on_refresh_pressed(self):
        entry_text = self.entry.get().strip().lower()
        if entry_text == "show paths":
            # Refresh selected folders if any, else refresh all folders in the table
            if not hasattr(self, "folders") or not self.folders:
                self.show_paths()
            selected_items = self.file_table.selection()
            if selected_items:
                # Get selected folder paths from the table
                folder_paths = []
                for item in selected_items:
                    folder_path = self.file_table.item(item, "values")[1]
                    folder_paths.append(folder_path.strip())
                msg = f"Refreshed {len(folder_paths)} selected folder(s)."
            else:
                # Refresh all folders
                folder_paths = [folder.strip() for folder, csv in self.folders]
                msg = f"Refreshed {len(folder_paths)} folder(s)."
            vf_loader = VideoFileLoader()
            vf_loader.refresh_folders(folder_paths)
            self.show_paths()
            messagebox.showinfo("Refreshed", msg)
        else:
            self.refresh_deletions()
            messagebox.showinfo("Refreshed", "Deletions refreshed.")

    def show_all_media(self):
        """Gathers all media and displays File Name and Source Folder in the table."""
        csv_path = gather_all_media()
        if not csv_path:
            messagebox.showerror("Error", "Failed to gather all media.")
            return

        self.reset_search_option()

        file_list = set()
        total_size_bytes = 0
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    file_name = row.get("File Name", "")
                    source_folder = row.get("Source Folder", "")
                    file_path = os.path.join(source_folder, file_name)
                    if os.path.exists(file_path) and source_folder:
                        file_list.add(file_path)
                        size_str = row.get("File Size (Bytes)", "0")
                        try:
                            total_size_bytes += int(size_str)
                        except (ValueError, TypeError):
                            pass
            self.video_files = list(file_list)
            # print(f"Some Files {file_list[:3]}")
            self.insert_to_table(self.file_path_tuple(file_list))
            self.total_files = len(file_list)
            self.total_size = self.convert_bytes(total_size_bytes)
            self.update_stats()
            self.update_entry_text("All Media Files")
            messagebox.showinfo("All Media", f"Total media files found: {len(file_list)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load all media: {e}")

    def open_media_stats(self):
        """Open the media stats window."""
        print("Opens Media Analysis Window, Currently Not Working")
        messagebox.showinfo("Info", "Media Analysis Window is not working currently.")  
        # stats_window = tk.Toplevel(self.root)
        # app = media_stats_window.StatsWindow(stats_window, WATCHED_HISTORY_LOG_PATH)
        # root.mainloop()

    def update_entry_text(self, text):
        self.entry.delete(0, tk.END)  
        self.entry.insert(0, text)

    def update_stats(self):
            self.total_files_label.config(text=f"Total Files: {self.total_files}")
            self.total_size_label.config(text=f"Total Size: {self.total_size}")
            self.search_results_label.config(text=f"Search Results: {self.total_search_results}")
            self.total_duration_label.config(text=f"Durations: {self.total_duration_watched}")
            self.search_size_label.config(text=f"S-Size: {self.search_size}")

    def list_files(self, directory):
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
        self.reset_search_option()
        try:
            if folder_path_string == "play favs":
                favs = FavoritesManager()
                self.video_files = sorted(favs.get_favorites())
                self.total_files = len(self.video_files)
                self.total_size = self.convert_bytes(favs.total_size)
                self.update_stats()
            
            elif folder_path_string == "show paths":
                # self.reset_search_option(folder=True)
                # with open(FOLDER_LOGS, "r", encoding="utf-8") as file:
                #     reader = csv.DictReader(file)

                #     self.folders = list(set((normalise_path(row["Folder Path"]), normalise_path(row["Csv Path"])) for row in reader if os.path.isdir(row["Folder Path"])))
                # self.video_files = []
                self.show_paths()
            
            elif folder_path_string == "show deletes":
                # Show files marked as "ToDelete"
                self.show_deletes()
            
            elif folder_path_string == "show deleted":
                # Show files marked as "Deleted"
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

    def show_paths(self):
        """Show only those folder/csv pairs where both the folder and the CSV file exist."""
        self.reset_search_option(folder=True)
        valid_folders = []
        try:
            with open(FOLDER_LOGS, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    folder_path = normalise_path(row["Folder Path"])
                    csv_path = normalise_path(row["Csv Path"])
                    if os.path.isdir(folder_path) and os.path.isfile(csv_path):
                        valid_folders.append((folder_path, csv_path))
            self.folders = list(set(valid_folders))
            # self.video_files = []
            # self.insert_to_table(sorted(self.folders))
            self.update_entry_text("show paths")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load valid folder/csv pairs: {e}")

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
                        delete_files.append(row[0])
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
                        delete_files.append(row[0])
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
            top_level_only = getattr(self, "top_level_only_on", False)
            folder_input = normalise_path(self.entry.get()).rstrip("\\/")
            for file in search_files:
                if top_level_only:
                    if os.path.dirname(normalise_path(file)).rstrip("\\/") != folder_input:
                        continue
                if query in file.lower():
                    file_name = os.path.basename(file)
                    file_list.append((file_name, file))
            print(f"Total Files for {query}: {len(file_list)}")
            if query == '' and not top_level_only:
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

    def reset_search_option(self, folder=False, images=False):
        self.play_folder = folder
        self.play_images = images
                    


    def on_double_click(self, event=None):
        try:
            item = self.file_table.selection()[0]
            file_path = self.file_table.item(item, "values")[2]
            if self.play_folder:
                folder_path = self.file_table.item(item, "values")[1]
                vf_load = VideoFileLoader()
                self.video_files = vf_load.start_here(file_path)
                self.total_size = self.convert_bytes(vf_load.total_size_in_bytes)
                self.total_files = len(self.video_files)
                self.update_stats()
                print(f"Total Videos Found in {folder_path}: {len(self.video_files)}")
                self.update_entry_text(folder_path)
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
                self.reset_search_option()
            
            elif self.play_images:
                # Disable the main window
                # self.root.wm_attributes("-disabled", True)
                viewer_window = Toplevel(self.root)
                viewer_window.title("Image Viewer")
                image_viewer_width = 900
                image_viewer_height = 600
                image_files = self.get_files_from_table()
                # self.reset_search_option(images=True)

                # Create ImageViewer instance with the specified width and height
                ImageViewer(viewer_window, image_files, index=image_files.index(file_path), width=image_viewer_width, height=image_viewer_height)
                # self.reset_search_option()
                
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
        self.total_duration_watched = 0
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
                    
                    unique_file_names.add(row['File Name'])
                
                # Show Progrees every 1000 rows
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
                # case for format HH:MM:SS.microseconds
                time_part = datetime.strptime(duration_parts[0], '%H:%M:%S')
            else:
                # case for format MM:SS.microseconds
                time_part = datetime.strptime(duration_parts[0], '%M:%S')
            
            seconds = time_part.hour * 3600 + time_part.minute * 60 + time_part.second + float(f"0.{duration_parts[1]}")
        else:
            if ':' in duration_str:
                # case for format HH:MM:SS
                time_part = datetime.strptime(duration_str, '%H:%M:%S')
            else:
                # case for format MM:SS
                time_part = datetime.strptime(duration_str, '%M:%S')
            
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