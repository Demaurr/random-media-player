from collections.abc import Iterable
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import csv
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Dict, List, Optional
from PIL import Image
import tracemalloc
from pprint import pprint
from __development_const import *

# from tqdm import tqdm
# from associations_manager import FileAssociator
from player_constants import *
from logs_writer import LogManager
from collections import defaultdict, deque

logger = LogManager(LOG_PATH)
# PRINT_TIME = True

def create_csv_file(headers=None, filename="New_CSV.csv"):
    if os.path.exists(filename):
        # print(f"{filename} File Exists...")
        return False
    if headers is None:
        headers = ["Heading_1", "Heading_2", "Heading_3"]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
    
    print(f"CSV file '{filename}' created with headers: {headers}")
    return True

def normalise_path(path, use_os_norm=True) -> str:
        """
        Normalizes a file path to use backslashes '\' as separators instead of '/'.
        Args:
            path (str): The file path to normalize.
        Returns:
            str: The normalized file path with backslashes.
        """
        return path.replace("/", "\\") if not use_os_norm else os.path.normpath(path.replace("/", "\\"))

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
    
def measure_time(
    *,
    logger=None,
    threshold=None,
    print_time=False,
    prefix="[TIME] "
):
    """
    Measure execution time of a synchronous function.

    Args:
        logger (LogManager): Your LogManager instance
        threshold (float): Warn if execution time exceeds this (seconds)
        print_time (bool): Print timing to console
        prefix (str): Prefix for log / print messages
    """

    def decorator(func):
        import time, functools

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                _handle_logging(func, elapsed)

        def _handle_logging(func, elapsed):
            message = f"{prefix} | {func.__name__} took {elapsed:.6f}s"

            if print_time:
                print(message)

            if logger:
                logger.update_logs("EXEC_TIME", message)

                if threshold is not None and elapsed > threshold:
                    logger.error_logs(
                        f"{func.__name__} exceeded threshold "
                        f"({elapsed:.6f}s > {threshold:.2f}s)"
                    )

        return wrapper

    return decorator

def measure_memory(
    *,
    logger=None,
    threshold=None,
    print_memory=False,
    prefix="[MEMORY] "
):
    """
    Measure memory usage of a synchronous function using tracemalloc.

    Args:
        logger (LogManager): Your LogManager instance
        threshold (float): Warn if peak memory exceeds this (in MB)
        print_memory (bool): Print memory usage to console
        prefix (str): Prefix for log / print messages
    """

    def decorator(func):
        import functools
        import tracemalloc

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracemalloc.start()
            try:
                return func(*args, **kwargs)
            finally:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                current_mb = current / (1024 * 1024)
                peak_mb = peak / (1024 * 1024)

                _handle_logging(func, current_mb, peak_mb)

        def _handle_logging(func, current_mb, peak_mb):
            message = (
                f"{prefix} | {func.__name__} "
                f"used {current_mb:.3f} MB (peak {peak_mb:.3f} MB)"
            )

            if print_memory:
                print(message)

            if logger:
                logger.update_logs("MEMORY_USAGE", message)

                if threshold is not None and peak_mb > threshold:
                    logger.error_logs(
                        f"{func.__name__} exceeded memory threshold "
                        f"({peak_mb:.3f} MB > {threshold:.2f} MB)"
                    )

        return wrapper

    return decorator

import functools
import tracemalloc

