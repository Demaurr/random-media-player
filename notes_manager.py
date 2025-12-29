import csv
import os
from datetime import datetime
from fingerprint_manager import MediaFingerprintManager
from player_constants import NOTES_CSV, NOTES_LOG_PATH
from static_methods import create_csv_file, get_file_transfer_history
from logs_writer import LogManager

class NotesManager:
    """
    Manages notes, comments, and metadata for files.
    Stores data in a CSV file for persistence and fast retrieval.
    
    Structure:
    - Primary key: index_hash (fingerprint)
    - Secondary: file_paths (set of all paths with same fingerprint)
    - All metadata (note, rating, tags, mood, context) is keyed by index_hash
    - CSV allows multiple rows per hash (one per file_path) for reference
    """

    FIELDNAMES = [
        "index_hash",
        "file_path",
        "note",
        "rating",
        "tags",
        "mood",
        "context",
        "timestamp"
    ]

    def __init__(self, fingerprint_manager=None):
        self.notes_file = NOTES_CSV
        create_csv_file(filename=self.notes_file, headers=self.FIELDNAMES)
        self.notes: dict[str, dict] = {}
        self.path_to_hash: dict[str, str] = {}
        self.logger = LogManager(NOTES_LOG_PATH)
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self._load_notes()

    def _load_notes(self):
        """
        Load notes from CSV with proper merging for duplicate hashes.
        Handles both new (with fingerprint) and legacy (path-only) entries.
        """
        if not os.path.exists(self.notes_file):
            return

        with open(self.notes_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                index_hash = row.get("index_hash") or None
                if not index_hash:
                    continue
                file_path = row.get("file_path")

                key = index_hash

                if key not in self.notes:
                    self.notes[key] = {
                        "file_paths": set(),
                        "note": "",
                        "rating": None,
                        "tags": [],
                        "mood": "",
                        "context": "",
                        "timestamp": ""
                    }

                entry = self.notes[key]

                if file_path:
                    entry["file_paths"].add(file_path)
                    self.path_to_hash[file_path] = key

                if not entry["note"]:
                    entry["note"] = row.get("note", "")
                if entry["rating"] is None:
                    entry["rating"] = self._parse_rating(row.get("rating"))
                if not entry["tags"]:
                    entry["tags"] = self._parse_tags(row.get("tags"))
                if not entry["mood"]:
                    entry["mood"] = row.get("mood", "")
                if not entry["context"]:
                    entry["context"] = row.get("context", "")
                if not entry["timestamp"]:
                    entry["timestamp"] = row.get("timestamp", "")

    def _save_notes(self):
        """
        Save notes to CSV with duplicated rows (one per file_path per hash).
        This allows tracking which file_paths are associated with each note.
        """
        with open(self.notes_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()

            for index_hash, data in self.notes.items():
                for file_path in data["file_paths"]:
                    writer.writerow({
                        "index_hash": index_hash if index_hash else "",
                        "file_path": file_path,
                        "note": data.get("note", ""),
                        "rating": data.get("rating", ""),
                        "tags": ",".join(data.get("tags", [])),
                        "mood": data.get("mood", ""),
                        "context": data.get("context", ""),
                        "timestamp": data.get("timestamp", "")
                    })

    def _parse_rating(self, rating):
        try:
            if rating is None or rating == "":
                return None
            return float(rating)
        except ValueError:
            return None

    def _parse_tags(self, tags):
        if not tags:
            return []
        if isinstance(tags, list):
            return tags
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    def _resolve_key(self, file_path: str) -> str | None:
        """
        Resolve a file path to its index_hash (fingerprint).
        Caches successful resolutions in path_to_hash.
        """
        if not file_path:
            return None

        if self.fingerprint_manager:
            index_hash = self.fingerprint_manager.get_index_hash_by_path(file_path)
            if index_hash:
                self.path_to_hash[file_path] = index_hash
                return index_hash

        return None

    def _resolve_keys_batch(self, file_paths: list) -> dict[str, str]:
        """
        Resolve multiple file paths to their hashes at once.
        More efficient than calling _resolve_key() repeatedly.
        Returns: {file_path: index_hash | None}
        """
        resolved = {}
        for file_path in file_paths:
            if file_path in self.path_to_hash:
                resolved[file_path] = self.path_to_hash[file_path]
            else:
                resolved[file_path] = self._resolve_key(file_path)
                if resolved[file_path] != file_path:
                    self.path_to_hash[file_path] = resolved[file_path]
        return resolved

    def set_note(self, file_key, note, rating=None, tags=None, mood=None, context=None):
        """Set note for a file by its path, resolving to hash internally."""
        index_key = self._resolve_key(file_key)
        if not index_key:
            raise ValueError(f"Cannot set note: no fingerprint for {file_key}")

        entry = self.notes.setdefault(index_key, {
            "file_paths": set(),
            "note": "",
            "rating": None,
            "tags": [],
            "mood": "",
            "context": "",
            "timestamp": ""
        })

        entry["file_paths"].add(file_key)
        self.path_to_hash[file_key] = index_key

        entry.update({
            "note": note,
            "rating": self._parse_rating(rating),
            "tags": self._parse_tags(tags),
            "mood": mood,
            "context": context,
            "timestamp": datetime.now().isoformat()
        })

        self._save_notes()
        self.logger.update_logs("[NOTES SAVED]", f"[{file_key}] Note saved: {note}, Rating: {rating}, Tags: {tags}, Mood: {mood}, Context: {context}")

    def get_note(self, file_key):
        """Get note for a file by its path."""
        index_key = self.path_to_hash.get(file_key)
        if not index_key:
            index_key = self._resolve_key(file_key)
            # self.path_to_hash[file_key] = index_key
        # return self.notes.get(index_key)
        return dict(self.notes[index_key]) if index_key in self.notes else None
    
    def has_note(self, file_key):
        """Check if a file has a note."""
        index_key = self.path_to_hash.get(file_key)
        if not index_key:
            index_key = self._resolve_key(file_key)
            # self.path_to_hash[file_key] = index_key
        return index_key in self.notes

    def delete_note(self, file_key):
        """Delete note for a file."""
        index_key = self.path_to_hash.get(file_key)
        if not index_key:
            index_key = self._resolve_key(file_key)
            self.path_to_hash[file_key] = index_key
        if index_key in self.notes:
            del self.notes[index_key]
            paths_to_remove = [p for p, h in self.path_to_hash.items() if h == index_key]
            for path in paths_to_remove:
                del self.path_to_hash[path]
            self._save_notes()
            self.logger.update_logs("[NOTE DELETED]", f"Note deleted for file: {file_key}")
            return True
        return False

    def list_notes(self):
        """Return all notes as a list of (index_hash, note_data) tuples, sorted by timestamp."""
        return list(sorted(self.notes.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True))

    def search_notes(self, query):
        """
        Search notes by text, tags, mood, context, file paths, or index_hash.
        Returns: list of (index_hash, note_data) tuples
        """
        q = query.lower()
        results = []

        for index_hash, data in self.notes.items():
            note_text = (data.get("note") or "").lower()
            mood = (data.get("mood") or "").lower()
            context = (data.get("context") or "").lower()
            tags = ",".join(data.get("tags", [])).lower()
            file_paths = data.get("file_paths", set())

            if (
                q in note_text
                or q in tags
                or q in mood
                or q in context
                or q in index_hash.lower()
                or any(q in p.lower() for p in file_paths)
            ):
                results.append((index_hash, data))

        return sorted(
            results,
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True
        )


    def search_notes_by_keys(
        self,
        query,
        allowed_keys,
        match_threshold=0.7,
        allowed_hashes=None,
        return_paths=True
    ):
        """
        Search notes within allowed fingerprints.
        Returns index_hashes or file paths.
        """

        query_words = query.lower().split()
        if not query_words:
            return []

        resolved_hashes = set(allowed_hashes or [])

        for file_path in allowed_keys:
            hash_key = self.path_to_hash.get(file_path)

            if not hash_key:
                hash_key = self._resolve_key(file_path)
                if not hash_key:
                    continue 
                self.path_to_hash[file_path] = hash_key

            resolved_hashes.add(hash_key)

        if not resolved_hashes:
            return []

        results = set() if return_paths else []

        for index_hash, data in self.notes.items():
            if index_hash not in resolved_hashes:
                continue

            note_text = data.get("note") or ""
            mood_text = data.get("mood") or ""
            context_text = data.get("context") or ""
            tags_list = data.get("tags") or []
            
            combined_text = " ".join([
                note_text,
                " ".join(str(tag) for tag in tags_list if tag),
                mood_text,
                context_text,
                index_hash or ""
            ]).lower()

            match_count = sum(word in combined_text for word in query_words)
            match_ratio = match_count / len(query_words)

            if match_ratio >= match_threshold:
                if return_paths:
                    file_paths = data.get("file_paths") or set()
                    results.update(file_paths)
                else:
                    results.append(index_hash)

        return list(results) if return_paths else results
    
    def get_nones_in_key(self, key="file_paths"):
        hashes = []
        for key, data in self.notes.items():
            if data.get(key) is None:
                hashes.append(key)
        return hashes

    def get_note_by_hash(self, index_hash: str) -> dict | None:
        """
        Return note data for a given fingerprint hash.
        Does NOT expose internal storage.
        """
        return self.notes.get(index_hash)

    def get_note_display_info(self, index_hash: str) -> dict | None:
        data = self.notes.get(index_hash)
        if not data:
            return None

        return {
            "note": data.get("note", ""),
            "rating": data.get("rating"),
            "tags": data.get("tags", []),
            "mood": data.get("mood", ""),
            "context": data.get("context", ""),
            "timestamp": data.get("timestamp", ""),
            "path_count": len(data.get("file_paths", set())),
            "file_paths": list(data.get("file_paths", set()))
        }



    def search_notes_by_file_paths(self, query, file_paths, match_threshold=0.7):
        """
        Search notes by query, but only within specific file paths.
        Returns matching index_hashes with their associated file_paths.
        
        This is useful when you want to see which file paths matched a query.
        
        Args:
            query: Search query string
            file_paths: List of file paths to search within
            match_threshold: Minimum ratio of query words that must match
        
        Returns:
            List of (index_hash, note_data, matching_file_paths) tuples
        """
        query_words = query.lower().split()
        if not query_words:
            return []

        hash_to_paths = {}
        for file_path in file_paths:
            hash_key = self.path_to_hash.get(file_path) or self._resolve_key(file_path)
            if hash_key not in hash_to_paths:
                hash_to_paths[hash_key] = set()
            hash_to_paths[hash_key].add(file_path)
            if hash_key != file_path:
                self.path_to_hash[file_path] = hash_key

        results = []

        for key, data in self.notes.items():
            if key not in hash_to_paths:
                continue

            text_fields = [
                data.get("note") or "",
                " ".join(data.get("tags", [])),
                data.get("mood") or "",
                data.get("context") or "",
                key
            ]
            combined_text = " ".join(text_fields).lower()

            match_count = sum(1 for word in query_words if word in combined_text)
            match_ratio = match_count / len(query_words)

            if match_ratio >= match_threshold:
                matching_paths = list(hash_to_paths[key])
                results.append((key, data, matching_paths))

        return sorted(results, key=lambda x: x[1].get("timestamp", ""), reverse=True)

    def get_notes_by_tag(self, tag):
        """Return all notes that have a specific tag."""
        tag = tag.lower()
        return [
            (key, data)
            for key, data in self.notes.items()
            if tag in [t.lower() for t in data.get("tags", [])]
        ]

    def get_notes_by_rating(self, min_rating=1):
        """Return all notes with rating >= min_rating."""
        return [
            (key, data)
            for key, data in self.notes.items()
            if data.get("rating") is not None and data["rating"] >= min_rating
        ]

    def get_recent_notes(self, n=10):
        """Return the n most recently added/edited notes."""
        sorted_notes = sorted(
            self.notes.items(),
            key=lambda item: item[1].get("timestamp", ""),
            reverse=True
        )
        return sorted_notes[:n]

    def get_all_file_paths(self):
        """Return all file paths that have notes."""
        paths = set()
        for data in self.notes.values():
            paths.update(data.get("file_paths", []))
        return list(paths)


    def get_all_index_hashes(self):
        """Return a list of all index_hash keys with notes."""
        return list(self.notes.keys())

    def get_notes_by_mood(self, mood):
        """Return all notes with a specific mood."""
        mood = mood.lower()
        return [
            (key, data)
            for key, data in self.notes.items()
            if data.get("mood", "").lower() == mood
        ]

    def get_notes_by_context(self, context):
        """Return all notes with a specific context."""
        context = context.lower()
        return [
            (key, data)
            for key, data in self.notes.items()
            if context in (data.get("context", "")).lower()
        ]

    def get_notes_in_date_range(self, start_date, end_date):
        """
        Return all notes with timestamps between start_date and end_date (inclusive).
        Dates should be ISO format strings (YYYY-MM-DD).
        """
        results = []
        for key, data in self.notes.items():
            ts = data.get("timestamp", "")
            if ts:
                date_part = ts[:10]
                if start_date <= date_part <= end_date:
                    results.append((key, data))
        return results

    def get_notes_with_empty_note(self):
        """Return all notes where the note/comment is empty."""
        return [
            (key, data)
            for key, data in self.notes.items()
            if not data.get("note")
        ]

    def get_notes_count(self):
        """Return the total number of unique notes (by hash)."""
        return len(self.notes)

    def get_field_by_hash(self, index_hash, field):
        data = self.notes.get(index_hash)
        if data:
            return data.get(field)
        return None

    def get_field_by_path(self, file_path, field):
        index_hash = self.path_to_hash.get(file_path) or self._resolve_key(file_path)
        if not index_hash:
            return None
        return self.get_field_by_hash(index_hash, field)

    def get_hash_path_count(self, index_hash: str) -> int:
        """
        Get the count of file paths associated with a specific index_hash.
        Fast O(1) operation since file_paths is a set.
        
        Args:
            index_hash: The fingerprint hash
        
        Returns:
            int: Number of file paths for this hash (0 if hash not found)
        """
        if index_hash in self.notes:
            return len(self.notes[index_hash].get("file_paths", set()))
        return 0

    def get_notes_with_counts(self):
        """
        Return all notes with their path counts included.
        Useful for display purposes where you want to show multi-path info.
        
        Returns:
            List of (index_hash, note_data, path_count) tuples
        """
        return [
            (key, data, len(data.get("file_paths", set())))
            for key, data in sorted(self.notes.items(), 
                                    key=lambda x: x[1].get("timestamp", ""), 
                                    reverse=True)
        ]

    def get_display_info_for_hash(self, index_hash: str) -> dict:
        """
        Get display information for a hash (short hash + path count).
        Useful for UI display showing hash identity and duplicate count.
        
        Args:
            index_hash: The fingerprint hash
        
        Returns:
            dict: {
                'short_hash': First 8 chars of hash,
                'path_count': Number of paths,
                'paths': Set of file paths
            }
        """
        if index_hash in self.notes:
            data = self.notes[index_hash]
            paths = data.get("file_paths", set())
            return {
                'short_hash': index_hash[:8] if index_hash else "unknown",
                'path_count': len(paths),
                'paths': paths
            }
        return {
            'short_hash': index_hash[:8] if index_hash else "unknown",
            'path_count': 0,
            'paths': set()
        }

    def update_note_key(self, old_key, new_key):
        """
        Update a note's file path from old_path to new_path.
        The note remains under the same index_hash; the hash is not changed.
        """
        old_path = old_key
        new_path = new_key
        index_hash = self.path_to_hash.get(old_path) or self._resolve_key(old_path)
        if not index_hash or index_hash not in self.notes:
            return False

        note_entry = self.notes[index_hash]

        if old_path in note_entry["file_paths"]:
            note_entry["file_paths"].remove(old_path)
        note_entry["file_paths"].add(new_path)

        del self.path_to_hash[old_path]
        self.path_to_hash[new_path] = index_hash

        self._save_notes()
        self.logger.update_logs("[NOTE PATH UPDATED]", f"Path updated from {old_path} to {new_path}")
        return True


    def migrate_notes_add_index_hash(
        self,
        fingerprint_manager,
        dry_run: bool = False
    ):
        """
        One-time migration:
        - Adds index_hash to existing notes using MediaFingerprintManager
        - Only fills missing index_hash values
        - Safe to re-run
        - If dry_run=True, does not write changes

        Returns:
            dict: {
                "updated": int,
                "skipped": int,
                "missing_fingerprint": int
            }
        """

        if not os.path.exists(self.notes_file):
            print("No notes CSV found. Migration skipped.")
            return

        updated = 0
        skipped = 0
        missing = 0

        tmp_file = self.notes_file + ".migrating"

        with open(self.notes_file, "r", encoding="utf-8", newline="") as src, \
            open(tmp_file, "w", encoding="utf-8", newline="") as dst:

            reader = csv.DictReader(src)

            fieldnames = reader.fieldnames or []
            if "index_hash" not in fieldnames:
                fieldnames = ["index_hash"] + fieldnames

            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                if row.get("index_hash"):
                    skipped += 1
                    writer.writerow(row)
                    continue

                file_path = row.get("file_path")
                if not file_path:
                    writer.writerow(row)
                    skipped += 1
                    continue

                index_hash = fingerprint_manager.get_index_hash_by_path(file_path)

                if index_hash:
                    row["index_hash"] = index_hash
                    updated += 1
                    self.logger.update_logs(
                        "[NOTES MIGRATION]",
                        f"Added index_hash {index_hash} for {file_path}"
                    )
                else:
                    missing += 1
                    row["index_hash"] = ""
                    self.logger.update_logs(
                        "[NOTES MIGRATION - NO FP]",
                        f"No fingerprint found for {file_path}"
                    )

                writer.writerow(row)

        if dry_run:
            os.remove(tmp_file)
            print("Dry run completed. No changes written.")
        else:
            os.replace(tmp_file, self.notes_file)
            print("Notes migration completed.")

        return {
            "updated": updated,
            "skipped": skipped,
            "missing_fingerprint": missing
        }


if __name__ == "__main__":
    fingerprint_manager = MediaFingerprintManager()
    notes_manager = NotesManager(fingerprint_manager)
    # notes_manager.search_notes_by_keys(query="Proud", allowed_keys=[])
    # print(notes_manager.get_none_paths())
    # notes_manager.migrate_notes_add_index_hash(fingerprint_manager=fingerprint_manager)