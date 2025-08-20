import csv
import importlib
import os
from datetime import datetime, timedelta

import threading
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk

from custom_messagebox import askdirectory, askyesno, showerror, showinfo
import file_loader
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
from properties_window import PropertiesWindow
from stats_manager import VideoStatsManager
from file_loader import VideoFileLoader
from file_manager import FileManager
from get_aspects import VideoProcessor
from image_player import ImageViewer
from logs_writer import LogManager
from player_constants import (
    VIDEO_STATS_CSV,
    Colors,
    DELETE_FILES_CSV,
    FILES_FOLDER,
    FOLDER_LOGS,
    LOG_PATH,
    REPORTS_FOLDER,
    SCREENSHOTS_FOLDER,
    WATCHED_HISTORY_LOG_PATH,
    DEMO_WATCHED_HISTORY,
    VIDEO_SNIPPETS_FOLDER,
)
from settings_manager import SettingsWindow
from static_methods import (
    create_csv_file, 
    ensure_folder_exists, 
    gather_all_media,
    get_all_media_files, 
    get_file_size,
    get_file_transfer_history, 
    get_screenshots_for_file, 
    normalise_path, 
    get_split_stats_by_folder, 
    convert_bytes
)
from videoplayer import MediaPlayerApp

import player_constants
from media_dashboard import DashboardWindow
from category_manager import CategoryManager
from category_window import CategoryWindow
from notes_manager import NotesManager
from notes_window import NotesManagerGUI
from snippets_manager import SnippetsManager
from description_manager import DescriptionManager
from backup_manager import BackupManager
# from pprint import pprint
# import cProfile

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaPlayer")
        self.root.configure(bg="black")
        self.root.geometry("1000x600")
        self.image_viewer_width = 1000
        self.image_viewer_height = 600
        self.play_images = False
        self.play_folder = False
        self.play_category = False
        self.total_files = 0
        self.total_size = 0
        self.total_search_results = 0
        self.total_duration_watched = 0.0
        self.search_size = 0
        self.video_files = []
        self.trimmed_segments = {}

        ensure_folder_exists(FILES_FOLDER)
        ensure_folder_exists(SCREENSHOTS_FOLDER)
        ensure_folder_exists(REPORTS_FOLDER)
        ensure_folder_exists(VIDEO_SNIPPETS_FOLDER)
        self.center_window(window=self.root)

        create_csv_file(["File Path", "Delete_Status", "File Size", "Modification Time"], DELETE_FILES_CSV)
        self.root.after(0, self._show_loading_message)
        
        threading.Thread(target=self._init_managers_background, daemon=True).start()

    def _show_loading_message(self):
        self.loading_label = tk.Label(self.root, text="Loading managers...", bg="black", fg="white", font=("Segoe UI", 18))
        self.loading_label.pack(pady=40)

    def _init_managers_background(self):
        self.fav_manager = FavoritesManager()
        self.deletion_manager = DeletionManager(fav_manager=self.fav_manager)
        self.logger = LogManager(LOG_PATH)
        self.video_processor = VideoProcessor
        self.video_stats_manager = VideoStatsManager()
        self.category_manager = CategoryManager()
        self.snippets_manager = SnippetsManager()
        self.notes_manager = NotesManager()
        self.deletion_manager.set_parent_window(self.root)
        self.description_manager = DescriptionManager()
        self.backup_manager = BackupManager({})
        create_csv_file(["File Path", "Delete_Status", "File Size", "Modification Time"], DELETE_FILES_CSV)
        self.root.after(0, self._on_managers_ready)

    def _on_managers_ready(self):
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
        self._create_widgets()
        self._keybinding()
        self.create_context_menu()
        self.update_stats_async()
        # self._precompute_trimmed_segments(get_all_media_files())



    def center_window(self, width=1000, height=600, window=None):
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
        self.file_table.bind('<Shift-KeyPress-a>', self.add_to_category)
        self.file_table.bind('<Shift-KeyPress-A>', self.add_to_category)
        self.file_table.bind('<Shift-KeyPress-s>', self.show_screenshots_for_selected)
        self.file_table.bind('<Shift-KeyPress-S>', self.show_screenshots_for_selected)
        self.file_table.bind('<Shift-KeyPress-P>', self.show_properties)
        self.file_table.bind('<Shift-KeyPress-p>', self.show_properties)
        self.file_table.bind('<Shift-KeyPress-N>', self.open_notes_manager)
        self.file_table.bind('<Shift-KeyPress-n>', self.open_notes_manager)
        self.file_table.bind('<Shift-KeyPress-T>', self.show_video_snippets_for_selected)
        self.file_table.bind('<Shift-KeyPress-t>', self.show_video_snippets_for_selected)

    def _precompute_trimmed_segments(self, video_files):
        """
        Not in Use Currently
        Precompute trimmed segments for all files in the background.
        """
        def worker():
            for f in video_files:
                segments = []
                file_paths = set(
                    filter(
                        None,
                        [normalise_path(p) for p in get_file_transfer_history(f).values() if p is not None]
                    )
                )
                for fp in file_paths:
                    snippets = self.snippets_manager.get_snippets_by_original_file(fp)
                    for snippet in snippets:
                        try:
                            start = float(snippet["Start Time (s)"])
                            end = float(snippet["End Time (s)"])
                            segments.append((start, end))
                        except Exception:
                            continue
                self.trimmed_segments[f] = segments

            print("[INFO] Precomputation of trimmed segments completed.")

        threading.Thread(target=worker, daemon=True).start()


    def open_notes_manager(self, event=None):
        """Open the Notes Manager window for the selected file."""
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select a file to view/edit notes.")
            return
        item = selected_items[0]
        file_path = self.file_table.item(item, "values")[2]
        NotesManagerGUI(self.notes_manager, snippets_manager=self.snippets_manager, parent=self.root, file_path=file_path)


    def get_selected_video(self):
        selected_item = self.file_table.selection()
        if not selected_item:
            showinfo(self.root, "No Selection", "Please select files to mark for deletion.")
            return -1
        file_path = []
        for selection in selected_item:
            file_path.append(self.file_table.item(selection, "values")[2])
        return file_path
    
    def remove_from_favorites(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Select a File To Remove from Favs.")
            return
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if self.fav_manager.check_favorites(file_path):
                    self.fav_manager.delete_from_favorites(file_path)
                else:
                    showerror(self.root, "Removal Failed", f"Failed to remove file: {file_path} from Favorites.")
            except Exception as e:
                showerror(self.root, "Error", f"An error occurred in Favorites Removal: {e}")
                continue

        showinfo(self.root, "File Removed From Favorites", f"{len(selected_items)} unfavorited successfully.")

    def add_to_favorites(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Select a File To Add-To Favs.")
            return
        
        confirm = askyesno(self.root, "Confirm Deletion", f"Are you sure you want to add {len(selected_items)} file(s) to Favorites?")
        if not confirm:
            return
        
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2])
            try:
                if not self.fav_manager.check_favorites(file_path):
                    self.fav_manager.add_to_favorites(file_path)
                else:
                    showerror(self.root, "Addition Failed", f"Failed to Add file: {file_path} To Favorites.")
            except Exception as e:
                showerror(self.root, "Error", f"An error occurred while Adding {file_path} To Favorites: {e}")
                continue

        showinfo(self.root, "File(s) Added To Favorites", f"{len(selected_items)} file(s) Added-To Favorites successfully.")

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Segoe UI", 9), foreground=Colors.PLAIN_WHITE, background=Colors.BLACK_HOVER)
        self.context_menu.add_command(label="Refresh Stats      ", command=self.refresh_stats_for_selected)
        self.context_menu.add_command(label="Add to Category    ", command=self.add_to_category)
        self.context_menu.add_command(label="Add Note           ", command=self.open_notes_manager)
        self.context_menu.add_command(label="Move to Other Folder", command=self.move_selected_files)
        self.context_menu.add_command(label="Move to Recycle Bin", command=self.delete_selected_files)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Show Screenshots   ", command=self.show_screenshots_for_selected)
        self.context_menu.add_command(label="Properties         ", command=self.show_properties)

    def show_properties(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select a file to view properties.")
            return
        item = selected_items[0]
        file_path = self.file_table.item(item, "values")[2]
        
        def open_properties():
            PropertiesWindow(
                self.root, 
                file_path, 
                category_manager=self.category_manager,
                notes_manager=self.notes_manager,
                description_manager=self.description_manager,
                trimmed_segments=self.trimmed_segments)

        self.root.after(0, open_properties)
    
    def refresh_stats_for_selected(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select a file to refresh stats.")
            return
        refreshed = 0
        errors = []
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            if not os.path.exists(file_path):
                errors.append(f"File not found: {file_path}")
                continue
            try:
                # file_size = os.path.getsize(file_path)
                result = self.video_stats_manager.refresh_stats(file_path)
                if result:
                    refreshed += 1
                else:
                    errors.append(f"Stats not found or failed for: {file_path}")
            except Exception as e:
                errors.append(f"Error refreshing {file_path}: {e}")
        msg = f"Stats refreshed for {refreshed} file(s)."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors)
        showinfo(self.root, "Refresh Stats", msg)

    def show_screenshots_for_selected(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select file(s) to view screenshots.")
            return

        shown_any = False
        max_files = 250
        screenshots = []
        for idx, item in enumerate(selected_items[:max_files]):
            file_path = self.file_table.item(item, "values")[2]
            filename = os.path.basename(file_path)
            screenshots += get_screenshots_for_file(filename)
        
        if screenshots:
            viewer_window = tk.Toplevel(self.root)
            viewer_window.title(f"Screenshots for {filename}")
            ImageViewer(viewer_window, screenshots, index=0, width=self.image_viewer_width, height=self.image_viewer_height)
            viewer_window.focus_force()
            shown_any = True
        else:
            showinfo(self.root, "No Screenshots", f"No screenshots found for: {filename}")

        if not shown_any:
            showinfo(self.root, "No Screenshots", "No screenshots found for any of the selected files.")

    def show_video_snippets_for_selected(self, event=None):
        import random
        from static_methods import get_all_related_paths, get_video_snippets_for_file

        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select file(s) to view video snippets.")
            return

        all_snippets = []
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            related_paths = get_all_related_paths(file_path)
            for related in related_paths:
                # filename = os.path.basename(related)
                snippets = get_video_snippets_for_file(related)
                all_snippets.extend(snippets)

        if all_snippets:
            random_index = random.randint(0, len(all_snippets) - 1)
            app = MediaPlayerApp(
                all_snippets,
                current_file=all_snippets[random_index],
                random_select=True,
                parent=self.root,
                category_manager=self.category_manager,
                favorites_manager=self.fav_manager,
                notes_manager=self.notes_manager,
                snippets_manager=self.snippets_manager,
                trimmed_segments=self.trimmed_segments
            )
            app.update_video_progress()
        else:
            showinfo(self.root, "No Snippets", "No video snippets found for the selected files.")

    def move_selected_files(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select files to move.")
            return

        dest_folder = askdirectory(self.root, title="Select Destination Folder")
        if not dest_folder:
            return
        
        src_files = [self.file_table.item(item, "values")[2] for item in selected_items]
        file_manager = FileManager(parent_window=self.root, favorites_manager=self.fav_manager, deletion_manager=self.deletion_manager,
                                    video_stats_manager=self.video_stats_manager, category_manager=self.category_manager, notes_manager=self.notes_manager)

        file_manager.move_files(src_files, dest_folder)

        moved_count = 0
        failed_count = 0

        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            if not os.path.isfile(file_path):
                self.file_table.delete(item)
                moved_count += 1
            else:
                failed_count += 1

        showinfo(self.root,
            "Move Complete",
            f"{moved_count} file(s) moved successfully.\n{failed_count} file(s) failed to move."
        )
        
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
            showinfo(self.root, "No Selection", "Please select files to mark for deletion.")
            return
        if direct_delete:
            status = "Deleted"

        confirm_message = "mark" if not direct_delete else "delete"
        confirm = askyesno(self.root, "Confirm Deletion", f"Are you sure you want to {confirm_message} {len(selected_items)} file(s)?")
        if not confirm:
            return

        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            self.deletion_manager.mark_for_deletion(file_path, status)
        
        # Not currently deleting files directly
        if direct_delete:
            self.deletion_manager.delete_files_in_csv(skip_confirmation=True)
        
        showinfo(self.root, "Deletion Marked", f"{len(selected_items)} file(s) marked for deletion.")

    def remove_from_deletion(self, file, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select files to move.")
            return
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            try:
                self.deletion_manager.remove_from_deletion(file_path)      
            except Exception as e:
                showerror(self.root, "Error", f"An error occurred: {e}")
        showinfo(self.root, "Removed Marked", f"{len(selected_items)} file(s) removed from deletion list.")

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
            self.deletion_manager.set_parent_window(self.root)
            self.fav_manager = FavoritesManager()
            self.logger = LogManager(LOG_PATH)
        SettingsWindow(self.root, backup_manager=self.backup_manager, on_save_callback=reload_constants)

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
            "NewStyle.TCheckbutton",
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
            "NewStyle.TCheckbutton",
            background=[("active", "#222"), ("selected", "#444")],
            foreground=[("active", "#4FC3F7"), ("selected", "#4FC3F7")],
        )


    def _create_widgets(self):
        """
        Create the main widgets for the GUI.
        """
        self._set_styles()
        
        self.heading_label = tk.Label(
            self.root, text="Media Analyser", bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_RED,
            font=("Segoe UI", 44, "bold"), pady=10
        )
        self.heading_label.pack(side="top", fill="x", pady=(10, 5))

        self.input_frame = tk.Frame(self.root, bg=Colors.PLAIN_BLACK)
        self.input_frame.pack(side="top", fill="x", padx=20, pady=(10, 5))

        self.entry = tk.Entry(
            self.input_frame, bg="#181818", fg=Colors.PLAIN_WHITE, width=50, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 13)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=5, ipady=4)

        self.enter_button = tk.Button(
            self.input_frame, text="Get", command=self.on_enter_pressed,
            bg=Colors.PLAIN_RED, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 13, "bold"),
            width=10, bd=0, relief=tk.RAISED, activebackground="#b30000",
            cursor="hand2"
        )
        self.enter_button.pack(side="left", padx=(0, 0), pady=5)
        self.browse_button = tk.Button(
            self.input_frame, text="📁", command=self.browse_folder,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_BLACK, font=("Segoe UI", 13, "bold"),
            width=3, bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.browse_button.pack(side="left", padx=(5, 0), pady=5)

        self.search_frame = tk.Frame(self.root, bg="black")
        self.search_frame.pack(side="top", fill="x", padx=20, pady=(0, 10))
        
        self.filter_favs = tk.Button(
            self.search_frame, text="★", command=self.check_update_favs,
            bg=Colors.PLAIN_GREEN, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.filter_favs.pack(side="left", padx=(0, 5), pady=0)

        self.show_caps = tk.Button(
            self.search_frame, text="Snaps", command=self.display_caps,
            bg=Colors.PLAIN_GREEN, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            width=8, bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.show_caps.pack(side="left", padx=(0, 5), pady=0)

        self.show_verticals = tk.Button(
            self.search_frame, text="V", command=self.get_verticals,
            bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.show_verticals.pack(side="left", padx=(0,5), pady=0, ipadx=3)

        self.show_horizontals = tk.Button(
            self.search_frame, text="L", command=self.get_horizontals,
            bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.show_horizontals.pack(side="left", padx=(0, 5), pady=0, ipadx=3)

        self.allow_deleted_on = False
        def toggle_allow_deleted():
            self.allow_deleted_on = not self.allow_deleted_on
            if self.allow_deleted_on:
                self.allow_deleted_button.config(fg=Colors.PLAIN_RED, relief=tk.SUNKEN)
            else:
                self.allow_deleted_button.config(bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, relief=tk.RAISED)
        self.allow_deleted_button = tk.Button(
            self.search_frame, text="🚫", command=toggle_allow_deleted,
            bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.allow_deleted_button.pack(side="left", padx=(0, 5), pady=5)
        
        self.search_entry = tk.Entry(
            self.search_frame, bg="#181818", fg=Colors.PLAIN_WHITE, width=30, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=0, ipady=2)

        self.top_level_only_on = False
        def toggle_top_level():
            self.top_level_only_on = not self.top_level_only_on
            if self.top_level_only_on:
                self.top_level_only_button.config(fg=Colors.INFO_BLUE, relief=tk.SUNKEN)
            else:
                self.top_level_only_button.config(bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, relief=tk.RAISED)
        self.top_level_only_button = tk.Button(
            self.search_frame, text="🔼", command=toggle_top_level,
            bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.top_level_only_button.pack(side="left", padx=(0, 5), pady=5)

        self.search_button = tk.Button(
            self.search_frame, text="Search", command=self.on_search_pressed,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_BLACK, font=("Segoe UI", 11, "bold"),
            width=10, bd=0, relief=tk.RAISED, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.search_button.pack(side="left", padx=(0, 5), pady=0)

        self.delete_button = tk.Button(
            self.search_frame, text="🗑", command=self.on_delete_all_pressed,
            bg=Colors.PLAIN_RED, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#b30000",
            anchor="center", cursor="hand2"
        )
        self.delete_button.pack(side="left", padx=(0,5), pady=5)

        self.refresh_button = tk.Button(
            self.search_frame, text="♻️", command=self.on_refresh_pressed,
            bg=Colors.PLAIN_RED, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#b30000",
            cursor="hand2"
        )
        self.refresh_button.pack(side="left", padx=(0, 5), pady=5)
        
        self.all_media_button = tk.Button(
            self.search_frame, text="All Media", command=lambda: self.root.after(50, self.show_all_media),
            bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#003366",
            cursor="hand2"
        )
        self.all_media_button.pack(side="left", padx=(0, 5), pady=0)

        self.categories_button = tk.Button(
            self.search_frame, text="☰", command=self.show_categories,
            bg=Colors.PLAIN_PURPLE, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 11, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#4B0082",
            cursor="hand2"
        )
        self.categories_button.pack(side="left", padx=(0, 5), pady=0)

        self.settings_button = tk.Button(
            self.root, text="⚙️", command=self.open_settings,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_GRAY, bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.settings_button.place(relx=1.0, x=-10, y=10, anchor="ne", width=40, height=30)

        self.stats_button = tk.Button(
            self.root, text="📊", command=self.open_media_stats,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_BLUE, bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.stats_button.place(relx=1.0, x=-60, y=10, anchor="ne", width=40, height=30)

        self.folder_stats_button = tk.Button(
            self.root, text="▦", command=self.show_folder_stats,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_BLUE, bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.folder_stats_button.place(relx=1.0, x=-10, y=50, anchor="ne", width=40, height=30)

        self.info_button = tk.Button(
            self.root, text="ℹ️", command=self.show_info,
            bg=Colors.PLAIN_WHITE, fg=Colors.PLAIN_RED, bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground="#e0e0e0",
            cursor="hand2"
        )
        self.info_button.place(relx=0.0, x=10, y=10, anchor="nw", width=40, height=30)

        # "Hovering Effects"
        def on_enter(e): e.widget.config(bg="#444")
        def on_leave(e):
            if e.widget == self.enter_button:
                e.widget.config(bg=Colors.PLAIN_RED)
            elif e.widget == self.delete_button or e.widget["text"] == "🗑":
                e.widget.config(bg=Colors.PLAIN_RED)
            elif e.widget == self.refresh_button or e.widget["text"] == "♻️":
                e.widget.config(bg=Colors.PLAIN_RED)
            elif "★" in e.widget["text"] or "Snaps" in e.widget["text"]:
                e.widget.config(bg=Colors.PLAIN_GREEN)
            elif "V" in e.widget["text"] or "L" in e.widget["text"] or e.widget in [self.all_media_button]:
                e.widget.config(bg=Colors.PLAIN_BLACK)
            elif e.widget == self.categories_button:
                e.widget.config(bg=Colors.PLAIN_PURPLE)
            else:
                e.widget.config(bg=Colors.PLAIN_WHITE)

        for btn in [self.enter_button, self.delete_button, self.refresh_button,
                     self.filter_favs, self.show_caps, self.show_verticals, self.show_horizontals,
                     self.all_media_button, self.categories_button]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        self._create_stats_frame()

    def _create_stats_frame(self):
        self.stats_frame = tk.Frame(self.root, bg=Colors.BLACK_ENTRYBOX, bd=2, relief=tk.GROOVE)
        self.stats_frame.pack(side="top", fill="x", padx=20, pady=(0, 5), anchor="center")

        self.selected_files_label = tk.Label(
            self.stats_frame, text="Selected: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.selected_files_label.grid(row=0, column=0, padx=10, pady=0, sticky="ew")

        self.total_files_label = tk.Label(
            self.stats_frame, text="All Files: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.total_files_label.grid(row=0, column=1, padx=10, pady=0, sticky="ew")

        self.search_results_label = tk.Label(
            self.stats_frame, text="Search Results: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.search_results_label.grid(row=0, column=2, padx=10, pady=0, sticky="ew")

        self.total_size_label = tk.Label(
            self.stats_frame, text="Size: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.total_size_label.grid(row=0, column=3, padx=10, pady=0, sticky="ew")

        self.search_size_label = tk.Label(
            self.stats_frame, text="S-Size: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.search_size_label.grid(row=0, column=4, padx=10, pady=0, sticky="ew")

        self.total_duration_label = tk.Label(
            self.stats_frame, text="Durations: 0", bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold")
        )
        self.total_duration_label.grid(row=0, column=5, padx=10, pady=0, sticky="ew")

        self._create_table()
        for i in range(6):
            self.stats_frame.grid_columnconfigure(i, weight=1)

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

    def show_folder_stats(self, event=None):
        file_paths = self.get_files_from_table()
        self._show_split_stats_by_folder(file_paths)

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
            "    - Ctrl+F/f: Add to Favorites\n"
            "    - Ctrl+D/d: Remove from Favorites\n"
            "    - Ctrl+M/m: Move selected files\n"
            "    - Delete: Mark for deletion\n"
            "    - Ctrl+Shift+Delete: Remove from deletion list\n" \
            "    - Shift+A/a: Add to Category\n" \
            "    - Shift+N/n: Add Note\n"
            "• You can use 'V' and 'L' buttons to filter for vertical and landscape videos.\n"
            "• Use the settings (⚙️) and stats (📊) buttons for more features.\n" \
            "• For more keyboard shortcuts and details of this app you can visit the following\n"
            "https://github.com/Demaurr/random-media-player/blob/master/Documentations/documentation.md\n"
            "\nNote: to use V, L or trimming functionality you'd have to download ffmpeg on your system.\n" \
            "Download FFmpeg from: https://ffmpeg.org/download.html\n" \
        )
        info_text.insert("1.0", info_content)
        info_text.config(state=tk.DISABLED)
        close_btn = tk.Button(
            self._info_window, text="Close", command=self._info_window.destroy,
            font=("Segoe UI", 12, "bold"), bg=Colors.PLAIN_WHITE, fg="#222", bd=0,
            relief="flat", activebackground="#0288D1", activeforeground="#fff",
            cursor="hand2"
        )
        close_btn.pack(pady=(0, 12))

    def _show_split_stats_by_folder(self, file_paths):
        """
        Display a modern, centered window with split stats by folder for the given file paths.
        """

        stats = get_split_stats_by_folder(file_paths)
        win = tk.Toplevel(self.root)
        win.title("Folder Split Stats")
        win.configure(bg="#181818")
        self.center_window(width=700, height=500, window=win)

        heading = tk.Label(win, text="Stats by Folder", font=("Segoe UI", 23, "bold"), bg=Colors.BLACK_ENTRYBOX, fg=Colors.INFO_BLUE, pady=10)
        heading.pack(side="top", fill="x")

        style = ttk.Style(win)
        style.theme_use("clam")
        style.configure("Treeview", font=("Segoe UI", 11), rowheight=28, background="#222", fieldbackground="#222", foreground="white")
        style.map("Treeview", background=[("selected", "#8B0000")])

        columns = ("Folder", "File Count", "Total Size")
        tree = ttk.Treeview(win, columns=columns, show="headings", selectmode="browse", height=15)
        tree.heading("Folder", text="Folder")
        tree.heading("File Count", text="File Count")
        tree.heading("Total Size", text="Total Size")
        tree.column("Folder", width=350, anchor="w")
        tree.column("File Count", width=100, anchor="center")
        tree.column("Total Size", width=150, anchor="center")

        for folder, stat in sorted(stats.items()):
            tree.insert("", "end", values=(folder, stat["file_count"], convert_bytes(stat["total_size"])))

        tree.pack(fill="both", expand=True, padx=20, pady=10)
        close_btn = tk.Button(win, text="Close", command=win.destroy, font=("Segoe UI", 11, "bold"), bg="#4FC3F7", fg="#181818", relief=tk.FLAT, padx=16, pady=4, cursor="hand2")
        close_btn.pack(pady=(0, 16))

        def sortby(col, descending):
            data = [(tree.set(child, col), child) for child in tree.get_children("")]
            if col == "File Count":
                data.sort(key=lambda t: int(t[0]), reverse=descending)
            elif col == "Total Size":
                def parse_size(s):
                    num, unit = s.split()
                    num = float(num)
                    factor = {"B":1, "KB":1024, "MB":1024**2, "GB":1024**3, "TB":1024**4}.get(unit, 1)
                    return num * factor
                data.sort(key=lambda t: parse_size(t[0]), reverse=descending)
            else:
                data.sort(key=lambda t: t[0].lower(), reverse=descending)
            for idx, (val, k) in enumerate(data):
                tree.move(k, '', idx)
            tree.heading(col, command=lambda: sortby(col, not descending))
        for col in columns:
            tree.heading(col, command=lambda c=col: sortby(c, False))

        win.grab_set()
        win.focus_force()

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
            showinfo(self.root, "Refreshed", msg)
        else:
            self.refresh_deletions()
            showinfo(self.root, "Refreshed", "Deletions refreshed.")

    def show_all_media(self):
        """Gathers all media and displays File Name and Source Folder in the table."""
        def worker():
            csv_path = gather_all_media()
            if not csv_path:
                self.root.after(0, lambda: showerror(self.root, "Error", "Failed to gather all media."))
                return

            file_list = set()
            total_size_bytes = 0
            try:
                with open(csv_path, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        file_name = row.get("File Name", "")
                        source_folder = row.get("Source Folder", "")
                        file_path = os.path.join(source_folder, file_name)
                        if self.allow_deleted_on or (os.path.exists(file_path) and source_folder):
                            file_list.add(file_path)
                            size_str = row.get("File Size (Bytes)", "0")
                            try:
                                total_size_bytes += int(size_str)
                            except (ValueError, TypeError):
                                pass

                self.root.after(100, lambda: self._on_all_media_loaded(file_list, total_size_bytes))
            except Exception as e:
                self.root.after(100, lambda: showerror(self.root, "Error", f"Failed to load all media: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_all_media_loaded(self, file_list, total_size_bytes):
        self.reset_search_option()
        self.video_files = list(file_list)
        self.root.after(self.insert_to_table(self.file_path_tuple(file_list)))
        self.total_files = len(file_list)
        self.total_size = self.convert_bytes(total_size_bytes)
        self.update_stats()
        self.update_entry_text("All Media Files")
        showinfo(self.root, "All Media", f"Total media files found: {len(file_list)}")

    def open_media_stats(self):
        """Open the media stats window."""
        try:
            # print("Opens Media Analysis Window, Currently Not Working")
            # messagebox.showinfo("Info", "Media Analysis Window is not working currently.")  
            stats_window = tk.Toplevel(self.root)
            stats_window.lift()
            stats_window.focus_force()
            app = DashboardWindow(
                stats_window, 
                WATCHED_HISTORY_LOG_PATH, 
                category_manager=self.category_manager)
            # app = DashboardWindow(stats_window, DEMO_WATCHED_HISTORY)
            self._set_styles()
        except Exception as e:
            showerror(self.root, "Error", f"Failed to open media stats: {e}")
            stats_window.destroy()
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

    def insert_to_table(self, files: list|tuple):
        """
        Inserts files into the file table with alternate row colors.
        Args:
            files (list|tuple): List of tuples containing file name and file path.
        """
        self.file_table.delete(*self.file_table.get_children())
        for idx, (file, file_path) in enumerate(files):
            tags = ("evenrow",) if idx % 2 == 0 else ("oddrow",)  # Apply alternate colors to rows
            self.file_table.insert("", tk.END, values=(idx, file, file_path), tags=tags)

    def filter_existing_files(self, file_list, callback):
        """Filter files that exist and call the callback with the result."""
        def worker():
            if self.allow_deleted_on:
                existing = file_list
            else:
                existing = [f for f in file_list if os.path.exists(f)]
            self.root.after(0, lambda: callback(existing))
        threading.Thread(target=worker, daemon=True).start()

    def on_enter_pressed(self, event=None):
        folder_path_string = self.entry.get()
        vf_loader = VideoFileLoader()
        self.reset_search_option()
        try:
            if folder_path_string == "play favs":
                favs = self.fav_manager
                all_favs = favs.get_favorites()
                def after_filter(existing_files):
                    self.video_files = sorted(existing_files)
                    self.total_files = len(self.video_files)
                    self.total_size = self.convert_bytes(favs.total_size)
                    self.update_stats()
                    self.insert_to_table(self.file_path_tuple(self.video_files))
                self.filter_existing_files(all_favs, after_filter)
                return
            
            elif folder_path_string == "show paths":
                self.show_paths()
            
            elif folder_path_string == "show deletes":
                self.show_deletes()
            
            elif folder_path_string == "show deleted":
                self.show_deletes(deleted=True)

            elif folder_path_string == "show history":
                self.video_files = self.get_history_files()
                self.total_files = len(self.video_files)
                self.update_stats()
                self.total_duration_watched = 0

            elif folder_path_string == "show categories":
                self.show_categories()

            else:
                self.video_files = vf_loader.start_here(normalise_path(folder_path_string))
                self.total_size = self.convert_bytes(vf_loader.total_size_in_bytes)
                self.total_files = len(self.video_files)
                self.update_stats()
                self.update_stats_async()
        
        except ImportError as e:
            print(f"An Import Error Occurred: {e}")
            self.video_files = vf_loader.get_videos_from_paths(folder_paths=folder_path_string.split(","))
        
        except Exception as e:
            print(f"An Unknown Error Occurred {e}")
            return
        
        if not self.play_folder and not self.play_category:
            print(f"Total Videos Found: {len(self.video_files)}")
            self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
        elif self.play_folder:
            print(f"Total Folders in Search History: {len(self.folders)}")
            self.insert_to_table(sorted(self.folders))
        elif self.play_category:
            print(f"Total Categories: {self.total_files}")
            # self.insert_to_table_custom(self.categories)

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
            showerror(self.root, "Error", f"Failed to load valid folder/csv pairs: {e}")

    def refresh_deletions(self):
        self.deletion_manager.check_deleted()
        self.update_entry_text("show deletes")
        self.show_deletes(deleted=False)
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
            showinfo(self.root, "No Files", "No files marked for deletion.")
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
            showinfo(self.root, "No Files", "No files marked for deletion.")
        self.total_size = self.convert_bytes(self.total_size)
        return delete_files

    def on_search_pressed(self, event=None):
        query = self.search_entry.get().lower()
        self.file_table.delete(*self.file_table.get_children())
        file_list = []
        matched = False
        try:
            search_files = self.image_files if self.play_images else self.video_files
            top_level_only = getattr(self, "top_level_only_on", False)
            if top_level_only:
                    matched_desc_keys = self.description_manager.search_description_by_keys(query, search_files)
                    matched_note_keys = self.notes_manager.search_notes_by_keys(query=query, allowed_keys=search_files)
                    matched_cat_keys = self.category_manager.search_categories_by_keys(query=query, allowed_keys=search_files)
            # folder_input = normalise_path(self.entry.get()).rstrip("\\/")
            for file in search_files:
                file_name_lower = file.lower()
                matched = False
                if query in file_name_lower:
                    matched = True
                
                elif top_level_only and file in matched_desc_keys:
                    matched = True

                elif top_level_only and file in matched_note_keys:
                    matched = True

                elif top_level_only and file in matched_cat_keys:
                    matched = True

                if matched:
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
            # self.update_stats_async()
        except AttributeError as e:
            print("No videos found to search from.")
            print(f"An Exception is raised {e}")
            showerror(self.root, "Attribute Error", f"Error in Search Pressed: {e}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            showerror(self.root, "Error", f"Exception in Search Pressed: {e}")

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

    def reset_search_option(self, folder=False, images=False, category=False):
        self.play_folder = folder
        self.play_images = images
        self.play_category = category
                    


    def on_double_click(self, event=None):
        try:
            item = self.file_table.selection()[0]
            file_path = self.file_table.item(item, "values")[2]
            
            if self.play_folder:
                selected_items = self.file_table.selection()
                folder_paths = [self.file_table.item(i, "values")[1] for i in selected_items]
                merged_paths = ",".join(folder_paths)

                vf_load = VideoFileLoader()
                self.video_files = vf_load.start_here(merged_paths)

                self.total_size = self.convert_bytes(vf_load.total_size_in_bytes)
                self.total_files = len(self.video_files)
                self.update_stats()

                print(f"Total Videos Found in {merged_paths}: {len(self.video_files)}")
                self.update_entry_text(merged_paths)
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
                self.reset_search_option()
                self.update_stats_async()

            
            elif self.play_category:
                category_name = self.file_table.item(item, "values")[2]
                files = self.category_manager.get_category_files(category_name)
                # The following can be used inorder to rid of file_size again and again
                if self.allow_deleted_on:
                    existing_files = self.category_manager.get_category_files(category_name)
                    total_size = sum(get_file_size(f) if os.path.exists(f) else 0 for f in existing_files)
                else:
                    existing_files = [f for f in files if os.path.exists(f)]
                    total_size = sum(get_file_size(f) for f in existing_files)

                
                self.video_files = existing_files
                self.total_files = len(existing_files)
                self.total_size = self.convert_bytes(total_size)
                self.total_search_results = len(existing_files)
                self.update_stats()
                
                print(f"Total Videos Found in category '{category_name}': {len(existing_files)}")
                self.update_entry_text(f"Category: {category_name}")
                self.insert_to_table(sorted(self.file_path_tuple(existing_files)))
                self.reset_search_option()
            
            elif self.play_images:
                viewer_window = Toplevel(self.root)
                viewer_window.title("Image Viewer")
                image_files = self.get_files_from_table()
                viewer_window.lift()
                viewer_window.focus_force()

                ImageViewer(viewer_window, image_files, index=image_files.index(file_path), width=self.image_viewer_width, height=self.image_viewer_height)

            else:
                if len(self.file_table.selection()) > 1:
                    selected_items = self.file_table.selection()
                    self.files = [self.file_table.item(i, "values")[2] for i in selected_items]
                else:
                    self.files = sorted(self.get_files_from_table())
                if not os.path.exists(file_path):
                        showerror(self.root, "File Not Found", f"The file '{file_path}' does not exist.")
                        return False
                print(f"Total Videos Found: {len(self.files)}")
                if self.files:
                    self.play_images = False
                    app = MediaPlayerApp(
                        self.files, 
                        current_file=file_path, 
                        random_select=True, 
                        parent=self.root,
                        category_manager=self.category_manager,
                        favorites_manager=self.fav_manager,
                        notes_manager=self.notes_manager,
                        snippets_manager=self.snippets_manager,
                        trimmed_segments=self.trimmed_segments
                    )
                    app.update_video_progress()
                    print(len(self.trimmed_segments))
                    # app.lift()
                    # app.focus_force()
                    # app.mainloop()
                else:
                    print("No video files found in the specified folder path(s).")
        
        except IndexError as e:
            showerror(self.root, "Error", f"{e}")

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
            showinfo(self.root, "Total Files Found", f"Total Vertical Videos Found: {self.total_search_results}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            showerror(self.root, "Error", f"Exception in Getting Vertical Pressed: {e}")

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
            showinfo(self.root, "Total Files Found", f"Total Vertical Videos Found: {self.total_search_results}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            showerror(self.root, "Error", f"Exception in Getting Vertical Pressed: {e}")


    def update_stats_async(self):
        threading.Thread(target=self.video_stats_manager.create_stats, daemon=True).start()

    def random_play(self, event=None):
        self.on_enter_pressed()
        self.files = sorted(self.get_files_from_table())
        if self.files:
            # self.root.wm_attributes("-disabled", True)
            app = MediaPlayerApp(self.files, 
                                 random_select=True,
                                 category_manager=self.category_manager,
                                 favorites_manager=self.fav_manager,
                                 notes_manager=self.notes_manager,
                                 snippets_manager=self.snippets_manager,
                                 parent=self.root,
                                 trimmed_segments=self.trimmed_segments)
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

    def add_to_category(self, event=None):
        """Open category manager for selected files."""
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select files to add to a category.")
            return
        selected_files = []
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            selected_files.append(file_path)

        category_window = CategoryWindow(self.root, selected_files)
        category_window.lift()
        category_window.focus_force()
        self.root.wait_window(category_window)
        self.category_manager._load_entries()

    def show_categories(self):
        """Show all categories and their file counts in the table."""
        self.reset_search_option(category=True)
        self.play_category = True
        self.category_manager._load_entries()
        categories = self.category_manager.get_all_categories()
        self.file_table.delete(*self.file_table.get_children())
        
        category_files = []
        total_size = 0
        total_files = 0
        for category in sorted(categories):
            # files = self.category_manager.get_category_files(category)
            # # size = sum(get_file_size(f) for f in files if os.path.exists(f))
            # # size = sum(get_file_size(f) for f in files)
            # size = sum(self.video_stats_manager.stats.get(f, 0) for f in files) # This doesn't work as the key in video_stats is (file_path, file_size)
            # total_size += size
            # total_files += len(files)
            # category_files.append((f"Contains {len(files)} Files", category))  # Using category as path for double-click handling
            files = self.category_manager.get_category_files(category)
            if not self.allow_deleted_on:
                files = [f for f in files if os.path.exists(f)]
            # size = sum(get_file_size(f) for f in files)
            # total_size += size
            total_files += len(files)
            category_files.append((f"Contains {len(files)} Files", category))

        self.total_files = len(categories)
        self.total_size = self.convert_bytes(total_size)
        self.total_search_results = total_files
        self.update_stats()

        self.insert_to_table(category_files)
        self.update_entry_text("show categories")

    def insert_to_table_custom(self, files: list|tuple):
        for file in files:
            self.file_table.insert("", "end", values=(file[0], file[1], file[2]))

def run_app():
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()

if __name__ == "__main__":
    # cProfile.run('run_app()')
    run_app()
    # import cProfile
    # cProfile.run('run_app()', 'gui_profile.prof')