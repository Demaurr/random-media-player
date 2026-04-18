import csv
import os
from typing import Any
import uuid
from datetime import datetime
from fingerprint_manager import MediaFingerprintManager
from collections import defaultdict
from logs_writer import LogManager
from static_methods import create_csv_file
from player_constants import ANNOTATIONS_CSV, ANNOTATIONS_LOG_PATH, CSV_CONFIG

class AnnotationsManager:
    """
    Manages video annotations/pointers tied to specific timestamps.
    Annotations are saved per video fingerprint with timestamp markers.
    
    Structure:
    - Primary key: index_hash (video fingerprint)
    - Annotations: List of timestamped annotations per video
    - Each annotation has: timestamp (seconds), text, created_at
    - Persisted in CSV for long-term storage
    """

    def __init__(self, fingerprint_manager=None):
        """
        Initialize the annotations manager.
        
        Args:
            fingerprint_manager: MediaFingerprintManager instance
        """
        self.annotations_file = ANNOTATIONS_CSV
        self.log_path = ANNOTATIONS_LOG_PATH
        
        # create_csv_file(filename=ANNOTATIONS_CSV, headers=self.FIELDNAMES)
        self.logger = LogManager(ANNOTATIONS_LOG_PATH)
        self._headers = CSV_CONFIG[ANNOTATIONS_CSV]["headers"]
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        
        self.annotations: dict[str, list] = {}
        self.annotation_ids: dict[str, str] = {}
        self.path_to_hash: dict[str, str] = {}
        self._text_index = defaultdict(list)
        
        self._load_annotations()

    def _create_db(self):
        create_csv_file(filename=ANNOTATIONS_CSV, headers=self._headers)

    def _load_annotations(self):
        """Load all annotations from CSV."""
        if not os.path.exists(self.annotations_file):
            return

        try:
            with open(self.annotations_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    annotation_id = row.get("annotation_id")
                    index_hash = row.get("index_hash")
                    file_path = row.get("file_path")
                    
                    if not annotation_id or not index_hash:
                        continue
                    
                    self.annotation_ids[annotation_id] = index_hash
                    if file_path:
                        self.path_to_hash[file_path] = index_hash
                    
                    if index_hash not in self.annotations:
                        self.annotations[index_hash] = []
                    
                    annotation = {
                        "annotation_id": annotation_id,
                        "timestamp_seconds": float(row.get("timestamp_seconds", 0)),
                        "annotation_text": row.get("annotation_text", ""),
                        "created_at": row.get("created_at", ""),
                        "modified_at": row.get("modified_at", ""),
                        "file_path": file_path
                    }
                    self.annotations[index_hash].append(annotation)
                
                for hash_key in self.annotations:
                    self.annotations[hash_key].sort(key=lambda x: x["timestamp_seconds"])
                
                for hash_key in self.annotations:
                    for annotation in self.annotations[hash_key]:
                        text = annotation["annotation_text"].lower()
                        for word in text.split():
                            self._text_index[word].append(annotation["annotation_id"])
                    
        except Exception as e:
            self.logger.error_logs(f"Error loading annotations: {e}")

    def _save_annotations(self):
        """Save all annotations to CSV."""
        try:
            with open(self.annotations_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                
                for index_hash, annotations_list in self.annotations.items():
                    for annotation in annotations_list:
                        writer.writerow({
                            "annotation_id": annotation["annotation_id"],
                            "index_hash": index_hash,
                            "file_path": annotation.get("file_path", ""),
                            "timestamp_seconds": annotation["timestamp_seconds"],
                            "annotation_text": annotation["annotation_text"],
                            "created_at": annotation.get("created_at", ""),
                            "modified_at": annotation.get("modified_at", "")
                        })
        except Exception as e:
            self.logger.error_logs(f"Error saving annotations: {e}")

    def _resolve_hash(self, file_path: str) -> str:
        """Resolve file path to index_hash."""
        if file_path in self.path_to_hash:
            return self.path_to_hash[file_path]
        
        if self.fingerprint_manager:
            hash_val = self.fingerprint_manager.get_index_hash_by_path(file_path)
            if hash_val:
                self.path_to_hash[file_path] = hash_val
                return hash_val
        
        return None

    def add_annotation(self, file_path: str, timestamp_seconds: float, 
                      annotation_text: str) -> str:
        """
        Add a new annotation to a video.
        
        Args:
            file_path: Path to video file
            timestamp_seconds: Timestamp in seconds where annotation is placed
            annotation_text: Text content of annotation
        
        Returns:
            annotation_id of the created annotation
        """
        index_hash = self._resolve_hash(file_path)
        if not index_hash:
            self.logger.error_logs(f"Cannot resolve hash for file: {file_path}")
            return None
        
        annotation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if index_hash not in self.annotations:
            self.annotations[index_hash] = []
        
        annotation = {
            "annotation_id": annotation_id,
            "timestamp_seconds": float(timestamp_seconds),
            "annotation_text": annotation_text,
            "created_at": now,
            "modified_at": now,
            "file_path": file_path
        }
        
        self.annotations[index_hash].append(annotation)
        self.annotations[index_hash].sort(key=lambda x: x["timestamp_seconds"])
        
        self.annotation_ids[annotation_id] = index_hash
        self.path_to_hash[file_path] = index_hash
        
        self._save_annotations()
        self.logger.update_logs(
            "[ANNOTATION ADDED]",
            f"File: {file_path}, Time: {timestamp_seconds}s, Text: {annotation_text}"
        )
        
        return annotation_id

    def get_annotations_for_file(self, file_path: str) -> list:
        """Get all annotations for a specific file."""
        index_hash = self._resolve_hash(file_path)
        if not index_hash:
            return []
        
        return self.get_annotations_for_hash(index_hash)

    def get_annotations_for_hash(self, index_hash: str) -> list:
        """Get all annotations for a specific video hash."""
        annotations = self.annotations.get(index_hash, [])
        return sorted(annotations, key=lambda x: x["timestamp_seconds"])

    def get_annotation_by_id(self, annotation_id: str) -> dict:
        """Get specific annotation by ID."""
        index_hash = self.annotation_ids.get(annotation_id)
        if not index_hash:
            return {}
        
        for annotation in self.annotations.get(index_hash, []):
            if annotation["annotation_id"] == annotation_id:
                return annotation
        
        return {}

    def update_annotation(self, annotation_id: str, annotation_text: str = None) -> bool:
        """Update annotation text."""
        annotation = self.get_annotation_by_id(annotation_id)
        if not annotation:
            return False
        
        if annotation_text is not None:
            annotation["annotation_text"] = annotation_text
        
        annotation["modified_at"] = datetime.now().isoformat()
        
        self._save_annotations()
        self.logger.update_logs("[ANNOTATION UPDATED]", f"ID: {annotation_id}")
        
        return True

    def delete_annotation(self, annotation_id: str) -> bool:
        """Delete an annotation by ID."""
        index_hash = self.annotation_ids.get(annotation_id)
        if not index_hash:
            return False
        
        annotations_list = self.annotations.get(index_hash, [])
        original_len = len(annotations_list)
        
        self.annotations[index_hash] = [
            a for a in annotations_list
            if a["annotation_id"] != annotation_id
        ]
        
        if len(self.annotations[index_hash]) < original_len:
            del self.annotation_ids[annotation_id]
            self._save_annotations()
            self.logger.update_logs("[ANNOTATION DELETED]", f"ID: {annotation_id}")
            return True
        
        return False

    def delete_all_annotations_for_file(self, file_path: str) -> int:
        """Delete all annotations for a file. Returns count deleted."""
        index_hash = self._resolve_hash(file_path)
        if not index_hash or index_hash not in self.annotations:
            return 0
        
        deleted_count = len(self.annotations[index_hash])
        
        for annotation in self.annotations[index_hash]:
            ann_id = annotation["annotation_id"]
            if ann_id in self.annotation_ids:
                del self.annotation_ids[ann_id]
        
        del self.annotations[index_hash]
        self._save_annotations()
        
        self.logger.update_logs(
            "[ANNOTATIONS CLEARED]",
            f"File: {file_path}, Deleted: {deleted_count}"
        )
        
        return deleted_count

    def get_annotation_timestamps(self, file_path: str) -> list[float]:
        """Get list of all annotation timestamps for a file (in seconds)."""
        annotations = self.get_annotations_for_file(file_path)
        return [a["timestamp_seconds"] for a in annotations]

    def has_annotation_at_timestamp(self, file_path: str, timestamp_seconds: float,
                                   tolerance: float = 1.0) -> bool:
        """
        Check if annotation exists near given timestamp.
        
        Args:
            file_path: Video file path
            timestamp_seconds: Timestamp to check
            tolerance: Tolerance in seconds (default 1.0)
        
        Returns:
            True if annotation exists within tolerance
        """
        annotations = self.get_annotations_for_file(file_path)
        for annotation in annotations:
            if abs(annotation["timestamp_seconds"] - timestamp_seconds) <= tolerance:
                return True
        return False

    def find_nearest_annotation(self, file_path: str, 
                               timestamp_seconds: float) -> dict:
        """Find annotation nearest to given timestamp."""
        annotations = self.get_annotations_for_file(file_path)
        if not annotations:
            return None
        
        nearest = min(
            annotations,
            key=lambda a: abs(a["timestamp_seconds"] - timestamp_seconds)
        )
        
        return nearest

    def search_annotations(self, file_path: str, search_text: str) -> list:
        """Search annotations by text content."""
        annotations = self.get_annotations_for_file(file_path)
        search_lower = search_text.lower()
        
        return [
            a for a in annotations
            if search_lower in a["annotation_text"].lower()
        ]

    def search_annotations_for_files(
        self,
        file_paths: list[str],
        text: str,
        return_file_paths: bool = False
    ) -> list:
        """
        Doesn't work correctly as intended. 
        Needs to be reworked to search annotations across multiple files 
        and return either matching annotations or file paths.    
        """

        annotation_ids = self.search_annotations_global(text)

        hashes = {
            self._resolve_hash(p)
            for p in file_paths
            if p
        }

        results = []
        result_paths = set()

        for ann_id in annotation_ids:
            index_hash = self.annotation_ids.get(ann_id)

            if index_hash not in hashes:
                continue

            if return_file_paths:
                annotation = self.get_annotation_by_id(ann_id)
                if annotation:
                    result_paths.add(annotation["file_path"])
            else:
                annotation = self.get_annotation_by_id(ann_id)
                if annotation:
                    results.append(annotation)

        return list(result_paths) if return_file_paths else results
    
    def search_annotations_global(self, search_text: str) -> list[str]:
        """Fast global search across all annotations."""
        if not search_text:
            return []

        words = search_text.lower().split()

        results = []
        for word in words:
            results.extend(self._text_index.get(word, []))

        seen = set()
        unique_ids = []

        for ann_id in results:
            if ann_id not in seen:
                seen.add(ann_id)
                unique_ids.append(ann_id)

        return unique_ids

    def get_stats(self) -> dict:
        """Get statistics about annotations."""
        total_videos = len(self.annotations)
        total_annotations = sum(len(v) for v in self.annotations.values())
        
        return {
            "total_videos_with_annotations": total_videos,
            "total_annotations": total_annotations,
            "average_per_video": (
                total_annotations / total_videos 
                if total_videos > 0 
                else 0
            )
        }

    def export_annotations_for_file(self, file_path: str) -> dict:
        """Export all annotations for a file as structured data."""
        index_hash = self._resolve_hash(file_path)
        if not index_hash:
            return {}
        
        annotations = self.get_annotations_for_hash(index_hash)
        return {
            "file_path": file_path,
            "index_hash": index_hash,
            "annotation_count": len(annotations),
            "annotations": annotations
        }

    def clear_all(self):
        """Clear all annotations (use with caution)."""
        self.annotations.clear()
        self.annotation_ids.clear()
        self.path_to_hash.clear()
        self._save_annotations()
        self.logger.update_logs("[WARNING]", "All annotations cleared")

if __name__ == "__main__":
    fm = MediaFingerprintManager()
    am = AnnotationsManager(fingerprint_manager=fm)
    