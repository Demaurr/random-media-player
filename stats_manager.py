import csv
import os
from static_methods import gather_all_media, normalise_path
from player_constants import ALL_MEDIA_CSV, VIDEO_STATS_CSV, STATS_LOG_PATH
from logs_writer import LogManager
from get_aspects import VideoProcessor

logger = LogManager(STATS_LOG_PATH)

class VideoStatsManager:
    STATS_HEADER = [
        "File Path", "File Size", "Duration (s)", "Resolution", "Aspect Ratio", "Orientation",
        "Format", "Video Codec", "Bitrate (kbps)", "Frame Rate", "Pixel Format",
        "Profile", "Level", "Audio Codec", "Audio Channels", "Audio Sample Rate"
    ]

    def __init__(self, stats_csv=VIDEO_STATS_CSV):
        self.stats_csv = stats_csv
        self.stats = self._load_existing_stats()
        self.processor = VideoProcessor()

    def _load_existing_stats(self):
        stats = {}
        if not os.path.exists(self.stats_csv):
            return stats
        with open(self.stats_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (normalise_path(row["File Path"]), row["File Size"])
                stats[key] = row
        return stats

    def create_stats(self):
        all_media_csv = gather_all_media()
        if not all_media_csv or not os.path.exists(all_media_csv):
            logger.error_logs("All media CSV not found or failed to generate.")
            return

        files_to_process = []
        with open(all_media_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                file_path = normalise_path(os.path.join(row["Source Folder"], row["File Name"]))
                if not os.path.exists(file_path):
                    continue
                file_size = str(os.path.getsize(file_path))
                key = (file_path, file_size)
                if key not in self.stats:
                    files_to_process.append(file_path)

        if not files_to_process:
            print("No new files to process.")
            return

        print(f"Processing {len(files_to_process)} files...")

        results = self.processor.process_videos(files_to_process)
        new_stats = [r for r in results if r]

        self._write_stats(new_stats)
        print(f"Processed {len(new_stats)} new files.")

    def _write_stats(self, new_stats):
        file_exists = os.path.exists(self.stats_csv)
        with open(self.stats_csv, "a", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.STATS_HEADER)
            if not file_exists:
                writer.writeheader()
            for row in new_stats:
                writer.writerow(row)
                key = (normalise_path(row["File Path"]), row["File Size"])
                self.stats[key] = row

    def read_stats(self, filters=None):
        results = []
        with open(self.stats_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not filters or all(row.get(k) == v for k, v in filters.items()):
                    results.append(row)
        return results

    def update_stat(self, file_path, file_size, updates: dict):
        updated = False
        rows = []
        with open(self.stats_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (normalise_path(row["File Path"]), row["File Size"]) == (normalise_path(file_path), str(file_size)):
                    row.update(updates)
                    updated = True
                rows.append(row)
        with open(self.stats_csv, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.STATS_HEADER)
            writer.writeheader()
            writer.writerows(rows)
        if updated:
            self.stats[(normalise_path(file_path), str(file_size))] = updates
        return updated

    def delete_stat(self, file_path, file_size):
        deleted = False
        rows = []
        with open(self.stats_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (normalise_path(row["File Path"]), row["File Size"]) == (normalise_path(file_path), str(file_size)):
                    deleted = True
                    continue
                rows.append(row)
        with open(self.stats_csv, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.STATS_HEADER)
            writer.writeheader()
            writer.writerows(rows)
        if deleted:
            logger.update_logs("[STATS DELETED]", file_path)
            self.stats.pop((normalise_path(file_path), str(file_size)), None)
        return deleted

    def get_vertical_videos(self):
        """Return list of vertical video file paths from stats."""
        vertical = []
        for row in self.stats.values():
            if row.get("Orientation") == "Vertical":
                vertical.append(row["File Path"])
        return vertical

    def get_horizontal_videos(self):
        """Return list of horizontal video file paths from stats."""
        horizontal = []
        for row in self.stats.values():
            if row.get("Orientation") == "Horizontal":
                horizontal.append(row["File Path"])
        return horizontal

    def refresh_stats(self, file_path, file_size=None):
        """
        Refresh the stats for a given file_path (and optional file_size).
        Deletes the old stats and adds new stats for the file.
        Returns True if refreshed, False if not found or failed.
        """
        file_path = normalise_path(file_path)

        if not os.path.exists(file_path):
            return False
        
        if file_size is None:
            file_size = str(os.path.getsize(file_path))
        else:
            file_size = str(file_size)

        self.delete_stat(file_path, file_size)
        return self.add_stats(file_path, file_size)

    def add_stats(self, file_path, file_size=None):
        """
        Add stats for a single file given its file_path (and optional file_size).
        If file_size is not provided, it will be determined automatically.
        Returns True if added, False if already exists or failed.
        """
        file_path = normalise_path(file_path)
        if not os.path.exists(file_path):
            return False
        if file_size is None:
            file_size = str(os.path.getsize(file_path))
        else:
            file_size = str(file_size)
        key = (file_path, file_size)
        if key in self.stats:
            print(f"Stats already exist for this file: {file_path}")
            return False
        # print(f"Processing file: {file_path}")
        result = self.processor.process_videos([file_path])
        if not result or not result[0]:
            return False 

        new_row = result[0]
        with open(self.stats_csv, "a", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.STATS_HEADER)
            if os.stat(self.stats_csv).st_size == 0:
                writer.writeheader()
            writer.writerow(new_row)
        self.stats[key] = new_row
        logger.update_logs("[STATS ADDED]",file_path)
        print(f"[Processed Stats] {file_path}")
        return True

if __name__ == "__main__":
    manager = VideoStatsManager()
    manager.create_stats()
    print("Vertical videos:", manager.get_vertical_videos())
    print("Horizontal videos:", manager.get_horizontal_videos())
