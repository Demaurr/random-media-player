import csv
import os
from datetime import datetime
from threading import Lock
from collections import defaultdict

from player_constants import CATEGORIES_FILE, LOG_PATH
from static_methods import create_csv_file
from logs_writer import LogManager


class CategoryManager:
    def __init__(self):
        self.categories_file = CATEGORIES_FILE
        self.logger = LogManager(LOG_PATH)
        self.lock = Lock()
        self._ensure_categories_file()
        self.entries = []
        self.category_to_files = defaultdict(set)
        self.file_to_categories = defaultdict(set)
        self._load_entries()

    def _ensure_categories_file(self):
        create_csv_file(headers=['Category Name', 'File Path', 'Date Added'], filename=self.categories_file)

    def _load_entries(self):
        try:
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                self.entries = []
                self.category_to_files.clear()
                self.file_to_categories.clear()
                for row in reader:
                    category, file_path, date_added = row
                    self.entries.append(row)
                    self.category_to_files[category].add(file_path)
                    self.file_to_categories[file_path].add(category)
        except FileNotFoundError:
            self.logger.error_logs(f"Categories file '{self.categories_file}' not found.")
            pass

    def _write_entries(self):
        with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Category Name', 'File Path', 'Date Added'])
            writer.writerows(self.entries)

    def add_to_category(self, category_name: str, file_path: str) -> bool:
        with self.lock:
            if file_path in self.category_to_files.get(category_name, set()):
                return False
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.entries.append([category_name, file_path, now])
            self.category_to_files[category_name].add(file_path)
            self.file_to_categories[file_path].add(category_name)
            self._write_entries()
            self.logger.update_logs('[CATEGORY ADDED]', f"'{file_path}' to category '{category_name}'")
            return True

    def remove_from_category(self, category_name: str, file_path: str) -> bool:
        with self.lock:
            before = len(self.entries)
            self.entries = [row for row in self.entries if not (row[0] == category_name and row[1] == file_path)]
            after = len(self.entries)
            if after < before:
                self.category_to_files[category_name].discard(file_path)
                self.file_to_categories[file_path].discard(category_name)
                self._write_entries()
                self.logger.update_logs('[CATEGORY REMOVED]', f"Removed '{file_path}' from category '{category_name}'")
                return True
            return False

    def get_category_files(self, category_name: str) -> list:
        return list(self.category_to_files.get(category_name, []))

    def get_all_categories(self) -> set:
        return set(self.category_to_files.keys())

    def is_file_in_category(self, category_name: str, file_path: str) -> bool:
        return file_path in self.category_to_files.get(category_name, set())

    def rename_category(self, old_name: str, new_name: str, merge: bool = False) -> tuple[bool, str]:
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
                    self.entries.append([new_name, file_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
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
        self.entries = [row for row in self.entries if row[0] != category_name]
        for file in self.category_to_files[category_name]:
            self.file_to_categories[file].discard(category_name)
        self.category_to_files.pop(category_name, None)

    def delete_category(self, category_name: str) -> bool:
        with self.lock:
            if category_name not in self.category_to_files:
                return False
            file_count = len(self.category_to_files[category_name])
            self._remove_category_entries(category_name)
            self._write_entries()
            self.logger.update_logs('[CATEGORY DELETED]', f"Deleted category '{category_name}' with {file_count} files")
            return True

    def get_file_categories(self, file_path: str) -> list:
        return list(self.file_to_categories.get(file_path, []))

    def get_all_categories_with_dates(self) -> list:
        latest_dates = {}
        for row in self.entries:
            category, _, date = row
            if category not in latest_dates or date > latest_dates[category]:
                latest_dates[category] = date
        return sorted(latest_dates.items(), key=lambda x: x[1], reverse=True)

    def get_categories_of_files(self, file_path: str) -> list:
        return sorted(self.file_to_categories.get(file_path, []))