def measure_class_memory(
    *,
    logger=None,
    threshold=None,
    print_memory=False,
    prefix="[CLASS MEMORY] "
):
    """
    Measure memory usage of a class by wrapping its methods and measuring
    instance memory after __init__.

    Args:
        logger: LogManager instance
        threshold: Warn if peak memory exceeds this (in MB)
        print_memory: Print memory usage
        prefix: Prefix for logs
    """
    def class_decorator(cls):
        original_init = cls.__init__

        @functools.wraps(cls.__init__)
        def new_init(self, *args, **kwargs):
            tracemalloc.start()
            try:
                original_init(self, *args, **kwargs)
            finally:
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                current_mb = current / (1024 * 1024)
                peak_mb = peak / (1024 * 1024)

                message = (
                    f"{prefix} | {cls.__name__} instance "
                    f"used {current_mb:.3f} MB (peak {peak_mb:.3f} MB)"
                )

                if print_memory:
                    print(message)

                if logger:
                    logger.update_logs("MEMORY_USAGE", message)
                    if threshold is not None and peak_mb > threshold:
                        logger.error_logs(
                            f"{cls.__name__} instance exceeded memory threshold "
                            f"({peak_mb:.3f} MB > {threshold:.2f} MB)"
                        )

        cls.__init__ = new_init

        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value) and attr_name != "__init__":
                setattr(cls, attr_name, measure_memory(
                    logger=logger,
                    threshold=threshold,
                    print_memory=print_memory,
                    prefix=prefix
                )(attr_value))

        return cls

    return class_decorator


