import csv
from datetime import datetime
import os

from deletion_manager import DeletionManager
from logs_writer import LogManager
from player_constants import ASSOCIATIONS_CSV, ASSOCIATION_LOG_PATH


class FileAssociator:
    def __init__(self, csv_path=ASSOCIATIONS_CSV, deletion_manager=None):
        self.csv_path = csv_path
        self.deletion_manager = deletion_manager or DeletionManager()
        self._headers = [
                    'source_file', 'target_file', 'association_type',
                    'source_size', 'target_size',
                    'association_date', 'association_status']
        self._associations = {}
        self.logger = LogManager(ASSOCIATION_LOG_PATH)

        self._ensure_csv_exists()
        self._load_associations()

    def _ensure_csv_exists(self):
        """Make sure CSV exists with headers."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(self._headers)

    def _get_file_size(self, file_path):
        """Get file size safely."""
        try:
            return os.stat(file_path).st_size
        except FileNotFoundError:
            self.deletion_manager.get_deleted_file_size(file_path)
        except Exception:
            return 0

    def _load_associations(self):
        """Load CSV into in-memory dict for fast lookup."""
        self._associations.clear()
        with open(self.csv_path, 'r', newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['source_file'], row['target_file'], row['association_type'])
                self._associations[key] = {
                    "source_size": row['source_size'],
                    "target_size": row['target_size'],
                    "association_date": row['association_date'],
                    "association_status": row['association_status']
                }

    def _save_associations(self):
        """Persist dict back to CSV."""
        with open(self.csv_path, 'w', newline='', encoding="utf-8") as f:
            fieldnames = [
                'source_file', 'target_file', 'association_type',
                'source_size', 'target_size',
                'association_date', 'association_status'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for (src, tgt, atype), data in self._associations.items():
                row = {
                    "source_file": src,
                    "target_file": tgt,
                    "association_type": atype,
                    **data
                }
                writer.writerow(row)

    def add_association(self, source_file, target_file, association_type, target_size=None, source_size=None):
        """Add or update an association between two files."""
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        source_size = self._get_file_size(source_file) if not source_size else source_size
        target_size = self._get_file_size(target_file) if not target_size else target_size

        key = (source_file, target_file, association_type)
        self._associations[key] = {
            "source_size": source_size,
            "target_size": target_size,
            "association_date": current_date,
            "association_status": "active"
        }
        self._save_associations()
        self.logger.update_logs("[ADDED ASSOCIATION]", f"Source: {source_file}, Target: {target_file}, Type: {association_type}")

    def reload_associations(self):
        self._associations.clear()
        self._load_associations()

    def get_associations(self, source_file):
        """Get all active associations for a source file."""
        return [
            {"source_file": k[0], "target_file": k[1], "association_type": k[2], **v}
            for k, v in self._associations.items()
            if k[0] == source_file and v["association_status"] == "active"
        ]

    def get_all_associations(self):
        """Get all associations."""
        return [
            {"source_file": k[0], "target_file": k[1], "association_type": k[2], **v}
            for k, v in self._associations.items()
        ]

    def remove_association(self, source_file, target_file, association_type):
        """Remove an association completely."""
        key = (source_file, target_file, association_type)
        if key in self._associations:
            del self._associations[key]
            self._save_associations()
            self.logger.update_logs("[REMOVED ASSOCIATION]", f"Source: {source_file}, Target: {target_file}, Type: {association_type}")

    def deactivate_association(self, source_file, target_file, association_type):
        """Mark an association as inactive instead of deleting it."""
        key = (source_file, target_file, association_type)
        if key in self._associations:
            self._associations[key]["association_status"] = "inactive"
            self._save_associations()

    def reactivate_association(self, source_file, target_file, association_type):
        """Re-enable an inactive association."""
        key = (source_file, target_file, association_type)
        if key in self._associations:
            self._associations[key]["association_status"] = "active"
            self._save_associations()

    def update_association_type(self, source_file, target_file, old_type, new_type):
        """Change the type of an existing association."""
        key = (source_file, target_file, old_type)
        if key in self._associations:
            data = self._associations.pop(key)
            new_key = (source_file, target_file, new_type)
            self._associations[new_key] = data
            self._save_associations()
            self.logger.update_logs("[UPDATED ASSOCIATION TYPE]", f"Source: {source_file}, Target: {target_file}, Old Type: {old_type}, New Type: {new_type}")

    def get_targets(self, source_file, association_type=None, active_only=True):
        """Get all target files for a given source file. Supports single or multiple types."""
        if association_type is None:
            types_set = None
        elif isinstance(association_type, (list, tuple, set)):
            types_set = set(association_type)
        else:
            types_set = {association_type}

        return [
            k[1]
            for k, v in self._associations.items()
            if k[0] == source_file
            and (types_set is None or k[2] in types_set)
            and (not active_only or v["association_status"] == "active")
        ]


    def get_sources(self, target_file, association_type=None, active_only=True):
        """Get all source files that point to a given target file. Supports single or multiple types."""
        if association_type is None:
            types_set = None
        elif isinstance(association_type, (list, tuple, set)):
            types_set = set(association_type)
        else:
            types_set = {association_type}

        return [
            k[0]
            for k, v in self._associations.items()
            if k[1] == target_file
            and (types_set is None or k[2] in types_set)
            and (not active_only or v["association_status"] == "active")
        ]

    def get_association_types(self, source_file=None, target_file=None):
        """Get distinct association types, optionally filtered by source/target."""
        return list({
            k[2]
            for k, v in self._associations.items()
            if (source_file is None or k[0] == source_file)
            and (target_file is None or k[1] == target_file)
        })

    def has_association(self, source_file, target_file, association_type=None, active_only=True):
        """Check if an association exists between source and target."""
        for (src, tgt, atype), v in self._associations.items():
            if src == source_file and tgt == target_file:
                if association_type is None or atype == association_type:
                    if not active_only or v["association_status"] == "active":
                        return True
        return False

    def get_inactive_associations(self):
        """Return all inactive associations."""
        return [
            {"source_file": k[0], "target_file": k[1], "association_type": k[2], **v}
            for k, v in self._associations.items()
            if v["association_status"] == "inactive"
        ]

    def count_associations(self, active_only=True):
        """Count associations, optionally only active ones."""
        return sum(
            1
            for v in self._associations.values()
            if not active_only or v["association_status"] == "active"
        )
