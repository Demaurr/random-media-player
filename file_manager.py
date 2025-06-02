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

class FileManager:
    def __init__(self, parent_window=None):
        self.log_file = FILE_TRANSFER_LOG
        self.favorites = FavoritesManager()
        self.deletes = DeletionManager()
        self.categories = CategoryManager()
        if parent_window:
            self.deletes.set_parent_window(parent_window)
        self.logger = LogManager(LOG_PATH)
        create_csv_file(["Source Path", "Destination Path", "Status", "Date"], self.log_file)

    def move_file(self, src, dest):
        """
        Move a single file from src to dest, ensuring the source file exists and
        the destination directory is created if it doesn't exist.
        Also updates the deletion CSV and favorites paths if applicable.
        """
        try:
            if not os.path.isfile(src):
                raise FileNotFoundError(f"Source file not found: {src}")
            
            ensure_folder_exists(dest)
            if compare_folders(src, dest):
                print(f"Source and Destination is Same: {dest} {src}")
                return False
            
            dest_path = os.path.join(dest, os.path.basename(src))
            if os.path.exists(dest_path):
                dest_path = rename_if_exists(dest_path)

            shutil.move(src, dest_path)
            self.logger.update_logs('[FILE MOVED]', f"{src} -> {dest_path}")
            self.log_transfer(src, dest_path)
            self.deletes.update_file_name_in_csv(src, dest_path)
            print(f"File moved from {src} to {normalise_path(dest_path)}")
            if self.favorites.check_favorites(src):
                self.favorites.update_favorite_path(src, normalise_path(dest_path))

            file_categories = self.categories.get_file_categories(src)
            for category in file_categories:
                self.categories.remove_from_category(category, normalise_path(src))
                self.categories.add_to_category(category, normalise_path(dest_path))

            return True
        except FileNotFoundError as e:
            self.logger.error_logs(f"{e}")
            print(f"Error: {e}")
            return False
        except PermissionError as e:
            self.logger.error_logs(f"Permission denied when moving file: {src}. {e}")
            print(f"Permission denied when moving file: {src}")
            return False
        except Exception as e:
            self.logger.error_logs(f"An unexpected error occurred while moving {src}: {e}")
            print(f"An unexpected error occurred while moving {src}: {e}")
            return False

    def move_files(self, src_files, dest_folder):
        """
        Move multiple files to the destination folder, with error handling for each.
        """
        for file in src_files:
            success = self.move_file(file, dest_folder)
            if not success:
                print(f"Skipping file: {file} due to errors.")

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
