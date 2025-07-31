import csv
import os
import datetime
from player_constants import DESCRIPTION_CSV
from static_methods import create_csv_file

class DescriptionManager:
    def __init__(self, csv_path=DESCRIPTION_CSV):
        self.csv_path = csv_path
        create_csv_file(headers=["video_path", "size", "description", "timestamp"], filename=csv_path)

    def get_description(self, video_path):
        if not os.path.exists(self.csv_path):
            return ""
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["video_path"] == video_path:
                    return row.get("description", "")
        return ""

    def set_description(self, video_path, size, description):
        rows = []
        found = False
        timestamp = datetime.datetime.now().isoformat()
        if os.path.exists(self.csv_path):
            with open(self.csv_path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["video_path"] == video_path:
                        row["description"] = description
                        row["size"] = str(size)
                        row["timestamp"] = timestamp
                        found = True
                    rows.append(row)
        if not found:
            rows.append({
                "video_path": video_path,
                "size": str(size),
                "description": description,
                "timestamp": timestamp
            })
        with open(self.csv_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["video_path", "size", "description", "timestamp"])
            writer.writeheader()
            writer.writerows(rows)

    def search_description(self, query):
        """Search for the query in the description (case-insensitive)."""
        results = []
        query_lower = query.lower()
        if not os.path.exists(self.csv_path):
            return results
        with open(self.csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if query_lower in row["description"].lower():
                    results.append({
                        "video_path": row["video_path"],
                        "description": row["description"],
                        "size": row["size"],
                        "timestamp": row["timestamp"]
                    })
        return results
