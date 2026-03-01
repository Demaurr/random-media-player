from concurrent.futures import ThreadPoolExecutor
import csv
import gc
import importlib
import os
from datetime import datetime, timedelta

from pprint import pprint
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox, ttk
import tracemalloc

import psutil

from annotations_manager import AnnotationsManager
from associations_window import FileAssociationWindow
from custom_messagebox import askdirectory, askyesno, showerror, showinfo
import file_loader
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
from media_paths_collector import MediaPathsCollector
from properties_window import PropertiesWindow
from stats_manager import VideoStatsManager
from file_loader import VideoFileLoader
from file_manager import FileManager
from image_player import ImageViewer
from logs_writer import LogManager
from tooltips import ToolTip
from player_constants import (
    SHOW_SNIPPETS,
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
    FILE_TRANSFER_LOG,
    ASSOCIATIONS_CSV
)
from settings_manager import SettingsWindow
from static_methods import (
    batch_convert_to_mp4,
    build_screenshot_index,
    build_transfer_graph,
    center_window,
    convert_png_to_jpg,
    create_csv_file, 
    ensure_folder_exists, 
    gather_all_media,
    get_all_media_files,
    get_all_related_paths,
    get_all_related_paths_multiple, 
    get_file_size,
    get_file_transfer_history, 
    get_screenshots_for_file,
    get_screenshots_for_file_from_index,
    get_video_snippets_for_file,
    natural_sort_iterables,
    natural_sort_key, 
    normalise_path, 
    get_split_stats_by_folder, 
    convert_bytes,
    get_memory_usage,
    remove_media_entries
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
from task_manager import TaskManager
from fingerprint_manager import MediaFingerprintManager
from associations_manager import FileAssociator

LOCKFILE = os.path.join(tempfile.gettempdir(), "my_tk_app.lock")

# from pprint import pprint
# import cProfile

class FileExplorerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MediaPlayer")
        self.root.configure(bg=Colors.PLAIN_BLACK)
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
        self.image_files = []
        self.categories = []
        self.category_names = []
        self.trimmed_segments = {}
        self.trimmed_segments_metadata = {}

        ensure_folder_exists(FILES_FOLDER)
        ensure_folder_exists(SCREENSHOTS_FOLDER)
        ensure_folder_exists(REPORTS_FOLDER)
        ensure_folder_exists(VIDEO_SNIPPETS_FOLDER)
        self.center_window(window=self.root)

        create_csv_file(["File Path", "Delete_Status", "File Size", "Modification Time"], DELETE_FILES_CSV)
        create_csv_file(["Folder Path","Csv Path", "Date"], FOLDER_LOGS)
        create_csv_file(["Source Path","Destination Path","Status","Date"], FILE_TRANSFER_LOG)
        self.root.after(0, self._show_loading_message)
        self.task_manager = TaskManager(self.root)
        self.logger = LogManager(LOG_PATH)
        self.task_manager.add_task(self._init_managers_background, threaded=True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # threading.Thread(target=self._init_managers_background, daemon=True).start()

    def _show_loading_message(self):
        self.loading_label = tk.Label(self.root, text="Loading managers...", bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, font=("Segoe UI", 18))
        self.loading_label.pack(pady=40)

    def _init_managers_background(self):
        self.fingerprint_manager = MediaFingerprintManager()
        self.backup_manager = BackupManager({})
        self.fav_manager = FavoritesManager(fingerprint_manager=self.fingerprint_manager)
        self.annotations_manager = AnnotationsManager(fingerprint_manager=self.fingerprint_manager)
        self.notes_manager = NotesManager(fingerprint_manager=self.fingerprint_manager)
        self.category_manager = CategoryManager(fingerprint_manager=self.fingerprint_manager)
        self.deletion_manager = DeletionManager(fav_manager=self.fav_manager, gui_parent=self.root)
        # self.video_processor = VideoProcessor
        self.snippets_manager = SnippetsManager(deletion_manager=self.deletion_manager, fingerprint_manager=self.fingerprint_manager)
        self.video_stats_manager = VideoStatsManager(snippets_manager=self.snippets_manager, deletion_manager=self.deletion_manager)
        self.deletion_manager.set_parent_window(self.root)
        self.associations_manager = FileAssociator(csv_path=ASSOCIATIONS_CSV, deletion_manager=self.deletion_manager, fingerprint_manager=self.fingerprint_manager)
        self.description_manager = DescriptionManager(association_manager=self.associations_manager, deletion_manager=self.deletion_manager)
        # self.media_collector = MediaPathsCollector(deletion_manager=self.deletion_manager, fingerprint_manager=self.fingerprint_manager)
        self.root.after(0, self._on_managers_ready)

    def _on_managers_ready(self):
        if hasattr(self, 'loading_label'):
            self.loading_label.destroy()
        self._create_widgets()
        self._keybinding()
        self.create_context_menu()
        self.update_stats_async()
        # self._precompute_trimmed_segments(get_all_media_files())

    def _create_fingerprints_background(self):
        """Create fingerprints for media files in the background."""
        try:
            collector = MediaPathsCollector(deletion_manager=self.deletion_manager, 
                                            fingerprint_manager=self.fingerprint_manager)
            collector.collect_all(all=False, video_stats=True)
            collector.create_fingerprints_parallel(workers=4)
        except Exception as e:
            print(f"Error creating fingerprints: {e}")

    def _load_video_files(self, folder_path_string, vf_loader):
        """Handles the heavy video loading process with a loading screen."""

        loading_win = self.show_loading_screen("Loading files...")

        def worker():
            try:
                video_files = vf_loader.start_here(normalise_path(folder_path_string, use_os_norm=False))
                total_size = self.convert_bytes(vf_loader.total_size_in_bytes)
                total_files = len(video_files)

                def on_finish():
                    self.video_files = video_files
                    self.total_size = total_size
                    self.total_files = total_files
                    self.update_stats()
                    if vf_loader.updated and folder_path_string != "":
                        self.update_stats_async()
                        vf_loader.updated = False
                    loading_win.destroy()
                    self.finish_loading_ui()

                self.root.after(0, on_finish)

            except Exception as e:
                self.root.after(0, lambda: loading_win.destroy())
                print(f"Error while loading: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def center_window(self, width=1000, height=600, window=None):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x_coordinate = (screen_width - width) // 2
        y_coordinate = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")

    def open_associations_window(self, event=None):
        """Open the associations manager for the selected file."""
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select a file to manage associations.")
            return
            
        file_path = self.file_table.item(selected_items[0], "values")[2]
        # if not os.path.exists(file_path):
        #     showerror(self.root, "File Not Found", f"The file {file_path} does not exist.")
        #     return
            
        window = tk.Toplevel(self.root)
        FileAssociationWindow(window, source_file=file_path, associator=self.associations_manager, fingerprint_manager=self.fingerprint_manager)
        window.focus_force()

    def on_close(self):
        """Handle window close event, prevent closing if tasks are running."""
        if self.task_manager.is_busy():
            showinfo(self.root, "Busy", "Background tasks are still running. Please wait for them to finish before closing.")
            return
        cleanup_lockfile()
        self.root.destroy()

    def _keybinding(self):
        self.entry.bind('<Return>', self.on_enter_pressed)
        self.search_entry.bind('<Return>', self.on_search_pressed)
        self.file_table.bind('<Double-1>', self.on_double_click)

        self.file_table.bind("<Button-3>", self.on_right_click)

        self.file_table.bind('<Return>', self.on_double_click)
        # self.entry.bind("<Control-Return>", self.random_play)
        # self.search_entry.bind("<Control-Return>", self.random_play)
    
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
        self.file_table.bind('<Shift-KeyPress-R>', self.open_associations_window) 
        self.file_table.bind('<Shift-KeyPress-r>', self.open_associations_window)

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
        
        confirm = askyesno(self.root, "Confirm Favorite", f"Are you sure you want to add {len(selected_items)} file(s) to Favorites?")
        if not confirm:
            return
        
        for item in selected_items:
            file_path = normalise_path(self.file_table.item(item, "values")[2]) if self.entry.get().strip() != "show categories" else self.file_table.item(item, "values")[1]
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
        self.context_menu = tk.Menu(
            self.root,
            tearoff=0,
            font=("Segoe UI", 9),
            foreground=Colors.PLAIN_WHITE,
            background=Colors.BLACK_HOVER
        )

        self.context_menu.add_command(label="Add to Category    ", command=self.add_to_category, accelerator="Shift+A")
        self.context_menu.add_command(label="Add Note           ", command=self.open_notes_manager, accelerator="Shift+N")
        self.context_menu.add_command(label="Add Association    ", command=self.open_associations_window, accelerator="Shift+R")
        self.context_menu.add_command(label="Remove from All Media", command=self.remove_selected_from_all_media)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh Stats      ", command=self.refresh_stats_for_selected)
        self.context_menu.add_command(label="Move to Other Folder", command=self.move_selected_files, accelerator="Ctrl+M")
        self.context_menu.add_command(label="Move to Recycle Bin", command=self.delete_selected_files, accelerator="Del")
        self.context_menu.add_command(label="Show Screenshots   ", command=self.show_screenshots_for_selected, accelerator="Shift+S")
        self.context_menu.add_command(label="Show Video Snippets   ", command=self.show_video_snippets_for_selected, accelerator="Shift+T")
        duplicates_menu = tk.Menu(
            self.context_menu,
            tearoff=0,
            font=("Segoe UI", 9),
            foreground=Colors.PLAIN_WHITE,
            background=Colors.BLACK_HOVER
        )
        duplicates_menu.add_command(
            label="By Hash   ", 
            command=lambda: self.show_duplicates_for_selected(mode="hash")
        )
        duplicates_menu.add_command(
            label="By Duration", 
            command=lambda: self.show_duplicates_for_selected(mode="duration")
        )
        duplicates_menu.add_command(
            label="By Size   ", 
            command=lambda: self.show_duplicates_for_selected(mode="size")
        )
        self.context_menu.add_cascade(label="Show Duplicates    ", menu=duplicates_menu)
        
        self.context_menu.add_separator()

        convert_menu = tk.Menu(
            self.context_menu,
            tearoff=0,
            font=("Segoe UI", 9),
            foreground=Colors.PLAIN_WHITE,
            background=Colors.BLACK_HOVER
        )

        convert_menu.add_command(label="Convert PNG to JPG", command=self.convert_selected_to_jpg)
        convert_menu.add_command(label="Convert GIF to MP4", command=self.convert_selected_gifs_to_mp4)

        self.context_menu.add_cascade(label="Convert", menu=convert_menu)

        favorites_menu = tk.Menu(
            self.context_menu,
            tearoff=0,
            font=("Segoe UI", 9),
            foreground=Colors.PLAIN_WHITE,
            background=Colors.BLACK_HOVER
        )
        favorites_menu.add_command(label="Add to Favorites  ", command=self.add_to_favorites, accelerator="Ctrl+F")
        favorites_menu.add_command(label="Remove from Favorites", command=self.remove_from_favorites, accelerator="Ctrl+D")

        self.context_menu.add_cascade(label="Favorites", menu=favorites_menu)

        

        self.context_menu.add_command(label="Properties         ", command=self.show_properties, accelerator="Shift+P")

    def convert_selected_to_jpg(self):
        """Convert selected PNG files to JPG using statics.convert_png_to_jpg."""
        try:

            selected_items = self.file_table.selection()

            if not selected_items:
                showinfo(self.root, "Convert to JPG", "No files selected.")
                return
            
            selected_files = [self.file_table.item(item, "values")[2] for item in selected_items]

            res = convert_png_to_jpg(selected_files, delete_original=False)

            msg = (
                f"{len(res['converted'])} newly converted\n"
                f"{len(res['skipped'])} already existed\n"
                f"{len(res['failed'])} failed\n"
                f"Saved in '{res['output_dir']}'"
            )

            showinfo(self.root, "Conversion Complete", msg)

        except Exception as e:
            showerror(self.root, "Conversion Failed", f"Error while converting:\n{e}")

    def convert_selected_gifs_to_mp4(self):
        """Convert selected GIF files to MP4 using batch_convert_to_mp4."""
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "Convert to MP4", "No files selected.")
            return

        gif_files = [
            self.file_table.item(item, "values")[2]
            for item in selected_items
            if self.file_table.item(item, "values")[2].lower().endswith(".gif")
        ]

        if not gif_files:
            showinfo(self.root, "Convert to MP4", "No GIF files selected.")
            return

        if len(gif_files) > 5:
            showerror(self.root, "Too Many Files", "Please select 5 or fewer GIF files for conversion.")
            return

        converted, failed = [], []

        def on_file_done(file, result):
            if isinstance(result, str) and os.path.exists(result):
                converted.append(file)
            else:
                failed.append(file)

        def on_all_done():
            msg = f"Conversion complete:\n{len(converted)} files converted"
            if converted:
                msg += "\n\nConverted:\n" + "\n".join(os.path.basename(f) for f in converted)
            if failed:
                msg += f"\n\n{len(failed)} files failed:\n" + "\n".join(os.path.basename(f) for f in failed)
            showinfo(self.root, "Conversion Complete", msg)

        batch_convert_to_mp4(
            self.task_manager,
            gif_files,
            overwrite=False,
            on_file_done=on_file_done,
            on_all_done=on_all_done,
            same_folder=True,  
        )


    def show_properties(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select a file to view properties.")
            return
        
        is_category_view = self.entry.get().strip().lower() == "show categories"
        is_multiple_selection = len(selected_items) > 1
        
        if is_multiple_selection or is_category_view:
            return self._show_grouped_properties(selected_items, is_category_view)
        
        item = selected_items[0]
        file_path = self.file_table.item(item, "values")[2]

        loading_win = self.show_loading_screen(message="Loading properties...")

        def worker():
            try:
                props_window = PropertiesWindow(
                    self.root,
                    file_path,
                    category_manager=self.category_manager,
                    notes_manager=self.notes_manager,
                    description_manager=self.description_manager,
                    deletion_manager=self.deletion_manager,
                    stats_manager=self.video_stats_manager,
                    trimmed_segments=self.trimmed_segments,
                    snippets_manager=self.snippets_manager,
                    association_manager=self.associations_manager,
                    fingerprint_manager=self.fingerprint_manager,
                    favorites_manager=self.fav_manager,
                    annotations_manager=self.annotations_manager
                )
                
                success = props_window.preload_properties()
                
                if success:
                    self.root.after(0, lambda: (
                        loading_win.destroy(),
                        props_window.show_properties()
                    ))
                else:
                    self.root.after(0, lambda: (
                        loading_win.destroy(),
                        showerror(self.root, "Error", "Failed to load properties")
                    ))
                    
            except Exception as e:
                self.root.after(0, lambda: (
                    loading_win.destroy(),
                    showerror(self.root, "Error", f"Failed to show properties: {e}")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def remove_selected_from_all_media(self):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select at least one file to remove.")
            return

        file_paths = []
        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            file_paths.append(file_path)

        confirm = messagebox.askyesno("Confirm Removal", 
            f"Are you sure you want to remove {len(file_paths)} file(s) from All Media?")
        if not confirm:
            return

        loading_win = self.show_loading_screen(message="Removing from All Media...")

        def worker():
            success = remove_media_entries(file_paths)
            self.root.after(0, loading_win.destroy)

            if success:
                for item in selected_items:
                    self.file_table.delete(item)
                self.root.after(0, lambda: showinfo(self.root, "Success", f"Removed {len(file_paths)} file(s) from All Media."))
            else:
                self.root.after(0, lambda: showerror(self.root, "Error", "Failed to remove selected files."))
            self.root.after(0, loading_win.destroy())

        threading.Thread(target=worker, daemon=True).start()


    def show_loading_screen(self, message="Loading...", width=300, height=100):
        loading_win = tk.Toplevel(self.root)
        # loading_win.title("Loading...")
        # loading_win.overrideredirect(True)
        # loading_win.attributes("-topmost", True)
        loading_win.geometry(f"{width}x{height}")
        loading_win.configure(bg=Colors.PLAIN_BLACK)
        loading_win.transient(self.root)
        loading_win.grab_set()
        loading_win.lift()

        label = tk.Label(
            loading_win, text=message, fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK,
            font=("Segoe UI", 12)
        )
        label.pack(pady=20)
        self.center_window(window=loading_win, width=width, height=height)

        progress = ttk.Progressbar(
            loading_win, mode="indeterminate", style="Thick.Horizontal.TProgressbar"
        )
        progress.pack(fill="x", padx=20, pady=10)
        progress.start(10)

        return loading_win
    
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
        
        loading_win = self.show_loading_screen("Loading screenshots...")
        
        def worker():
            screenshots_index = build_screenshot_index()
            # max_files = 250
            screenshots = []
            filename = None
            
            if self.entry.get().strip().lower() == "show categories":
                category_names = [self.file_table.item(item, "values")[1] for item in selected_items]
                all_files = self._get_category_files(category_names)
                for file_path in all_files:
                    filename = os.path.basename(file_path)
                    screenshots += get_screenshots_for_file_from_index(filename, screenshots_index)
            else:
                for idx, item in enumerate(selected_items):
                    file_path = self.file_table.item(item, "values")[2]
                    filename = os.path.basename(file_path)
                    screenshots += get_screenshots_for_file_from_index(filename, screenshots_index)
            
            self.root.after(0, self._on_screenshots_loaded, loading_win, screenshots, filename)
        
        threading.Thread(target=worker, daemon=True).start()
    
    def _on_screenshots_loaded(self, loading_win, screenshots, filename):
        if loading_win.winfo_exists():
            loading_win.destroy()
        
        if screenshots:
            viewer_window = tk.Toplevel(self.root)
            viewer_window.title(f"Screenshots for {filename}")
            ImageViewer(
                viewer_window, 
                screenshots, 
                index=0, 
                width=self.image_viewer_width, 
                height=self.image_viewer_height,
                deletion_manager=self.deletion_manager
            )
            viewer_window.focus_force()
        else:
            showinfo(self.root, "No Screenshots", f"No screenshots found for: {filename}")

        if not screenshots:
            showinfo(self.root, "No Screenshots", "No screenshots found for any of the selected files.")

    def get_video_snippets_for_selected(self, files=None, all_files=True, check_deleted=False, on_complete=None, msg="Fetching video snippets..."):
        """Fetch video snippets for selected files with a loading screen, then run on_complete(snippets)."""
        if not files:
            selected_items = self.file_table.selection()
            if not selected_items:
                showinfo(self.root, "No Selection", "Please select file(s) to view video snippets.")
                return
        else:
            selected_items = files if all_files else files[:1]

        loading = self.show_loading_screen(msg)
        
        if self.entry.get().strip().lower() == "show categories":
            category_names = [self.file_table.item(item, "values")[1] for item in selected_items]
            file_paths = self._get_category_files(category_names)
        else:
            file_paths = [self.file_table.item(item, "values")[2] if not files else item for item in selected_items]
        
        transfer_graph = build_transfer_graph()
        all_related_paths = get_all_related_paths_multiple(file_paths, transfer_graph)
        all_snippets = [
            file_path
            for file_path in all_related_paths
            if check_deleted and os.path.exists(file_path)
        ]
        snippet_set = set(all_snippets)

        all_related_paths = [
            path for path in all_related_paths
            if path not in snippet_set
        ]

        def worker():
            try:
                snippets = list(all_snippets)

                snippets.extend(
                    self.get_snippets(all_related_paths, related_paths=False, graph=transfer_graph)
                )

                snippets = natural_sort_iterables(snippets)

                self.root.after(100, lambda: (
                    loading.destroy(),
                    on_complete and on_complete(snippets)
                ))

            except Exception as e:
                err_msg = str(e)
                self.root.after(100, lambda: (
                    loading.destroy(),
                    showerror(self.root, "Error", f"Failed to fetch snippets: {err_msg}")
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _show_grouped_properties(self, selected_items, is_category_view):
        """Show grouped properties for multiple files or category view."""
        from grouped_properties import GroupedPropertiesWindow
        
        loading_win = self.show_loading_screen(message="Loading grouped properties...")
        
        def worker():
            try:
                if is_category_view:
                    category_names = [self.file_table.item(item, "values")[1] for item in selected_items]
                    file_paths = self._get_category_files(category_names)
                    category_name = ", ".join(category_names) if len(category_names) <= 3 else f"{len(category_names)} Categories"
                else:
                    file_paths = [self.file_table.item(item, "values")[2] for item in selected_items]
                    category_name = None
                
                grouped_window = GroupedPropertiesWindow(
                    self.root,
                    file_paths=file_paths,
                    category_name=category_name,
                    category_manager=self.category_manager,
                    favorites_manager=self.fav_manager,
                    notes_manager=self.notes_manager,
                    description_manager=self.description_manager,
                    deletion_manager=self.deletion_manager,
                    stats_manager=self.video_stats_manager,
                    snippets_manager=self.snippets_manager,
                    association_manager=self.associations_manager,
                    fingerprint_manager=self.fingerprint_manager,
                    annotations_manager=self.annotations_manager,
                    trimmed_segments=self.trimmed_segments
                )
                
                if grouped_window.preload_properties():
                    self.root.after(0, lambda: (
                        loading_win.destroy(),
                        grouped_window.show_properties()
                    ))
                else:
                    self.root.after(0, lambda: (
                        loading_win.destroy(),
                        showerror(self.root, "Error", "Failed to load grouped properties data.")
                    ))
                
            except Exception as e:
                self.root.after(0, lambda: (
                    loading_win.destroy(),
                    showerror(self.root, "Error", f"Failed to show grouped properties: {e}")
                ))

        threading.Thread(target=worker, daemon=True).start()


    def show_video_snippets_for_selected(self, event=None):
        import random

        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select file(s) to view video snippets.")
            return

        def after_snippets(all_snippets):
            if all_snippets:
                random_index = random.randint(0, len(all_snippets) - 1)
                file_path = all_snippets[random_index]
                self.play_media(all_snippets, file_path)
            else:
                showinfo(self.root, "No Snippets", "No video snippets found for the selected files.")

        self.get_video_snippets_for_selected(on_complete=after_snippets)

    def move_selected_files(self, event=None):
        selected_items = self.file_table.selection()
        if not selected_items:
            showinfo(self.root, "No Selection", "Please select files to move.")
            return

        dest_folder = askdirectory(self.root, title="Select Destination Folder")
        if not dest_folder:
            return
        
        src_files = [self.file_table.item(item, "values")[2] for item in selected_items]
        file_manager = FileManager(
            parent_window=self.root, 
            favorites_manager=self.fav_manager, 
            deletion_manager=self.deletion_manager,
            video_stats_manager=self.video_stats_manager, 
            category_manager=self.category_manager, 
            notes_manager=self.notes_manager,
            description_manager=self.description_manager,
            fingerprint_manager=self.fingerprint_manager,
            task_manager=self.task_manager,)

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
        self.deletion_manager.set_parent_window(self.root)
        # self.update_stats_async()

    def treeview_sort_column(self, col, reverse):
        data = [(self.file_table.set(k, col), k) for k in self.file_table.get_children('')]
        
        data.sort(key=lambda t: natural_sort_key(t[0]), reverse=reverse)

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

        skip_confirm = True if self.entry.get() == "show deletes" else False

        for item in selected_items:
            file_path = self.file_table.item(item, "values")[2]
            self.deletion_manager.mark_for_deletion(file_path, status, skip_confirm, commit=False)

        self.deletion_manager.commit_changes()
        
        # Not currently deleting files directl
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
    
    def check_gc_collection(self):
        gc.collect()
        print([obj for obj in gc.get_objects() if isinstance(obj, tk.Toplevel)])
        # for obj in gc.get_objects():
        #     if isinstance(obj, MediaPlayerApp):
        #         print(f"\nLeaked MediaPlayerApp: {obj}")
        #         for ref in gc.get_referrers(obj):
        #             print("↳", type(ref), getattr(ref, "__name__", ""), getattr(ref, "__class__", ""), ref)

    def open_settings(self):
        def reload_constants():
            importlib.reload(player_constants)
            importlib.reload(file_loader)
            self.deletion_manager = DeletionManager()
            self.deletion_manager.set_parent_window(self.root)
            self.fav_manager = FavoritesManager(self.fingerprint_manager)
            self.logger = LogManager(LOG_PATH)
        SettingsWindow(self.root, 
                       backup_manager=self.backup_manager, 
                       task_manager=self.task_manager, 
                       on_save_callback=reload_constants)

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
        style.configure("Treeview.Heading", font=("Segoe UI", 16, "bold"), background=Colors.PLAIN_BLACK, foreground=Colors.PLAIN_RED)
        style.configure("Treeview", font=("Segoe UI", 11), rowheight=28, background="#222", fieldbackground="#222", foreground=Colors.PLAIN_WHITE)
        style.map("Treeview", background=[("selected", "#8B0000")])
        style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=6, borderwidth=0)
        style.configure("TEntry", font=("Segoe UI", 11), padding=4)
        style.configure(
            "NewStyle.TCheckbutton",
            background=Colors.PLAIN_BLACK,
            foreground=Colors.PLAIN_WHITE,
            font=("Segoe UI", 13),
            focuscolor="",
            indicatorcolor=Colors.PLAIN_WHITE,
            indicatordiameter=18,
            indicatormargin=[8, 4, 8, 4],
            padding=4,
        )
        style.map(
            "NewStyle.TCheckbutton",
            background=[("active", "#222222"), ("selected", "#444444")],
            foreground=[("active", Colors.INFO_BLUE), ("selected", Colors.INFO_BLUE)],
        )
        style.configure("Thick.Horizontal.TProgressbar", thickness=20)


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
            self.input_frame, bg=Colors.BLACK_ENTRYBOX, fg=Colors.PLAIN_WHITE, width=50, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 13)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=5, ipady=4)

        self.enter_button = tk.Button(
            self.input_frame, text="Get", command=self.on_enter_pressed,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_RED,
            font=("Segoe UI", 13, "bold"),
            width=8, bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_RED,
            cursor="hand2"
        )
        self.enter_button.pack(side="left", padx=0, pady=5)

        self.browse_button = tk.Button(
            self.input_frame, text="📁", command=self.browse_folder,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 13, "bold"),
            width=3, bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.browse_button.pack(side="left", padx=0, pady=5)

        self.search_frame = tk.Frame(self.root, bg=Colors.PLAIN_BLACK)
        self.search_frame.pack(side="top", fill="x", padx=20, pady=(0, 10))
        
        self.filter_favs = tk.Button(
            self.search_frame, text="★", command=self.check_update_favs,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_GREEN,
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.filter_favs.pack(side="left", padx=0, pady=0)

        self.show_caps = tk.Button(
            self.search_frame, text="Snaps", command=self.display_caps,
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_GREEN,
            font=("Segoe UI", 12, "bold"),
            width=8, bd=0, relief=tk.RAISED, activebackground="#006400",
            cursor="hand2"
        )
        self.show_caps.pack(side="left", padx=0, pady=0)

        self.show_verticals = tk.Button(
            self.search_frame, text="V", command=self.get_verticals,
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_WHITE, 
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.show_verticals.pack(side="left", padx=0, pady=0, ipadx=3)

        self.show_horizontals = tk.Button(
            self.search_frame, text="L", command=self.get_horizontals,
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_WHITE, 
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.show_horizontals.pack(side="left", padx=0, pady=0, ipadx=3)

        self.allow_deleted_on = False

        def toggle_allow_deleted():
            self.allow_deleted_on = not self.allow_deleted_on
            if self.allow_deleted_on:
                self.allow_deleted_button.config(fg=Colors.PLAIN_RED, relief=tk.SUNKEN)
            else:
                self.allow_deleted_button.config(bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, relief=tk.RAISED)

        self.allow_deleted_button = tk.Button(
            self.search_frame, text="🚫", command=toggle_allow_deleted,
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_WHITE, 
            font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.allow_deleted_button.pack(side="left", padx=0, pady=0)
        
        self.search_entry = tk.Entry(
            self.search_frame, 
            bg=Colors.BLACK_ENTRYBOX, 
            fg=Colors.PLAIN_WHITE, 
            width=30, bd=2, relief=tk.FLAT,
            font=("Segoe UI", 12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=0, pady=0, ipady=2)

        self.top_level_only_on = False

        def toggle_top_level():
            self.top_level_only_on = not self.top_level_only_on
            if self.top_level_only_on:
                self.top_level_only_button.config(fg=Colors.INFO_BLUE, relief=tk.SUNKEN)
            else:
                self.top_level_only_button.config(bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE, relief=tk.RAISED)

        self.top_level_only_button = tk.Button(
            self.search_frame, text="🔼", command=toggle_top_level,
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_WHITE, 
            font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.top_level_only_button.pack(side="left", padx=0, pady=0)

        self.search_button = tk.Button(
            self.search_frame, text="Search", command=self.on_search_pressed,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 12, "bold"),
            width=10, bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.search_button.pack(side="left", padx=0, pady=0)

        self.delete_button = tk.Button(
            self.search_frame, text="🗑", command=self.on_delete_all_pressed,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_RED,
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_RED,
            anchor="center", cursor="hand2"
        )
        self.delete_button.pack(side="left", padx=0, pady=0)

        self.refresh_button = tk.Button(
            self.search_frame, text="♻️", command=self.on_refresh_pressed,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_RED,
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_RED,
            cursor="hand2"
        )
        self.refresh_button.pack(side="left", padx=0, pady=0)
        
        self.all_media_button = tk.Button(
            self.search_frame, text="All Media", command=lambda: self.root.after(50, self.show_all_media),
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_WHITE, 
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#003366",
            cursor="hand2"
        )
        self.all_media_button.pack(side="left", padx=0, pady=0)

        self.categories_button = tk.Button(
            self.search_frame, text="☰", command=self.show_categories,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_PURPLE,
            font=("Segoe UI", 12, "bold"),
            bd=0, relief=tk.RAISED, activebackground="#4B0082",
            cursor="hand2"
        )
        self.categories_button.pack(side="left", padx=0, pady=0)

        self.settings_button = tk.Button(
            self.root, text="⚙️", command=self.open_settings,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_GRAY, 
            bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.settings_button.place(relx=1.0, x=-10, y=10, anchor="ne", width=40, height=30)

        self.stats_button = tk.Button(
            self.root, text="📊", command=self.open_media_stats,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.ORANGE, 
            bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.stats_button.place(relx=1.0, x=-60, y=10, anchor="ne", width=40, height=30)

        self.folder_stats_button = tk.Button(
            self.root, text="▦", command=self.show_folder_stats,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.ORANGE,
            bd=0, font=("Segoe UI", 14, "bold"),
            relief=tk.FLAT, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.folder_stats_button.place(relx=1.0, x=-10, y=50, anchor="ne", width=40, height=30)

        self.info_button = tk.Button(
            self.root, text="ℹ️", command=self.show_info,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_RED, 
            bd=0, font=("Segoe UI", 13, "bold"),
            relief=tk.FLAT, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.info_button.place(relx=0.0, x=10, y=10, anchor="nw", width=40, height=30)

        self.show_duplicates_button = tk.Button(
            self.root, text="🔍", command=lambda: self.show_duplicates_for_selected(all_mode=True),
            bg=Colors.PLAIN_BLACK, 
            fg=Colors.PLAIN_ORANGE, 
            font=("Segoe UI", 13, "bold"),
            bd=0, relief=tk.RAISED, activebackground=Colors.ACTIVE_WHITE,
            cursor="hand2"
        )
        self.show_duplicates_button.place(relx=1.0, x=-100, y=55, anchor="nw", width=40, height=30)

        def on_enter(e): e.widget.config(fg="#444")
        def on_leave(e):
            if e.widget == self.enter_button:
                e.widget.config(fg=Colors.PLAIN_RED)
            elif e.widget == self.delete_button or e.widget["text"] == "🗑":
                e.widget.config(fg=Colors.PLAIN_RED)
            elif e.widget == self.refresh_button or e.widget["text"] == "♻️":
                e.widget.config(fg=Colors.PLAIN_RED)
            elif "★" in e.widget["text"] or "Snaps" in e.widget["text"]:
                e.widget.config(fg=Colors.PLAIN_GREEN)
            elif "V" in e.widget["text"] or "L" in e.widget["text"] or e.widget in [self.all_media_button]:
                e.widget.config(fg=Colors.PLAIN_WHITE)
            elif e.widget == self.categories_button:
                e.widget.config(fg=Colors.PLAIN_PURPLE)
            else:
                e.widget.config(fg=Colors.PLAIN_WHITE)

        for btn in [self.enter_button, self.delete_button, self.refresh_button,
                     self.filter_favs, self.show_caps, self.show_verticals, self.show_horizontals,
                     self.all_media_button, self.categories_button]:
            btn.bind("<Enter>", on_enter, add="+")
            btn.bind("<Leave>", on_leave, add="+")
        self._set_tooltips()
        self._create_stats_frame()

    def _set_tooltips(self):
        ToolTip(self.enter_button, "Fetch media files from the specified folder path(s)")
        ToolTip(self.browse_button, "Browse and select folder(s) for fetching")
        ToolTip(self.search_entry, "Enter search text and press Enter or click Search")
        ToolTip(self.delete_button, "Show files set for deletion (Ctrl+Shift+Delete to remove from deletion list)")
        ToolTip(self.refresh_button, "Refresh the file list, folders, categories, or deletions based on the command in entrybox.")
        ToolTip(self.settings_button, "Open Settings")
        ToolTip(self.stats_button, "Open Media Dashboard")
        ToolTip(self.folder_stats_button, "Show stats for folders of files from file table")
        ToolTip(self.info_button, "How to use this application")
        ToolTip(self.filter_favs, "Filter only favorite files from the file table")
        ToolTip(self.show_caps, "Show all screenshots available")
        ToolTip(self.show_verticals, "Filter only vertical videos (portrait mode) from the file table")
        ToolTip(self.show_horizontals, "Filter only horizontal videos (landscape mode) from the file table")
        ToolTip(self.allow_deleted_button, "Toggle inclusion of deleted files in searches")
        ToolTip(self.top_level_only_button, "Toggle searching on file_names, categories, descriptions, and notes.")
        ToolTip(self.all_media_button, "Show all media files")
        ToolTip(self.categories_button, "Show Categories")
        ToolTip(self.show_duplicates_button, "Show all duplicate files in the Database")

    def show_duplicates_for_selected(self, event=None, all_mode=False, mode="hash"):
        """
        Show duplicates in a new window.
        - If event is triggered from selection -> use selected files
        - If all_mode=True (button press) -> show all duplicates
        - mode: "hash" (default), "duration", or "size" to control duplicate matching
        """
        if isinstance(event, tk.Event) and hasattr(event.widget, 'cget') and event.widget.cget('text') == "⚯":
            all_mode = True
            mode = "hash"

        if not all_mode:
            selected_items = self.file_table.selection()
            if not selected_items:
                showinfo(self.root, "No Selection", "Please select file(s) to find duplicates.")
                return
        else:
            selected_items = None

        loading = self.show_loading_screen("Finding duplicates...")

        def worker():
            try:
                all_duplicates = {}

                if not all_mode:
                    for item in selected_items:
                        file_path = self.file_table.item(item, "values")[2]
                        
                        if mode == "hash":
                            index_hash = self.fingerprint_manager.get_index_hash_by_path(file_path)
                            if not index_hash:
                                continue
                            duplicates = self.fingerprint_manager.get_duplicates_by_hash(index_hash)
                        elif mode == "duration":
                            fp = self.fingerprint_manager.fingerprints.get(
                                self.fingerprint_manager.get_index_hash_by_path(file_path), {}
                            )
                            if not fp:
                                continue
                            duration = float(fp.get("duration", 0))
                            hashes = self.fingerprint_manager.get_hashes_by_duration(duration, tolerance=0.1)
                            duplicates = []
                            for h in hashes:
                                duplicates.extend(self.fingerprint_manager.get_paths_by_hash(h))
                        elif mode == "size":
                            fp = self.fingerprint_manager.fingerprints.get(
                                self.fingerprint_manager.get_index_hash_by_path(file_path), {}
                            )
                            if not fp:
                                continue
                            size = fp.get("size_bytes", "0")
                            hashes = self.fingerprint_manager.get_hashes_by_size(int(size))
                            duplicates = []
                            for h in hashes:
                                duplicates.extend(self.fingerprint_manager.get_paths_by_hash(h))

                        duplicates = [d for d in duplicates if d != file_path]
                        if not self.allow_deleted_on:
                            duplicates = [d for d in duplicates if os.path.exists(d)]

                        if duplicates:
                            all_duplicates[file_path] = duplicates

                else:
                    if mode == "hash":
                        dupes_dict = self.fingerprint_manager.get_all_duplicates()
                    elif mode == "duration":
                        dupes_dict = {}
                        duration_groups = self.fingerprint_manager.get_groups_by_duration()
                        for duration, hashes in duration_groups.items():
                            paths = []
                            for h in hashes:
                                paths.extend(self.fingerprint_manager.get_paths_by_hash(h))
                            if len(paths) > 1:
                                dupes_dict[paths[0]] = paths[1:]
                    else:
                        dupes_dict = {}
                        size_groups = self.fingerprint_manager.get_groups_by_size()
                        for size, hashes in size_groups.items():
                            paths = []
                            for h in hashes:
                                paths.extend(self.fingerprint_manager.get_paths_by_hash(h))
                            if len(paths) > 1:
                                dupes_dict[paths[0]] = paths[1:]

                    for paths in dupes_dict.values():
                        if len(paths) < 2:
                            continue
                        filtered_paths = [p for p in paths if self.allow_deleted_on or os.path.exists(p)]
                        if len(filtered_paths) > 1:
                            all_duplicates[filtered_paths[0]] = filtered_paths[1:]

                def show_results():
                    loading.destroy()
                    if not all_duplicates:
                        showinfo(self.root, "No Duplicates", "No duplicates found.")
                        return

                    win = tk.Toplevel(self.root)
                    # win.title("Duplicate Files")
                    win.title(f"Duplicate Files - By {mode.title()}")
                    win.geometry("800x600")
                    win.configure(bg=Colors.PLAIN_BLACK)
                    center_window(win, 800, 600)
                    win.focus_force()
                    win.bind("<Escape>", lambda e: win.destroy())

                    heading = tk.Label(
                        win, 
                        text="Duplicate Files", 
                        font=("Segoe UI", 20, "bold"),
                        bg=Colors.PLAIN_BLACK,
                        fg=Colors.PLAIN_RED
                    )
                    heading.pack(pady=10)

                    frame = tk.Frame(win, bg=Colors.PLAIN_BLACK)
                    frame.pack(fill="both", expand=True, padx=10, pady=5)

                    tree = ttk.Treeview(frame, show="tree", selectmode="extended")
                    tree.pack(side="left", fill="both", expand=True)

                    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
                    sb.pack(side="right", fill="y")
                    tree.configure(yscrollcommand=sb.set)

                    def on_double_click(event):
                        selected_items = tree.selection()
                        if not selected_items:
                            return

                        all_selected_paths = []

                        for item in selected_items:
                            item_text = tree.item(item)["text"]

                            if item_text.startswith("Original:"):
                                original_path = item_text.replace("Original: ", "")
                                duplicate_paths = [original_path] + all_duplicates.get(original_path, [])
                                all_selected_paths.extend(duplicate_paths)

                        if not all_selected_paths:
                            return

                        all_selected_paths = sorted(set(all_selected_paths))

                        self.total_search_results = len(all_selected_paths)
                        self.update_search_size(all_selected_paths)
                        self.update_stats()
                        self.insert_to_table(sorted(self.file_path_tuple(all_selected_paths)))

                        win.destroy()

                    tree.bind("<Return>", on_double_click)

                    for original, dupes in all_duplicates.items():
                        parent = tree.insert("", "end", text=f"Original: {original}", open=True)
                        for dupe in dupes:
                            tree.insert(parent, "end", text=dupe)

                    total_dupes = sum(len(dupes) for dupes in all_duplicates.values())
                    status = tk.Label(
                        win,
                        text=f"Press Enter on Original(s) to show duplicates in main window\n" \
                            f"Found {total_dupes} duplicate files for {len(all_duplicates)} originals",
                        bg=Colors.PLAIN_BLACK,
                        fg=Colors.PLAIN_WHITE,
                        font=("Segoe UI", 10)
                    )
                    status.pack(pady=5)

                self.root.after(0, show_results)

            except Exception as e:
                self.root.after(0, lambda err=e: (
                    loading.destroy(),
                    showerror(self.root, "Error", f"Failed to find duplicates: {err}")
                ))

        threading.Thread(target=worker, daemon=True).start()

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
        table_frame = tk.Frame(self.root, bg=Colors.PLAIN_BLACK)
        table_frame.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 10))

        self.file_table = ttk.Treeview(
            table_frame, columns=("#", "File Name", "Folder Path"), show="headings", selectmode="extended"
        )
        self.file_table.heading("#", text="#", command=lambda: self.treeview_sort_column("#", False))
        self.file_table.heading("File Name", text="File Name", command=lambda: self.treeview_sort_column("File Name", False))
        self.file_table.heading("Folder Path", text="Folder Path", command=lambda: self.treeview_sort_column("Folder Path", False))

        self.file_table.column("#", width=40, anchor="center", stretch=False)
        self.file_table.column("File Name", width=400, anchor="w")
        self.file_table.column("Folder Path", width=400, anchor="w")

        self.file_table.tag_configure("evenrow", background="#222", foreground=Colors.PLAIN_WHITE)
        self.file_table.tag_configure("oddrow", background="#333", foreground=Colors.PLAIN_WHITE)
        self.file_table.tag_configure("missing", background="#5a1e1e", foreground=Colors.PLAIN_WHITE)
        self.file_table.tag_configure("present", background="#1e5a1e", foreground=Colors.PLAIN_WHITE)

        self.file_table.pack(side="left", fill="both", expand=True)

        self.file_table.bind("<<TreeviewSelect>>", self.update_selected_files_label)

        self.scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.file_table.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.file_table.configure(yscrollcommand=self.scrollbar.set)

        self._tooltip = ToolTip(self.file_table, "", wraplength=450)

        def on_motion(event):
            self._generate_table_tooltip(event=event, display_index=2 if self.entry.get() != "show categories" else 1)

        self.file_table.bind("<Motion>", on_motion, add="+")
        self.file_table.bind("<Leave>", lambda e: self._tooltip.hide_tooltip())

    def _generate_table_tooltip(self, event=None, display_index=2, column="#2"):
        region = self.file_table.identify("region", event.x, event.y)
        if region == "cell":
            row_id = self.file_table.identify_row(event.y)
            col_id = self.file_table.identify_column(event.x)

            if row_id and col_id == column:
                values = self.file_table.item(row_id, "values")
                if values and len(values) >= 3:
                    file_path = values[display_index]
                    
                    parts = [(file_path + "\n", {"foreground": Colors.PLAIN_WHITE})]

                    # if self.entry.get() != "show categories":
                    #     size_text = f"Size: {convert_bytes(get_file_size(file_path))}"
                    #     parts.append((size_text, {"foreground": "cyan"}))
                    text_display = file_path
                    text_display += f"\nSize - {convert_bytes(get_file_size(file_path))}" if self.entry.get() != "show categories" else ""
                    descs = self.description_manager.get_all_related_descriptions(file_path, latest_only=True).get("description", "")
                    # all_desc = " ".join([d for d in descs.values() if d])
                    all_desc = descs
                    if all_desc:
                        sentence = all_desc.split("\n")
                        short_desc = "\n".join(sentence[:10]) + ("..." if len(sentence) > 10 else "")
                        text_display += f"\n\n{short_desc}"
                    
                    categories = self.category_manager.get_file_categories(file_path)
                    if categories:
                        text_display += f"\nin-{categories}"
                        # parts.append(("\nDescription:\n", {"foreground": "orange", "font": ("Segoe UI", 9, "bold")}))
                        # parts.append((short_desc, {"foreground": "lightgray"}))
                        
                    x = event.x_root + 20
                    y = event.y_root + 10
                    self._tooltip.hide_tooltip()
                    # self._tooltip.show_tooltip(x, y, parts)
                    self._tooltip.show_tooltip(x, y, text_display)
                    return
        self._tooltip.hide_tooltip()

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
        self._info_window.title("How to use this App")
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
            "• Use '🔼' to search in everything, names, notes, categories, descriptions.\n"
            "• Use '★' and 'Snaps' to view favorite files and screenshots taken respectively.\n"
            "• Double-click/Enter a file to play it.\n"
            "• Right-click a file for more options (move, delete, convert etc).\n"
            "• Keyboard Shortcuts:\n"
            "    - Ctrl+F/f: Add to Favorites\n"
            "    - Ctrl+D/d: Remove from Favorites\n"
            "    - Ctrl+M/m: Move selected files\n"
            "    - Delete: Mark for deletion\n"
            "    - Ctrl+Shift+Delete: Remove from deletion\n" \
            "    - Shift+A/a: Add to Category\n" \
            "    - Shift+N/n: Add Note\n" \
            "    - Shift+S/s: View Screenshots\n" \
            "    - Shift+P/p: View Properties\n" \
            "    - Control+R/r: Add Association for a File To Another File\n"
            "• You can use 'V' and 'L' buttons to filter for vertical and landscape videos.\n"
            "• Use the settings (⚙️) and stats (📊) buttons for more features.\n" \
            "• For more keyboard shortcuts and detail commands of this app you can visit the following\n"
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
        stats = get_split_stats_by_folder(file_paths)
        win = tk.Toplevel(self.root)
        win.title("Folder Split Stats")
        win.configure(bg="#181818")
        self.center_window(width=800, height=600, window=win)

        heading = tk.Label(
            win,
            text="Folder-wise Stats",
            font=("Segoe UI", 23, "bold"),
            bg=Colors.BLACK_ENTRYBOX,
            fg=Colors.INFO_BLUE,
            pady=10
        )
        heading.pack(side="top", fill="x")

        style = ttk.Style(win)
        style.theme_use("clam")
        style.configure(
            "Treeview",
            font=("Segoe UI", 11),
            rowheight=28,
            background="#222",
            fieldbackground="#222",
            foreground=Colors.PLAIN_WHITE
        )
        style.map("Treeview", background=[("selected", "#8B0000")])

        columns = ("Folder", "File Count", "Total Size")
        tree = ttk.Treeview(
            win,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=15
        )

        tree.heading("Folder", text="Folder")
        tree.heading("File Count", text="File Count")
        tree.heading("Total Size", text="Total Size")
        tree.column("Folder", width=350, anchor="w")
        tree.column("File Count", width=100, anchor="center")
        tree.column("Total Size", width=150, anchor="center")

        total_folders = 0
        for folder, stat in sorted(stats.items()):
            tree.insert("", "end", values=(folder, stat["file_count"], convert_bytes(stat["total_size"])))
            total_folders += 1

        tree.pack(fill="both", expand=True, padx=20, pady=10)

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

        def on_double_click(event):
            selected_items = tree.selection()
            if not selected_items:
                return

            selected_folders = [tree.item(item, "values")[0] for item in selected_items]

            files = [
                f for f in file_paths
                if os.path.dirname(f) in selected_folders
            ]

            if not self.allow_deleted_on:
                files = [f for f in files if os.path.exists(f)]

            self.total_files = len(files)
            self.search_size = self.convert_bytes(sum(get_file_size(f) for f in files))
            self.total_search_results = len(files)
            self.update_stats()
            self.insert_to_table(sorted(self.file_path_tuple(files)))

            # print(f"Loaded {len(files)} files from {len(selected_folders)} selected folders")

        tree.bind("<Return>", on_double_click)
        tree.bind("<Double-1>", on_double_click)

        win.bind("<Escape>", lambda e: win.destroy())

        status = tk.Label(
            win,
            text=f"Press Enter (or double-click) on selected folders to show their files in the main window\n"
                f"Hold Ctrl or Shift to select multiple folders\n"
                f"Found {total_folders} folders in the file table",
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE,
            font=("Segoe UI", 9, "italic")
        )
        status.pack(pady=5)

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

    def refresh_folders(self, folder_paths, message):
        """Worker to refresh folders with loading screen."""
        loading_win = self.show_loading_screen(f"Refreshing {len(folder_paths)} folders...")

        def worker():
            vf_loader = VideoFileLoader()
            vf_loader.refresh_folders(folder_paths)

            self.root.after(0, lambda: self._finish_refresh(loading_win, message))

        threading.Thread(target=worker, daemon=True).start()


    def _finish_refresh(self, loading_win, message):
        """Close loading screen and update UI after refresh."""
        if loading_win.winfo_exists():
            loading_win.destroy()
        self.show_paths()
        showinfo(self.root, "Refreshed", message)
        self.update_stats_async()


    def on_refresh_pressed(self):
        entry_text = self.entry.get().strip().lower()

        if entry_text == "show paths":
            if not hasattr(self, "folders") or not self.folders:
                self.show_paths()

            selected_items = self.file_table.selection()
            if selected_items:
                folder_paths = [
                    self.file_table.item(item, "values")[1].strip()
                    for item in selected_items
                ]
                msg = f"Refreshed {len(folder_paths)} selected folder(s)."
            else:
                # folder_paths = [folder.strip() for folder, csv in self.folders]
                # msg = f"Refreshed {len(folder_paths)} folder(s)."
                folder_paths = []
                showerror(self.root, "No Selection", "Please select folders to refresh stats for.")
                return

            self.refresh_folders(folder_paths, msg)
            
        elif entry_text == "all media files":
            self.show_all_media(refresh=True)

        elif self.categories:
            self.display_category_files(self.category_names)

        else:
            self.refresh_deletions()

    def show_all_media(self, event=None, refresh=False):
        """Gathers all media and displays File Name and Source Folder in the table with a loading screen."""
        self.clean_memory(["video_files", "file_path", "categories", "image_files", "category_names"])
        loading = self.show_loading_screen("Loading all media...")

        def worker():
            csv_path = gather_all_media(refresh=refresh)
            if not csv_path:
                self.root.after(0, lambda: (loading.destroy(),
                                            showerror(self.root, "Error", "Failed to gather all media.")))
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
                        if self.allow_deleted_on or (row.get("Status", "") == "Present"):
                            file_list.add(file_path)
                            size_str = row.get("File Size (Bytes)", "0")
                            try:
                                total_size_bytes += int(size_str)
                            except (ValueError, TypeError):
                                pass

                self.root.after(100, lambda: (
                    loading.destroy(),
                    self._on_all_media_loaded(file_list, total_size_bytes)
                ))
            except Exception as e:
                self.root.after(100, lambda: (loading.destroy(),
                                            showerror(self.root, "Error", f"Failed to load all media: {e}")))

        threading.Thread(target=worker, daemon=True).start()


    def _on_all_media_loaded(self, file_list, total_size_bytes):
        self.reset_search_option()
        self.video_files = list(file_list)
        self.total_files = len(file_list)
        self.total_size = self.convert_bytes(total_size_bytes)
        self.update_stats()
        self.update_entry_text("All Media Files")
        self.root.after(0, self.insert_to_table(self.file_path_tuple(file_list)))
        showinfo(self.root, "All Media", f"Total media files found: {len(file_list)}")
        self.display_memory_usage()

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

    def insert_to_table(self, files: list | tuple):
        """
        Inserts files into the file table with alternate row colors.
        Adds lazy loading if more than 1000 items.
        """

        self.file_table.delete(*self.file_table.get_children())
        self._all_files = files
        self._loaded_count = 0
        self._chunk_size = 500

        def load_next_chunk():
            """Insert next chunk of rows"""
            start = self._loaded_count
            end = min(start + self._chunk_size, len(self._all_files))

            for idx in range(start, end):
                file, file_path = self._all_files[idx]
                tags = ("evenrow",) if idx % 2 == 0 else ("oddrow",)
                self.file_table.insert("", tk.END, values=(idx, file, file_path), tags=tags)

            self._loaded_count = end

        def check_scroll(event=None):
            """Check if near bottom, load next chunk"""
            if not self.file_table.yview():
                return
            top, bottom = self.file_table.yview()
            # print(len(self._all_files))
            if bottom > 0.9 and self._loaded_count < len(self._all_files):
                load_next_chunk()

        if len(files) <= 500:
            load_next_chunk()
        else:
            load_next_chunk()

            self.file_table.bind("<Configure>", check_scroll)
            self.file_table.bind("<Motion>", check_scroll, add="+")
            self.file_table.bind("<MouseWheel>", check_scroll)
            # self.file_table.bind("<Button-4>", check_scroll)
            # self.file_table.bind("<Button-5>", check_scroll)


    def insert_all_media_to_table(self, files: list|tuple):
        """
        Currently not in use.
        Testing function to insert all media files with status indicatin via background color.
        Takes input a list of tuples (filename, filepath, status)
        Where status is either "Present" or "Missing"
        """
        self.file_table.delete(*self.file_table.get_children())
        count = 0

        for idx, (file, file_path, status) in enumerate(files):
            row_tag = "evenrow" if idx % 2 == 0 else "oddrow"
            if status != "Present":
                tags = (row_tag, "missing")
                count += 1
            else:
                tags = (row_tag, "present")
            self.file_table.insert("", tk.END, values=(idx, file, file_path), tags=tags)
        print("Total Missing Files:", count)
            

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
        folder_path_string = self.entry.get().strip()
        vf_loader = VideoFileLoader()
        self.reset_search_option()
        self.clean_memory(["video_files", "image_files", "categories"], mode="empty")
        try:
            if folder_path_string == "play favs":
                favs = self.fav_manager
                all_favs = favs.get_favorites()
                def after_filter(existing_files):
                    self.video_files = sorted(existing_files)
                    self.total_files = len(self.video_files)
                    self.total_size = self.convert_bytes(favs.total_size)
                    favs.total_size = 0
                    self.update_stats()
                    self.insert_to_table(self.file_path_tuple(self.video_files))
                self.filter_existing_files(all_favs, after_filter)
                return
            
            elif folder_path_string == "show paths":
                self.show_paths()
                self.reset_search_option(folder=True)
            
            elif folder_path_string == "show deletes":
                self.show_deletes()
            
            elif folder_path_string == "show deleted":
                self.show_deletes(deleted=True)

            elif folder_path_string == "show history":
                self.video_files = self.get_history_files()
                self.total_files = len(self.video_files)
                self.update_stats()
                self.total_duration_watched = 0
                # self.finish_loading_ui()

            elif folder_path_string == "show categories":
                self.show_categories()

            else:
                self._load_video_files(folder_path_string, vf_loader)
        
        except ImportError as e:
            print(f"An Import Error Occurred: {e}")
            self.video_files = vf_loader.get_videos_from_paths(folder_paths=folder_path_string.split(","))
        
        except Exception as e:
            print(f"An Unknown Error Occurred {e}")
            showerror(self.root, "Error", f"An error occurred: {e}")
            return

        finally:
            self.finish_loading_ui()
            self.display_memory_usage()
            # self.check_gc_collection()

    def finish_loading_ui(self):
        """Handles UI updates once self.video_files/self.folders/etc are set."""
        if not self.play_folder and not self.play_category:
            print(f"Total Videos Found: {len(self.video_files)}")
            self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
        elif self.play_folder:
            print(f"Total Folders in Search History: {len(self.folders)}")
            self.insert_to_table(sorted(self.folders))
        elif self.play_category:
            print(f"Total Categories: {self.total_files}")

    def display_memory_usage(self):
        cur, peak = get_memory_usage()
        print(f"Current: {cur} MB | Peak: {peak} MB")   

    def show_paths(self):
        """Show only those folder/csv pairs where both the folder and the CSV file exist."""
        self.reset_search_option(folder=True)
        self.clean_memory(["video_files", "image_files", "categories", "category_names"], mode="empty")
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
            self.update_entry_text("show paths")
        except Exception as e:
            showerror(self.root, "Error", f"Failed to load valid folder/csv pairs: {e}")

    def refresh_deletions(self):
        """Refresh deletions with a loading screen."""
        loading_win = self.show_loading_screen("Refreshing deletions...")

        def worker():
            try:
                self.deletion_manager.check_deleted()
                self.show_deletes(deleted=False)
            finally:
                self.root.after(0, loading_win.destroy)
                self.update_entry_text("show deletes")
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
                showinfo(self.root, "Refreshed", "Deletions refreshed.")

        threading.Thread(target=worker, daemon=True).start()


    def on_right_click(self, event):
        """ Handle right-click to open context menu """
        item = self.file_table.identify_row(event.y)
        
        if item not in self.file_table.selection():
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
            if self.play_images:
                search_files = self.image_files
            elif self.entry.get() == "show categories":
                search_files = self.categories
            # elif self.play_folder:
            #     folder_file_tuple = self.get_files_from_table(folders=True)
            #     search_files = [folder for folder, file in folder_file_tuple]
            else:
                search_files = self.video_files

            top_level_only = getattr(self, "top_level_only_on", False)
            # matched_files = self.search_inf_filepaths(query, search_files)
            if top_level_only and query != "":
                    # matched_desc_keys = self.description_manager.search_description_by_keys(query, search_files)
                    matched_desc_keys = self.description_manager.search_description_by_keys_advanced(query, search_files)
                    matched_note_keys = self.notes_manager.search_notes_by_keys(query=query, allowed_keys=search_files)
                    matched_cat_keys = self.category_manager.search_categories_by_keys(query=query, allowed_keys=search_files)
                    # matched_snippets_keys = self.snippets_manager.search_snippets_by_notes_global(query) if self.entry.get() == "All Media Files" else None
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
                    file_name = os.path.basename(file) if self.entry.get() != "show categories" else file
                    file_list.append((file_name, file))
            
            # if top_level_only and matched_snippets_keys:
            #         file_list.extend(self.file_path_tuple(matched_snippets_keys))
    
                
            print(f"Total Files for {query}: {len(file_list)}")

            if query == '' and not top_level_only:
                self.search_size = self.total_size
            elif not self.entry.get() in ["show deleted"]:
                self.update_search_size([file[1] for file in file_list])

            self.total_search_results = len(file_list)
            self.update_stats()
            self.insert_to_table(natural_sort_iterables(file_list))
            # self.update_stats_async()
        except AttributeError as e:
            print("No videos found to search from.")
            print(f"An Exception is raised {e}")
            showerror(self.root, "Attribute Error", f"Error in Search Pressed: {e}")
        except Exception as e:
            print(f"An Error {e} Occurred")
            showerror(self.root, "Error", f"Exception in Search Pressed: {e}")

    def search_in_filepaths(self, query, file_list):
        matched_files = []
        query = query.lower()
        for file in file_list:
            if query in file.lower():
                matched_files.append(file)
        return matched_files

    def on_filter_fav(self, event=None):
        files = self.get_files_from_table()
        favs = self.fav_manager
        if files:
            files = [normalise_path(file) for file in files if favs.check_favorites(file)]
            self.total_search_results = len(files)
            self.update_search_size(files)
            self.update_stats()
            self.insert_to_table(self.file_path_tuple(files))

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
            self.update_stats()
            self.insert_to_table(fav_files)

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
                self.reset_search_option()
                self.insert_to_table(sorted(self.file_path_tuple(self.video_files)))
                # self.update_stats_async()
            
            elif self.play_category:
                selected_items = self.file_table.selection()
                self.category_names = [self.file_table.item(i, "values")[1] for i in selected_items]

                self.display_category_files(self.category_names)
            
            elif self.play_images:
                viewer_window = Toplevel(self.root)
                viewer_window.title("Image Viewer")
                image_files = self.get_files_from_table()
                viewer_window.lift()
                viewer_window.focus_force()

                ImageViewer(viewer_window, image_files, 
                            index=image_files.index(file_path), 
                            width=self.image_viewer_width, 
                            height=self.image_viewer_height,
                            deletion_manager=self.deletion_manager)
                
                self.deletion_manager.set_parent_window(self.root)

            else:
                if len(self.file_table.selection()) > 1:
                    selected_items = self.file_table.selection()
                    self.files = [self.file_table.item(i, "values")[2] for i in selected_items]
                else:
                    self.files = sorted(self.get_files_from_table())
                    # self.files = self._all_files

                if not os.path.exists(file_path) and not SHOW_SNIPPETS:
                        showerror(self.root, "File(s) Not Found", f"The file '{file_path}' does not exist.")
                        return False
                
                if SHOW_SNIPPETS and (len(self.file_table.selection()) != 1 or (not os.path.exists(file_path))):
                    def after_snippets(snippets):
                        self.files = snippets
                        file_path = self.files[0] if self.files else None

                        if not file_path or (not os.path.exists(file_path)):
                            showerror(self.root, "File(s) Not Found", f"The file '{file_path}' does not exist.")
                            return

                        print(f"Total Videos Found: {len(self.files)}")
                        self.play_media(self.files, file_path)
                        # self.deletion_manager.set_parent_window(self.root)

                    self.get_video_snippets_for_selected(
                        # files=self.files[:150],
                        check_deleted=True,
                        # all_files=True,
                        on_complete=after_snippets
                    )
                    
                else:
                    if not os.path.exists(file_path):
                        showerror(self.root, "File(s) Not Found", f"The file '{file_path}' does not exist.")
                        return False
                    self.play_media(self.files, file_path)
                    # self.deletion_manager.set_parent_window(self.root)

                print(f"Total Videos Found: {len(self.files)}")
        
        except IndexError as e:
            showerror(self.root, "Error", f"{e}")

    def _get_category_files(self, category_names):
        all_files = []
        for category_name in category_names:
            files = self.category_manager.get_category_files(category_name)
            all_files.extend(files)
        return all_files

    def display_category_files(self, category_names):
        if not category_names:
            self.show_categories()
            return

        # all_files = []
        # for category_name in category_names:
        #     files = self.category_manager.get_category_files(category_name)
        #     all_files.extend(files)

        all_files = self._get_category_files(category_names)

        unique_files = list(dict.fromkeys(all_files))

        if self.allow_deleted_on:
            existing_files = unique_files
        else:
            existing_files = [f for f in unique_files if os.path.exists(f)]

        with ThreadPoolExecutor(max_workers=8) as executor:
            sizes = list(executor.map(get_file_size, existing_files))

        total_size = sum(sizes)

        self.video_files = existing_files
        self.total_files = len(existing_files)
        self.total_size = self.convert_bytes(total_size)
        self.total_search_results = len(existing_files)
        self.update_stats()

        categories_str = ", ".join(category_names)
        print(f"Total Videos Found in categories [{categories_str}]: {len(existing_files)}")
        self.update_entry_text(f"Categories: {categories_str}")
        self.reset_search_option()
        self.insert_to_table(sorted(self.file_path_tuple(existing_files)))

    def play_media(self, files, file_path, random_select=True):
        if files:
            self.play_images = False
            app = MediaPlayerApp(
                files, 
                current_file=file_path, 
                random_select=random_select, 
                parent=self.root,
                category_manager=self.category_manager,
                favorites_manager=self.fav_manager,
                annotations_manager=self.annotations_manager,
                notes_manager=self.notes_manager,
                snippets_manager=self.snippets_manager,
                trimmed_segments=self.trimmed_segments,
                associations_manager=self.associations_manager,
                deletion_manager=self.deletion_manager,
                fingerprint_manager=self.fingerprint_manager,
                trimmed_segments_metadata=self.trimmed_segments_metadata
            )
            app.update_video_progress()
            print(len(self.trimmed_segments))
            # self.deletion_manager.set_parent_window(self.root)
        else:
            print("No video files found in the specified folder path(s).")

    def update_search_size(self, file_list):
        self.search_size = 0
        size = 0
        for file in file_list:
             size += get_file_size(file)

        self.search_size = self.convert_bytes(size)

    def get_snippets(self, file_paths: list = None, related_paths=False, graph=None):
        files = []
        transfer_graph = build_transfer_graph() if not graph else graph
        snippets = self.snippets_manager.get_snippets_for_files(file_paths, related_paths=related_paths, graph=transfer_graph)
        files += [s["Output File"] for s in snippets if s.get("Output File")]
        return list(set(files))

    def get_verticals(self):
        try:
            file_list = self.get_files_from_table()
            verticals = self.video_stats_manager.get_vertical_videos(file_list)
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
            horizontals = self.video_stats_manager.get_horizontal_videos(file_list)
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
        def on_stats_done(result=None):
            self.task_manager.add_task(
                self._create_fingerprints_background,
                threaded=True
            )
        
        self.task_manager.add_task(
            self.video_stats_manager.create_stats,
            threaded=True,
            on_done=on_stats_done
        )

    def random_play(self, event=None):
        # self.on_enter_pressed()
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
                                 trimmed_segments=self.trimmed_segments,
                                 deletion_manager=self.deletion_manager,
                                 fingerprint_manager=self.fingerprint_manager,
                                 annotations_manager=self.annotations_manager,
                                 trimmed_segments_metadata=self.trimmed_segments_metadata
                                 )
            app.update_video_progress()
            # app.protocol("WM_DELETE_WINDOW", lambda: self._on_close_player(app))
            app.mainloop()
            self.deletion_manager.set_parent_window(self.root)
        else:
            print("No files found in the specified folder path(s).")

    def show_deletes(self, deleted=False):
        self.clean_memory(["categories", "category_names", "image_files"])
        self.reset_search_option()
        self.deletion_manager.reload_deletion_files()
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

    def clean_memory(self, var_names, mode="empty", deep=False):
        """
        Clean or reset one or more attributes of the object.

        Parameters
        ----------
        var_names : str | list[str]
            The name(s) of the attribute(s) to clean.
        mode : str | callable, optional
            How to clean:
            - "none"   -> set to None
            - "empty"  -> set to empty type (list->[], dict->{}, str->"")
            - "delete" -> remove the attribute entirely
            - callable -> function that transforms the value
        deep : bool, optional
            If True and the attribute is a collection (list/dict/set),
            clear its contents in place instead of reassigning.
        """

        if isinstance(var_names, str):
            var_names = [var_names]

        for var_name in var_names:
            if not hasattr(self, var_name):
                continue

            value = getattr(self, var_name)

            if mode == "none":
                setattr(self, var_name, None)

            elif mode == "empty":
                if isinstance(value, list):
                    setattr(self, var_name, [] if not deep else value.clear() or value)
                elif isinstance(value, dict):
                    setattr(self, var_name, {} if not deep else value.clear() or value)
                elif isinstance(value, set):
                    setattr(self, var_name, set() if not deep else value.clear() or value)
                elif isinstance(value, str):
                    setattr(self, var_name, "")
                else:
                    setattr(self, var_name, None)

            elif mode == "delete":
                delattr(self, var_name)

            elif callable(mode):
                setattr(self, var_name, mode(value))

            else:
                raise ValueError(f"Unknown clean mode: {mode}")

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
        

    def get_files_from_table(self, all_files=True, folders=False):
        """
        Get file paths from the file_table.
        all_files: allow to get all the files from the table, even if the chunk is displayed.
        Returns a list of file paths.
        """
        file_paths = []
        if all_files and hasattr(self, "_all_files"):
            return [file[1] for file in self._all_files]

        # Not used currently
        if folders:
            return [(self.file_table.item(item, "values")[1], self.file_table.item(item, "values")[2])\
                      for item in self.file_table.get_children()]
        
        for item in self.file_table.get_children():
            file_path = self.file_table.item(item, "values")[2] if self.entry.get() != "show categories" else self.file_table.item(item, "values")[1]
            file_paths.append(file_path)
        return file_paths
    
    
    def display_caps(self):
        """Display screenshots with a loading screen (runs in background)."""
        self.reset_search_option(images=True)
        self.clean_memory(["video_files", "categories"], mode="empty")
        loading_win = self.show_loading_screen("Loading screenshots...\n " \
        "This may take a while for large image collections", width=350, height=150)

        def worker():
            try:
                self.image_files = VideoFileLoader.load_image_files() if not self.image_files else self.image_files

                def on_finish():
                    # self.image_files = image_files
                    self.total_files = len(self.image_files)
                    self.update_entry_text(SCREENSHOTS_FOLDER)
                    self.update_stats()
                    loading_win.destroy()
                    self.display_memory_usage()
                    self.insert_to_table(self.file_path_tuple(self.image_files))

                self.root.after(0, on_finish)

            except Exception as e:
                self.root.after(0, loading_win.destroy)
                print(f"Error while loading screenshots: {e}")

        threading.Thread(target=worker, daemon=True).start()

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

        category_window = CategoryWindow(self.root, selected_files, category_manager=self.category_manager, fingerprint_manager=self.fingerprint_manager)
        category_window.lift()
        category_window.focus_force()
        self.root.wait_window(category_window)
        self.category_manager._load_entries()

    def show_categories(self):
        """Show all categories and their file counts and sizes in the table, with loading screen."""
        self.reset_search_option(category=True)
        self.clean_memory(["image_files", "video_files", "category_names"], mode="empty")

        loading_win = self.show_loading_screen("Loading categories...")

        def worker():
            try:
                if not self.categories:
                    self.category_manager._load_entries()
                    self.categories = [cat for cat, _ in self.category_manager.get_all_categories_with_dates()]

                category_files = []
                total_files = 0
                total_size = 0

                def process_category(category):
                    """Process one category: count and total size."""
                    files = self.category_manager.get_category_files(category)
                    if not self.allow_deleted_on:
                        files = [f for f in files if os.path.exists(f)]
                    size = sum(get_file_size(f) for f in files)
                    return category, len(files), size

                with ThreadPoolExecutor(max_workers=8) as executor:
                    results = list(executor.map(process_category, self.categories))

                for category, count, size in results:
                    total_files += count
                    total_size += size
                    category_files.append((category, f"Contains {count} Files"))

                def on_finish():
                    self.file_table.delete(*self.file_table.get_children())

                    self.total_files = len(self.categories)
                    self.total_size = self.convert_bytes(total_size)
                    self.total_search_results = total_files
                    self.update_stats()
                    self.update_entry_text("show categories")

                    self.insert_to_table(category_files)

                    loading_win.destroy()

                self.root.after(0, on_finish)

            except Exception as e:
                self.root.after(0, loading_win.destroy)
                print(f"Error while loading categories: {e}")

        threading.Thread(target=worker, daemon=True).start()


def check_if_already_running():
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                pid = int(f.read())
            if psutil.pid_exists(pid):
                print(f"Another instance is already running. {pid}")
                return True
            else:
                print("Found stale lock, removing.")
                os.remove(LOCKFILE)
        except Exception:
            os.remove(LOCKFILE)

    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))
    return False

def cleanup_lockfile():
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)

def run_app():
    if check_if_already_running():
        sys.exit("App is already running!")
    root = tk.Tk()
    app = FileExplorerApp(root)
    root.mainloop()

if __name__ == "__main__":
    # cProfile.run('run_app()')
    tracemalloc.start()
    run_app()
    # import cProfile
    # cProfile.run('run_app()', 'gui_profile.prof')