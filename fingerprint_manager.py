import csv
from datetime import datetime
import os
import hashlib
import tempfile
from typing import Dict, List, Optional
import uuid
from player_constants import FINGERPRINTS_CSV, FINGERPRINTS_LOG_PATH, FINGERPRINTS_PATHS_CSV
from logs_writer import LogManager
from static_methods import _atomic_save_csv

class MediaFingerprintManager:
    def __init__(self):
        self.new_files_counter = 0
        self.csv_file = FINGERPRINTS_CSV
        self.paths_file = FINGERPRINTS_PATHS_CSV
        self.logger = LogManager(FINGERPRINTS_LOG_PATH)

        self.fingerprints: Dict[str, Dict] = {}  
        self.paths: Dict[str, List[Dict]] = {}

        # self.refactor_paths_csv()
        self._load_from_csv()
        self._load_paths()
        # self.refactor_fingerprints_round_duration()

    def _load_from_csv(self) -> None:
        """Load existing fingerprints into memory."""
        if not os.path.exists(self.csv_file):
            return
        try:
            with open(self.csv_file, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.fingerprints = {row["index_hash"]: row for row in reader}
        except Exception as e:
            self.logger.error_logs(f"Error loading CSV {self.csv_file}: {e}")
            self.fingerprints = {}

    def _load_paths(self):
        """Load join table mapping index_hash -> file paths."""
        if not os.path.exists(self.paths_file):
            return
        try:
            with open(self.paths_file, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.paths.setdefault(row["index_hash"], []).append({
                        "file_path": row["file_path"],
                        "unique_id": row.get("unique_id", str(uuid.uuid4())),
                        "added_at": row.get("added_at", datetime.now().isoformat())
                    })
        except Exception as e:
            self.logger.error_logs(f"Error loading paths CSV {self.paths_file}: {e}")
            self.paths = {}


    def _save_to_csv(self) -> None:
        """Save all fingerprints back to CSV (atomic)."""
        rows = list(self.fingerprints.values())
        _atomic_save_csv(
            self.csv_file,
            ["name", "duration", "size_bytes", "partial_hash", "index_hash"],
            rows,
        )

    def _save_paths(self) -> None:
        """Save all paths back to CSV (atomic) with unique_id and timestamp."""
        rows = []
        for h, paths_list in self.paths.items():
            for path_entry in paths_list:
                if isinstance(path_entry, dict):
                    # Already has unique_id and timestamp
                    rows.append({
                        "index_hash": h,
                        "file_path": path_entry["file_path"],
                        "unique_id": path_entry["unique_id"],
                        "added_at": path_entry["added_at"]
                    })
                else:
                    entry = {
                        "file_path": path_entry,
                        "unique_id": str(uuid.uuid4()),
                        "added_at": datetime.now().isoformat()
                    }
                    rows.append({"index_hash": h, **entry})
                    paths_list[paths_list.index(path_entry)] = entry

        _atomic_save_csv(
            self.paths_file,
            ["index_hash", "file_path", "unique_id", "added_at"],
            rows,
        )


    def _generate_partial_hash(self, file_path: str, block_size: int = 65536) -> str:
        """
        Generate a partial hash of the file using the first and last block.
        This is very fast and reduces collision chances for large files.
        """
        hasher = hashlib.md5()

        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return ""

            with open(file_path, 'rb') as f:
                first_chunk = f.read(block_size)
                if first_chunk:
                    hasher.update(first_chunk)

                if file_size > block_size:
                    f.seek(-block_size, os.SEEK_END)
                    last_chunk = f.read(block_size)
                    if last_chunk:
                        hasher.update(last_chunk)

        except (FileNotFoundError, PermissionError):
            return ""

        return hasher.hexdigest()

    def _generate_index_hash(self, duration: str, size_bytes: str, partial_hash: str = "", force_partial: bool = False) -> str:
        """Generate a pseudo 'partial hash' based purely on duration and size."""
        key = f"{duration}:{size_bytes}" if not force_partial else f"{duration}:{size_bytes}:{partial_hash}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def add_fingerprint(self, file_path : str, duration: str, size_bytes: str = "", force_partial: bool = False) -> bool:
        if not file_path or not duration or not size_bytes:
            self.logger.error_logs("File path, duration, and size are mandatory for fingerprint creation.")
            return False

        name = os.path.basename(file_path)
        partial_hash = ""

        if not force_partial:
            index_hash = self._generate_index_hash(duration, size_bytes, "", force_partial)
        else:
            partial_hash = self._generate_partial_hash(file_path) if os.path.exists(file_path) else ""
            index_hash = self._generate_index_hash(duration, size_bytes, partial_hash, force_partial)

        if index_hash in self.fingerprints:
            if not any(p["file_path"] == file_path for p in self.paths.get(index_hash, [])):
                self.paths.setdefault(index_hash, []).append({
                    "file_path": file_path,
                    "unique_id": str(uuid.uuid4()),
                    "added_at": datetime.now().isoformat()
                })
                self.logger.update_logs("[PATH ADDED]", f"{file_path} -> {index_hash}")
                self.new_files_counter += 1
            else:
                # self.logger.update_logs("[SKIPPED]", f"Fingerprint already exists for {file_path}")
                pass
            return True

        if not force_partial and os.path.exists(file_path):
            partial_hash = self._generate_partial_hash(file_path)

        entry = {
            "index_hash": index_hash,
            "name": name,
            "duration": duration,
            "size_bytes": size_bytes,
            "partial_hash": partial_hash,
        }
        self.fingerprints[index_hash] = entry
        self.new_files_counter += 1

        self.logger.update_logs("[FINGERPRINT ADDED]", f"{entry}")

        self.paths.setdefault(index_hash, []).append({
                    "file_path": file_path,
                    "unique_id": str(uuid.uuid4()),
                    "added_at": datetime.now().isoformat()
                })

        self.logger.update_logs("[PATH ADDED]", f"{file_path} -> {index_hash}")

        return True
    
    def flush(self):
        self._save_to_csv()
        self._save_paths()
        print(f"Saved {self.new_files_counter} new fingerprints.")


    def get_all_fingerprints(self) -> Dict[str, Dict]:
        return self.fingerprints
    
    def get_fingerprint_by_hash(self, index_hash: str) -> Optional[Dict]:
        """Return a fingerprint by its index_hash, or None if not found."""
        return self.fingerprints.get(index_hash)

    def get_fingerprint_by_name(self, name: str) -> List[Dict]:
        """Return all fingerprints that match the given name."""
        return [fp for fp in self.fingerprints.values() if fp["name"] == name]
    
    def get_paths_by_hash(self, index_hash: str) -> List[str]:
        return [p["file_path"] for p in self.paths.get(index_hash, [])]
    
    def get_paths_info_by_hash(self, index_hash: str) -> List[Dict]:
        return self.paths.get(index_hash, [])

    def get_hash_by_path(self, file_path: str) -> Optional[str]:
        """Find which fingerprint a file belongs to."""
        for index_hash, paths in self.paths.items():
            if file_path in paths:
                return index_hash
        return None


    def delete_fingerprint(self, index_hash: str) -> bool:
        if index_hash in self.fingerprints:
            del self.fingerprints[index_hash]
            self._save_to_csv()
            self.logger.update_logs("[FINGERPRINT DELETED]", f"for {index_hash}")

            if index_hash in self.paths:
                del self.paths[index_hash]
                self._save_paths()
            return True
        return False

    def update_fingerprint(self, index_hash: str, **kwargs) -> Optional[str]:
        """Update fields of a fingerprint by index_hash."""
        fp = self.fingerprints.get(index_hash)
        if not fp:
            return None

        for k, v in kwargs.items():
            if k in fp and v is not None:
                fp[k] = v

        new_index_hash = self._generate_index_hash(fp["duration"], fp["size_bytes"])
        if new_index_hash != index_hash:
            self.fingerprints[new_index_hash] = fp
            del self.fingerprints[index_hash]
            fp["index_hash"] = new_index_hash

        if index_hash in self.paths:
            self.paths[new_index_hash] = self.paths.pop(index_hash)

        self._save_to_csv()
        return fp["index_hash"]

    def find_match(
        self,
        duration: str,
        size_bytes: str = "",
        partial_hash: str = "",
        mode: str = "strict",
    ) -> Optional[Dict]:
        """Find a matching fingerprint."""
        for fp in self.fingerprints.values():
            matches = 0

            if fp["duration"] == duration:
                matches += 2
            if size_bytes and fp["size_bytes"] == size_bytes:
                matches += 1
            if partial_hash and fp["partial_hash"] == partial_hash:
                matches += 4

            if mode == "strict" and matches == 7:
                return fp
            elif mode == "relaxed" and matches == 3:
                return fp
            elif mode == "fuzzy" and matches >= 3:
                return fp
        return None
    
    def get_all_duplicates(self) -> Dict[str, List[str]]:
        """
        Find duplicates: fingerprints (index_hash) that are linked to more than one file path.
        Returns:
            Dict[str, List[str]]: A dictionary where the key is the index_hash,
            and the value is a list of file paths that share the same fingerprint.
        """
        duplicates = {
            h: [p["file_path"] for p in paths]
            for h, paths in self.paths.items() if len(paths) > 1
        }
        return duplicates
    
    def get_index_hash_by_path(self, file_path: str) -> Optional[str]:
        """
        Given a file path, return its associated index_hash.
        Returns None if not found.
        """
        for index_hash, paths in self.paths.items():
            if any(p["file_path"] == file_path for p in paths):
                return index_hash
        return None
    
    def are_files_same(self, path1: str, path2: str) -> bool:
        """
        Check if two file paths map to the same fingerprint (same index_hash).
        Returns True if they have the same index_hash, False otherwise.
        """
        hash1 = self.get_index_hash_by_path(path1)
        hash2 = self.get_index_hash_by_path(path2)

        if hash1 and hash2:
            return hash1 == hash2
        return False
    
    def get_index_hashes_by_path(self, file_paths: List[str]) -> Dict[str, str]:
        result = {}
        for p in file_paths:
            h = self.get_index_hash_by_path(p)
            if h:
                result[p] = h
        return result
    
    def get_duplicates_by_hash(self, index_hash: str) -> List[str]:
        """
        Given an index_hash, return all file paths that share the same fingerprint.
        If there are no duplicates, returns an empty list or a single-item list.
        """
        return [p["file_path"] for p in self.paths.get(index_hash, [])]
    
    def get_unique_id_by_path(self, file_path: str) -> str | None:
        """
        Return the unique_id for a given file path.
        Returns None if the path is not found.
        """
        for entries in self.paths.values():
            for p in entries:
                if p["file_path"] == file_path:
                    return p["unique_id"]
        return None

    def get_path_info_by_file(self, file_path: str) -> dict | None:
        """
        Return the full path entry (file_path, unique_id, added_at, index_hash) by file_path.
        """
        for index_hash, entries in self.paths.items():
            for p in entries:
                if p["file_path"] == file_path:
                    return {
                        "index_hash": index_hash,
                        **p
                    }
        return None
    
    def update_path_info_bypath(self, old_file_path: str, new_file_path: str) -> bool:
        """
        Update the file path for an existing path entry.
        The unique_id and added_at remain unchanged.
        Returns True if updated, False if path not found.
        """
        for entries in self.paths.values():
            for p in entries:
                if p["file_path"] == old_file_path:
                    p["file_path"] = new_file_path
                    # self._save_paths()
                    return True
        return False
    
    def update_path_info_by_id(self, unique_id: str, new_file_path: str) -> bool:
        """
        Update the file path for an existing path entry identified by unique_id.
        The unique_id and added_at remain unchanged.
        Returns True if updated, False if unique_id not found.
        """
        for entries in self.paths.values():
            for p in entries:
                if p["unique_id"] == unique_id:
                    p["file_path"] = new_file_path
                    # self._save_paths()
                    self.logger.update_logs("[PATH UPDATED]", f"{unique_id} -> {new_file_path}")
                    return True
        return False
        
    def get_hashes_by_duration(self, duration: float, tolerance: float = 0.0) -> List[str]:
        """
        Return all index_hashes with the given duration.
        If tolerance > 0, also match durations within +/- tolerance.
        """
        matches = []
        for h, fp in self.fingerprints.items():
            try:
                d = float(fp["duration"])
                if tolerance > 0:
                    if abs(d - duration) <= tolerance:
                        matches.append(h)
                else:
                    if d == duration:
                        matches.append(h)
            except (ValueError, TypeError):
                continue
        return matches

    def get_hashes_by_size(self, size_bytes: int) -> List[str]:
        """
        Return all index_hashes with the same size.
        """
        return [h for h, fp in self.fingerprints.items() if fp.get("size_bytes") == str(size_bytes)]

    def get_duplicate_durations(self, tolerance: float = 0.0) -> Dict[float, List[str]]:
        """
        Find all durations that are shared by more than one fingerprint.
        Returns {duration: [index_hashes]}.
        If tolerance > 0, group durations that are close together.
        """
        duration_map = {}
        for h, fp in self.fingerprints.items():
            try:
                d = float(fp["duration"])
            except (ValueError, TypeError):
                continue

            if tolerance > 0:
                # normalize into a rounded key
                d = round(d / tolerance) * tolerance

            duration_map.setdefault(d, []).append(h)

        return {d: hashes for d, hashes in duration_map.items() if len(hashes) > 1}

    def get_duplicate_sizes(self) -> Dict[int, List[str]]:
        """
        Find all file sizes that are shared by more than one fingerprint.
        Returns {size_bytes: [index_hashes]}.
        """
        size_map = {}
        for h, fp in self.fingerprints.items():
            try:
                s = int(fp["size_bytes"])
            except (ValueError, TypeError):
                continue

            size_map.setdefault(s, []).append(h)

        return {s: hashes for s, hashes in size_map.items() if len(hashes) > 1}

    def get_groups_by_duration(self) -> Dict[str, List[str]]:
        """
        Return a dictionary mapping duration -> list of index_hashes.
        Useful for finding collisions based on duration only.
        """
        groups: Dict[str, List[str]] = {}
        for h, fp in self.fingerprints.items():
            groups.setdefault(fp["duration"], []).append(h)
        return {d: hashes for d, hashes in groups.items() if len(hashes) > 1}

    def get_groups_by_size(self) -> Dict[str, List[str]]:
        """
        Return a dictionary mapping size_bytes -> list of index_hashes.
        """
        groups: Dict[str, List[str]] = {}
        for h, fp in self.fingerprints.items():
            groups.setdefault(fp["size_bytes"], []).append(h)
        return {s: hashes for s, hashes in groups.items() if len(hashes) > 1}

    def get_groups_by_duration_and_size(self) -> Dict[tuple, List[str]]:
        """
        Return a dictionary mapping (duration, size_bytes) -> list of index_hashes.
        This helps find files with the same duration and size but possibly different paths.
        """
        groups: Dict[tuple, List[str]] = {}
        for h, fp in self.fingerprints.items():
            key = (fp["duration"], fp["size_bytes"])
            groups.setdefault(key, []).append(h)
        return {k: hashes for k, hashes in groups.items() if len(hashes) > 1}
    
    def refactor_paths_csv(self):
        """
        Refactor the paths CSV:
        - Ensure each entry has a unique_id and added_at timestamp.
        - Convert old string-only paths to dict format.
        - Remove duplicates based on (index_hash + file_path).
        - Save back atomically.
        """
        if not os.path.exists(self.paths_file):
            print("No paths CSV to refactor.")
            return

        seen = set()
        new_rows = []

        with open(self.paths_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                index_hash = row["index_hash"]
                file_path = row["file_path"]
                key = (index_hash, file_path)

                if key in seen:
                    continue
                seen.add(key)

                unique_id = row.get("unique_id") or str(uuid.uuid4())
                added_at = row.get("added_at") or datetime.now().isoformat()

                new_rows.append({
                    "index_hash": index_hash,
                    "file_path": file_path,
                    "unique_id": unique_id,
                    "added_at": added_at
                })

        _atomic_save_csv(
            self.paths_file,
            ["index_hash", "file_path", "unique_id", "added_at"],
            new_rows
        )

        print(f"Refactored paths CSV with {len(new_rows)} unique entries.")

    def refactor_fingerprints_round_duration(self):
        """
        Refactor fingerprints:
        - Round durations from 3 decimals to 1 decimal.
        - Update index_hashes accordingly.
        - Update paths mapping for new index_hashes.
        """
        new_fingerprints = {}
        new_paths = {}

        for old_index_hash, fp in self.fingerprints.items():
            try:
                rounded_duration = str(round(float(fp["duration"]), 1))
            except (ValueError, TypeError):
                rounded_duration = fp["duration"]

            new_index_hash = self._generate_index_hash(
                rounded_duration,
                fp["size_bytes"],
                fp.get("partial_hash", "")
            )
            new_fp = fp.copy()
            new_fp["duration"] = rounded_duration
            new_fp["index_hash"] = new_index_hash
            new_fingerprints[new_index_hash] = new_fp

            if old_index_hash in self.paths:
                new_paths[new_index_hash] = self.paths.pop(old_index_hash)

        self.fingerprints = new_fingerprints
        self.paths.update(new_paths)

        self._save_to_csv()
        self._save_paths()

        print(f"Refactored {len(new_fingerprints)} fingerprints with rounded durations.")


if __name__ == "__main__":
    manager = MediaFingerprintManager()
    # dupes = manager.get_duplicates()

    # print(len(dupes))

    # Find by exact duration
    # print(manager.get_hashes_by_duration(123.452))

    # Find by duration with tolerance (0.01 sec)
    # print(manager.get_hashes_by_duration(123.452, tolerance=0.01))

    # print(manager.get_groups_by_duration())

    # Find all duplicate durations
    # print(manager.get_duplicate_durations(tolerance=0.01))

    # Find all duplicate sizes
    # print(manager.get_duplicate_sizes())

    # if dupes:
    #     for h, paths in dupes.items():
    #         print(f"Duplicate hash {h} found for:")
    #         for p in paths:
    #             print(f"   - {p}")
    # else:
    #     print("No duplicates found.")