import os
import csv

class VideoFileLoader:
    """A class for loading video files from folders or CSV files."""

    def __init__(self, media_extensions=[".avi", ".mp4", ".mkv", ".m4v", ".webm"]):
        """
        Initializes the VideoFileLoader.

        Args:
            media_extensions (list, optional): List of media file extensions to consider as video files. 
            Defaults to [".avi", ".mp4", ".mkv", ".m4v", ".webm"].
        """
        self.video_extensions = media_extensions
    
    def get_video_files(self, folder_paths=[]):
        """
        Retrieves video files from the specified folder paths.

        Args:
            folder_paths (list, optional): List of folder paths to search for video files. Defaults to [].

        Returns:
            list: List of video file paths.
        """
        video_files = []
        for folder_path in folder_paths:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.endswith(tuple(self.video_extensions)):
                        video_files.append(os.path.join(root, file))
        return video_files
    
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
            except (FileNotFoundError, csv.Error) as e:
                print(f"Error reading CSV file '{csv_file}': {e}")
            except Exception as e:
                print(f"Exception {e} Occurred. File Might Not Exists")
        return video_files