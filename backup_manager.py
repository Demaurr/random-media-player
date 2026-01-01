import os
import csv
import json
from typing import Dict
from player_constants import (
    BACKUP_FOLDER,
    FOLDER_LOGS,
    WATCHED_HISTORY_LOG_PATH,
    DELETE_FILES_CSV,
    CATEGORIES_FILE,
    DESCRIPTION_CSV,
    FILE_TRANSFER_LOG,
    ALL_MEDIA_CSV,
    NOTES_CSV,
    VIDEO_STATS_CSV,
    SNIPPETS_HISTORY_CSV,
    FAV_FILES,
    FINGERPRINTS_CSV,
    FINGERPRINTS_PATHS_CSV,
    ASSOCIATIONS_CSV,
    ANNOTATIONS_CSV,
    CATEGORIES_OPERATIONS_FILE,
    CATEGORIES_USAGE_FILE,
    CATEGORIES_INTERACTION_FILE
)
from static_methods import ensure_folder_exists
from datetime import datetime

class BackupManager:
    def __init__(self, file_paths: Dict[str, str]):
        self.file_paths = {
            "FOLDER_LOGS": FOLDER_LOGS,
            "WATCHED_HISTORY_LOG": WATCHED_HISTORY_LOG_PATH,
            "DELETE_FILES_CSV": DELETE_FILES_CSV,
            "CATEGORIES_FILE": CATEGORIES_FILE,
            "DESCRIPTION_CSV": DESCRIPTION_CSV,
            "FILE_TRANSFER_LOG": FILE_TRANSFER_LOG,
            "ALL_MEDIA_CSV": ALL_MEDIA_CSV,
            "NOTES_CSV": NOTES_CSV,
            "VIDEO_STATS_CSV": VIDEO_STATS_CSV,
            "SNIPPETS_HISTORY_CSV": SNIPPETS_HISTORY_CSV,
            "FAV_FILES": FAV_FILES,
            "ASSOCIATIONS_CSV": ASSOCIATIONS_CSV,
            "FINGERPRINTS_CSV": FINGERPRINTS_CSV,
            "FINGERPRINTS_PATHS_CSV": FINGERPRINTS_PATHS_CSV,
            "ANNOTATIONS_CSV": ANNOTATIONS_CSV
        }
        self.backup_folder = BACKUP_FOLDER
        ensure_folder_exists(self.backup_folder)

    def create_backup(self):
        backup_data = {}
        self.backup_file = os.path.join(
            self.backup_folder,
            f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        for name, path in self.file_paths.items():
            print("Fetching backup for:", name)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Required file not found: {path}")

            ext = os.path.splitext(path)[1].lower()
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                if ext == '.csv':
                    reader = csv.DictReader(f)
                    backup_data[name] = {
                        "type": "csv",
                        "header": reader.fieldnames,
                        "data": list(reader)
                    }
                else:
                    backup_data[name] = {
                        "type": "text",
                        "data": f.read()
                    }
            print(f"Backup for {name} completed.")

        with open(self.backup_file, 'w', encoding='utf-8') as backup_file:
            json.dump(backup_data, backup_file, indent=2)

        print(f"Backup created at: {self.backup_folder}")

    def restore_backup(self, backup_path: str):
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        for name, content in backup_data.items():
            if name not in self.file_paths:
                raise KeyError(f"No path mapping for backup entry: {name}")

            path = self.file_paths[name]
            ext = os.path.splitext(path)[1].lower()
            os.makedirs(os.path.dirname(path), exist_ok=True)

            if content['type'] == 'csv':
                with open(path, 'w', newline='', encoding='utf-8') as f_out:
                    writer = csv.DictWriter(f_out, fieldnames=content['header'])
                    writer.writeheader()
                    writer.writerows(content['data'])
            else:
                with open(path, 'w', encoding='utf-8') as f_out:
                    f_out.write(content['data'])

        print(f"Backup restored from: {backup_path}")

    def restore_single_from_backup(self, backup_path: str, file_key: str):
        """
        Restore a specific file (e.g., 'FAV_FILES') from a backup JSON.

        Args:
            backup_path (str): Path to the backup JSON file.
            file_key (str): Key of the file in self.file_paths (e.g., 'FAV_FILES').

        Raises:
            FileNotFoundError: If the backup file or target file path does not exist.
            KeyError: If the given file_key is not in the backup.
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f" Backup file not found: {backup_path}")

        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        if file_key not in backup_data:
            raise KeyError(f"{file_key} not found in backup data")

        if file_key not in self.file_paths:
            raise KeyError(f"No path mapping for backup entry: {file_key}")

        path = self.file_paths[file_key]
        content = backup_data[file_key]
        ext = os.path.splitext(path)[1].lower()

        os.makedirs(os.path.dirname(path), exist_ok=True)

        if content['type'] == 'csv':
            with open(path, 'w', newline='', encoding='utf-8') as f_out:
                writer = csv.DictWriter(f_out, fieldnames=content['header'])
                writer.writeheader()
                writer.writerows(content['data'])
        else:
            with open(path, 'w', encoding='utf-8') as f_out:
                f_out.write(content['data'])

        print(f"Restored {file_key} to {path} from {backup_path}")

if __name__ == "__main__":
    bm = BackupManager({})
    pass