import csv
import os
from datetime import datetime
from threading import Lock
from collections import defaultdict

from player_constants import CATEGORIES_FILE, LOG_PATH
from static_methods import create_csv_file, measure_time, normalise_path
from logs_writer import LogManager
from fingerprint_manager import MediaFingerprintManager

Logger = LogManager(LOG_PATH)
class CategoryManager:
    """
    Manages file categorization with support for both path-based and fingerprint-based lookups.
    
    CSV Schema: Category Name | File Path | Index Hash | Date Added
    - Index Hash is optional (for files with fingerprints)
    - Path-based lookups are primary and always work
    - Fingerprint lookups are secondary and only work when index_hash is present
    """

    def __init__(self, fingerprint_manager=None):
        self.categories_file = CATEGORIES_FILE
        self.logger = Logger
        self.lock = Lock()
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self._ensure_categories_file()
        self.entries = []
        self.category_to_files = defaultdict(set)
        self.file_to_categories = defaultdict(set)
        self.hash_to_files = defaultdict(set)
        self.file_to_hash = {}
        self._load_entries()

    def _ensure_categories_file(self):
        """Ensure CSV exists with updated headers including index_hash."""
        if not os.path.exists(self.categories_file):
            create_csv_file(
                headers=['Category Name', 'File Path', 'Index Hash', 'Date Added'],
                filename=self.categories_file
            )
        else:
            self._migrate_csv_if_needed()

    def _migrate_csv_if_needed(self):
        """Migrate old CSV format (3 columns) to new format (4 columns with Index Hash)."""
        try:
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                
                if headers and len(headers) == 3 and 'Index Hash' not in headers:
                    rows = list(reader)
                    
                    with open(self.categories_file, 'w', newline='', encoding='utf-8') as out_f:
                        writer = csv.writer(out_f)
                        writer.writerow(['Category Name', 'File Path', 'Index Hash', 'Date Added'])
                        
                        for row in rows:
                            category, file_path, date_added = row
                            index_hash = ""
                            if self.fingerprint_manager:
                                index_hash = self.fingerprint_manager.get_index_hash_by_path(file_path) or ""
                            writer.writerow([category, file_path, index_hash, date_added])
                    
                    self.logger.update_logs('[CATEGORY CSV MIGRATED]', f"Upgraded to new format with fingerprints")
        except Exception as e:
            self.logger.error_logs(f"Error during CSV migration: {e}")

    # @measure_time(print_time=True, logger=Logger)
    def _load_entries(self):
        """Load entries from CSV, supporting both old and new formats."""
        try:
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                headers = next(reader, None)
                
                self.entries = []
                self.category_to_files.clear()
                self.file_to_categories.clear()
                self.hash_to_files.clear()
                self.file_to_hash.clear()
                
                has_hash_column = headers and len(headers) >= 4
                
                for row in reader:
                    if not row or len(row) < 3:
                        continue
                    
                    category = row[0]
                    file_path = normalise_path(row[1])
                    index_hash = row[2] if has_hash_column and len(row) > 2 else ""
                    date_added = row[3] if has_hash_column and len(row) > 3 else row[2]
                    
                    self.entries.append([category, file_path, index_hash, date_added])
                    self.category_to_files[category].add(file_path)
                    self.file_to_categories[file_path].add(category)
                    
                    if index_hash:
                        self.hash_to_files[index_hash].add(file_path)
                        self.file_to_hash[file_path] = index_hash
        except FileNotFoundError:
            self.logger.error_logs(f"Categories file '{self.categories_file}' not found.")
            self._ensure_categories_file()

    def _write_entries(self):
        """Write entries to CSV with all 4 columns."""
        with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Category Name', 'File Path', 'Index Hash', 'Date Added'])
            writer.writerows(self.entries)

    def _resolve_fingerprint(self, file_path: str) -> str:
        """
        Retrieve and cache fingerprint for a file if fingerprint_manager is available.
        Returns the index_hash or empty string if not available.
        """
        if not self.fingerprint_manager:
            return ""
        
        file_path = normalise_path(file_path)
        index_hash = self.fingerprint_manager.get_index_hash_by_path(file_path) or ""
        
        if index_hash:
            self.file_to_hash[file_path] = index_hash
            self.hash_to_files[index_hash].add(file_path)
        
        return index_hash

    def add_to_category(self, category_name: str, file_path: str, index_hash: str = "") -> bool:
        """
        Add a file to a category.
        
        Args:
            category_name: Name of the category
            file_path: Path to the file
            index_hash: Optional fingerprint hash; if not provided, will be auto-retrieved
        
        Returns:
            True if added, False if already exists
        """
        with self.lock:
            file_path = normalise_path(file_path)
            
            if file_path in self.category_to_files.get(category_name, set()):
                return False
            
            if not index_hash:
                index_hash = self._resolve_fingerprint(file_path)
            else:
                self.file_to_hash[file_path] = index_hash
                self.hash_to_files[index_hash].add(file_path)
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.entries.append([category_name, file_path, index_hash, now])
            self.category_to_files[category_name].add(file_path)
            self.file_to_categories[file_path].add(category_name)
            self._write_entries()
            self.logger.update_logs('[CATEGORY ADDED]', f"'{file_path}' (hash: {index_hash[:8] if index_hash else 'N/A'}) to '{category_name}'")
            return True

    def remove_from_category(self, category_name: str, file_path: str) -> bool:
        """Remove a file from a category."""
        with self.lock:
            file_path = normalise_path(file_path)
            before = len(self.entries)
            self.entries = [row for row in self.entries if not (row[0] == category_name and row[1] == file_path)]
            after = len(self.entries)
            
            if after < before:
                self.category_to_files[category_name].discard(file_path)
                self.file_to_categories[file_path].discard(category_name)
                
                if file_path not in self.file_to_categories or not self.file_to_categories[file_path]:
                    old_hash = self.file_to_hash.pop(file_path, None)
                    if old_hash:
                        self.hash_to_files[old_hash].discard(file_path)
                
                self._write_entries()
                self.logger.update_logs('[CATEGORY REMOVED]', f"Removed '{file_path}' from '{category_name}'")
                return True
            return False
        
    # @measure_time(print_time=True, logger=Logger)
    def get_category_files(self, category_name: str) -> list:
        """Get all files in a category (by path)."""
        return list(self.category_to_files.get(category_name, []))

    # @measure_time(print_time=True, logger=Logger)
    def get_all_categories(self) -> set:
        """Get all category names."""
        return set(self.category_to_files.keys())

    def is_file_in_category(self, category_name: str, file_path: str) -> bool:
        """Check if a file is in a category (by path)."""
        return normalise_path(file_path) in self.category_to_files.get(category_name, set())

    def is_hash_in_category(self, category_name: str, index_hash: str) -> bool:
        """
        Check if any file with a given fingerprint is in a category.
        Returns True if any path with this hash is in the category.
        """
        files_with_hash = self.hash_to_files.get(index_hash, set())
        category_files = self.category_to_files.get(category_name, set())
        return bool(files_with_hash.intersection(category_files))

    def get_files_by_hash_in_category(self, category_name: str, index_hash: str) -> list:
        """Get all files with a given fingerprint in a specific category."""
        files_with_hash = self.hash_to_files.get(index_hash, set())
        category_files = self.category_to_files.get(category_name, set())
        return list(files_with_hash.intersection(category_files))

    def rename_category(self, old_name: str, new_name: str, merge: bool = False) -> tuple[bool, str]:
        """Rename or merge a category."""
        with self.lock:
            if new_name in self.category_to_files and not merge:
                msg = f"Category '{new_name}' already exists. Use merge option if you want to combine categories."
                self.logger.error_logs(f"Cannot rename category '{old_name}' to '{new_name}': Already exists")
                return False, msg

            if old_name not in self.category_to_files:
                return False, f"Category '{old_name}' not found"

            if merge:
                merged_files = self.category_to_files[old_name].union(self.category_to_files.get(new_name, set()))
                self._remove_category_entries(old_name)
                self._remove_category_entries(new_name)
                for file_path in merged_files:
                    index_hash = self.file_to_hash.get(file_path, "")
                    self.entries.append([new_name, file_path, index_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                    self.category_to_files[new_name].add(file_path)
                    self.file_to_categories[file_path].add(new_name)
                self._write_entries()
                self.logger.update_logs('[CATEGORY MERGED]', f"Merged '{old_name}' into '{new_name}'")
                return True, f"Merged '{old_name}' into '{new_name}'"

            # Rename without merge
            for row in self.entries:
                if row[0] == old_name:
                    row[0] = new_name
            self.category_to_files[new_name] = self.category_to_files.pop(old_name)
            for file in self.category_to_files[new_name]:
                self.file_to_categories[file].discard(old_name)
                self.file_to_categories[file].add(new_name)

            self._write_entries()
            self.logger.update_logs('[CATEGORY RENAMED]', f"Renamed '{old_name}' to '{new_name}'")
            return True, f"Renamed '{old_name}' to '{new_name}'"

    def _remove_category_entries(self, category_name: str):
        """Remove all entries for a category."""
        old_entries = self.entries.copy()
        self.entries = [row for row in self.entries if row[0] != category_name]
        
        for row in old_entries:
            if row[0] == category_name:
                file_path = row[1]
                if file_path not in self.file_to_categories or not self.file_to_categories[file_path]:
                    old_hash = self.file_to_hash.pop(file_path, None)
                    if old_hash:
                        self.hash_to_files[old_hash].discard(file_path)
        
        for file in self.category_to_files[category_name]:
            self.file_to_categories[file].discard(category_name)
        self.category_to_files.pop(category_name, None)

    def delete_category(self, category_name: str) -> bool:
        """Delete a category and all its associations."""
        with self.lock:
            if category_name not in self.category_to_files:
                return False
            file_count = len(self.category_to_files[category_name])
            self._remove_category_entries(category_name)
            self._write_entries()
            self.logger.update_logs('[CATEGORY DELETED]', f"Deleted category '{category_name}' with {file_count} files")
            return True

    def get_file_categories(self, file_path: str) -> list:
        """Get all categories for a file (by path)."""
        return list(self.file_to_categories.get(normalise_path(file_path), []))

    def get_categories_by_hash(self, index_hash: str) -> list:
        """
        Get all categories that contain any file with a given fingerprint.
        """
        files_with_hash = self.hash_to_files.get(index_hash, set())
        categories = set()
        for file_path in files_with_hash:
            categories.update(self.file_to_categories.get(file_path, set()))
        return sorted(categories)

    # @measure_time(print_time=True, logger=Logger)
    def get_all_categories_with_dates(self) -> list:
        """Get all categories with their latest modification date."""
        latest_dates = {}
        for row in self.entries:
            category = row[0]
            date = row[3]
            if category not in latest_dates or date > latest_dates[category]:
                latest_dates[category] = date
        return sorted(latest_dates.items(), key=lambda x: x[1], reverse=True)

    def get_categories_of_files(self, file_path: str) -> list:
        """Get sorted categories for a file."""
        return sorted(self.file_to_categories.get(normalise_path(file_path), []))

    def update_file_path(self, old_path: str, new_path: str) -> bool:
        """
        Update a file path in categories (e.g., after moving a file).
        The fingerprint hash remains unchanged since it's based on content, not location.
        
        Args:
            old_path: Previous file path
            new_path: New file path
        
        Returns:
            True if updated, False if old_path not found
        """
        with self.lock:
            old_path = normalise_path(old_path)
            new_path = normalise_path(new_path)
            
            updated = False
            for row in self.entries:
                if row[1] == old_path:
                    row[1] = new_path
                    
                    old_hash = self.file_to_hash.pop(old_path, "")
                    if old_hash:
                        row[2] = old_hash
                        self.hash_to_files[old_hash].discard(old_path)
                        self.hash_to_files[old_hash].add(new_path)
                        self.file_to_hash[new_path] = old_hash
                    
                    updated = True
            
            if updated:
                self.category_to_files = defaultdict(set)
                self.file_to_categories = defaultdict(set)
                for row in self.entries:
                    self.category_to_files[row[0]].add(row[1])
                    self.file_to_categories[row[1]].add(row[0])
                
                self._write_entries()
                self.logger.update_logs('[CATEGORY PATH UPDATED]', f"{old_path} -> {new_path}")
                return True
            
            return False

    def search_categories_by_keys(self, query: str, allowed_keys: list[str] = None) -> list[str]:
        """
        Search for files in categories based on query matching category name or file path.
        Optionally restrict search to allowed_keys.
        """
        if not query:
            return []

        words = query.lower().split()
        allowed_keys_set = set(normalise_path(k) for k in allowed_keys) if allowed_keys else None
        results = set()

        for category, file_paths in self.category_to_files.items():
            category_lc = category.lower()

            for file_path in file_paths:
                if allowed_keys_set and file_path not in allowed_keys_set:
                    continue

                file_path_lc = file_path.lower()
                combined_text = f"{category_lc} {file_path_lc}"

                if all(word in combined_text for word in words):
                    results.add(file_path)

        return sorted(results)

    def get_category_stats(self) -> dict:
        """
        Get statistics about categories.
        
        Returns:
            dict with keys: total_categories, total_files, avg_files_per_category, 
                           categories_with_fingerprints, categories_without_fingerprints
        """
        total_cats = len(self.category_to_files)
        total_files = len(self.file_to_categories)
        with_hashes = len([f for f in self.file_to_hash.values() if f])
        without_hashes = total_files - with_hashes
        
        return {
            "total_categories": total_cats,
            "total_files": total_files,
            "avg_files_per_category": total_files / total_cats if total_cats > 0 else 0,
            "files_with_fingerprints": with_hashes,
            "files_without_fingerprints": without_hashes,
        }
    
if __name__ == "__main__":
    # Simple test code
    from fingerprint_manager import MediaFingerprintManager
    fm = MediaFingerprintManager()
    cat_mgr = CategoryManager(fingerprint_manager=fm)
    cat_mgr._migrate_csv_if_needed()
    # print(cat_mgr.get_category_stats())
    # print(cat_mgr.get_all_categories())
    # print(cat_mgr.get_all_categories_with_dates())
    # cat_mgr.add_to_category("Testing", r"C:\Users\dever\From C Drive\Videos\Reddit\RDT_20230521_193934(2).mp4")
    # print(cat_mgr.get_category_files("Testing"))
    # success, msg = cat_mgr.rename_category(
    #                 old_name="Testing",
    #                 new_name="New_Testing"
    #             )
    # print(success, msg)
    # stats = cat_mgr._migrate_csv_if_needed()
    # stats = cat_mgr.migrate_to_fingerprint_format()
    # print(f"Migration complete: {stats['migrated_count']} entries, {stats['hashes_found']} hashes found")