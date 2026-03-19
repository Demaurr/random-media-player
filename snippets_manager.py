from collections import defaultdict
import csv
import os
from pprint import pprint
import time
from deletion_manager import DeletionManager
from fingerprint_manager import MediaFingerprintManager
from player_constants import SNIPPETS_HISTORY_CSV, LOG_PATH
from static_methods import _atomic_save_csv, create_csv_file, get_all_identity_paths, get_all_related_paths, measure_time
from logs_writer import LogManager
from associations_manager import FileAssociator


class SnippetsManager:
    def __init__(self, csv_path=SNIPPETS_HISTORY_CSV, logger=None, deletion_manager=None, association_manager=None,
                 fingerprint_manager=None):
        self.csv_path = csv_path
        self.headers = [
            "Timestamp", "Original File", "Original File Size", "Output File",
            "Start Time (s)", "End Time (s)", "Trim Mode",
            "Total Duration (s)", "Resolution", "File Size (MB)", "File Size (Bytes)",
            "Video Format", "Notes", "Original Fingerprint", "Snippet Fingerprint"
        ]
        create_csv_file(self.headers, self.csv_path)
        self.snippets = []
        self.deletion_manager = deletion_manager or DeletionManager()
        # self.associator = association_manager or FileAssociator()
        self.logger = logger or LogManager(LOG_PATH)
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self._snippet_fingerprint_index = set()
        self._snippet_path_index = set()
        self._original_to_snippets = defaultdict(list)
        self._load_snippets()
        # self.refactor_csv()
        self._build_indexes()

    def _load_snippets(self):
        self.snippets.clear()
        if os.path.exists(self.csv_path):
            with open(self.csv_path, "r", encoding="utf-8", newline='') as f:
                reader = csv.DictReader(f)
                self._defined_headers = reader.fieldnames
                self.snippets = list(reader)

    def _save_snippets(self):
        _atomic_save_csv(
            file_path=self.csv_path,
            fieldnames=self.headers,
            rows=self.snippets
        )

    def record_trim(self, original, output, start_s, end_s, mode,
                total_duration_s, resolution="Unknown",
                file_size=None, video_format="mp4", notes="", original_fingerprint=""):
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
        size_bytes = file_size if file_size else "Unknown"
        if original_fingerprint == "":
            original_fingerprint = self.fingerprint_manager.get_index_hash_by_path(original)

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
            "File Size (Bytes)": size_bytes,
            "Video Format": video_format,
            "Notes": notes,
            "Original Fingerprint": original_fingerprint,
            "Snippet Fingerprint": ""
        }

        self.snippets.append(row)
        self._save_snippets()
        self.logger.update_logs("[SNIPPET RECORDED]",
                                f"Recorded snippet: {output} from {original}")
        if row["Snippet Fingerprint"]:
            self._snippet_fingerprint_index.add(row["Snippet Fingerprint"])

        self._snippet_path_index.add(row["Output File"])
        self._original_to_snippets[original].append(row)

    
    def _build_indexes(self):
        self._snippet_fingerprint_index.clear()
        self._snippet_path_index.clear()

        self._original_to_snippets.clear()

        for s in self.snippets:
            fp = s.get("Snippet Fingerprint")
            path = s.get("Output File")
            original = s.get("Original File")

            if fp:
                self._snippet_fingerprint_index.add(fp)

            if path:
                self._snippet_path_index.add(path)

            if original:
                self._original_to_snippets[original].append(s)

    def get_all_snippets(self):
        return self.snippets

    def get_snippets_by_original_file(self, original_file, related_paths=False, graph=None):
        """
        Get all snippets related to a specific original file.

        Args:
            original_file (str): Path or name of the original file.
            related_paths (bool): get the snippets for all the related paths of the original file
            graph: transfer graph to pass for getting related paths

        Returns:
            list: A list of snippet dicts (can be empty if none found).
        """
        if related_paths:
            related_paths = get_all_related_paths(original_file, graph=graph)
            return [s for s in self.snippets if s["Original File"] in related_paths]
        return [s for s in self.snippets if s["Original File"] == original_file]

    def get_snippets_for_files(self, file_paths, related_paths=False, graph=None):
        """
        Efficiently fetch snippets for multiple files.

        Args:
            file_paths (list[str]): list of original file paths
            related_paths (bool): include related paths
            graph: graph for related paths

        Returns:
            list: list of snippet dicts
        """
        if not file_paths:
            return []

        target_files = set()

        if related_paths:
            for f in file_paths:
                related = get_all_related_paths(f, graph=graph)
                target_files.update(related)
        else:
            target_files = set(file_paths)

        results = []

        for f in target_files:
            results.extend(self._original_to_snippets.get(f, []))

        return results

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
    
    # @measure_time(print_time=True)
    def get_complete_snippet_info(self, 
                                  original_file: str, 
                                  related_paths: bool = True, 
                                  graph=None,
                                  original_hash: str = "") -> dict:
        """
        Return a complete dictionary of all snippets and related info for a given original file.

        Args:
            original_file (str): Path of the original file.
            related_paths (bool): Whether to include snippets for all related file paths.
            graph: Optional transfer graph for resolving related paths.

        Returns:
            dict: {
                'original_file': str,
                'related_files': [list of related paths],
                'snippets': [list of snippet dicts with file existence info],
                'available_snippets': [existing snippet outputs],
                'missing_snippets': [snippet outputs that don't exist],
                'total_snippets': int,
                'available_count': int,
                'missing_count': int,
            }
        """
        if related_paths:
            files_to_check = get_all_identity_paths(original_file, graph=graph, fingerprint_manager=self.fingerprint_manager)
        else:
            files_to_check = [original_file]

        relevant_snippets = [s for s in self.snippets if s["Original File"] in files_to_check]
        complete_snippets_info = []
        available_snippets = []
        missing_snippets = []

        for s in relevant_snippets:
            output_file = s["Output File"]
            exists = os.path.exists(output_file)
            snippet_info = {**s, "exists": exists}
            complete_snippets_info.append(snippet_info)

            if exists:
                available_snippets.append(output_file)
            else:
                missing_snippets.append(output_file)

        info = {
            "original_file": original_file,
            "related_files": files_to_check,
            "snippets": complete_snippets_info,
            "available_snippets": available_snippets,
            "missing_snippets": missing_snippets,
            "total_snippets": len(relevant_snippets),
            "available_count": len(available_snippets),
            "missing_count": len(missing_snippets)
        }

        return info

    def fill_missing_snippet_fingerprints(self):
        """
        Check all snippets, and fill in missing 'Snippet Fingerprint' using the fingerprint manager.
        Useful if snippet files were not available at record time.
        """
        updated = 0
        for snippet in self.snippets:
            out_file = snippet.get("Output File")
            if not snippet.get("Snippet Fingerprint") and os.path.exists(out_file):
                duration = snippet.get("Total Duration (s)", "")
                size_bytes = snippet.get("File Size (Bytes)")
                if not size_bytes or not isinstance(size_bytes, int):
                    continue 
                self.fingerprint_manager.add_fingerprint(out_file, str(duration), str(size_bytes))
                index_hash = self.fingerprint_manager.get_index_hash_by_path(out_file)
                snippet["Snippet Fingerprint"] = index_hash
                updated += 1

        if updated:
            self._save_snippets()
            self.fingerprint_manager.flush()
            print(f"Filled {updated} missing snippet fingerprints.")
    
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

    def integrate_fingerprints(self, force_recompute=False):
        """
        Add fingerprints from MediaFingerprintManager for both the original and snippet files.
        Columns added: 'Original Fingerprint', 'Snippet Fingerprint'.

        Args:
            force_recompute (bool): if True, recompute fingerprints even if already present
        """
        fingerprint_manager = self.fingerprint_manager
        if "Original Fingerprint" not in self.headers:
            self.headers.append("Original Fingerprint")
        if "Snippet Fingerprint" not in self.headers:
            self.headers.append("Snippet Fingerprint")

        if not self.snippets:
            self._load_snippets()

        for snippet in self.snippets:
            orig_file = snippet.get("Original File")
            out_file = snippet.get("Output File")

            if force_recompute or not snippet.get("Original Fingerprint"):
                index_hash = fingerprint_manager.get_index_hash_by_path(orig_file)
                if not index_hash and os.path.exists(orig_file):
                    duration = snippet.get("Total Duration (s)", "")
                    size_bytes = snippet.get("File Size (Bytes)")
                    if not size_bytes or not isinstance(size_bytes, int):
                        continue 
                    self.fingerprint_manager.add_fingerprint(out_file, str(duration), str(size_bytes))
                    index_hash = fingerprint_manager.get_index_hash_by_path(orig_file)
                snippet["Original Fingerprint"] = index_hash

            if force_recompute or not snippet.get("Snippet Fingerprint"):
                index_hash = fingerprint_manager.get_index_hash_by_path(out_file)
                if not index_hash and os.path.exists(out_file):
                    duration = snippet.get("Total Duration (s)", "")
                    size_bytes = snippet.get("File Size (Bytes)")
                    if not size_bytes or not isinstance(size_bytes, int):
                        continue
                    self.fingerprint_manager.add_fingerprint(out_file, str(duration), str(size_bytes))
                    index_hash = fingerprint_manager.get_index_hash_by_path(out_file)
                snippet["Snippet Fingerprint"] = index_hash

        self._save_snippets()
        fingerprint_manager.flush()
        print("CSV updated: Added/Updated 'Original Fingerprint' and 'Snippet Fingerprint' columns.")

    def populate_file_size_bytes(self):
        """
        Populate the 'File Size (Bytes)' column for all snippets.
        - First tries to get the accurate size from VideoStatsManager.
        - If not available, falls back to converting 'File Size (MB)'.
        """
        updated = 0
        try:
            from stats_manager import VideoStatsManager
            stats_manager = VideoStatsManager()
        except ImportError:
            stats_manager = None

        for snippet in self.snippets:
            if "File Size (Bytes)" in snippet and snippet["File Size (Bytes)"]:
                continue

            out_file = snippet.get("Output File")
            size_bytes = None

            if stats_manager and out_file:
                size_bytes = stats_manager.get_file_size_bytes(out_file)

            if size_bytes is None:
                mb = snippet.get("File Size (MB)", 0)
                try:
                    size_bytes = int(float(mb) * 1024 * 1024)
                except Exception:
                    size_bytes = 0

            snippet["File Size (Bytes)"] = size_bytes
            updated += 1

        if updated:
            self._save_snippets()
            print(f"Updated 'File Size (Bytes)' for {updated} snippets.")


    def get_snippets_by_original_fingerprint(
        self,
        original_fingerprint: str
    ) -> list[dict]:
        """
        Return all snippets associated with a given original fingerprint.

        Args:
            original_fingerprint (str): Fingerprint of the original media file.

        Returns:
            list[dict]: List of snippet rows (can be empty).
        """
        if not original_fingerprint:
            return []

        return [
            s for s in self.snippets
            if s.get("Original Fingerprint") == original_fingerprint
        ]
    
    def is_snippet(self, snippet_fingerprint: str = None, snippet_path: str = None) -> bool:
        """
        Check if a given fingerprint or file path corresponds to a recorded snippet.

        Args:
            snippet_fingerprint (str): Fingerprint of the snippet file.
            snippet_path (str): Path of the snippet file.
        Returns:
            bool: True if it's a recorded snippet, False otherwise.
        """
        if snippet_fingerprint:
            for s in self.snippets:
                if s.get("Snippet Fingerprint") == snippet_fingerprint:
                    return True

        if snippet_path:
            for s in self.snippets:
                if s.get("Output File") == snippet_path:
                    return True

        return False

    
if __name__ == "__main__":
    sm = SnippetsManager()
    pprint(sm.get_snippets_by_original_fingerprint("c227c88949826f0f9fd0b8199d24ab89"), sort_dicts=False)
    # sm.fill_missing_snippet_fingerprints()
    # sm.build_all_associations()
    # sm.integrate_fingerprints(force_recompute=True)
    # sm.populate_file_size_bytes()
