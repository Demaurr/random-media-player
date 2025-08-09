from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import os
import re
from player_constants import ALL_MEDIA_CSV, DELETE_FILES_CSV, FILE_TRANSFER_LOG, FILES_FOLDER, FOLDER_LOGS, LOG_PATH, SCREENSHOTS_FOLDER, SNIPPETS_HISTORY_CSV, WATCHED_HISTORY_LOG_PATH
from logs_writer import LogManager
from collections import defaultdict, deque

logger = LogManager(LOG_PATH)

def create_csv_file(headers=None, filename="New_CSV.csv"):
    if os.path.exists(filename):
        # print(f"{filename} File Exists...")
        return 
    # If no headers are provided, create three random headers
    if headers is None:
        headers = ["Heading_1", "Heading_2", "Heading_3"]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
    
    print(f"CSV file '{filename}' created with headers: {headers}")

def normalise_path(path) -> str:
        """
        Normalizes a file path to use backslashes '\' as separators instead of '/'.
        Args:
            path (str): The file path to normalize.
        Returns:
            str: The normalized file path with backslashes.
        """
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
        # print(f"File not found: {file_path}")
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
        # print("The folders match!")
        return True
    else:
        # print("The folders don't match!")
        # print(f"File directory: {file_directory}")
        # print(f"Folder path: {folderpath}")
        return False
    
