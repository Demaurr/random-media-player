import os
import csv
from send2trash import send2trash
from tkinter import messagebox, filedialog
from static_methods import get_favs_folder, normalise_path, ensure_folder_exists
from player_constants import DEFAULT_FAV, DELETE_FILES_CSV, FILES_FOLDER, LOG_PATH
from logs_writer import LogManager
from favorites_manager import FavoritesManager

class DeletionManager:
    def __init__(self):
        self.delete_csv = DELETE_FILES_CSV  # Path to the CSV file tracking deletions
        self.fav_manager = FavoritesManager(DEFAULT_FAV)  # FavoritesManager instance
        self.logger = LogManager(LOG_PATH)  # Logger instance for logging operations

    def read_csv_file(self):
        """Reads the CSV file and returns a dictionary of file paths and statuses."""
        file_status_dict = {}
        try:
            with open(self.delete_csv, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[0]:  # Ensure it's not an empty row
                        file_status_dict[normalise_path(row[0])] = row[1]
        except FileNotFoundError:
            # File will be created later if it doesn't exist
            pass
        return file_status_dict

    def write_csv_file(self, file_status_dict):
        """Writes the updated dictionary back to the CSV."""
        with open(self.delete_csv, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for file_path, file_status in file_status_dict.items():
                writer.writerow([file_path, file_status])

    def mark_for_deletion(self, video_file, status="ToDelete"):
        """Marks a video file for deletion by adding it to the CSV."""
        video_file = normalise_path(video_file)
        file_status_dict = self.read_csv_file()

        if video_file in file_status_dict:
            existing_status = file_status_dict[video_file]
            if existing_status == "ToDelete":
                confirm_delete = messagebox.askyesno("File Already Marked", 
                                                     f"{video_file} is already marked for deletion. Do you want to delete it now?")
                if confirm_delete:
                    if self.delete_file(video_file):
                        file_status_dict[video_file] = "Deleted"
                        self.logger.update_logs('[FILE DELETED]', video_file)
        else:
            file_status_dict[video_file] = status
            self.logger.update_logs('[MARKED FOR DELETION]', video_file)

        self.write_csv_file(file_status_dict)

    def remove_from_deletion(self, video_file):
        """Removes a file from the deletion list if it's marked for deletion."""
        video_file = normalise_path(video_file)
        file_status_dict = self.read_csv_file()

        if video_file in file_status_dict:
            existing_status = file_status_dict[video_file]
            if existing_status == "ToDelete":
                del file_status_dict[video_file]
                self.logger.update_logs('[REMOVED FROM DELETION]', video_file)
            elif existing_status == "Deleted":
                messagebox.showinfo("Already Deleted", f"{video_file} is already deleted and cannot be undeleted.")
        else:
            print(f"{video_file} is not in the deletion list.")

        self.write_csv_file(file_status_dict)

    def delete_files_in_csv(self, skip_confirmation=False): 
        """Deletes or moves files marked for deletion, offering options for files in favorites."""
        
        # Check if confirmation should be skipped
        if not skip_confirmation:
            confirm_delete = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete all marked files?")
            if not confirm_delete:
                messagebox.showinfo("SKipped", "Skipping Files marked for deletion.")
                return

        file_status_dict = self.read_csv_file()

        for file_path, status in file_status_dict.items():
            if status == "ToDelete":
                if self.fav_manager.check_favorites(current_file=file_path):
                    self.handle_favorites(file_path, file_status_dict)
                else:
                    self.delete_file(file_path, handle_favs=False)
                    file_status_dict[file_path] = "Deleted"

        self.write_csv_file(file_status_dict)
        messagebox.showinfo("Deletion Complete", "All 'ToDelete' files have been processed.")


    def handle_favorites(self, file_path, file_status_dict):
        """Handles favorite files by either moving them to a folder or removing them from favorites."""
        # Ask the user if they want to move the favorite file instead of deleting
        move_to_favorites = messagebox.askyesno("File in Favorites", 
                                                f"{file_path} is in your favorites. Do you want to move it to the backup folder instead of deleting?")
        if move_to_favorites:
            # Get the default favorites folder
            default_favorites_folder = ensure_folder_exists(get_favs_folder())
            use_default_folder = messagebox.askyesno("Select Folder", 
                                                    f"Do you want to move the file to the default folder: {default_favorites_folder}?")

            if use_default_folder:
                self.move_file_to_folder(file_path, default_favorites_folder, file_status_dict)
                self.remove_from_deletion(file_path)
                return False  # Indicating that the file was moved, not deleted
            else:
                # Ask the user for a new folder if they don't want to use the default one
                new_folder = filedialog.askdirectory(title="Select Folder to Move Favorites")
                if new_folder:
                    self.move_file_to_folder(file_path, new_folder, file_status_dict)
                    return False  # File was moved, not deleted
                else:
                    print(f"Skipping {file_path} as no folder was selected.")
                    return False  # No folder was selected, so no deletion happens
        else:
            # If the user does not want to move the file, remove it from favorites and mark for deletion
            self.remove_from_favorites_and_delete(file_path, file_status_dict)
            return True  # File can now be deleted

    def move_file_to_folder(self, file_path, folder, file_status_dict):
        """Moves a file to the specified folder."""
        ensure_folder_exists(folder)
        try:
            new_path = os.path.join(folder, os.path.basename(file_path))
            os.rename(file_path, new_path)
            file_status_dict[file_path] = "Moved to Favorites Backup"
            self.logger.update_logs('[FILE MOVED]', f"{file_path} to {new_path}")
            self.fav_manager.update_favorite_path(file_path, new_path)
        except Exception as e:
            self.logger.error_logs(f'Error moving {file_path}: {e}')
            print(f'Error moving {file_path}: {e}')

    def remove_from_favorites_and_delete(self, file_path, file_status_dict):
        """Removes a file from favorites and deletes it."""
        self.fav_manager.delete_from_favorites(file_path)
        if self.delete_file(file_path, handle_favs=False):
            file_status_dict[file_path] = "Deleted"

    def delete_file(self, file_path, handle_favs=True):
        """Deletes a file by moving it to the recycle bin, checking if it's in favorites first."""
        try:
            # Use handle_favorites to decide how to handle favorites
            if handle_favs:
                file_status_dict = self.read_csv_file()
                if not self.handle_favorites(file_path, file_status_dict):
                    print(f"Skipping deletion of {file_path} because it's a favorite and not removed.")
                    return False
            
            # Proceed with file deletion
            send2trash(file_path)
            print(f"[FILE DELETED] {file_path} has been deleted.")
            self.logger.update_logs('[FILE DELETED]', file_path)
            return True
            
        except Exception as e:
            self.logger.error_logs(f'Error deleting {file_path}: {e}')