import csv
import os
import time
from player_constants import SNIPPETS_HISTORY_CSV, LOG_PATH
from static_methods import create_csv_file
from logs_writer import LogManager


class SnippetsManager:
    def __init__(self, csv_path=SNIPPETS_HISTORY_CSV, logger=None):
        self.csv_path = csv_path
        self.headers = [
            "Timestamp", "Original File", "Output File",
            "Start Time (s)", "End Time (s)", "Trim Mode",
            "Total Duration (s)", "Resolution", "File Size (MB)",
            "Video Format", "Notes"
        ]
        create_csv_file(self.headers, self.csv_path)
        self.snippets = []
        self.logger = logger or LogManager(LOG_PATH)
        self._load_snippets()

    def _load_snippets(self):
        self.snippets.clear()
        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r", encoding="utf-8", newline='') as f:
                reader = csv.DictReader(f)
                self.snippets = list(reader)

    def _save_snippets(self):
        with open(self.csv_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(self.snippets)

    def record_trim(self, original, output, start_s, end_s, mode,
                    total_duration_s, resolution="Unknown",
                    file_size=None, video_format="mp4", notes=""):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        size_mb = round(file_size / (1024 * 1024), 2) if file_size else "Unknown"
        row = {
            "Timestamp": timestamp,
            "Original File": original,
            "Output File": output,
            "Start Time (s)": round(start_s, 2),
            "End Time (s)": round(end_s, 2),
            "Trim Mode": "Fast" if mode else "Accurate",
            "Total Duration (s)": round(total_duration_s, 2),
            "Resolution": resolution,
            "File Size (MB)": size_mb,
            "Video Format": video_format,
            "Notes": notes
        }
        self.snippets.append(row)
        self._save_snippets()
        self.logger.update_logs("[SNIPPET RECORDED]",
                                f"Recorded snippet: {output} from {original}")

    def get_all_snippets(self):
        return self.snippets

    def get_snippet_by_output_file(self, output_file):
        return next((s for s in self.snippets if s["Output File"] == output_file), None)

    def update_snippet(self, output_file, **updates):
        snippet = self.get_snippet_by_output_file(output_file)
        if snippet:
            snippet.update({k: v for k, v in updates.items() if k in self.headers})
            self._save_snippets()
            self.logger.update_logs("[SNIPPET UPDATED]", f"Updated snippet: {output_file}")
            return True
        return False

    def delete_snippet(self, output_file):
        before = len(self.snippets)
        self.snippets = [s for s in self.snippets if s["Output File"] != output_file]
        if len(self.snippets) < before:
            self._save_snippets()
            self.logger.update_logs("[SNIPPET DELETED]", f"Deleted snippet: {output_file}")
            return True
        return False

    def get_recent_snippets(self, n=10):
        return self.snippets[-n:]

    def get_snippets_by_note_text(self, query):
        query = query.lower()
        return [s for s in self.snippets if query in s.get("Notes", "").lower()]

    def get_total_snippet_count(self):
        return len(self.snippets)

    def get_total_storage_used(self):
        total = 0
        for s in self.snippets:
            try:
                total += float(s["File Size (MB)"])
            except (ValueError, TypeError):
                continue
        return round(total, 2)
