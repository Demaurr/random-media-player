from datetime import datetime
import csv
import os
from logs_writer import LogManager
from player_constants import LOG_PATH

class WatchHistoryLogger:
    """A class for logging the history of watched videos."""

    def __init__(self, csv_file):
        """
        Initializes the WatchHistoryLogger.

        Args:
            csv_file (str): Path to the CSV file for logging watch history.
        """
        self.csv_file = csv_file
        self.logger = LogManager(LOG_PATH)
        self.fieldnames = ['File Name', 'Total Duration', 'Date Watched', 'Duration Watched']
        self.file_exists = self.check_file_exists()
        if not self.file_exists:
            self.create_csv_file()
        

    def check_file_exists(self):
        """
        Checks if the CSV file for logging watch history exists.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return os.path.isfile(self.csv_file)

    def create_csv_file(self):
        """Creates a new CSV file for logging watch history if it doesn't exist."""
        with open(self.csv_file, 'a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()

    def log_watch_history(self, file_name, total_duration, video_duration):
        """
        Logs the history of a watched video.

        Args:
            file_name (str): Name of the watched video file.
            duration_watched (str): Total duration of the video watched.
            video_duration (str): Total duration of the video.
        """
        try:
            date_watched = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.csv_file, 'a', newline='', encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writerow({
                    'File Name': file_name,
                    'Total Duration': total_duration,
                    'Date Watched': date_watched,
                    'Duration Watched': video_duration
                })
        except Exception as e:
            print(f"Error Occurred While Writing Watch History Logs {e}")
            self.logger.error_logs(f"{e} While Writing Watch History")
            