from collections import defaultdict, deque
import csv
import os
import datetime

from player_constants import DESCRIPTION_CSV, DESCRIPTION_LOG_PATH, FILE_TRANSFER_LOG
from static_methods import create_csv_file, normalise_path
from logs_writer import LogManager

logger = LogManager(DESCRIPTION_LOG_PATH)

class DescriptionManager:
    def __init__(self, csv_path=DESCRIPTION_CSV):
        self.csv_path = csv_path
        self.descriptions = {}
        create_csv_file(headers=["video_path", "size", "description", "timestamp"], filename=csv_path)
        self._load_descriptions()
        self.graph = self.build_graph()

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

    def build_graph(self):
        """Builds the transfer graph from FILE_TRANSFER_LOG once."""
        graph = defaultdict(set)
        if not os.path.exists(FILE_TRANSFER_LOG):
            return graph

        with open(FILE_TRANSFER_LOG, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                src = normalise_path(row['Source Path'])
                dst = normalise_path(row['Destination Path'])
                graph[src].add(dst)
                graph[dst].add(src)
        return graph

    def get_related_paths(self, start_path):
        """BFS traversal to get all related paths for one starting path."""
        related = set()
        visited = set([start_path])
        queue = deque([start_path])

        while queue:
            current = queue.popleft()
            related.add(current)
            for neighbor in self.graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return related

    def get_description(self, video_path):
        desc = self.descriptions.get(video_path)
        return desc.get("description", "") if desc else ""
    
    def get_all_related_descriptions(self, target_path):
        """
        Return all descriptions for paths related to the given file.
        Uses the transfer log graph to collect connected paths.
        """
        related_paths = self.get_related_paths(target_path)
        descs = {}
        for path in related_paths:
            descs[path] = self.get_description(path)
        return descs


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

    def search_description_by_keys(self, query, allowed_paths, also_related=True):
        query = query.lower()
        expanded_paths = set()

        for path in allowed_paths:
            related = self.get_related_paths(path)
            expanded_paths.update(related)

        results = set() 
        for p in expanded_paths:
            data = self.descriptions.get(p)
            if data and query in data.get("description", "").lower():
                results.add(p)
                if also_related:
                    results.update(self.get_related_paths(p))

        return list(results)

    def update_video_path(self, old_path, new_path):
        """
        Update the video_path key in the descriptions dictionary 
        and persist changes to the CSV.
        """
        if old_path not in self.descriptions:
            print("[NO DESCRIPTION]", f"Old path not found: {old_path}")
            return False

        if new_path in self.descriptions:
            print("[DESCRIPTION UPDATE FAILED]", f"New path already exists: {new_path}")
            logger.error_logs(f"New path already exists in descriptions: {new_path}")
            return False

        self.descriptions[new_path] = self.descriptions[old_path].copy()

        self.descriptions[new_path]["timestamp"] = datetime.datetime.now().isoformat()

        self._save_descriptions()

        logger.update_logs("[DESCRIPTION UPDATED]", f"Path Changed from {old_path} -> {new_path}")
        return True