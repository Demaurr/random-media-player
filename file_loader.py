import hashlib
import os
import csv
from pprint import pprint

from static_methods import compare_folders

try:
    from Filing import filestatser
except ImportError:
    filestatser = None

from datetime import datetime
from logs_writer import LogManager
from player_constants import CSV_FOLDER, LOG_PATH, SCREENSHOTS_FOLDER, SKIP_FOLDERS

class VideoFileLoader:
    """A class for loading video files from folders or CSV files."""

    def __init__(self, csv_folder=None, media_extensions=[".avi", ".mov",".mp4", ".mkv", ".m4v", ".webm", ".wmv", ".flv"]):
        """
        Initializes the VideoFileLoader.

        Args:
            media_extensions (list, optional): List of media file extensions to consider as video files. 
            Defaults to [".avi", ".mp4", ".mkv", ".m4v", ".webm"].
            sets the var of total_size in bytes
        """
        self.csv_folder = os.path.dirname(os.path.abspath(__file__)) if csv_folder is None else csv_folder
        self.video_extensions = media_extensions
        self.csv_path = os.path.join(self.csv_folder, CSV_FOLDER, "Log_Folders.csv")
        self.refresh = []
        self.logger = LogManager(LOG_PATH)
        self.total_size_in_bytes = 0

    @staticmethod
    def load_image_files():
        stats = filestatser.FileStatsCollector(SCREENSHOTS_FOLDER, media_extensions=[".jpeg", ".jpg", ".PNG", ".png", ".JPG"], all_files=False)
        image_files = [file["Source Folder"] + "/" + file["File Name"] for file in stats.file_stats]
        return image_files

    @staticmethod
    def are_paths_same(path1, path2):
        normalized_path1 = os.path.normpath(path1)
        normalized_path2 = os.path.normpath(path2)
        return normalized_path1 == normalized_path2
    
    @staticmethod
    def normalise_path(path):
        return path.replace("/", "\\")
    
    @staticmethod
    def hash_string(input_string, hash_length=64):
        # Convert the input string to bytes
        input_bytes = input_string.encode('utf-8')
        
        # Create a hashlib object for SHA-256 (you can choose a different algorithm if you prefer)
        hasher = hashlib.sha256()
        
        # Update the hasher with the input bytes
        hasher.update(input_bytes)
        hashed_string = hasher.hexdigest()
        hashed_string = hashed_string[:hash_length]
        
        return hashed_string
    
    def get_videos_from_paths(self, folder_paths=[], skip_check=False):
        """
        Retrieves video files from the specified folder paths.

        Args:
            folder_paths (list, optional): List of folder paths to search for video files. Defaults to [].
            skip_check (bool, optional): Flag to skip folder existence check. Defaults to False.

        Returns:
            list: List of video file paths.
        """
        video_files = []
        for folder_path in folder_paths:
            try:
                # if not skip_check and not os.path.exists(folder_path):
                #     print(f"Folder '{folder_path}' does not exist.")
                #     continue
                if not os.path.exists(folder_path):
                    continue
                
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.endswith(tuple(self.video_extensions)):
                            video_files.append(os.path.join(root, file))
            except Exception as e:
                print(f"An error occurred while retrieving video files from folder '{folder_path}': {e}")
                self.logger.error_logs(f"{e} While Retrieving {folder_path}")
        return video_files
    
    def add_folder_data_csv(self, folder_paths=[]):
        try:
            # folders_without_csv, _ = self.seg_with_without_csv(folder_paths)
            # for folder in folders_without_csv:
            csv_files = []
            for folder in folder_paths:
                stats = filestatser.FileStatsCollector(folder, self.video_extensions, all_files=False)
                # testing_csv_path = os.path.join(self.csv_folder, CSV_FOLDER, f"Testing_{os.path.basename(folder)}.csv")
                testing_csv_path = os.path.join(self.csv_folder, CSV_FOLDER, f"Testing_{self.hash_string(folder, hash_length=32)}.csv")
                stats.generate_file_stats_csv(csv_path=testing_csv_path)
                self.add_to_csv_file(folder, testing_csv_path)
                csv_files.append(testing_csv_path)
            return csv_files
        except Exception as e:
            print(f"An error occurred while storing file data: {e}")
            self.logger.error_logs(f"{e} While Storing {folder}")
            return []

    def update_folder_data_csv(self, folder_paths=[]):
        """
        Update folder data CSV files for the specified folder paths.

        Args:
            folder_paths (list): List of folder paths to update CSV files.
        """
        try:
            for folder in folder_paths:
                csv_file = os.path.join(self.csv_folder, CSV_FOLDER, f"Testing_{self.hash_string(folder, hash_length=32)}.csv")
                stats = filestatser.FileStatsCollector(folder, self.video_extensions, all_files=False, skip_folders=SKIP_FOLDERS)
                stats.generate_file_stats_csv(csv_path=csv_file)
                # Update CSV path in Log_Folders.csv
                self.add_to_csv_file(folder, csv_file)
        except Exception as e:
            print(f"An error occurred while updating folder data CSV: {e}")    

    def add_to_csv_file(self, folder_path, testing_csv_path):
        """
        Add folder and the location of its testing CSV file to Log_Folders.csv.

        Args:
            folder_path (str): Path of the folder.
            testing_csv_path (str): Path of the testing CSV file corresponding to the folder.
        """
        with open(self.csv_path, 'a', newline='') as csvfile:
            csv_writer = csv.writer(csvfile)
            # Check if the file is empty to add header
            if csvfile.tell() == 0:
                csv_writer.writerow(["Folder Path", "Csv Path", "Date"])  # Header
            csv_writer.writerow([folder_path, testing_csv_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])

    def check_folders_path(self, folder_path):
        """
        Check if the folder is in Log_Folders.csv and return its CSV path.

        Args:
            folder_path (str): Path of the folder.

        Returns:
            str or False: Testing CSV path if folder is found, False otherwise.
        """
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                csv_reader = csv.reader(csvfile)
                next(csv_reader)
                for row in csv_reader:
                    # if self.are_paths_same(row[0], folder_path):
                    #     return row[1]
                    if compare_folders(row[0], folder_path):
                        return row[1]
        except FileNotFoundError:
            print(f"ERROR: Log_Folders.csv file not found at {self.csv_path}\n")
        except Exception as e:
            print(f"An error occurred while reading Log_Folders.csv: {e}\n")
        return folder_path
    
    def clean_input_paths(self, paths=[]):
        csv_files = set()
        folders = set()
        for ipath in paths:
            if ".csv" in ipath:
                csv_files.add(ipath)
            else:
                folders.add(ipath)
        return list(folders), list(csv_files)
    
    def seg_with_without_csv(self, folder_paths=[]):
        """
        Check if each folder in folder_paths has a corresponding CSV file.
        
        Args:
            folder_paths (list): List of folder paths to check for CSV files.

        Returns:
            tuple: A tuple containing two lists:
                - List of folder paths that do not have their corresponding CSV files.
                - List of paths of CSV files found in the specified folders.
        """
        folders = []
        csv_files = []
        for folder in folder_paths:
            # print(folder_paths)
            try:
                if os.path.exists(folder):
                    folder = self.normalise_path(folder)
                    print(f"Checking Database for { folder }....")
                    # csv_file = os.path.join(self.csv_folder, CSV_FOLDER, f"Testing_{os.path.basename(folder)}.csv")
                    csv_file = os.path.join(self.csv_folder, CSV_FOLDER, f"Testing_{self.hash_string(folder, hash_length=32)}.csv")
                    if os.path.exists(csv_file):
                        csv_files.append(csv_file)
                        print(f"Database has File For { folder }")
                    else:
                        # print(folder)
                        folders.append(folder)
                else:
                    print(f"The Given Folder Doesn't Exist: {folder}")
            except Exception as e:
                print(f"An error occurred while checking CSV file for folder '{folder}': {e}")
                continue
        return folders, csv_files

    
    def get_videos_from_csv(self, csv_files=[]):
        """
        Retrieves video files listed in CSV files.

        Args:
            csv_files (list, optional): List of CSV file paths. Defaults to [].

        Returns:
            list: List of video file paths extracted from the CSV files.
        """
        video_files = []
        for csv_file in csv_files:
            try:
                with open(csv_file, "r", encoding="utf-8") as file:
                    csv_reader = csv.DictReader(file)
                    for row in csv_reader:
                        if row.get("File Type", "").lower() in self.video_extensions:
                            source_folder = row.get("Source Folder", "")
                            file_name = row.get("File Name", "")
                            if source_folder and file_name:
                                video_files.append(os.path.join(source_folder, file_name))
                                self.total_size_in_bytes += float(row.get("File Size (Bytes)", 0))
            except (FileNotFoundError, csv.Error) as e:
                print(f"Error reading CSV file '{csv_file}': {e}")
            except TypeError as e:
                print(f"Exception {e} Occurred")
            except Exception as e:
                print(f"Exception {e} Occurred. File Might Not Exists")
                continue
        return video_files
    
    def strip_string_by_comma(self, input_string):
        # Split the input string by ", "
        split_by_comma_space = input_string.split(", ")
        
        stripped_strings = []
        for substr in split_by_comma_space:
            # Split each substring by ","
            substr = substr.strip()
            split_by_comma = substr.split(",")
            # print(substr)
            stripped_strings.extend(split_by_comma)
        
        return stripped_strings
    
    def check_to_refresh(self, folder_paths=[]):
        folders = []
        for folder in folder_paths:
            try:
                if "--update" in folder:
                    folder = self.normalise_path(folder.replace("--update", "").strip())
                    # folders.append(folder.replace("--update", ""))
                    self.update_folder_data_csv([folder])
                folders.append(folder)
            except Exception as e:
                self.logger.error_logs(f"{e} While refreshing {folder}")
                print(f"{e} While refreshing {folder}")
        return folders
    
    def refresh_folders(self, folder_paths):
        """
        Refresh (update) the CSV data for the given folder(s).

        Args:
            folder_paths (list or str): Folder path or list of folder paths to refresh.
        Returns:
            list: List of refreshed CSV file paths.
        """
        if isinstance(folder_paths, str):
            folder_paths = [folder_paths]
        refreshed_csvs = []
        for folder in folder_paths:
            try:
                folder = self.normalise_path(folder)
                self.update_folder_data_csv([folder])
                csv_file = os.path.join(
                    self.csv_folder, CSV_FOLDER, f"Testing_{self.hash_string(folder, hash_length=32)}.csv"
                )
                refreshed_csvs.append(csv_file)
                print(f"Refreshed: {folder}")
            except Exception as e:
                print(f"Failed to refresh {folder}: {e}")
                self.logger.error_logs(f"{e} While refreshing {folder}")
        return refreshed_csvs

    
    def start_here(self, input_string):
        """
        Process input string to retrieve video files.

        Args:
            input_string (str): A comma-separated string containing paths to folders and CSV files.

        Returns:
            list: List of video file paths extracted from the provided input.

        Note:
            This method performs the following steps:
            1. Strips the input string to obtain individual paths.
            2. Separates the paths into folder inputs and CSV inputs.
            3. Segregates the folders into two lists: one with CSV files and another without.
            4. Updates the folder data CSV files.
            5. Combines all CSV files into a single list.
            6. Retrieves video files from the combined CSV file paths.
        """
        final_paths = self.strip_string_by_comma(input_string)
        folder_inputs, csv_inputs = self.clean_input_paths(final_paths)
        refreshed_folders = self.check_to_refresh(folder_inputs)
        undocumented_folders, folders_csv = self.seg_with_without_csv(refreshed_folders)
        updated_csv_files = self.add_folder_data_csv(folder_paths=undocumented_folders)
        total_csvs = updated_csv_files + folders_csv + csv_inputs
        final_videos = self.get_videos_from_csv(total_csvs)
        return final_videos
    

    

if __name__ == "__main__":
    # Assuming you have instantiated your VideoFileLoader class as vf_loader
    # folder_paths = ["C:/Users/HP/Videos", "C:/Users/HP/Downloads"]

    # try:
    vf_loader = VideoFileLoader()
    pprint(vf_loader.start_here(input("Enter a Folder or Csv Path(s) separated with comma: ")))
    # folders_without_csv, csv_files = vf_loader.seg_with_without_csv(folder_paths=folder_paths)
    # updated_csv_file = vf_loader.update_folder_data_csv(folder_paths=folders_without_csv)
    # csv_files.extend(updated_csv_file)
    # vf_loader.get_videos_from_csv(csv_files)
        # print(csv_files)
        # print(folders_without_csv)
        # if folders_without_csv:
        #     print("Folders without CSV files:")
        #     for folder in folders_without_csv:
        #         print(folder)
        # else:
        #     print("No folders without CSV files found.")
        
    # except Exception as e:
    #     print(f"An error occurred: {e}")
