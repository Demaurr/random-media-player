import os
import shutil
import csv
from datetime import datetime
from player_constants import FILE_TRANSFER_LOG, LOG_PATH
from favorites_manager import FavoritesManager
from deletion_manager import DeletionManager
from logs_writer import LogManager
from static_methods import create_csv_file, ensure_folder_exists, rename_if_exists, compare_folders, normalise_path
from category_manager import CategoryManager
from stats_manager import VideoStatsManager
from file_loader import VideoFileLoader
from notes_manager import NotesManager
import threading


class FileManager:
    def __init__(self, parent_window=None, favorites_manager=None, deletion_manager=None,
            category_manager=None, video_stats_manager=None, notes_manager=None):
        self.log_file = FILE_TRANSFER_LOG
        self.favorites = favorites_manager or FavoritesManager()
        self.deletes = deletion_manager or DeletionManager()
        self.categories = category_manager or CategoryManager()
        self.video_stats_manager = video_stats_manager or VideoStatsManager()
        self.file_loader = VideoFileLoader()
        self.notes_manager = notes_manager or NotesManager()
        if parent_window:
            self.deletes.set_parent_window(parent_window)
        self.logger = LogManager(LOG_PATH)
        create_csv_file(["Source Path", "Destination Path", "Status", "Date"], self.log_file)

    def move_file(self, src: str, dest: str) -> bool:
        try:
            dest_path = self._validate_and_prepare(src, dest)
            if dest_path is None:
                return False

            shutil.move(src, dest_path)
            dest_src = normalise_path(dest) # currently no use
            self._apply_post_move_hooks(src, normalise_path(dest_path), dest_src)
            # print(f"File moved from {src} to {normalise_path(dest_path)}")
            return True

        except FileNotFoundError as e:
            self.logger.error_logs(str(e))
            print(f"[Error] {e}")
            return False

        except PermissionError as e:
            self.logger.error_logs(f"Permission denied: {e}")
            print(f"[Permission denied] {e}")
            return False

        except Exception as e:
            self.logger.error_logs(f"Unexpected error: {e}")
            print(f"[Unexpected error] {e}")
            return False

        
    def _validate_and_prepare(self, src: str, dest_dir: str) -> str | None:
        """
        Returns the final destination path if valid, or None if the move should be skipped
        (e.g., same source and destination folder).
        """
        if not os.path.isfile(src):
            # raise FileNotFoundError(f"Source file not found: {src}")
            print(f"[File Not Found]: {src}")
            self.logger.error_logs(f"Source file not found: {src}")
            return None

        ensure_folder_exists(dest_dir)

        if compare_folders(src, dest_dir):
            print(f"[Skipping] (same folder): {src} → {dest_dir}")
            return None

        filename = os.path.basename(src)
        dest_path = os.path.join(dest_dir, filename)

        if os.path.exists(dest_path):
            dest_path = rename_if_exists(dest_path)

        return normalise_path(dest_path)



    def _apply_post_move_hooks(self, old_src, new_src, dest):
        for hook in [
            self._log_move,
            self._update_csv_log,
            self._update_deletes,
            self._update_favorites,
            self._update_categories,
            self._update_stats,
            self._update_notes_key,
            # self._reload_folder_async,
        ]:
            try:
                hook(old_src, new_src)
            except Exception as e:
                self.logger.error_logs(f"{hook.__name__} failed: {e}")

        
    def _log_move(self, old_src, new_src):
        self.logger.update_logs('[FILE MOVED]', f"{old_src} -> {new_src}")

    def _update_csv_log(self, old_src, new_src):
        self.log_transfer(old_src, new_src)

    def _update_deletes(self, old_src, new_src):
        self.deletes.update_file_name_in_csv(old_src, new_src)

    def _update_favorites(self, old_src, new_src):
        if self.favorites.check_favorites(old_src):
            self.favorites.update_favorite_path(old_src, new_src)

    def _update_categories(self, old_src, new_src):
        categories = self.categories.get_file_categories(old_src)
        for cat in categories:
            self.categories.remove_from_category(cat, old_src)
            self.categories.add_to_category(cat, new_src)

    def _update_stats(self, old_src, new_src):
        old_size = os.path.getsize(new_src)
        self.video_stats_manager.delete_stat(old_src, old_size)
        self.video_stats_manager.add_stats(new_src)

    def _update_notes_key(self, old_src, new_src):
        if self.notes_manager:
            self.notes_manager.update_note_key(old_src, new_src)

    def _reload_folder_async(self, old_src, new_src):
        dest_folder = os.path.dirname(new_src)
        threading.Thread(
            target=self.file_loader.add_folder_data_csv,
            args=([dest_folder],),
            daemon=True
        ).start()


    def move_files(self, src_files, dest_folder):
        """
        Move multiple files to the destination folder, with error handling for each.
        Reloads the folder only once at the end for performance.
        """
        src_folders = set()
        any_success = False
        for idx, file in enumerate(src_files):
            src_folders.add(normalise_path(os.path.dirname(file)))
            print(f"[Moving] {idx + 1}/ {len(src_files)}")
            success = self.move_file(file, dest_folder)
            if success:
                any_success = True

        folders_to_reload = [normalise_path(dest_folder)] + list(src_folders)
        # print(folders_to_reload)
        if any_success:
            threading.Thread(
                target=self.file_loader.add_folder_data_csv,
                args=(folders_to_reload,),
                daemon=True
            ).start()


    def log_transfer(self, src, dest, action="MOVED"):
        """
        Log the file transfer details into a CSV file. If the log file doesn't exist, create it.
        """
        try:
            with open(self.log_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([src, dest, action, datetime.now()])
        except Exception as e:
            self.logger.error_logs(f"Error logging the file transfer: {e}")
            print(f"Error logging the file transfer: {e}")

    def ensure_csv_headers(self):
        """
        Ensure the CSV log file exists and has the required headers.
        If the file doesn't exist, create it and add the headers.
        """
        if not os.path.isfile(self.log_file):
            try:
                with open(self.log_file, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["Source Path", "Destination Path", "Status", "Date"])
                self.logger.update_logs("[LOG FILE CREATED]", f"Log file created with headers: {self.log_file}")
                print(f"Log file created with headers: {self.log_file}")
            except Exception as e:
                self.logger.error_logs(f"Error creating log file: {e}")
                print(f"Error creating log file: {e}")