def gather_all_media():
    try:
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
        if not os.path.exists(LOG_FOLDERS_CSV):
            create_csv_file(headers=["Folder Path","Csv Path","Date"], filename=LOG_FOLDERS_CSV)
            create_csv_file(headers=HEADER, filename=OUTPUT_CSV)
            return OUTPUT_CSV
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

        all_rows = []
        for csv_file in csv_paths:
            if not os.path.exists(csv_file):
                continue
            with open(csv_file, newline='', encoding='utf-8') as inf:
                reader = csv.reader(inf)
                next(reader, None)  # skip header
                for row in reader:
                    if len(row) < 7:
                        continue
                    key = (normalise_path(row[6]), row[0].lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    all_rows.append(row)

        with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as outf:
            writer = csv.writer(outf)
            writer.writerow(HEADER)
            writer.writerows(all_rows)
        return OUTPUT_CSV
    except Exception as e:
        logger.error_logs(f"Error gathering all media: {e}")
        print(f"Error gathering all media: {e}")
        return None

def seconds_to_hhmmss(seconds):
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def convert_bytes(bytes_size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        index = 0
        size = float(bytes_size)

        while size >= 1024 and index < len(units) - 1:
            size /= 1024
            index += 1

        return f"{size:.2f} {units[index]}"

def open_in_default_app(file_path):
    """
    Opens the given file with the default application set in the OS.
    Supports Windows, macOS, and Linux.
    """
    try:
        if os.name == 'nt':  # Windows
            os.startfile(file_path)
        elif os.name == 'posix':
            import subprocess
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux and others
                subprocess.run(['xdg-open', file_path])
        else:
            print("Unsupported OS.")
    except Exception as e:
        print(f"Failed to open file: {e}")

def sort_treeview_column(treeview, col, reverse):
    """
    Generic function to sort a ttk.Treeview column.
    
    Args:
        treeview: The ttk.Treeview widget to sort
        col: The column identifier to sort by
        reverse: Boolean indicating reverse sort order
        
    Returns:
        None
    """
    data = [(treeview.set(k, col), k) for k in treeview.get_children('')]
    try:
        data.sort(key=lambda t: int(t[0]), reverse=reverse)
    except ValueError:
        data.sort(key=lambda t: t[0].lower(), reverse=reverse)
    
    for index, (val, k) in enumerate(data):
        treeview.move(k, '', index)
    treeview.heading(col, command=lambda: sort_treeview_column(treeview, col, not reverse))

def get_screenshots_for_file(filename):
    """
    Returns a list of screenshot file paths for the given filename from the screenshots folder.
    Screenshots are named as: screenshot_{filename}_<timestamp>.png
    If no screenshots are found, returns an empty list.
    Handles errors gracefully.
    """
    screenshots = []
    if not filename:
        print("No filename provided.")
        return screenshots
    try:
        if not os.path.exists(SCREENSHOTS_FOLDER):
            print(f"Screenshots folder does not exist: {SCREENSHOTS_FOLDER}")
            return screenshots
        for file in os.listdir(SCREENSHOTS_FOLDER):
            if file.startswith(f"screenshot_{filename}_") and file.endswith(".png"):
                screenshots.append(os.path.join(SCREENSHOTS_FOLDER, file))
        if not screenshots:
            print(f"No screenshots found for file: {filename}")
        return screenshots
    except Exception as e:
        print(f"Error while getting screenshots for {filename}: {e}")
        return []
    
def get_video_snippets_for_file(filename):
    """
    Returns a list of output file paths for video snippets that match the given original filename.
    Args:
        filename (str): The original video filename to match.
        snippets_csv_path (str): Path to the snippets CSV file.
    Returns:
        List[str]: List of output file paths for the matching snippets.
    """
    snippets = []
    if not filename or not os.path.exists(SNIPPETS_HISTORY_CSV):
        print("Invalid filename or snippets CSV path.")
        return snippets
    try:
        with open(SNIPPETS_HISTORY_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get("Original File") == filename:
                    output_file = row.get("Output File")
                    if output_file:
                        snippets.append(output_file)
        if not snippets:
            print(f"No video snippets found for file: {filename}")
        return snippets
    except Exception as e:
        print(f"Error while getting video snippets for {filename}: {e}")
        return []

def get_file_transfer_history(file_path):
    """
    Given a file path, returns its previous path (if it was moved from somewhere),
    its destination path (if it was moved to somewhere), and the current path.
    Args:
        file_path (str): The file path to look up.
    Returns:
        dict: {'previous': <previous_path or None>, 'current': <file_path>, 'destination': <destination_path or None>}
    """
    previous = None
    destination = None
    if not os.path.exists(FILE_TRANSFER_LOG):
        print(f"Transfer log not found: {FILE_TRANSFER_LOG}")
        return {'previous': None, 'current': normalise_path(file_path), 'destination': None}
    try:
        with open(FILE_TRANSFER_LOG, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                src = row.get("Source Path")
                dst = row.get("Destination Path")
                if src and os.path.normcase(src) == os.path.normcase(file_path):
                    destination = dst
                if dst and os.path.normcase(dst) == os.path.normcase(file_path):
                    previous = src
        return {
            'previous': normalise_path(previous) if previous else None,
            'current': normalise_path(file_path),
            'destination': normalise_path(destination) if destination else None
        }
    except Exception as e:
        print(f"Error reading transfer log: {e}")
        return {'previous': None, 'current': normalise_path(file_path), 'destination': None}

# def get_watch_stats_for_files(file_paths, by_filename=True):
#     """
#     Get aggregated watch stats for multiple file paths efficiently.
    
#     file_paths: list of file paths (full or filename)
#     by_filename: whether to match only filename or full normalized path
#     """
#     if by_filename:
#         targets = set(os.path.basename(fp).lower() for fp in file_paths)
#     else:
#         targets = set(normalise_path(fp) for fp in file_paths)

#     watch_count = 0
#     total_seconds = 0
#     last_watched = None

#     try:
#         with open(WATCHED_HISTORY_LOG_PATH, newline='', encoding='utf-8') as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 if by_filename:
#                     row_val = os.path.basename(row.get("File Name", "")).lower()
#                 else:
#                     row_val = normalise_path(row.get("File Name", ""))
#                 if row_val in targets:
#                     watch_count += 1
#                     try:
#                         total_seconds += calculate_duration_in_seconds(row.get("Duration Watched", "0:00.0"))
#                     except Exception:
#                         pass
#                     try:
#                         dt = datetime.strptime(row.get("Date Watched", ""), "%Y-%m-%d %H:%M:%S")
#                         if not last_watched or dt > last_watched:
#                             last_watched = dt
#                     except Exception:
#                         pass
#     except Exception:
#         pass

#     return {
#         "watch_count": watch_count,
#         "total_seconds": total_seconds,
#         "last_watched": last_watched.strftime("%Y-%m-%d %H:%M:%S") if last_watched else "Never"
#     }

def get_watch_stats_for_filenames(file_paths):
    """
    Efficiently get combined watch stats for a set of filenames
    derived from related file paths.
    Matches only by filename, not full path.
    """
    filenames = set(os.path.basename(p).lower() for p in file_paths)

    watch_count = 0
    total_seconds = 0
    last_watched = None

    try:
        with open(WATCHED_HISTORY_LOG_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_filename = os.path.basename(row.get("File Name", "")).lower()
                if row_filename in filenames:
                    watch_count += 1

                    try:
                        total_seconds += calculate_duration_in_seconds(row.get("Duration Watched", "0:00.0"))
                    except Exception:
                        pass

                    try:
                        dt = datetime.strptime(row.get("Date Watched", ""), "%Y-%m-%d %H:%M:%S")
                        if not last_watched or dt > last_watched:
                            last_watched = dt
                    except Exception:
                        pass
    except Exception as e:
        print("Error reading watch log:", e)

    return {
        "watch_count": watch_count,
        "total_seconds": total_seconds,
        "last_watched": last_watched.strftime("%Y-%m-%d %H:%M:%S") if last_watched else "Never"
    }



def calculate_duration_in_seconds(duration_str):
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


def get_all_related_paths(target_path):
    graph = defaultdict(set)
    
    with open(FILE_TRANSFER_LOG, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            src = normalise_path(row['Source Path'])
            dst = normalise_path(row['Destination Path'])
            graph[src].add(dst)
            graph[dst].add(src)

    target_path = normalise_path(target_path)
    visited = set()
    queue = deque([target_path])
    related_paths = []

    while queue:
        path = queue.popleft()
        if path not in visited:
            visited.add(path)
            related_paths.append(path)
            queue.extend(graph[path] - visited)

    return sorted(related_paths)

def get_split_stats_by_folder(file_paths):
    """
    Given a list or tuple of file paths, returns a dict with folder as key and stats as value.
    Stats include: number of files and total size in bytes for each folder.
    Returns:
        dict: {folder_path: {"file_count": int, "total_size": int, "files": [file1, ...]}}
    """
    from collections import defaultdict
    folder_stats = defaultdict(lambda: {"file_count": 0, "total_size": 0, "files": []})
    for path in file_paths:
        folder = os.path.dirname(path)
        try:
            size = os.path.getsize(path)
        except Exception:
            size = 0
        folder_stats[folder]["file_count"] += 1
        folder_stats[folder]["total_size"] += size
        folder_stats[folder]["files"].append(path)
    return dict(folder_stats)

def get_video_and_screenshots_map():
    """
    Efficiently maps video file paths to screenshot paths using threading and optimization.
    Returns:
        dict: {video_path: [screenshot_path1, screenshot_path2, ...]}
    """
    MAX_WORKERS = 2
    video_to_screenshots = {}

    if not os.path.exists(ALL_MEDIA_CSV):
        print(f"CSV not found: {ALL_MEDIA_CSV}")
        return video_to_screenshots

    try:
        with open(ALL_MEDIA_CSV, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            video_rows = [normalise_path(row["File Name"]) for row in reader if row.get("File Name")]

        def process_video(video_path):
            try:
                filename = os.path.basename(video_path)
                screenshots = get_screenshots_for_file(filename)
                return (video_path, screenshots)
            except Exception as e:
                print(f"Error processing {video_path}: {e}")
                return (video_path, [])

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_path = {executor.submit(process_video, path): path for path in video_rows}
            for future in as_completed(future_to_path):
                video_path, screenshots = future.result()
                video_to_screenshots[video_path] = screenshots

    except Exception as e:
        print(f"Error reading {ALL_MEDIA_CSV}: {e}")

    return video_to_screenshots

def get_video_file_from_screenshot(screenshot_path):
    """
    Given a screenshot path, returns the original video file path(s) based on the naming pattern.
    Pattern: screenshot_{filename}_{timestamp}.png
    Returns:
        List[str]: List of possible video file paths (with extension).
    """
    if not screenshot_path or not os.path.exists(screenshot_path):
        return []

    base = os.path.basename(screenshot_path)
    if not base.startswith("screenshot_") or not base.endswith(".png"):
        return []

    middle = base[len("screenshot_"):-len(".png")]
    parts = middle.rsplit("_", 1)
    if len(parts) != 2:
        return []

    filename = parts[0]  
    file_paths = []
    try:
        if os.path.exists(ALL_MEDIA_CSV):
            with open(ALL_MEDIA_CSV, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    file_name = os.path.basename(row.get("File Name", ""))
                    if file_name == filename:
                        file_paths.append(normalise_path(row.get("File Name")))
    except Exception as e:
        print(f"Error searching for video file in CSV: {e}")

    if not file_paths:
        file_paths.append(filename)

    return file_paths

if __name__ == "__main__":
    # print("Static methods module loaded successfully.")
    # filepath_to_search = r"sample.mp4"
    # all_paths = get_all_related_paths(filepath_to_search)

    # print("All known paths for the file:")
    # for p in all_paths:
    #     print(p)
    # get_video_and_screenshots_map()
    print()