import os
import shutil
import csv
from datetime import datetime
from typing import Dict, List
from description_manager import DescriptionManager
from fingerprint_manager import MediaFingerprintManager
from player_constants import FILE_TRANSFER_LOG, LOG_PATH, CSV_CONFIG
from favorites_manager import FavoritesManager
from deletion_manager import DeletionManager
from logs_writer import LogManager
from static_methods import create_csv_file, ensure_folder_exists, rename_if_exists, compare_folders, normalise_path
from category_manager import CategoryManager
from stats_manager import VideoStatsManager
from file_loader import VideoFileLoader
from notes_manager import NotesManager
from task_manager import TaskManager
import threading


class FileManager:
    def __init__(self, parent_window=None, favorites_manager=None, deletion_manager=None,
            category_manager=None, video_stats_manager=None, notes_manager=None, description_manager=None,
            fingerprint_manager=None, task_manager=None):
        self.log_file = FILE_TRANSFER_LOG
        self._headers = CSV_CONFIG[self.log_file]["headers"]
        
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self.favorites = favorites_manager or FavoritesManager(fingerprint_manager=self.fingerprint_manager)
        self.deletes = deletion_manager or DeletionManager(favorites_manager=self.favorites)
        if parent_window:
            self.deletes.set_parent_window(parent_window)
        self.categories = category_manager or CategoryManager(fingerprint_manager=self.fingerprint_manager)
        self.video_stats_manager = video_stats_manager or VideoStatsManager()
        self.file_loader = VideoFileLoader()
        self.notes_manager = notes_manager or NotesManager()
        self.description_manager = description_manager or DescriptionManager()
        self.task_manager = task_manager or TaskManager(root=self.parent, max_workers=4)
        
        self.logger = LogManager(LOG_PATH)
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        create_csv_file(self._headers, self.log_file)

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
            print(f"[Skipping] (same folder): {src} -> {dest_dir}")
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
            self._update_description,
            self._update_fingerprint_path,
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
        success = self.categories.update_file_path(old_src, new_src)
        if not success:
            self.logger.error_logs(f"Failed to update categories for: {old_src}")

    def _update_stats(self, old_src, new_src):
        old_size = os.path.getsize(new_src)
        self.video_stats_manager.add_stats(new_src)
        # self.video_stats_manager.delete_stat(old_src, old_size)
        pass
    
    def _update_description(self, old_src, new_src):
        if self.description_manager:
            self.description_manager.update_video_path(old_src, new_src)

    def _update_notes_key(self, old_src, new_src):
        if self.notes_manager:
            self.notes_manager.update_note_key(old_src, new_src)

    def _update_fingerprint_path(self, old_src, new_src):
        """
        Update the file path in MediaFingerprintManager if the file has a fingerprint entry.
        """
        if not hasattr(self, "fingerprint_manager"):
            return

        entry = self.fingerprint_manager.get_path_info_by_file(old_src)
        if entry:
            unique_id = entry["unique_id"]
            self.fingerprint_manager.update_path_info_byid(unique_id, new_src)

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
        if any_success:
            self.task_manager.add_task(self.file_loader.add_folder_data_csv, folders_to_reload, threaded=True)
            self.task_manager.add_task(self.video_stats_manager.create_stats, threaded=True)
            self.task_manager.add_task(self.fingerprint_manager.flush, threaded=True)
            self.categories._write_entries()


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

    def auto_detect_external_moves(self, discovered_files: List[str]) -> Dict[str, str]:
        """
        Unused for now.
        Auto-detect files that were moved outside the app and add them to transfer_log.
        
        Logic:
        - Takes discovered files that exist (e.g., in dir B after external move)
        - Gets their fingerprints
        - Finds all known paths for that fingerprint
        - If there's a previous path (from dir A) not in transfer log yet
        - Adds entry: old_path → new_path (AUTO_RECOVERED)
        - This keeps get_all_related_paths() connected despite external moves
        
        Args:
            discovered_files: List of file paths that currently exist (from file loader)
        
        Returns:
            dict: {old_path: new_path} for files that were auto-recovered
        """
        recovered = {}
        
        for file_path in discovered_files:
            file_path = normalise_path(file_path)
            
            index_hash = self.fingerprint_manager.get_index_hash_by_path(file_path)
            if not index_hash:
                continue
            all_known_paths = self.fingerprint_manager.get_paths_by_hash(index_hash)
            
            alternative_paths = [p for p in all_known_paths if normalise_path(p) != file_path]
            
            if not alternative_paths:
                continue  

            for old_path in alternative_paths:
                old_path = normalise_path(old_path)
                
                if self._is_path_in_transfer_log(old_path):
                    continue
                
                if os.path.exists(old_path):
                    continue

                self.log_transfer(old_path, file_path, action="AUTO_RECOVERED")
                recovered[old_path] = file_path
                self.logger.update_logs("[AUTO_RECOVERED]", 
                                    f"{old_path} -> {file_path}")
        
        self.fingerprint_manager.flush()
        return recovered

    def _is_path_in_transfer_log(self, file_path: str) -> bool:
        """
        Unused for now.
        Check if a path already exists as Source Path in the transfer log.
        """
        file_path = normalise_path(file_path)
        try:
            with open(self.log_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if normalise_path(row.get('Source Path', '')) == file_path:
                        return True
        except FileNotFoundError:
            pass
        return False

    def auto_reconcile_on_refresh(self, discovered_files: List[str]) -> Dict[str, str]:
        """
        Unused for now.
        Wrapper method to be called during GUI refresh operations.
        Combines external move detection with broken link recovery.
        
        This runs after file discovery, before displaying results.
        
        Args:
            discovered_files: Files discovered in the current refresh
        
        Returns:
            dict: Summary of auto-recovered files
        """
        external_moves = self.auto_detect_external_moves(discovered_files)
        
        if external_moves:
            self.logger.update_logs("[AUTO RECONCILE]", 
                                f"Auto-recovered {len(external_moves)} externally-moved file(s)")
            print(f"[AUTO RECONCILE] Recovered {len(external_moves)} files from external moves")
        
        return external_moves
    
