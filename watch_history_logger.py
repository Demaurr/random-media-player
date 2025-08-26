from datetime import datetime
import csv
import os
from logs_writer import LogManager
from player_constants import LOG_PATH, WATCHED_HISTORY_LOG_PATH
from static_methods import convert_date_format, normalise_path, create_csv_file

class WatchHistoryLogger:
    """A class for logging the history of watched videos."""

    def __init__(self, csv_file=WATCHED_HISTORY_LOG_PATH):
        """
        Initializes the WatchHistoryLogger.

        Args:
            csv_file (str): Path to the CSV file for logging watch history.
        """
        self.csv_file = csv_file
        self.logger = LogManager(LOG_PATH)
        self.fieldnames = ['File Name', 'Total Duration', 'Date Watched', 'Duration Watched', 'Last Position']
        self.file_exists = self.check_file_exists()
        if not self.file_exists:
            self.create_csv_file()
        else:
            self.refresh_csv_if_needed()
    
    def build_last_position_index(self):
        """
        Builds a dictionary mapping file names to their last known position.
        Keeps only the most recent record for each file.

        Returns:
            dict: {file_name: last_position}
        """
        index = {}
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_name = normalise_path(row['File Name'])
                    last_position = row['Last Position'] or row['Duration Watched']
                    index[file_name] = last_position  # overwrites older entries
        except FileNotFoundError:
            pass
        return index

    def check_file_exists(self):
        """
        Checks if the CSV file for logging watch history exists.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return os.path.isfile(self.csv_file)

    def create_csv_file(self):
        """Creates a new CSV file for logging watch history if it doesn't exist."""
        with open(self.csv_file, 'a', newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()

    def refresh_csv_if_needed(self):
        """Refreshes the CSV file to add 'Last Position' column if missing."""
        with open(self.csv_file, 'r', newline='', encoding="utf-8") as file:
            reader = csv.reader(file)
            headers = next(reader)
            if 'Last Position' not in headers:
                rows = list(reader)
                old_fieldnames = headers
                new_fieldnames = self.fieldnames
                new_rows = []
                for row in rows:
                    row_dict = dict(zip(old_fieldnames, row))
                    row_dict['Last Position'] = row_dict.get("Duration Watched", "00:00:00")
                    new_rows.append(row_dict)
                with open(self.csv_file, 'w', newline='', encoding="utf-8") as out_file:
                    writer = csv.DictWriter(out_file, fieldnames=new_fieldnames)
                    writer.writeheader()
                    writer.writerows(new_rows)

    def log_watch_history(self, file_name, total_duration, video_duration, last_position):
        """
        Logs the history of a watched video.

        Args:
            file_name (str): Name of the watched video file.
            total_duration (str): Total duration of the video.
            video_duration (str): Duration watched.
            last_position (str): Last position watched.
        """
        try:
            date_watched = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.csv_file, 'a', newline='', encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writerow({
                    'File Name': file_name,
                    'Total Duration': total_duration,
                    'Date Watched': date_watched,
                    'Duration Watched': video_duration,
                    'Last Position': last_position
                })
            if hasattr(self, "_last_position_index"):
                self._last_position_index[normalise_path(file_name)] = last_position
        except Exception as e:
            print(f"Error Occurred While Writing Watch History Logs {e}")
            self.logger.error_logs(f"{e} While Writing Watch History")

    def get_last_position(self, file_name):
        """
        Get the last watched position for a given file from the in-memory index.

        Args:
            file_name (str): Name of the video file.

        Returns:
            str | None: The last position if found, otherwise None.
        """
        try:
            if not hasattr(self, "_last_position_index"):
                self._last_position_index = self.build_last_position_index()

            normalized_name = normalise_path(file_name)
            return self._last_position_index.get(normalized_name)

        except Exception as e:
            print(f"Error while fetching last position: {e}")
            return None

if __name__ == "__main__":
    convert_date_format(WATCHED_HISTORY_LOG_PATH)