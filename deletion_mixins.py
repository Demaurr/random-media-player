from collections import Counter, defaultdict
from datetime import datetime
import os


class DeletionStatsMixin:

    def get_deletion_stats(self):
        """
        Returns all deletion statistics.
        """
        return {
            "total_entries": self.get_total_deletion_entries(),
            "status_counts": self.get_deletion_status_counts(),
            "total_size_bytes": self.get_total_deletion_size(),
            "size_by_status": self.get_deletion_size_by_status(),
            "existing_files": self.get_existing_deletion_files_count(),
            "missing_files": self.get_missing_deletion_files_count(),
            "unique_folders": self.get_unique_deletion_folders_count(),
            "largest_file": self.get_largest_deletion_file(),
            "oldest_file": self.get_oldest_deletion_file(),
            "newest_file": self.get_newest_deletion_file(),
        }

    def get_total_deletion_entries(self):
        return len(self.deletion_files)

    def get_deletion_status_counts(self):
        counter = Counter()

        for metadata in self.deletion_files.values():
            counter[metadata.get("status", "Unknown")] += 1

        return dict(counter)

    def get_total_deletion_size(self):
        total = 0

        for metadata in self.deletion_files.values():
            size = metadata.get("size", 0)

            if isinstance(size, int):
                total += size

        return total

    def get_deletion_size_by_status(self):
        size_map = defaultdict(int)

        for metadata in self.deletion_files.values():
            status = metadata.get("status", "Unknown")
            size = metadata.get("size", 0)

            if isinstance(size, int):
                size_map[status] += size

        return dict(size_map)

    def get_largest_deletion_file(self):
        largest_file = None
        largest_size = 0

        for file_path, metadata in self.deletion_files.items():
            size = metadata.get("size", 0)

            if isinstance(size, int) and size > largest_size:
                largest_size = size
                largest_file = file_path

        return {
            "file": largest_file,
            "size": largest_size
        }


    def get_existing_deletion_files_count(self):
        return sum(
            1
            for file_path in self.deletion_files
            if os.path.exists(file_path)
        )

    def get_missing_deletion_files_count(self):
        return sum(
            1
            for file_path in self.deletion_files
            if not os.path.exists(file_path)
        )

    def get_unique_deletion_folders_count(self):
        folders = {
            os.path.dirname(file_path)
            for file_path in self.deletion_files
        }

        return len(folders)

    def get_oldest_deletion_file(self):
        return self._get_extreme_deletion_file(find_oldest=True)

    def get_newest_deletion_file(self):
        return self._get_extreme_deletion_file(find_oldest=False)

    def _get_extreme_deletion_file(self, find_oldest=True):
        target_file = None
        target_date = None

        for file_path, metadata in self.deletion_files.items():
            mod_time = metadata.get("mod_time")

            if not mod_time or mod_time == "N/A":
                continue

            try:
                dt = datetime.strptime(
                    mod_time,
                    "%Y-%m-%d %H:%M:%S"
                )

                if target_date is None:
                    target_date = dt
                    target_file = file_path
                    continue

                if find_oldest and dt < target_date:
                    target_date = dt
                    target_file = file_path

                elif not find_oldest and dt > target_date:
                    target_date = dt
                    target_file = file_path

            except Exception:
                continue

        return {
            "file": target_file,
            "date": target_date
        }