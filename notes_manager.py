import csv
import os
from datetime import datetime
from player_constants import NOTES_CSV, NOTES_LOG_PATH
from static_methods import create_csv_file, get_file_transfer_history
from logs_writer import LogManager

class NotesManager:
    """
    Manages notes, comments, and metadata for files.
    Stores data in a CSV file for persistence and fast retrieval.
    """

    FIELDNAMES = [
        "file_path", "note", "rating", "tags", "mood", "context", "timestamp"
    ]

    def __init__(self):
        self.notes_file = NOTES_CSV
        create_csv_file(filename=self.notes_file, headers=self.FIELDNAMES)
        self.notes = {}
        self.logger = LogManager(NOTES_LOG_PATH)
        self._load_notes()

    def _load_notes(self):
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r", encoding="utf-8", newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_key = row["file_path"]
                    self.notes[file_key] = {
                        "note": row.get("note", ""),
                        "rating": self._parse_rating(row.get("rating")),
                        "tags": self._parse_tags(row.get("tags")),
                        "mood": row.get("mood", ""),
                        "context": row.get("context", ""),
                        "timestamp": row.get("timestamp", "")
                    }

    def _save_notes(self):
        with open(self.notes_file, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for file_key, data in self.notes.items():
                writer.writerow({
                    "file_path": file_key,
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

    def get_note(self, file_key):
        """
        Get the merged note and metadata for all related paths of a file.
        Merges notes from all paths (by file name) in the transfer history.
        """
        history = get_file_transfer_history(file_key)
        related_paths = set()
        for k in ['previous', 'current', 'destination']:
            if history.get(k):
                related_paths.add(history[k])

        # Combine with notes from other paths with the same file name
        file_name = os.path.basename(file_key)
        for key in self.notes.keys():
            if os.path.basename(key) == file_name:
                related_paths.add(key)

        merged_note = ""
        merged_data = None
        notes_found = []

        for path in related_paths:
            note_data = self.notes.get(path)
            if note_data and note_data.get("note"):
                notes_found.append((path, note_data))

        if not notes_found:
            return self.notes.get(file_key)

        merged_note = "\n---\n".join(nd["note"] for _, nd in notes_found if nd.get("note"))
        merged_tags = []
        merged_rating = None
        merged_mood = ""
        merged_context = ""
        latest_timestamp = ""
        for _, nd in notes_found:
            merged_tags.extend(nd.get("tags", []))
            if nd.get("rating") is not None:
                merged_rating = nd.get("rating")
            if nd.get("mood"):
                merged_mood = nd.get("mood")
            if nd.get("context"):
                merged_context = nd.get("context")
            if nd.get("timestamp") and nd.get("timestamp") > latest_timestamp:
                latest_timestamp = nd.get("timestamp")

        merged_data = {
            "note": merged_note,
            "rating": merged_rating,
            "tags": list(set(merged_tags)),
            "mood": merged_mood,
            "context": merged_context,
            "timestamp": latest_timestamp
        }
        return merged_data

    def set_note(self, file_key, note, rating=None, tags=None, mood=None, context=None):
        """
        Add or update a note for a file.
        If there are notes for other paths (with the same file name), move them to the current path.
        """
        history = get_file_transfer_history(file_key)
        related_paths = set()
        for k in ['previous', 'current', 'destination']:
            if history.get(k):
                related_paths.add(history[k])

        file_name = os.path.basename(file_key)
        for key in self.notes.keys():
            if os.path.basename(key) == file_name:
                related_paths.add(key)

        for path in related_paths:
            if path != file_key and path in self.notes:
                self.update_note_key(path, file_key)

        self.notes[file_key] = {
            "note": note,
            "rating": self._parse_rating(rating),
            "tags": self._parse_tags(tags),
            "mood": mood,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        self.logger.update_logs("[NOTES SAVED]", f"[{file_key}] Note saved: {note}, Rating: {rating}, Tags: {tags}, Mood: {mood}, Context: {context}")
        self._save_notes()

    def delete_note(self, file_key):
        """Remove a note for a filePath."""
        if file_key in self.notes:
            del self.notes[file_key]
            self._save_notes()
            self.logger.update_logs("[NOTE DELETED]", f"Note deleted for file: {file_key}")


    def list_notes(self):
        """Return all notes as a list of (file_key, note_data) tuples."""
        return list(self.notes.items())

    def search_notes(self, query):
        """Search notes by text, tags, or mood/context."""
        query = query.lower()
        results = []
        for key, data in self.notes.items():
            if (
                query in (data.get("note") or "").lower()
                or query in ",".join(data.get("tags", [])).lower()
                or query in (data.get("mood") or "").lower()
                or query in (data.get("context") or "").lower()
                or query in key.lower()
            ):
                results.append((key, data))
        return results

    def search_notes_by_keys(self, query, allowed_keys, match_threshold=0.6):
        """
        Search for a query inside notes, tags, mood, context, or key,
        but only within the given list of allowed file keys.
        Uses token-based partial matching: if enough words from the query appear, it's a match.
        """
        query_words = query.lower().split()
        if not query_words:
            return []

        allowed_keys_set = set(allowed_keys)
        results = []

        for key, data in self.notes.items():
            if key not in allowed_keys_set:
                continue

            # Combine searchable text fields
            text_fields = [
                data.get("note") or "",
                " ".join(data.get("tags", [])),
                data.get("mood") or "",
                data.get("context") or "",
                key
            ]
            combined_text = " ".join(text_fields).lower()

            # Count how many query words appear in combined_text
            match_count = sum(1 for word in query_words if word in combined_text)
            match_ratio = match_count / len(query_words)

            if match_ratio >= match_threshold:
                results.append(key)

        return results

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

    def get_all_file_keys(self):
        """Return a list of all file keys with notes."""
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
        """Return the total number of notes stored."""
        return len(self.notes)

    def get_field(self, file_key, field):
        """Return a specific field (e.g., 'rating', 'tags') for the given file_key, or None if not found."""
        note = self.get_note(file_key)
        if note and field in note:
            return note[field]
        return None

    def update_note_key(self, old_key, new_key):
        """
        Move a note from old_key to new_key.
        If a note already exists at new_key, you may want to merge or overwrite.
        """
        if old_key == new_key:
            return
        if old_key in self.notes:
            self.notes[new_key] = self.notes.pop(old_key)
            self._save_notes()
            self.logger.update_logs("[NOTE MOVED]", f"Note moved from {old_key} to {new_key}")