import csv
import os
import time
from deletion_manager import DeletionManager
from player_constants import SNIPPETS_HISTORY_CSV, LOG_PATH
from static_methods import create_csv_file, get_all_related_paths
from logs_writer import LogManager
from associations_manager import FileAssociator


class SnippetsManager:
    def __init__(self, csv_path=SNIPPETS_HISTORY_CSV, logger=None, deletion_manager=None, association_manager=None):
        self.csv_path = csv_path
        self.headers = [
            "Timestamp", "Original File", "Original File Size", "Output File",
            "Start Time (s)", "End Time (s)", "Trim Mode",
            "Total Duration (s)", "Resolution", "File Size (MB)",
            "Video Format", "Notes"
        ]
        create_csv_file(self.headers, self.csv_path)
        self.snippets = []
        self.deletion_manager = deletion_manager or DeletionManager()
        # self.associator = association_manager or FileAssociator()
        self.logger = logger or LogManager(LOG_PATH)
        self._load_snippets()
        self.refactor_csv()

    def _load_snippets(self):
        self.snippets.clear()
        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r", encoding="utf-8", newline='') as f:
                reader = csv.DictReader(f)
                self._defined_headers = reader.fieldnames
                self.snippets = list(reader)

    def _save_snippets(self):
        with open(self.csv_path, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()
            writer.writerows(self.snippets)

    def record_trim(self, original, output, start_s, end_s, mode,
                total_duration_s, resolution="Unknown",
                file_size=None, video_format="mp4", notes=""):
        """
        Records a snippet trim into the CSV and caches sizes efficiently.
        - original: original video file path
        - output: output snippet file path
        - start_s, end_s: snippet start and end times (seconds)
        - mode: True for Fast, False for Accurate trim
        - total_duration_s: total duration of snippet
        - resolution: string, optional
        - file_size: size of snippet in bytes; if None, calculated
        - video_format: string, default 'mp4'
        - notes: optional string
        """

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(original):
            try:
                original_size = os.path.getsize(original)
            except Exception:
                original_size = "N/A"
        else:
            original_size = self.deletion_manager.get_deleted_file_size(original)

        if file_size is None and os.path.exists(output):
            try:
                file_size = os.path.getsize(output)
            except Exception:
                file_size = None

        size_mb = round(file_size / (1024 * 1024), 2) if file_size else "Unknown"

        row = {
            "Timestamp": timestamp,
            "Original File": original,
            "Original File Size": original_size,
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

    def get_snippets_by_original_file(self, original_file, related_paths=False):
        """
        Get all snippets related to a specific original file.

        Args:
            original_file (str): Path or name of the original file.

        Returns:
            list: A list of snippet dicts (can be empty if none found).
        """
        if related_paths:
            related_paths = get_all_related_paths(original_file)
            return [s for s in self.snippets if s["Original File"] in related_paths]
        return [s for s in self.snippets if s["Original File"] == original_file]

    def get_snippet_by_output_file(self, output_file):
        return next((s for s in self.snippets if s["Output File"] == output_file), None)

    def update_snippet(self, output_file, **updates):
        snippet = self.get_snippet_by_output_file(output_file)
        if not snippet:
            return False

        if "Output File" in updates:
            self.logger.update_logs("[WARNING]", f"Cannot update 'Output File'. Use rename_snippet_file() instead.")
            print("[WARNING] 'Output File' cannot be updated directly. Use rename_snippet_file().")
            updates.pop("Output File")

        valid_updates = {k: v for k, v in updates.items() if k in self.headers}
        snippet.update(valid_updates)
        self._save_snippets()
        self.logger.update_logs("[SNIPPET UPDATED]", f"Updated snippet: {output_file} {updates.keys()}")
        return True
    
    def rename_snippet_file(self, old_output_file, new_output_file):
        if self.get_snippet_by_output_file(new_output_file):
            self.logger.error_logs(f"Snippet name already exists: {new_output_file}")
            return False

        snippet = self.get_snippet_by_output_file(old_output_file)
        if snippet:
            snippet["Output File"] = new_output_file
            self._save_snippets()
            self.logger.update_logs("[SNIPPET RENAMED]", f"{old_output_file} -> {new_output_file}")
            return True
        elif not snippet:
            print(f"[Snippet Not Found]: {old_output_file}")
            self.logger.error_logs(f"[Snippet Not Found]: {old_output_file}")
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
        """
        Returns total storage used by unique original files in MB.
        Avoids counting duplicates if multiple snippets belong to the same original file.
        """
        total = 0
        seen_files = set()

        for snippet in self.snippets:
            original_file = snippet.get("Original File")
            if original_file in seen_files:
                continue
            seen_files.add(original_file)

            try:
                size_mb = float(snippet.get("File Size (MB)", 0))
            except (ValueError, TypeError):
                size_mb = 0
            total += size_mb

        return round(total, 2)

    
    def refactor_csv(self):
        """
        Adds 'Original File Size' column to the CSV if missing.
        Populates it with the size of the original file (in bytes).
        If the file doesn't exist, uses DeletionManager to get its size.
        Optimized to calculate each original file's size only once.
        """
        if "Original File Size" in self._defined_headers:
            # print("Refactor skipped: 'Original File Size' column already exists.")
            return

        # self.headers.append("Original File Size")
        deletion_manager = self.deletion_manager

        size_cache = {}

        for snippet in self.snippets:
            original_file = snippet.get("Original File", "")
            
            if original_file in size_cache:
                size = size_cache[original_file]
            else:
                if os.path.exists(original_file):
                    try:
                        size = os.path.getsize(original_file)
                    except Exception:
                        size = "N/A"
                else:
                    size = deletion_manager.get_deleted_file_size(original_file)
                
                size_cache[original_file] = size

            snippet["Original File Size"] = size

        self._save_snippets()
        print("CSV refactored: 'Original File Size' column added.")

    
    def search_snippets_by_notes(self, query, allowed_original_files):
        """
        Search snippets' notes text for a query, restricted to given original files.

        Args:
            query (str): Text to search (case-insensitive).
            allowed_original_files (list|set|str): Allowed original file paths/names.

        Returns:
            list: A list of snippet dicts that matched.
        """
        query = query.lower()

        if isinstance(allowed_original_files, str):
            allowed_original_files = [allowed_original_files]

        related_paths = [p for path in allowed_original_files for p in get_all_related_paths(path)]
        allowed_set = set(related_paths)

        results = []
        for snippet in self.snippets:
            if snippet["Original File"] in allowed_set:
                notes = snippet.get("Notes", "").lower()
                if query in notes:
                    print(f"[MATCHED SNIPPET] {snippet['Output File']} in {snippet['Original File']}")
                    results.append(snippet["Output File"])

        return results

    def search_snippets_by_notes_global(self, query):
        """
        Search all snippets' notes for a given query across all originals.

        Args:
            query (str): Text to search (case-insensitive).

        Returns:
            list: A list of snippet dicts that matched the query.
        """
        query = query.lower().strip()
        results = []

        for snippet in self.snippets:
            notes = snippet.get("Notes", "").lower()
            if query in notes:
                print(f"[MATCHED SNIPPET] {snippet['Output File']} (Original: {snippet['Original File']})")
                results.append(snippet["Output File"])

        return results
    
    def build_all_associations(self, association_type="related"):
        """
        Add associations for all snippets with their original files.
        Association type is 'related' by default.
        """
        self.associator = FileAssociator()
        if not self.snippets:
            self.logger.update_logs("[ASSOCIATION BUILDER]", "No snippets found to build associations.")
            return 0

        added = 0
        for snippet in self.snippets:
            src = snippet.get("Original File")
            tgt = snippet.get("Output File")

            if not src or not tgt:
                continue

            if not self.associator.has_association(src, tgt, association_type):
                try:
                    self.associator.add_association(src, tgt, association_type)
                    added += 1
                    self.logger.update_logs("[ASSOCIATION ADDED]", f"{src} -> {tgt} (type='{association_type}')")
                except Exception as e:
                    self.logger.error_logs(f"Failed to associate {src} -> {tgt}: {e}")

        self.logger.update_logs("[ASSOCIATION BUILDER]",
                                f"Built {added} new associations (type='{association_type}').")
        return added
    
if __name__ == "__main__":
    sm = SnippetsManager()
    sm.build_all_associations()

