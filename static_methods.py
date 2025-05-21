import csv
from datetime import datetime
import os
import re
from player_constants import ALL_MEDIA_CSV, DELETE_FILES_CSV, FILES_FOLDER, FOLDER_LOGS, LOG_PATH
from logs_writer import LogManager

logger = LogManager(LOG_PATH)

def create_csv_file(headers=None, filename="New_CSV.csv"):
    if os.path.exists(filename):
        print(f"{filename} File Exists...")
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
    Expected format: FAV_FOLDER: E:\\New folder\\New folder (2)\\Or something
    Returns:
        str: The favorite folder path if found, otherwise None.
    """
    with open(FILES_FOLDER + "\\" + "Extra_Paths.txt", "r", encoding='utf-8') as file:
        for line in file:
            if line.startswith("FAV_FOLDER:"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
    return None 

def ensure_folder_exists(folder_path):
        """
        Checks whether a folder exists at the specified path.
        If it doesn't exist, creates the folder.
        
        Parameters:
            folder_path (str): The path of the folder to check/create.
            
        Returns:
            None
        """
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)  # Create the folder and any missing parent directories
                print(f"Folder created at {folder_path}")
                return True
            except OSError as e:
                print(f"Error creating folder at {folder_path}: {e}")
                return True
        else:
            # print(f"Folder already exists at {folder_path}")
            return True

def rename_if_exists(filename):
    base_name, extension = os.path.splitext(filename)
    base_name = remove_number_suffix(base_name)
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
        return 0
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 0
    
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
                date_watched = datetime.strptime(row['Date Watched'], '%m/%d/%Y %H:%M')

                row['Date Watched'] = datetime.strftime(date_watched, '%Y-%m-%d %H:%M:%S')
                rows.append(row)
                
            except ValueError:
                rows.append(row)
                print(f"Warning: Invalid date format in row {row_count}. Skipping: {row['Date Watched']}")
                continue

    with open(file_path, 'w', newline='', encoding='utf-8') as output_csv:
        writer = csv.DictWriter(output_csv, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Date format update complete. File: {file_path}")


def compare_folders(filepath, folderpath):
    file_directory = os.path.dirname(filepath)
    print(file_directory)
    
    file_directory = os.path.normpath(file_directory)
    folderpath = os.path.normpath(folderpath)
    
    # Compare the paths
    if file_directory == folderpath:
        print("The folders match!")
        return True
    else:
        # print("The folders don't match!")
        # print(f"File directory: {file_directory}")
        # print(f"Folder path: {folderpath}")
        return False
    
def gather_all_media():
    LOG_FOLDERS_CSV = FOLDER_LOGS
    OUTPUT_CSV = ALL_MEDIA_CSV
    HEADER = [
        "File Name",
        "File Type",
        "File Size (Bytes)",
        "File Size (Human Readable)",
        "Creation Date",
        "Modification Date",
        "Source Folder"
    ]
    seen = set()
    csv_paths = set()
    with open(LOG_FOLDERS_CSV, newline='', encoding='utf-8') as logf:
        reader = csv.reader(logf)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) < 2:
                continue
            csv_path = row[1].strip()
            if csv_path:
                csv_paths.add(normalise_path(csv_path))

    with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as outf:
        writer = csv.writer(outf)
        writer.writerow(HEADER)
        for csv_file in csv_paths:
            if not os.path.exists(csv_file):
                continue
            with open(csv_file, newline='', encoding='utf-8') as inf:
                reader = csv.reader(inf)
                in_header = next(reader, None)
                for row in reader:
                    if len(row) < 7:
                        continue
                    # Only unique combination of Source Folder + File Name
                    key = (normalise_path(row[6]), row[0].lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    writer.writerow(row)
    return OUTPUT_CSV