def gather_all_media(refresh=False):
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
            "Source Folder",
            "Status"
        ]

        if not os.path.exists(LOG_FOLDERS_CSV):
            create_csv_file(headers=["Folder Path", "Csv Path", "Date"], filename=LOG_FOLDERS_CSV)
            create_csv_file(headers=HEADER, filename=OUTPUT_CSV)
            return OUTPUT_CSV

        if not refresh and os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0:
            return OUTPUT_CSV

        old_data = {}
        if os.path.exists(OUTPUT_CSV):
            with open(OUTPUT_CSV, newline='', encoding='utf-8') as oldf:
                reader = csv.DictReader(oldf)
                for row in reader:
                    if len(row) < 7:
                        continue
                    key = (normalise_path(row["Source Folder"], use_os_norm=True), row["File Name"].lower())
                    row["Status"] = row.get("Status", "Present")
                    old_data[key] = row

        csv_paths = set()
        with open(LOG_FOLDERS_CSV, newline='', encoding='utf-8') as logf:
            reader = csv.reader(logf)
            next(reader, None)
            for row in reader:
                if len(row) < 2:
                    continue
                csv_path = row[1].strip()
                if csv_path:
                    csv_paths.add(normalise_path(csv_path, use_os_norm=True))

        new_data = {}
        for csv_file in csv_paths:
            if not os.path.exists(csv_file):
                continue
            with open(csv_file, newline='', encoding='utf-8') as inf:
                reader = csv.DictReader(inf)
                for row in reader:
                    if len(row) < 7:
                        continue
                    key = (normalise_path(row["Source Folder"], use_os_norm=True), row["File Name"].lower())
                    file_path = os.path.join(row["Source Folder"], row["File Name"])
                    row["Status"] = "Present" if os.path.exists(file_path) else "Missing"
                    new_data[key] = row

        merged_data = old_data.copy()
        merged_data.update(new_data)

        with open(OUTPUT_CSV, "w", newline='', encoding='utf-8') as outf:
            writer = csv.DictWriter(outf, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(merged_data.values())

        return OUTPUT_CSV

    except Exception as e:
        logger.error_logs(f"Error gathering all media: {e}")
        print(f"Error gathering all media: {e}")
        return None

def remove_media_entries(file_paths, csv_path=ALL_MEDIA_CSV):
    """
    Remove entries from ALL_MEDIA_CSV that match the given file paths.

    :param file_paths: An iterable of absolute file paths (Source Folder + File Name).
    :param csv_path: Path to the ALL_MEDIA_CSV file.
    :return: True if successful, False otherwise.
    """
    try:
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            return False

        # Normalize incoming paths for matching
        to_remove = set()
        for fp in file_paths:
            folder, fname = os.path.split(normalise_path(fp))
            to_remove.add((folder, fname.lower()))

        # Read existing data
        with open(csv_path, newline='', encoding='utf-8') as inf:
            reader = csv.DictReader(inf)
            rows = list(reader)
            headers = reader.fieldnames

        # Filter out unwanted rows
        updated_rows = []
        for row in rows:
            key = (normalise_path(row["Source Folder"]), row["File Name"].lower())
            if key not in to_remove:
                updated_rows.append(row)

        # Rewrite the file
        with open(csv_path, "w", newline='', encoding='utf-8') as outf:
            writer = csv.DictWriter(outf, fieldnames=headers)
            writer.writeheader()
            writer.writerows(updated_rows)

        return True

    except Exception as e:
        logger.error_logs(f"Error removing media entries: {e}")
        print(f"Error removing media entries: {e}")
        return False

    
def get_all_media_files():
    all_file_paths = []
    with open(ALL_MEDIA_CSV, "r",newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)
        for row in reader:
            all_file_paths.append(row[6] + "\\" + row[0])

    return all_file_paths


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

def are_paths_same(path1, path2):
        normalized_path1 = os.path.normpath(path1)
        normalized_path2 = os.path.normpath(path2)
        return normalized_path1 == normalized_path2


def sort_treeview_column(treeview, col, reverse):
    """
    Sorts a ttk.Treeview column using natural sorting.
    """
    rows = treeview.get_children('')
    data = []
    for k in rows:
        val = treeview.set(k, col)
        key = natural_sort_key(val)
        data.append((key, k, val))

    data.sort(key=lambda t: t[0], reverse=reverse)

    for idx, (_key, k, val) in enumerate(data):
        treeview.move(k, '', idx)

    treeview.heading(col, command=lambda: sort_treeview_column(treeview, col, not reverse))

@measure_time(print_time=PRINT_TIME)
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
            if file.startswith(f"screenshot_{filename}_") and (file.endswith(".jpg") or file.endswith(".png")):
                screenshots.append(os.path.join(SCREENSHOTS_FOLDER, file))
        if not screenshots:
            print(f"No screenshots found for file: {filename}")
        return screenshots
    except Exception as e:
        print(f"Error while getting screenshots for {filename}: {e}")
        return []

@measure_time(print_time=PRINT_TIME)
def build_screenshot_index():
    """
    Builds a mapping:
    {
        "filename1": [path1, path2],
        "filename2": [path3, path4]
    }
    """
    index = defaultdict(list)
    folder = SCREENSHOTS_FOLDER

    if not os.path.exists(folder):
        print(f"Screenshots folder does not exist: {folder}")
        return index

    try:
        for file in os.listdir(folder):
            if not (file.endswith(".png") or file.endswith(".jpg")):
                continue

            # Expected: screenshot_<filename>_<timestamp>.png
            if not file.startswith("screenshot_"):
                continue

            parts = file.split("_")

            if len(parts) < 3:
                continue

            # Extract filename (everything between screenshot_ and timestamp)
            filename = "_".join(parts[1:-1])

            full_path = os.path.join(folder, file)
            index[filename].append(full_path)

    except Exception as e:
        print(f"Error building screenshot index: {e}")

    return index

@measure_time(print_time=PRINT_TIME)
def get_screenshots_for_file_from_index(filename, index):
    """
    Build a screenshot index via static_methods.build_screenshot_index()
    And pass the index along side the filename
    """
    screenshots = index.get(filename, [])
    if not screenshots:
            print(f"No screenshots found for file: {filename}")
    return screenshots
    
def get_video_snippets_for_file(filename, sorted_list=False):
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
        return natural_sort_iterables(snippets) if sorted_list else snippets
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

def build_transfer_graph():
    graph = defaultdict(set)
    with open(FILE_TRANSFER_LOG, newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            src = normalise_path(row['Source Path'])
            dst = normalise_path(row['Destination Path'])
            if src and dst:
                graph[src].add(dst)
                graph[dst].add(src)
    return graph

@measure_time(print_time=PRINT_TIME)
def get_all_related_paths(target_path, graph=None):
    """
    Return all related file paths connected to target_path in the transfer graph.
    
    If graph is not provided, it will be built from FILE_TRANSFER_LOG.
    """
    if graph is None:
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

def get_all_connected_paths(target_path, graph):
    """
    Return all related file paths connected to target_path using BFS.
    """
    target_path = normalise_path(target_path)

    if target_path not in graph:
        return [target_path]

    visited = set()
    queue = deque([target_path])
    related_paths = []

    while queue:
        path = queue.popleft()
        if path in visited:
            continue
        visited.add(path)
        related_paths.append(path)
        queue.extend(graph[path] - visited)

    return sorted(related_paths)

@measure_time(print_time=PRINT_TIME)
def get_all_related_paths_multiple(file_paths, graph=None):
    """
    Return all related file paths connected to any file in file_paths.
    
    If graph is not provided, it will be built using build_transfer_graph().
    """
    if graph is None:
        graph = build_transfer_graph()

    file_paths = [normalise_path(p) for p in file_paths]

    visited = set()
    queue = deque(file_paths)
    related_paths = set()

    while queue:
        path = queue.popleft()
        if path not in visited:
            visited.add(path)
            related_paths.add(path)
            queue.extend(graph[path] - visited)

    return sorted(related_paths)

def build_path_to_fingerprint_map(fingerprint_manager, graph=None):
    """
    Build a dict mapping each path (including related/linked paths)
    to its fingerprint (index_hash).
    """

    path_to_index = {}

    for index_hash, paths in fingerprint_manager.paths.items():
        for p in paths:
            norm = normalise_path(p["file_path"])
            path_to_index[norm] = index_hash

    graph = graph or build_transfer_graph()

    for p in path_to_index.keys():
        graph.setdefault(p, set())

    final_map = {}
    visited_groups = set()
    for path in graph.keys():

        if path in visited_groups:
            continue

        related_paths = get_all_related_paths(path, graph)
        visited_groups.update(related_paths)

        fingerprint = None

        for p in related_paths:
            if p in path_to_index:
                fingerprint = path_to_index[p]
                break

        if not fingerprint:
            continue

        for p in related_paths:
            final_map[p] = fingerprint

    for p, f in path_to_index.items():
        if p not in final_map:
            final_map[p] = f

    return final_map

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

def natural_sort_key(s):
    """
    Split string into text and numbers.
    Numbers are converted to int for proper sorting.
    """
    return [int(text) if text.isdigit() else text.lower() 
            for text in re.split(r'(\d+)', s)]

def natural_sort_iterables(data):
    """
    Sorts any iterable of iterables (list, tuple, set) containing strings.
    Works on list of lists, tuple of lists, set of tuples, etc.
    """
    # Convert outer container to a stable type (list) for sorting
    sorted_data = sorted(
        data,
        key=lambda sub: [natural_sort_key(item) for item in sub]
        if isinstance(sub, Iterable) and not isinstance(sub, (str, bytes))
        else natural_sort_key(sub)
    )
    
    return sorted_data

def get_memory_usage():
    """
    Returns the current and peak memory usage (in MB) 
    since tracemalloc.start() was called.
    """
    current, peak = tracemalloc.get_traced_memory()
    return round(current / 1024 / 1024, 2), round(peak / 1024 / 1024, 2)

def _convert_single(file_path, output_dir, quality=80, delete_original=False):
    """Worker: convert one PNG to JPG."""
    try:
        if not file_path.lower().endswith(".png"):
            return None, "skipped"

        filename = os.path.basename(file_path)
        output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + ".jpg")

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if delete_original:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Could not delete {file_path}: {e}")
            return output_path, "skipped"

        img = Image.open(file_path).convert("RGB")
        img.save(output_path, "JPEG", quality=quality, optimize=True)

        if delete_original:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Could not delete {file_path}: {e}")

        return output_path, "converted"

    except Exception as e:
        print(f"Failed {file_path}: {e}")
        return None, "failed"

def add_hover_effect(btn, bg_color, hover_color):
    def on_enter(e):
        btn['background'] = bg_color
        btn['foreground'] = hover_color
    def on_leave(e):
        btn['background'] = bg_color
        btn['foreground'] = 'white'
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

def convert_png_to_jpg(files=None, output_dir=SCREENSHOTS_FOLDER,
                       quality=80, max_workers=None, delete_original=False):
    os.makedirs(output_dir, exist_ok=True)

    if files is None:
        from file_loader import VideoFileLoader
        files = VideoFileLoader.load_image_files()

    file_list = [f for f in files if f.lower().endswith(".png")]

    converted, skipped, failed = [], [], []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_convert_single, f, output_dir, quality, delete_original): f
            for f in file_list
        }
        for future in as_completed(futures):
            result, status = future.result()
            if status == "converted" and result:
                converted.append(result)
            elif status == "skipped" and result:
                skipped.append(result)
            elif status == "failed":
                failed.append(futures[future])

    return {
        "converted": converted,
        "skipped": skipped,
        "failed": failed,
        "output_dir": output_dir,
    }

