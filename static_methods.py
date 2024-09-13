import csv
import os
from tkinter import messagebox
from send2trash import send2trash
from player_constants import DELETE_FILES_CSV, LOG_PATH
from logs_writer import LogManager

logger = LogManager(LOG_PATH)

def create_csv_file(headers=None, filename="New_CSV.csv"):
    if os.path.exists(filename):
        print("Deletion File Already Exists...")
        return 
    # If no headers are provided, create three random headers
    if headers is None:
        headers = ["Heading_1", "Heading_2", "Heading_3"]
    
    # Write the headers to the CSV file
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
    
    print(f"CSV file '{filename}' created with headers: {headers}")

def normalise_path(path):
        return path.replace("/", "\\")

def mark_for_deletion(video_file, status="ToDelete", event=None):
    """Marks the given video file for deletion by adding it to the CSV, avoiding duplicates."""
    video_file = normalise_path(video_file)

    # Read existing entries into a dictionary
    file_status_dict = {}
    try:
        with open(DELETE_FILES_CSV, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row and row[0]:  # Ensure it's not an empty row
                    file_status_dict[normalise_path(row[0])] = row[1]  # Store file path and status
    except FileNotFoundError:
        # If the file doesn't exist, continue without raising an error (will be created on write)
        pass

    # Check if the video file is already in the CSV
    if video_file in file_status_dict:
        existing_status = file_status_dict[video_file]
        if existing_status == "ToDelete":
            # Ask the user if they want to delete the file since it's already marked
            confirm_delete = messagebox.askyesno("File Already Marked", 
                                                 f"{video_file} is already marked for deletion. Do you want to delete it now?")
            if confirm_delete:
                # Proceed to delete the file
                send2trash(video_file)
                print(f"{video_file} has been deleted.")
                file_status_dict[video_file] = "Deleted"  # Update status to Deleted
                logger.update_logs('[FILE DELETED]', video_file)
    else:
        # If the file is not marked, add the new entry
        file_status_dict[video_file] = status
        logger.update_logs('[MARKED FOR DELETION]', video_file)
    
    # Write the updated dictionary back to the CSV
    with open(DELETE_FILES_CSV, mode='w', newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        for file_path, file_status in file_status_dict.items():
            writer.writerow([file_path, file_status])
        print(f"{video_file} marked for deletion with status: {status}.")


def remove_from_deletion(video_file, event=None):
    """Removes the given video file from the deletion list if marked for deletion (ToDelete).
       Notifies if the file is already deleted and cannot be undeleted."""
    video_file = normalise_path(video_file)

    # Read existing entries into a dictionary
    file_status_dict = {}
    try:
        with open(DELETE_FILES_CSV, mode='r', newline='', encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row and row[0]:  # Ensure it's not an empty row
                    file_status_dict[row[0]] = row[1]  # Store file path and status
    except FileNotFoundError:
        # If the file doesn't exist, continue without raising an error (will be created on write)
        pass

    # Check if the video file is in the dictionary
    if video_file in file_status_dict:
        existing_status = file_status_dict[video_file]
        if existing_status == "ToDelete":
            # Remove from the deletion list
            del file_status_dict[video_file]
            print(f"{video_file} has been removed from the deletion list.")
            logger.update_logs('[REMOVED FROM DELETION]', video_file)
        elif existing_status == "Deleted":
            # Notify the user that the file is already deleted
            messagebox.showinfo("Already Deleted", f"{video_file} is already deleted and cannot be undeleted.")
            print(f"{video_file} is already deleted.")
    else:
        # If the file is not in the deletion list, do nothing
        print(f"{video_file} is not in the deletion list.")

    # Write the updated dictionary back to the CSV
    with open(DELETE_FILES_CSV, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for file_path, file_status in file_status_dict.items():
            writer.writerow([file_path, file_status])

def ensure_folder_exists(folder_path):
        """
        Checks whether a folder exists at the specified path.
        If it doesn't exist, creates the folder.
        
        Parameters:
            folder_path (str): The path of the folder to check/create.
            
        Returns:
            None
        """
        if not os.path.exists(folder_path):  # Check if folder doesn't exist
            try:
                os.makedirs(folder_path)  # Create the folder and any missing parent directories
                print(f"Folder created at {folder_path}")
            except OSError as e:
                print(f"Error creating folder at {folder_path}: {e}")
        else:
            print(f"Folder already exists at {folder_path}")
            return True