import os
import csv
from send2trash import send2trash
from tkinter import messagebox, filedialog
from static_methods import get_favs_folder, normalise_path, ensure_folder_exists, rename_if_exists
from player_constants import FAV_FILES, DELETE_FILES_CSV, LOG_PATH
from logs_writer import LogManager
from favorites_manager import FavoritesManager
from datetime import datetime
import shutil

class DeletionManager:
    def __init__(self):
        self.delete_csv = DELETE_FILES_CSV  
        self.fav_manager = FavoritesManager(FAV_FILES) 
        self.logger = LogManager(LOG_PATH)  

    def read_csv_file(self):
        """Reads the CSV file and returns a dictionary of file paths and their metadata."""
        file_status_dict = {}
        try:
            with open(self.delete_csv, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    # Make sure to check if the row is not empty and has enough columns
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
        headers = ["File Path", "Delete_Status", "File Size", "Modification Time"]
        with open(self.delete_csv, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for file_path, metadata in file_status_dict.items():
                try:
                    writer.writerow([file_path, metadata['status'], metadata['size'], metadata['mod_time']])
                except Exception as e:
                    self.logger.error_logs(f"{e} occurred while moving {file_path} with data: {metadata}")
                    continue

    def mark_for_deletion(self, video_file, status="ToDelete"):
        """Marks a video file for deletion by adding it to the CSV with size and datetime."""
        video_file = normalise_path(video_file)
        file_status_dict = self.read_csv_file()

        file_size = os.path.getsize(video_file)
        mod_time = datetime.fromtimestamp(os.path.getmtime(video_file)).strftime('%Y-%m-%d %H:%M:%S')

        if video_file in file_status_dict:
            existing_status = file_status_dict[video_file]['status']
            if existing_status == "ToDelete":
                confirm_delete = messagebox.askyesno("File Already Marked", 
                                                     f"{video_file} is already marked for deletion. Do you want to delete it now?")
                if confirm_delete:
                    if self.delete_file(video_file, file_status_dict):
                        file_status_dict[video_file]['status'] = "Deleted"
                        # self.logger.update_logs('[FILE DELETED]', video_file)
        else:
            file_status_dict[video_file] = {'status': status, 'size': file_size, 'mod_time': mod_time}
            self.logger.update_logs('[MARKED FOR DELETION]', video_file)

        self.write_csv_file(file_status_dict)

    def remove_from_deletion(self, video_file):
        """Removes a file from the deletion list if it's marked for deletion."""
        video_file = normalise_path(video_file)
        file_status_dict = self.read_csv_file()

        if video_file in file_status_dict:
            existing_status = file_status_dict[video_file]['status']
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
                messagebox.showinfo("Skipped", "Skipping Files marked for deletion.")
                return

        file_status_dict = self.read_csv_file()

        for file_path, metadata in file_status_dict.items():
            if metadata['status'] == "ToDelete":
                if self.fav_manager.check_favorites(current_file=file_path):
                    self.handle_favorites(file_path, file_status_dict)
                else:
                    self.delete_file(file_path, file_status_dict, handle_favs=False)
                    file_status_dict[file_path]['status'] = "Deleted"

        self.write_csv_file(file_status_dict)
        messagebox.showinfo("Deletion Complete", "All 'ToDelete' files have been processed.")

    def check_deleted(self):
        """
        Check if files marked as 'Deleted' are still present in the file system. 
        If found, reset their status to 'ToDelete'.
        """
        file_status_dict = self.read_csv_file()
        updated = False

        for file_path, metadata in file_status_dict.items():
            if metadata['status'] == 'Deleted' and os.path.exists(file_path):
                # File marked as deleted but still exists, reset status
                file_status_dict[file_path]['status'] = 'ToDelete'
                updated = True
                print(f"File {file_path} exists. Status reset to 'ToDelete'.")
            elif metadata['status'] == 'ToDelete' and not os.path.exists(file_path):
                file_status_dict[file_path]['status'] = 'Deleted'
                updated = True
                print(f"File {file_path} doesn't exist. Status set to 'Deleted'.")

        if updated:
            self.write_csv_file(file_status_dict)
            print("CSV updated with files reset to 'ToDelete'.")
            self.logger.update_logs("[DELETED FILES UPDATED]", f"Checked The Deleted Files Still Available.")
        else:
            print("No updates required; all deleted files are missing.")



    def handle_favorites(self, file_path, file_status_dict):
        """Handles favorite files by either moving them to a folder or removing them from favorites."""
        if not self.fav_manager.check_favorites(file_path):
            return True
        
        move_to_favorites = messagebox.askyesno("File in Favorites", 
                                                f"{file_path} is in your favorites. Do you want to move it to the backup folder instead of deleting?")
        if move_to_favorites:
            default_favorites_folder = get_favs_folder()
            use_default_folder = messagebox.askyesno("Select Folder", 
                                                    f"Do you want to move the file to the default folder: {default_favorites_folder}?")

            if use_default_folder:
                self.move_file_to_folder(file_path, default_favorites_folder, file_status_dict)
                return False 
            else:
                # Ask the user for a new folder if they don't want to use the default one
                new_folder = filedialog.askdirectory(title="Select Folder to Move Favorites")
                if new_folder:
                    self.move_file_to_folder(file_path, new_folder, file_status_dict)
                    return False
                else:
                    print(f"Skipping {file_path} as no folder was selected.")
                    return False
        else:
            # If the user does not want to move the file, remove it from favorites and mark for deletion
            self.remove_from_favorites_and_delete(file_path, file_status_dict)
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
        # self.fav_manager.delete_from_favorites(file_path) # skipping the deletion from fav files
        if self.delete_file(file_path, file_status_dict, handle_favs=False):
            file_status_dict[file_path]["status"] = "Deleted"
        self.logger.update_logs(f"[DELETED] from Favorites", file_path)

    def delete_file(self, file_path, file_status_dict, handle_favs=True):
        """Deletes a file by moving it to the recycle bin, checking if it's in favorites first."""
        try:
            # Use handle_favorites to decide how to handle favorites
            if handle_favs:
                if not self.handle_favorites(file_path, file_status_dict):
                    print(f"Skipping deletion of {file_path} because it's a favorite and not removed.")
                    return False
            
            send2trash(file_path)
            print(f"[FILE DELETED] {file_path} has been deleted.")
            self.logger.update_logs('[FILE DELETED]', file_path)
            return True
            
        except Exception as e:
            self.logger.error_logs(f'Error deleting {file_path}: {e}')
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
            print(f"{old_name} is not in the deletion list.")
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
    de = DeletionManager()
    de.refactor_csv()