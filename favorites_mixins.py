import os
from datetime import datetime
from static_methods import get_file_size

class FavoritesGettersMixin:
    def _read_favorites(self, force_reload=False):
        # Delegate to the class's implementation if present
        if hasattr(super(), "_read_favorites"):
            return super()._read_favorites(force_reload=force_reload)
        raise NotImplementedError("_read_favorites must be implemented on the host class")

    def get_total_favorites(self):
        return len(self._read_favorites())

    def get_unique_video_count(self):
        return len({row["Video Name"] for row in self._read_favorites()})

    def get_unique_source_folder_count(self):
        return len({row["Source Path"] for row in self._read_favorites()})

    def get_favorite_extensions(self):
        extensions = {}
        for row in self._read_favorites():
            ext = os.path.splitext(row["Video Name"])[1].lower()
            extensions[ext] = extensions.get(ext, 0) + 1
        return extensions

    def get_duplicate_names_count(self):
        counts = {}
        for row in self._read_favorites():
            name = row["Video Name"]
            counts[name] = counts.get(name, 0) + 1
        return sum(1 for count in counts.values() if count > 1)

    def get_missing_files_count(self):
        missing = 0
        for row in self._read_favorites():
            path = os.path.join(row["Source Path"], row["Video Name"])
            if not os.path.exists(path):
                missing += 1
        return missing

    def get_total_size(self):
        total_size = 0.0
        for row in self._read_favorites():
            path = os.path.join(row["Source Path"], row["Video Name"])
            if os.path.exists(path):
                total_size += get_file_size(path)
        return total_size

    def get_oldest_favorite(self):
        oldest = None
        for row in self._read_favorites():
            try:
                date_added = datetime.strptime(row["Date Added"], "%Y-%m-%d %H:%M:%S")
                if oldest is None or date_added < oldest:
                    oldest = date_added
            except (KeyError, ValueError):
                continue
        return oldest

    def get_newest_favorite(self):
        newest = None
        for row in self._read_favorites():
            try:
                date_added = datetime.strptime(row["Date Added"], "%Y-%m-%d %H:%M:%S")
                if newest is None or date_added > newest:
                    newest = date_added
            except (KeyError, ValueError):
                continue
        return newest

    def get_favorites_stats(self):
        oldest = self.get_oldest_favorite()
        newest = self.get_newest_favorite()
        return {
            "total_favorites": self.get_total_favorites(),
            "total_size_gb": self.get_total_size(),
            "unique_filenames": self.get_unique_video_count(),
            "unique_folders": self.get_unique_source_folder_count(),
            "missing_files": self.get_missing_files_count(),
            "duplicate_names": self.get_duplicate_names_count(),
            "oldest_favorite": (oldest.strftime("%Y-%m-%d %H:%M:%S") if oldest else None),
            "newest_favorite": (newest.strftime("%Y-%m-%d %H:%M:%S") if newest else None),
        }