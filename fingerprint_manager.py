import csv
import os
import hashlib
import tempfile
from typing import Dict, List, Optional
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
        self.paths: Dict[str, List[str]] = {}

        self._load_from_csv()
        self._load_paths()

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
                    self.paths.setdefault(row["index_hash"], []).append(row["file_path"])
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
        """Save all paths back to CSV (atomic)."""
        rows = []
        for h, paths in self.paths.items():
            for p in paths:
                rows.append({"index_hash": h, "file_path": p})

        _atomic_save_csv(
            self.paths_file,
            ["index_hash", "file_path"],
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
            if file_path not in self.paths.get(index_hash, []):
                self.paths.setdefault(index_hash, []).append(file_path)
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

        self.paths.setdefault(index_hash, []).append(file_path)

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
        """Get all file paths for a given fingerprint."""
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
        duplicates = {h: paths for h, paths in self.paths.items() if len(paths) > 1}
        return duplicates
    
    def get_index_hash_by_path(self, file_path: str) -> Optional[str]:
        """
        Given a file path, return its associated index_hash.
        Returns None if not found.
        """
        for index_hash, paths in self.paths.items():
            if file_path in paths:
                return index_hash
        return None
    
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
        return self.paths.get(index_hash, [])
    
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


if __name__ == "__main__":
    manager = MediaFingerprintManager()
    # dupes = manager.get_duplicates()

    # print(len(dupes))

    # Find by exact duration
    print(manager.get_hashes_by_duration(123.452))

    # Find by duration with tolerance (0.01 sec)
    # print(manager.get_hashes_by_duration(123.452, tolerance=0.01))

    print(manager.get_groups_by_duration())

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