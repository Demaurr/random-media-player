import csv
import os
from datetime import datetime

from player_constants import CATEGORIES_FILE, LOG_PATH
from static_methods import create_csv_file
from logs_writer import LogManager

class CategoryManager:
    def __init__(self):
        self.categories_file = CATEGORIES_FILE
        self.logger = LogManager(LOG_PATH)
        self._ensure_categories_file()

    def _ensure_categories_file(self):
        """Ensure the categories file exists with proper headers."""
        create_csv_file(headers=['Category Name', 'File Path', 'Date Added'], filename=self.categories_file)

    def add_to_category(self, category_name: str, file_path: str) -> bool:
        """Add a file to a category."""
        try:
            if self.is_file_in_category(category_name, file_path):
                return False

            with open(self.categories_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([category_name, file_path, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            self.logger.update_logs('[CATEGORY ADDED]', f"'{file_path}' to category '{category_name}'")
            return True
        except Exception as e:
            self.logger.error_logs(f"Error adding file '{file_path}' to category '{category_name}': {e}")
            print(f"Error adding to category: {e}")
            return False

    def remove_from_category(self, category_name: str, file_path: str) -> bool:
        """Remove a file from a category."""
        try:
            temp_rows = []
            removed = False
            
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                temp_rows.append(next(reader))
                
                for row in reader:
                    if not (row[0] == category_name and row[1] == file_path):
                        temp_rows.append(row)
                    else:
                        removed = True

            if removed:
                with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(temp_rows)
                self.logger.update_logs('[CATEGORY REMOVED]', f"Removed '{file_path}' from category '{category_name}'")
                    
            return removed
        except Exception as e:
            self.logger.error_logs(f"Error removing file '{file_path}' from category '{category_name}': {e}")
            print(f"Error removing from category: {e}")
            return False

    def get_category_files(self, category_name: str) -> list:
        """Get all files in a category."""
        try:
            files = []
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader) 
                for row in reader:
                    if row[0] == category_name:
                        files.append(row[1])
            return files
        except Exception as e:
            print(f"Error getting category files: {e}")
            return []

    def get_all_categories(self) -> set:
        """Get a list of all unique categories."""
        try:
            categories = set()
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    categories.add(row[0])
            return categories
        except Exception as e:
            print(f"Error getting categories: {e}")
            return set()

    def is_file_in_category(self, category_name: str, file_path: str) -> bool:
        """Check if a file exists in a category."""
        try:
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row[0] == category_name and row[1] == file_path:
                        return True
            return False
        except Exception as e:
            print(f"Error checking file in category: {e}")
            return False

    def rename_category(self, old_name: str, new_name: str, merge: bool = False) -> tuple[bool, str]:
        """
        Rename a category.
        Args:
            old_name: Current category name
            new_name: New category name
            merge: If True and new_name exists, merge the categories. If False, prevent renaming to existing category.
        Returns:
            tuple: (success, message)
        """
        try:
            if new_name in self.get_all_categories():
                if not merge:
                    self.logger.error_logs(f"Cannot rename category '{old_name}' to '{new_name}': Category already exists")
                    return False, f"Category '{new_name}' already exists. Use merge option if you want to combine categories."
                
                # If merging, get all files from both categories
                old_files = set(self.get_category_files(old_name))
                new_files = set(self.get_category_files(new_name))
                self._remove_category_entries(old_name)
                self._remove_category_entries(new_name)
                merged_files = old_files.union(new_files)
                for file_path in merged_files:
                    self.add_to_category(new_name, file_path)
                
                self.logger.update_logs('[CATEGORY MERGED]', f"Merged category '{old_name}' into '{new_name}' with {len(merged_files)} files")
                return True, f"Merged '{old_name}' into '{new_name}' with {len(merged_files)} unique files"
            
            temp_rows = []
            renamed = False
            
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                temp_rows.append(next(reader))
                
                for row in reader:
                    if row[0] == old_name:
                        row[0] = new_name
                        renamed = True
                    temp_rows.append(row)

            if renamed:
                with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(temp_rows)
                self.logger.update_logs('[CATEGORY RENAMED]', f"Renamed category '{old_name}' to '{new_name}'")
                return True, f"Renamed '{old_name}' to '{new_name}'"
                    
            self.logger.error_logs(f"Cannot rename category '{old_name}': Category not found")
            return False, f"Category '{old_name}' not found"
        except Exception as e:
            self.logger.error_logs(f"Error renaming category '{old_name}' to '{new_name}': {e}")
            print(f"Error renaming category: {e}")
            return False, f"Error: {str(e)}"

    def _remove_category_entries(self, category_name: str) -> None:
        """Remove all entries for a given category without returning anything."""
        temp_rows = []
        with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            temp_rows.append(next(reader))
            for row in reader:
                if row[0] != category_name:
                    temp_rows.append(row)
        
        with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(temp_rows)

    def delete_category(self, category_name: str) -> bool:
        """Delete an entire category."""
        try:
            temp_rows = []
            deleted = False
            file_count = 0
            
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                temp_rows.append(next(reader))
                
                for row in reader:
                    if row[0] != category_name:
                        temp_rows.append(row)
                    else:
                        deleted = True
                        file_count += 1

            if deleted:
                with open(self.categories_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerows(temp_rows)
                self.logger.update_logs('[CATEGORY DELETED]', f"Deleted category '{category_name}' containing {file_count} files")
                    
            return deleted
        except Exception as e:
            self.logger.error_logs(f"Error deleting category '{category_name}': {e}")
            print(f"Error deleting category: {e}")
            return False

    def get_file_categories(self, file_path: str) -> list:
        """Get all categories that a file belongs to."""
        try:
            categories = []
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row[1] == file_path:
                        categories.append(row[0])
            return categories
        except Exception as e:
            print(f"Error getting file categories: {e}")
            return []

    def get_all_categories_with_dates(self) -> list:
        """Get a list of all categories with their most recent date."""
        try:
            categories = {}
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    category, _, date_added = row
                    if category not in categories or date_added > categories[category]:
                        categories[category] = date_added
            return sorted(categories.items(), key=lambda x: x[1], reverse=True)
        except Exception as e:
            print(f"Error getting categories with dates: {e}")
            return []

    def get_categories_of_files(self, file_path: str) -> list:
        """Get all categories that contain this file."""
        try:
            categories = []
            with open(self.categories_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    category_name, path, _ = row
                    if path == file_path:
                        categories.append(category_name)
            return sorted(categories)
        except Exception as e:
            print(f"Error getting categories for file: {e}")
            return [] 