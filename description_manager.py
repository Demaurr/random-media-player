import csv
import os
import datetime
from player_constants import DESCRIPTION_CSV, DESCRIPTION_LOG_PATH
from static_methods import create_csv_file
from logs_writer import LogManager

logger = LogManager(DESCRIPTION_LOG_PATH)

class DescriptionManager:
    def __init__(self, csv_path=DESCRIPTION_CSV):
        self.csv_path = csv_path
        self.descriptions = {}  # in-memory cache
        create_csv_file(headers=["video_path", "size", "description", "timestamp"], filename=csv_path)
        self._load_descriptions()

    def _load_descriptions(self):
        if not os.path.exists(self.csv_path):
            return
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.descriptions[row["video_path"]] = {
                    "size": row.get("size", ""),
                    "description": row.get("description", ""),
                    "timestamp": row.get("timestamp", "")
                }

    def _save_descriptions(self):
        with open(self.csv_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["video_path", "size", "description", "timestamp"])
            writer.writeheader()
            for path, data in self.descriptions.items():
                writer.writerow({
                    "video_path": path,
                    "size": data.get("size", ""),
                    "description": data.get("description", ""),
                    "timestamp": data.get("timestamp", "")
                })

    def get_description(self, video_path):
        desc = self.descriptions.get(video_path)
        return desc.get("description", "") if desc else ""

    def set_description(self, video_path, size, description):
        timestamp = datetime.datetime.now().isoformat()
        self.descriptions[video_path] = {
            "size": str(size),
            "description": description,
            "timestamp": timestamp
        }
        self._save_descriptions()
        logger.update_logs("[DESCRIPTION SET]", f"Path: {video_path}, Size: {size}, Description: {description}")

    def search_description(self, query):
        query = query.lower()
        results = []
        for path, data in self.descriptions.items():
            if query in data.get("description", "").lower():
                results.append({
                    "video_path": path,
                    "description": data["description"],
                    "size": data["size"],
                    "timestamp": data["timestamp"]
                })
        return results

    def search_description_by_keys(self, query, allowed_paths):
        query = query.lower()
        allowed_set = set(allowed_paths)
        results = []
        for path in allowed_set:
            data = self.descriptions.get(path)
            if data and query in data.get("description", "").lower():
                results.append(path)
                # print(f"Found in {path}: {data['description']}")
        return results
