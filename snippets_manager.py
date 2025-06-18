import csv
import os
import time
from player_constants import SNIPPETS_HISTORY_CSV
from static_methods import create_csv_file

class SnippetsManager:
    def __init__(self, csv_path=SNIPPETS_HISTORY_CSV):
        self.csv_path = csv_path
        self.headers = [
            "Timestamp", "Original File", "Output File",
            "Start Time (s)", "End Time (s)", "Trim Mode",
            "Total Duration (s)", "Resolution", "File Size (MB)",
            "Video Format", "Notes"
        ]

        # Create file if it doesn't exist
        # if not os.path.exists(self.csv_path):
        #     with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
        #         writer = csv.writer(f)
        #         writer.writerow(self.headers)
        create_csv_file(self.headers, self.csv_path)

    def record_trim(
        self,
        original,
        output,
        start_s,
        end_s,
        mode,
        total_duration_s,
        resolution="Unknown",
        file_size=None,
        video_format="mp4",
        notes=""
    ):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        size_mb = round(file_size / (1024 * 1024), 2) if file_size else "Unknown"
        row = [
            timestamp,
            original,
            output,
            round(start_s, 2),
            round(end_s, 2),
            "Fast" if mode else "Accurate",
            round(total_duration_s, 2),
            resolution,
            size_mb,
            video_format,
            notes
        ]
        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            print(f"[TrimManager] Error writing to CSV: {e}")
