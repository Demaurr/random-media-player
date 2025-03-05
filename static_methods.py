import csv
from datetime import datetime
import os
import re
from tkinter import messagebox
from send2trash import send2trash
from player_constants import DELETE_FILES_CSV, FILES_FOLDER, LOG_PATH
from logs_writer import LogManager

logger = LogManager(LOG_PATH)

def create_csv_file(headers=None, filename="New_CSV.csv"):
    if os.path.exists(filename):
        print(f"{filename} File Already Exists...")
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

def get_favs_folder():
    """
    Reads the favorite folder path from Extra_Paths.txt.
    Expected format: FAV_FOLDER: E:\\New folder\\New folder (2)\\
    """
    with open(FILES_FOLDER + "\\" + "Extra_Paths.txt", "r", encoding='utf-8') as file:
        for line in file:
            if line.startswith("FAV_FOLDER:"):
                # Split only on the first occurrence of ':'
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
    return None  # Return None if the FAV_FOLDER entry is not found

def mark_for_deletion(video_file, status="ToDelete", event=None):
    """
    Deprecated: Use deletion_manager for this
    Marks the given video file for deletion by adding it to the CSV, avoiding duplicates.
    """
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
    """
    Deprecated: Use deletion_manager for this
    Removes the given video file from the deletion list if marked for deletion (ToDelete).
       Notifies if the file is already deleted and cannot be undeleted.
    """
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
                return True
            except OSError as e:
                print(f"Error creating folder at {folder_path}: {e}")
                return True
        else:
            print(f"Folder already exists at {folder_path}")
            return True

def rename_if_exists(filename):
    base_name, extension = os.path.splitext(filename)
    base_name = remove_number_suffix(base_name)  # Remove (number) suffix if exists
    counter = 1
    new_filename = filename
    
    while os.path.exists(new_filename):
        new_filename = f"{base_name}({counter}){extension}"
        counter += 1

    return new_filename

def remove_number_suffix(basename):
    match = re.match(r'^(.*?)\(\d+\)$', basename)
    if match:
        return match.group(1)
    return basename

def get_file_size(file_path):
    """
    Returns the size of the file in bytes.
    
    :param file_path: The path to the file.
    :return: The size of the file in bytes, or None if the file does not exist.
    """
    try:
        return os.path.getsize(file_path)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    
def convert_date_format(file_path):
    """
    Updates the date format in the 'Date Watched' column of a CSV file.
    Input format: 'M/d/yyyy H:m'
    Output format: 'yyyy-MM-dd H:m:ss'
    Used in Watched_history csv file
    """
    rows = []
    row_count = 0

    with open(file_path, 'r', encoding='utf-8') as input_csv:
        reader = csv.DictReader(input_csv)
        for row in reader:
            row_count += 1
            try:
                # Convert the date string to a datetime object
                date_watched = datetime.strptime(row['Date Watched'], '%m/%d/%Y %H:%M')

                # Convert the datetime object to the desired format
                row['Date Watched'] = datetime.strftime(date_watched, '%Y-%m-%d %H:%M:%S')

                # Add the updated row to the list
                rows.append(row)
            except ValueError:
                rows.append(row)
                print(f"Warning: Invalid date format in row {row_count}. Skipping: {row['Date Watched']}")
                continue

    # Overwrite the original file with the updated rows
    with open(file_path, 'w', newline='', encoding='utf-8') as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Date format update complete. File: {file_path}")