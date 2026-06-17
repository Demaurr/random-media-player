import os
import csv
import tkinter as tk
from collections import Counter, defaultdict
from send2trash import send2trash
from tkinter import filedialog
from static_methods import get_favs_folder, normalise_path, ensure_folder_exists, rename_if_exists, create_csv_file
from player_constants import FAV_FILES, DELETE_FILES_CSV, LOG_PATH, CSV_CONFIG
from logs_writer import LogManager
from favorites_manager import FavoritesManager
from datetime import datetime
import shutil
from custom_messagebox import showinfo, showwarning, showerror, askyesno
from deletion_mixins import DeletionStatsMixin

class DeletionManager(DeletionStatsMixin):
    def __init__(self, fav_manager, gui_parent=None):
        self.delete_csv = DELETE_FILES_CSV  
        self.headers = CSV_CONFIG[self.delete_csv]["headers"]
        self.fav_manager = fav_manager 
        self.logger = LogManager(LOG_PATH)
        self.deletion_files = self.read_csv_file()
        self.gui_parent = gui_parent
        self.parent_window = None
        self.message_window = self.parent_window
        self._ensure_csv_exists()

    def _ensure_csv_exists(self):
        create_csv_file(headers=self.headers, filename=self.delete_csv)

    def get_deletion_stats(self):
        """
        Returns summary statistics for deletion_files.
        """
        stats = {
            "total_entries": 0,
            "status_counts": {},
            "total_size_bytes": 0,
            "size_by_status": {},
            "existing_files": 0,
            "missing_files": 0,
            "unique_folders": 0,
            "largest_file": None,
            "largest_file_size": 0,
            "oldest_file": None,
            "newest_file": None,
        }

        status_counts = Counter()
        size_by_status = defaultdict(int)

        folders = set()
        largest_file = None
        largest_size = 0

        oldest_dt = None
        newest_dt = None
        oldest_file = None
        newest_file = None

        for file_path, metadata in self.deletion_files.items():

            stats["total_entries"] += 1

            status = metadata.get("status", "Unknown")
            size = metadata.get("size", 0)

            if not isinstance(size, int):
                size = 0

            status_counts[status] += 1
            size_by_status[status] += size
            stats["total_size_bytes"] += size

            folders.add(os.path.dirname(file_path))

            if os.path.exists(file_path):
                stats["existing_files"] += 1
            else:
                stats["missing_files"] += 1

            if size > largest_size:
                largest_size = size
                largest_file = file_path

            mod_time = metadata.get("mod_time")

            if mod_time and mod_time != "N/A":
                try:
                    dt = datetime.strptime(mod_time, "%Y-%m-%d %H:%M:%S")

                    if oldest_dt is None or dt < oldest_dt:
                        oldest_dt = dt
                        oldest_file = file_path

                    if newest_dt is None or dt > newest_dt:
                        newest_dt = dt
                        newest_file = file_path

                except Exception:
                    pass

        stats["status_counts"] = dict(status_counts)
        stats["size_by_status"] = dict(size_by_status)
        stats["unique_folders"] = len(folders)

        stats["largest_file"] = largest_file
        stats["largest_file_size"] = largest_size

        stats["oldest_file"] = oldest_file
        stats["newest_file"] = newest_file

        return stats

    def set_parent_window(self, parent):
        """Set the parent window for message boxes."""
        self.parent_window = parent

    def read_csv_file(self):
        """Reads the CSV file and returns a dictionary of file paths and their metadata."""
        file_status_dict = {}
        try:
            with open(self.delete_csv, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row and len(row) >= 4:
                        file_path = normalise_path(row[0])
                        status = row[1]
                        size = int(row[2]) if row[2] != 'N/A' else row[2]
                        mod_time = row[3]
                        file_status_dict[file_path] = {'status': status, 'size': size, 'mod_time': mod_time}
        except FileNotFoundError:
            pass
        return file_status_dict

    def write_csv_file(self, file_status_dict):
        """Writes the updated dictionary back to the CSV with size and modification datetime."""
        # headers = ["File Path", "Delete_Status", "File Size", "Modification Time"]
        headers = self.headers
        with open(self.delete_csv, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for file_path, metadata in file_status_dict.items():
                try:
                    writer.writerow([file_path, metadata['status'], metadata['size'], metadata['mod_time']])
                except Exception as e:
                    self.logger.error_logs(f"{e} occurred while moving {file_path} with data: {metadata}")
                    continue

    def get_deleted_file_size(self, file_path):
        """Returns the size of a file marked for deletion."""
        file_path = normalise_path(file_path)
        return self.deletion_files.get(file_path, {}).get('size', '0')


    def mark_for_deletion(self, video_file, status="ToDelete", skip_confirmation=False, commit=True):
        video_file = normalise_path(video_file)
        if not os.path.exists(video_file):
            showerror(self.message_window, "Error", f"File not found: {video_file}")
            return

        try:
            file_size = os.path.getsize(video_file)
            mod_time = datetime.fromtimestamp(os.path.getmtime(video_file)).strftime('%Y-%m-%d %H:%M:%S')

            if video_file in self.deletion_files:
                existing_status = self.deletion_files[video_file]['status']
                if existing_status == "ToDelete":
                    confirm_delete = askyesno(
                        self.message_window,
                        "File Already Marked",
                        f"{video_file} is already marked. Delete now?"
                    ) if not skip_confirmation else True

                    if confirm_delete:
                        if self.delete_file(video_file, self.deletion_files):
                            self.deletion_files[video_file]['status'] = "Deleted"
            else:
                self.deletion_files[video_file] = {
                    'status': status,
                    'size': file_size,
                    'mod_time': mod_time
                }
                self.logger.update_logs('[MARKED FOR DELETION]', video_file)

        except Exception as e:
            self.logger.error_logs(f"Error marking {video_file} for deletion: {e}")
            showerror(self.message_window, "Error", f"Error marking {video_file} for deletion: {e}")

        if commit:
            self.write_csv_file(self.deletion_files)

    def commit_changes(self):
        """Write in-memory deletion_files dict back to CSV once."""
        self.write_csv_file(self.deletion_files)

    def reload_deletion_files(self):
        self.deletion_files = self.read_csv_file()

    def remove_from_deletion(self, video_file):
        """Removes a file from the deletion list if it's marked for deletion."""
        video_file = normalise_path(video_file)

        if video_file in self.deletion_files:
            existing_status = self.deletion_files[video_file]['status']
            if existing_status == "ToDelete":
                del self.deletion_files[video_file]
                self.logger.update_logs('[REMOVED FROM DELETION]', video_file)
            elif existing_status == "Deleted":
                showinfo(self.message_window, "Already Deleted",
                        f"{video_file} is already deleted and cannot be undeleted.")

        self.commit_changes()

    def delete_files_in_csv(self, skip_confirmation=False):
        """Deletes files marked for deletion, offering options skipping for files in favorites."""

        if not skip_confirmation:
            confirm_delete = askyesno(self.message_window, "Confirm Deletion",
                                    "Are you sure you want to delete all marked files?")
            if not confirm_delete:
                showinfo(self.message_window, "Skipped", "Skipping Files marked for deletion.")
                return

        for file_path, metadata in list(self.deletion_files.items()):
            if metadata['status'] == "ToDelete":
                if self.fav_manager.check_favorites(current_file=file_path):
                    self.handle_favorites(file_path, self.deletion_files)
                else:
                    if self.delete_file(file_path, self.deletion_files, handle_favs=False):
                        self.deletion_files[file_path]['status'] = "Deleted"

        self.commit_changes()
        showinfo(self.message_window, "Deletion Complete", "All 'ToDelete' files have been processed.")

    def check_deleted(self):
        """Check if files marked as 'Deleted' are still present in the file system."""
        updated = False

        for file_path, metadata in self.deletion_files.items():
            if metadata['status'] == 'Deleted' and os.path.exists(file_path):
                self.deletion_files[file_path]['status'] = 'ToDelete'
                updated = True
                print(f"File {file_path} exists. Status reset to 'ToDelete'.")

            elif metadata['status'] == 'ToDelete' and not os.path.exists(file_path):
                self.deletion_files[file_path]['status'] = 'Deleted'
                updated = True
                print(f"File {file_path} doesn't exist. Status set to 'Deleted'.")

        if updated:
            self.commit_changes()
            self.logger.update_logs("[DELETED FILES UPDATED]",
                                    "Checked The Deleted Files Still Available.")
        else:
            showinfo(self.message_window, "No Updates",
                    "All files marked as 'Deleted' are no longer present in the file system.")

    def handle_favorites_move(self, file_path, file_status_dict):
        """Handles favorite files by either moving them to a folder or removing them from favorites."""
        if not self.fav_manager.check_favorites(file_path):
            return True
        
        move_to_favorites = askyesno(self.message_window, "File in Favorites", 
                                                f"{file_path} is in your favorites. Do you want to move it to the backup folder instead of deleting?")
        if move_to_favorites:
            default_favorites_folder = get_favs_folder()
            use_default_folder = askyesno(self.message_window, "Select Folder", 
                                                    f"Do you want to move the file to the default folder: {default_favorites_folder}?")

            if use_default_folder:
                self.move_file_to_folder(file_path, default_favorites_folder, file_status_dict)
                return False 
            else:
                new_folder = filedialog.askdirectory(title="Select Folder to Move Favorites")
                if new_folder:
                    self.move_file_to_folder(file_path, new_folder, file_status_dict)
                    return False
                else:
                    print(f"Skipping {file_path} as no folder was selected.")
                    return False
        else:
            self.remove_from_favorites_and_delete(file_path, file_status_dict)
            return True 

    def handle_favorites(self, file_path, file_status_dict):
        """Handles favorite files by asking whether to skip downloading them."""
        if not self.fav_manager.check_favorites(file_path):
            return True
        
        skip_download = askyesno(
            self.message_window,
            "File in Favorites",
            f"{file_path} is in your favorites.\nDo you want to skip deletion this file?"
        )

        if skip_download:
            print(f"[FILE SKIPPED] {file_path}")
            return False 
        else:
            return True

    def move_file_to_folder(self, file_path, folder, file_status_dict):
        """Moves a file to the specified folder."""
        ensure_folder_exists(folder)
        try:
            new_path = normalise_path(os.path.join(folder, os.path.basename(file_path)))
            if os.path.exists(new_path):
                new_path = rename_if_exists(new_path)
            shutil.move(file_path, new_path)
            file_status_dict[file_path]["status"] = "Moved to Favorites Backup"
            self.logger.update_logs('[FILE MOVED]', f"{file_path} to {new_path}")
            self.fav_manager.update_favorite_path(file_path, new_path)
        except Exception as e:
            self.logger.error_logs(f'Error moving {file_path}: {e}')
            print(f'Error moving {file_path}: {e}')

    def remove_from_favorites_and_delete(self, file_path, file_status_dict):
        """
        Removes a file from favorites and deletes it.
        For Now it will not Remove from favorites, but it will delete the file.
        """
        if self.delete_file(file_path, file_status_dict, handle_favs=False):
            file_status_dict[file_path]["status"] = "Deleted"
        self.logger.update_logs(f"[DELETED] from Favorites", file_path)

    def delete_file(self, file_path, file_status_dict, handle_favs=True, retry=False):
        """Deletes a file by moving it to the recycle bin, checking if it's in favorites first."""
        try:
            if handle_favs:
                if not self.handle_favorites(file_path, file_status_dict):
                    print(f"Skipping deletion of {file_path} because it's a favorite and not removed.")
                    return False
            
            send2trash(file_path)
            print(f"[FILE DELETED] {file_path} has been deleted.")
            self.logger.update_logs('[FILE DELETED]', file_path)
            return True
        
        except tk.TclError as e:
            if "bad window path name" in str(e):
                if not retry:
                    print("Updated the parent window reference due to TclError.")
                    self.parent_window = getattr(self, "gui_parent", None)
                    self.message_window = self.parent_window
                    return self.delete_file(file_path, file_status_dict, handle_favs, retry=True)
                else:
                    self.logger.error_logs(f"TclError persisted after retry for {file_path}: {e}")
            else:
                raise e
            
        except Exception as e:
            self.logger.error_logs(f'Error deleting {file_path} in delete_file: {e}')
            return False

    def update_file_name_in_csv(self, old_name, new_name):
        """Updates the file name in the CSV for a file marked 'ToDelete'."""
        old_name = normalise_path(old_name)
        new_name = normalise_path(new_name)
        
        file_status_dict = self.read_csv_file()

        if old_name in file_status_dict.keys():
            if file_status_dict[old_name]['status'] == "ToDelete":
                file_status_dict[new_name] = file_status_dict.pop(old_name)
                self.logger.update_logs('[DELETION-LIST UPDATED]: ', f"{old_name} -> {new_name}")
            else:
                print(f"{old_name} is not marked for deletion.")
        else:
            # print(f"{old_name} is not in the deletion list.")
            pass
        self.write_csv_file(file_status_dict)

    def refactor_csv(self):
        """Refactors the CSV file to include file size and modification time."""
        temp_file = self.delete_csv + ".tmp"  # Temporary file to store updated CSV content

        try:
            with open(self.delete_csv, mode='r', newline='', encoding='utf-8') as infile, \
                open(temp_file, mode='w', newline='', encoding='utf-8') as outfile:
                
                reader = csv.reader(infile)
                writer = csv.writer(outfile)
                
                for row in reader:
                    if row:
                        file_path = normalise_path(row[0])
                        status = row[1]
                        # Check if the file exists before trying to get its size and modification time
                        if len(row) < 4:
                            try:
                                size = os.path.getsize(file_path)
                                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                            except FileNotFoundError:
                                size = "N/A"
                                mod_time = "N/A"
                        else:
                            size = row[2]
                            mod_time = row[3]

                        writer.writerow([file_path, status, size, mod_time])

            os.replace(temp_file, self.delete_csv)
            print("CSV refactoring complete. New columns added: File Size, Modification Time.")

        except FileNotFoundError:
            print(f"CSV file {self.delete_csv} not found. No changes made.")

if __name__ == "__main__":
    from fingerprint_manager import MediaFingerprintManager
    from favorites_manager import FavoritesManager
    fm = MediaFingerprintManager()
    fav_manager = FavoritesManager(fingerprint_manager=fm)
    de = DeletionManager(fav_manager=fav_manager)
    print(de.get_deletion_stats())
    # de.refactor_csv()