def convert_single_file_to_mp4(file, output_dir=None, overwrite=False):
    """
    Convert a single file to MP4 using ffmpeg.
    Returns output path on success or error message on failure.
    """
    file_path = Path(file)

    if not file_path.exists():
        return f"File not found: {file}"
    if not file_path.is_file():
        return f"Not a valid file: {file}"

    out_dir = Path(output_dir) if output_dir else file_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / (file_path.stem + ".mp4")

    if out_file.exists() and not overwrite:
        return f"Skipped (output exists: {out_file})"

    try:
        cmd = [
            "ffmpeg", "-y" if overwrite else "-n",
            "-i", str(file_path),
            "-movflags", "faststart",
            "-pix_fmt", "yuv420p",
            str(out_file)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return str(out_file)
    except subprocess.CalledProcessError as e:
        return f"Conversion failed for {file}: {e.stderr.decode(errors='ignore')[:200]}..."
    
def batch_convert_to_mp4(
    task_manager,
    files,
    output_dir=None,
    overwrite=False,
    on_file_done=None,
    on_all_done=None,
    max_files=5,
    same_folder=True,
):
    """
    Add a batch of file conversions to the TaskManager as parallel tasks.

    Args:
        task_manager (TaskManager): your task manager instance
        files (list[str]): list of file paths
        output_dir (str | None): global output directory (ignored if same_folder=True)
        overwrite (bool): overwrite existing files
        on_file_done (callable): called with (file, result) when a file is done
        on_all_done (callable): called when all files are processed
        max_files (int): maximum number of files to process
        same_folder (bool): if True, each file’s .mp4 will be saved in the same folder
    """
    if not files:
        print("No files provided.")
        return

    if len(files) > max_files:
        files = files[:max_files]
        print(f"Only first {max_files} files will be converted.")

    pending = len(files)

    def file_done_closure(file):
        def _inner(result):
            nonlocal pending
            if on_file_done:
                on_file_done(file, result)
            pending -= 1
            if pending == 0 and on_all_done:
                on_all_done()
        return _inner

    for file in files:
        if same_folder:
            out_dir = os.path.dirname(file)
        else:
            ensure_folder_exists(output_dir)
            out_dir = output_dir

        task_manager.add_parallel_task(
            convert_single_file_to_mp4,
            file,
            output_dir=out_dir,
            overwrite=overwrite,
            on_done=file_done_closure(file),
        )

def get_related_associations(source_path, associator=None, graph=None):
    """
    Given a source path:
      1. Get all related paths using transfer graph.
      2. For each related path, fetch its associations from the associator.
    Returns a list of unique associations.
    """
    from associations_manager import FileAssociator
    associator = FileAssociator(ASSOCIATIONS_CSV) if associator is None else associator

    source_path = normalise_path(source_path)

    related_paths = get_all_related_paths(source_path, graph)

    associations = []
    seen = set()

    for path in related_paths:
        for assoc in associator.get_associations(path):
            key = (assoc["source_file"], assoc["target_file"], assoc["association_type"])
            if key not in seen:
                seen.add(key)
                associations.append((assoc["target_file"], assoc["target_size"], assoc["association_type"]))

    return associations

def get_related_targets(source_path, associator=None, graph=None, association_type=None, active_only=True, related_paths=None):
    """
    Given a source path:
      1. Get all related paths using transfer graph.
      2. For each related path, fetch its targets from the associator using get_targets().
    Returns a list of unique target paths.
    
    - association_type can be None, a single type, or a list/tuple of types.
    - active_only=True will include only active associations.
    """
    from associations_manager import FileAssociator
    associator = FileAssociator(ASSOCIATIONS_CSV) if associator is None else associator

    source_path = normalise_path(source_path)
    related_paths = get_all_related_paths(source_path, graph) if related_paths is None else related_paths

    if association_type is None:
        types_set = None
    elif isinstance(association_type, (list, tuple, set)):
        types_set = set(association_type)
    else:
        types_set = {association_type}

    targets = []
    seen = set()

    for path in related_paths:
        path_targets = associator.get_targets(path, association_type=types_set, active_only=active_only)
        targets.extend(path_targets)
    # print(targets)

    return targets

def parse_duration_to_seconds(duration_str: str) -> Optional[float]:
    """
    Converts duration strings like '00:30.2' or '0:00:22.600' into seconds (float).
    Returns None if invalid.
    """
    if not duration_str:
        return None

    try:
        parts = duration_str.split(":")
        if len(parts) == 1:
            # Example: "30.2"
            return float(parts[0])
        elif len(parts) == 2:
            # Example: "00:30.2" -> MM:SS
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:
            # Example: "0:00:22.600" -> HH:MM:SS
            hours, minutes, seconds = parts
            return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except ValueError:
        return None

    return None

def _atomic_save_csv(file_path: str, fieldnames: list[str], rows: list[dict]) -> None:
        """
        Atomically save a list of dict rows to CSV.
        Writes to a temporary file first, then replaces the original.
        """
        dir_name = os.path.dirname(file_path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", prefix="atomic_")
        try:
            with os.fdopen(fd, mode="w", newline="", encoding="utf-8") as tmp_file:
                writer = csv.DictWriter(tmp_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            os.replace(tmp_path, file_path)
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

def center_window(window, width=1000, height=600, offset_x=0, offset_y=0):
    """
    Center a Tkinter window on the screen with optional offsets.

    Args:
        window: The Tkinter window to center (Tk() or Toplevel()).
        width (int): Desired window width.
        height (int): Desired window height.
        offset_x (int): Extra horizontal offset (+ right, - left).
        offset_y (int): Extra vertical offset (+ down, - up).
    """
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    x_coordinate = (screen_width - width) // 2 + offset_x
    y_coordinate = (screen_height - height) // 2 + offset_y
    
    window.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def plot_fingerprint_analysis(csv_file, key_column="File Name", value_column="Fingerprint"):
    """
    Load CSV, analyze missing vs present fingerprints, and plot the results.

    Args:
        csv_file (str): Path to CSV file.
        key_column (str): Column to use as key (default "File Name").
        value_column (str): Column to analyze for missing values (default "Fingerprint").
    """
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    try:
        df = pd.read_csv(csv_file)
        df.columns = [c.strip() for c in df.columns]

        df[key_column] = df[key_column].astype(str).apply(normalise_path)

        df["Has_Fingerprint"] = df[value_column].notna() & (df[value_column].astype(str).str.strip() != "")

        summary = df["Has_Fingerprint"].value_counts().rename({True: "Has Fingerprint", False: "Missing Fingerprint"})

        # Plotting
        sns.set(style="whitegrid")
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(x=summary.index, y=summary.values, palette=["green", "red"])
        plt.title("Fingerprint Availability Analysis")
        plt.ylabel("Number of Files")
        plt.xlabel("")
        for i, v in enumerate(summary.values):
            ax.text(i, v + max(summary.values)*0.01, str(v), ha="center", fontweight="bold")
        plt.show()

        return summary.to_dict()

    except Exception as e:
        print(f"Error plotting fingerprint analysis: {e}")
        return {}

def format_seconds_to_str(time_duration):
    from datetime import timedelta
    """
    Convert a duration in seconds to a human-readable format.

    Args:
        time_duration (int): Duration in milliseconds.

    Returns:
        str: A string representing the duration in the format 'HH:MM:SS'.
    """
    time_str = str(timedelta(seconds=time_duration))[:-3]
    return time_str

def auto_reconcile_external_moves(file_manager, file_paths: List[str]) -> Dict[str, str]:
    """
    High-level function to auto-detect and reconcile externally-moved files.
    
    Should be called during:
    - on_enter_pressed (when loading a folder)
    - on_refresh_pressed (when refreshing)
    - show_all_media (when gathering all media)
    
    Args:
        file_manager: FileManager instance
        file_paths: List of discovered file paths
    
    Returns:
        dict: Mapping of recovered paths
    """
    if not file_paths:
        return {}
    
    return file_manager.auto_reconcile_on_refresh(file_paths)

@measure_time(print_time=PRINT_TIME)
def get_all_identity_paths(
    target_path: str,
    graph=None,
    fingerprint_manager=None
):
    """
    Return all paths that represent the same logical media file.
    Combines:
      - transfer log relationships (causal)
      - fingerprint relationships (identity)

    Allows you get the paths related to a file even if it was moved external to the app
    """
    target_path = normalise_path(target_path)

    transfer_paths = set(
        get_all_related_paths(target_path, graph)
    )

    fingerprint_paths = set()
    if fingerprint_manager:
        index_hash = fingerprint_manager.get_index_hash_by_path(target_path)
        if index_hash:
            fingerprint_paths.update(
                normalise_path(p)
                for p in fingerprint_manager.get_paths_by_hash(index_hash)
            )

    return sorted(transfer_paths | fingerprint_paths)

@measure_time(print_time=PRINT_TIME)
def get_all_identity_paths_multi(
    target_paths,
    graph=None,
    fingerprint_manager=None
):
    """
    Optimized multi-path identity resolution.
    """

    if not target_paths:
        return []

    target_paths = {normalise_path(p) for p in target_paths}

    visited_paths = set()
    result = set()
    queue = deque(target_paths)

    expanded_transfer_roots = set()
    expanded_fingerprint_hashes = set()

    while queue:
        path = queue.popleft()
        if path in visited_paths:
            continue

        visited_paths.add(path)
        result.add(path)

        if path not in expanded_transfer_roots:
            expanded_transfer_roots.add(path)

            for p in get_all_related_paths(path, graph):
                if p not in visited_paths:
                    queue.append(p)

        if fingerprint_manager:
            index_hash = fingerprint_manager.get_index_hash_by_path(path)
            if index_hash and index_hash not in expanded_fingerprint_hashes:
                expanded_fingerprint_hashes.add(index_hash)

                for p in fingerprint_manager.get_paths_by_hash(index_hash):
                    p = normalise_path(p)
                    if p not in visited_paths:
                        queue.append(p)

    return sorted(result)

@measure_time(print_time=PRINT_TIME)
def get_all_identity_paths_multi_optimized(paths, graph, fingerprint_manager, sort=True):
    """
    Takes a set of paths and returns all paths related to it.
    Includes both internal transfer relationsips and fingerprint-based relationships.

    Args:
        paths (set | list | str): one or more file paths
        graph (dict): transfer graph
        fingerprint_manager (FingerprintManager): fingerprint manager instance
        sort (bool): whether to return sorted list
    Returns:
        list: all related paths
    """

    if not paths:
        return []
    
    if isinstance(paths, str):
        paths = [paths]

    paths = {normalise_path(p) for p in paths}

    all_transfer_paths = set(get_all_related_paths_multiple(paths, graph))

    visited = set(all_transfer_paths)
    result = set(all_transfer_paths)

    expanded_hashes = set()
    for path in all_transfer_paths:
        if fingerprint_manager:
            index_hash = fingerprint_manager.get_index_hash_by_path(path)
            if index_hash and index_hash not in expanded_hashes:
                expanded_hashes.add(index_hash)
                for p in fingerprint_manager.get_paths_by_hash(index_hash):
                    p = normalise_path(p)
                    if p not in visited:
                        visited.add(p)
                        result.add(p)
    if sort:
        return sorted(result)

    return result

def build_identity_groups(paths, graph, fingerprint_manager):
    paths = {normalise_path(p) for p in paths}
    unvisited = set(paths)
    groups = []

    while unvisited:
        start = unvisited.pop()

        group = set(
            get_all_identity_paths_multi_optimized(
                [start],
                graph,
                fingerprint_manager
            )
        )

        groups.append(group)
        unvisited -= group

    return groups



if __name__ == "__main__":
    # plot_fingerprint_analysis("dump.csv","file_path", "note")
    pass