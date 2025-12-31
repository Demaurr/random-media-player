import csv
from datetime import datetime
import os
from typing import Optional, List, Dict, Tuple

from deletion_manager import DeletionManager
from logs_writer import LogManager
from player_constants import ASSOCIATIONS_CSV, ASSOCIATION_LOG_PATH
from static_methods import normalise_path


class FileAssociator:
    """
    Associations will generally be lower than categories or other stuff, therefore not using the indexing
    """
    def __init__(self, csv_path=ASSOCIATIONS_CSV, deletion_manager=None, fingerprint_manager=None):
        self.csv_path = csv_path
        self.deletion_manager = deletion_manager or DeletionManager()
        self.fingerprint_manager = fingerprint_manager
        
        self._headers = [
            'source_file', 'source_hash', 'target_file', 'target_hash',
            'association_type', 'source_size', 'target_size',
            'association_date', 'association_status'
        ]
        
        self._associations = {}
        self.logger = LogManager(ASSOCIATION_LOG_PATH)

        self._ensure_csv_exists()
        self._load_associations()

    def set_fingerprint_manager(self, fingerprint_manager):
        """Set or update the fingerprint manager instance."""
        self.fingerprint_manager = fingerprint_manager

    def _ensure_csv_exists(self):
        """Make sure CSV exists with headers."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self._headers)
        else:
            self._migrate_csv_if_needed()

    def _migrate_csv_if_needed(self):
        """Migrate old CSV format (without fingerprints) to new format."""
        try:
            with open(self.csv_path, 'r', newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and 'source_hash' not in reader.fieldnames:
                    rows = list(reader)
                    self._save_associations()
                    
                    for row in rows:
                        source_hash = ""
                        target_hash = ""
                        
                        if self.fingerprint_manager:
                            source_hash = self.fingerprint_manager.get_index_hash_by_path(normalise_path(row['source_file'])) or ""
                            target_hash = self.fingerprint_manager.get_index_hash_by_path(normalise_path(row['target_file'])) or ""
                        
                        key = (row['source_file'], row['target_file'], row['association_type'])
                        self._associations[key] = {
                            "source_hash": source_hash,
                            "target_hash": target_hash,
                            "source_size": row.get('source_size', ''),
                            "target_size": row.get('target_size', ''),
                            "association_date": row.get('association_date', ''),
                            "association_status": row.get('association_status', 'active')
                        }
                    
                    self._save_associations()
                    self.logger.update_logs("[MIGRATION]", "Migrated associations to include fingerprints")
        except Exception as e:
            self.logger.error_logs(f"Error during CSV migration: {e}")

    def _get_file_size(self, file_path):
        """Get file size safely."""
        try:
            return os.stat(file_path).st_size
        except FileNotFoundError:
            return self.deletion_manager.get_deleted_file_size(file_path)
        except Exception:
            return 0

    def _get_fingerprint_for_file(self, file_path: str) -> str:
        """Get the fingerprint (index_hash) for a given file path."""
        if not self.fingerprint_manager:
            return ""
        
        file_path = normalise_path(file_path)
        return self.fingerprint_manager.get_index_hash_by_path(file_path) or ""

    def _load_associations(self):
        """Load CSV into in-memory dict for fast lookup."""
        self._associations.clear()
        
        if not os.path.exists(self.csv_path):
            return
        
        with open(self.csv_path, 'r', newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return
            
            for row in reader:
                source_file = row.get('source_file', '')
                target_file = row.get('target_file', '')
                association_type = row.get('association_type', '')
                
                key = (source_file, target_file, association_type)
                self._associations[key] = {
                    "source_hash": row.get('source_hash', ''),
                    "target_hash": row.get('target_hash', ''),
                    "source_size": row.get('source_size', ''),
                    "target_size": row.get('target_size', ''),
                    "association_date": row.get('association_date', ''),
                    "association_status": row.get('association_status', 'active')
                }

    def _save_associations(self):
        """Persist dict back to CSV."""
        with open(self.csv_path, 'w', newline='', encoding="utf-8") as f:
            fieldnames = self._headers
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

    def add_association(self, source_file: str, target_file: str, association_type: str, 
                       target_size: Optional[int] = None, source_size: Optional[int] = None):
        """Add or update an association between two files."""
        try:
            source_file = normalise_path(source_file)
            target_file = normalise_path(target_file)
            
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            source_size = self._get_file_size(source_file) if not source_size else source_size
            target_size = self._get_file_size(target_file) if not target_size else target_size
            
            source_hash = self._get_fingerprint_for_file(source_file)
            target_hash = self._get_fingerprint_for_file(target_file)

            if source_hash == target_hash and source_hash != "":
                self.logger.update_logs(
                    "[SKIPPED ASSOCIATION]",
                    f"Source and target have the same fingerprint ({source_hash}). Association not added."
                )
                raise ValueError(f"Source: {source_file}--{source_hash} and target: {target_file}--{target_hash} are the same files. Can't add associations to itself.")

            key = (source_file, target_file, association_type)
            self._associations[key] = {
                "source_hash": source_hash,
                "target_hash": target_hash,
                "source_size": source_size,
                "target_size": target_size,
                "association_date": current_date,
                "association_status": "active"
            }
            self._save_associations()
            self.logger.update_logs(
                "[ADDED ASSOCIATION]",
                f"Source: {source_file} ({source_hash}), Target: {target_file} ({target_hash}), Type: {association_type}"
            )
        except Exception as e:
            self.logger.error_logs(f"Error adding association: {e}")

    def reload_associations(self):
        """Reload associations from CSV."""
        self._associations.clear()
        self._load_associations()

    def get_associations(self, source_file: str) -> List[Dict]:
        """Get all active associations for a source file."""
        source_file = normalise_path(source_file)
        return [
            {
                "source_file": k[0], "target_file": k[1], "association_type": k[2],
                "source_hash": v.get("source_hash", ""),
                "target_hash": v.get("target_hash", ""),
                **{k: v for k, v in v.items() if k not in ["source_hash", "target_hash"]}
            }
            for k, v in self._associations.items()
            if k[0] == source_file and v.get("association_status") == "active"
        ]

    def get_associations_by_hash(
        self,
        index_hash: str,
        association_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict]:
        """
        Get all associations where the given fingerprint hash appears
        either as source or target.

        API-presentable output with explicit role information.
        """
        results = []

        for (src_file, tgt_file, atype), data in self._associations.items():
            if active_only and data.get("association_status") != "active":
                continue

            if association_type and atype != association_type:
                continue

            role = None
            if data.get("source_hash") == index_hash:
                role = "source"
            elif data.get("target_hash") == index_hash:
                role = "target"

            if not role:
                continue

            results.append({
                "role": role,
                "association_type": atype,

                "source": {
                    "file": src_file,
                    "hash": data.get("source_hash", ""),
                    "size": data.get("source_size")
                },
                "target": {
                    "file": tgt_file,
                    "hash": data.get("target_hash", ""),
                    "size": data.get("target_size")
                },

                "association_date": data.get("association_date"),
                "association_status": data.get("association_status")
            })

        return results

    def get_all_associations(self) -> List[Dict]:
        """Get all associations."""
        return [
            {
                "source_file": k[0], "target_file": k[1], "association_type": k[2],
                "source_hash": v.get("source_hash", ""),
                "target_hash": v.get("target_hash", ""),
                **{k: v for k, v in v.items() if k not in ["source_hash", "target_hash"]}
            }
            for k, v in self._associations.items()
        ]

    def remove_association(self, source_file: str, target_file: str, association_type: str):
        """Remove an association completely."""
        source_file = normalise_path(source_file)
        target_file = normalise_path(target_file)
        
        key = (source_file, target_file, association_type)
        if key in self._associations:
            del self._associations[key]
            self._save_associations()
            self.logger.update_logs(
                "[REMOVED ASSOCIATION]",
                f"Source: {source_file}, Target: {target_file}, Type: {association_type}"
            )

    def deactivate_association(self, source_file: str, target_file: str, association_type: str):
        """Mark an association as inactive instead of deleting it."""
        source_file = normalise_path(source_file)
        target_file = normalise_path(target_file)
        
        key = (source_file, target_file, association_type)
        if key in self._associations:
            self._associations[key]["association_status"] = "inactive"
            self._save_associations()

    def reactivate_association(self, source_file: str, target_file: str, association_type: str):
        """Re-enable an inactive association."""
        source_file = normalise_path(source_file)
        target_file = normalise_path(target_file)
        
        key = (source_file, target_file, association_type)
        if key in self._associations:
            self._associations[key]["association_status"] = "active"
            self._save_associations()

    def update_association_type(self, source_file: str, target_file: str, old_type: str, new_type: str):
        """Change the type of an existing association."""
        source_file = normalise_path(source_file)
        target_file = normalise_path(target_file)
        
        key = (source_file, target_file, old_type)
        if key in self._associations:
            data = self._associations.pop(key)
            new_key = (source_file, target_file, new_type)
            self._associations[new_key] = data
            self._save_associations()
            self.logger.update_logs(
                "[UPDATED ASSOCIATION TYPE]",
                f"Source: {source_file}, Target: {target_file}, Old Type: {old_type}, New Type: {new_type}"
            )

    def get_targets(self, source_file: str, association_type: Optional[str] = None, active_only: bool = True) -> List[str]:
        """Get all target files for a given source file. Supports single or multiple types."""
        source_file = normalise_path(source_file)
        
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
            and (not active_only or v.get("association_status") == "active")
        ]

    def get_targets_by_hash(self, source_hash: str, association_type: Optional[str] = None, active_only: bool = True) -> List[str]:
        """Get all target files for a given source fingerprint hash."""
        if association_type is None:
            types_set = None
        elif isinstance(association_type, (list, tuple, set)):
            types_set = set(association_type)
        else:
            types_set = {association_type}

        return [
            k[1]
            for k, v in self._associations.items()
            if v.get("source_hash") == source_hash
            and (types_set is None or k[2] in types_set)
            and (not active_only or v.get("association_status") == "active")
        ]

    def get_sources(self, target_file: str, association_type: Optional[str] = None, active_only: bool = True) -> List[str]:
        """Get all source files that point to a given target file. Supports single or multiple types."""
        target_file = normalise_path(target_file)
        
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
            and (not active_only or v.get("association_status") == "active")
        ]

    def get_sources_by_hash(self, target_hash: str, association_type: Optional[str] = None, active_only: bool = True) -> List[str]:
        """Get all source files that point to a given target fingerprint hash."""
        if association_type is None:
            types_set = None
        elif isinstance(association_type, (list, tuple, set)):
            types_set = set(association_type)
        else:
            types_set = {association_type}

        return [
            k[0]
            for k, v in self._associations.items()
            if v.get("target_hash") == target_hash
            and (types_set is None or k[2] in types_set)
            and (not active_only or v.get("association_status") == "active")
        ]

    def get_association_types(self, source_file: Optional[str] = None, target_file: Optional[str] = None,
                             source_hash: Optional[str] = None, target_hash: Optional[str] = None) -> List[str]:
        """Get distinct association types, optionally filtered by source/target (file or hash)."""
        return list({
            k[2]
            for k, v in self._associations.items()
            if (source_file is None or k[0] == normalise_path(source_file) if source_file else True)
            and (target_file is None or k[1] == normalise_path(target_file) if target_file else True)
            and (source_hash is None or v.get("source_hash") == source_hash)
            and (target_hash is None or v.get("target_hash") == target_hash)
        })

    def has_association(self, source_file: str, target_file: str, association_type: Optional[str] = None, 
                       active_only: bool = True) -> bool:
        """Check if an association exists between source and target."""
        source_file = normalise_path(source_file)
        target_file = normalise_path(target_file)
        
        for (src, tgt, atype), v in self._associations.items():
            if src == source_file and tgt == target_file:
                if association_type is None or atype == association_type:
                    if not active_only or v.get("association_status") == "active":
                        return True
        return False

    def has_association_by_hash(self, source_hash: str, target_hash: str, association_type: Optional[str] = None,
                               active_only: bool = True) -> bool:
        """Check if an association exists between source and target fingerprints."""
        for (src, tgt, atype), v in self._associations.items():
            if v.get("source_hash") == source_hash and v.get("target_hash") == target_hash:
                if association_type is None or atype == association_type:
                    if not active_only or v.get("association_status") == "active":
                        return True
        return False

    def get_inactive_associations(self) -> List[Dict]:
        """Return all inactive associations."""
        return [
            {
                "source_file": k[0], "target_file": k[1], "association_type": k[2],
                "source_hash": v.get("source_hash", ""),
                "target_hash": v.get("target_hash", ""),
                **{k: v for k, v in v.items() if k not in ["source_hash", "target_hash"]}
            }
            for k, v in self._associations.items()
            if v.get("association_status") == "inactive"
        ]

    def count_associations(self, active_only: bool = True) -> int:
        """Count associations, optionally only active ones."""
        return sum(
            1
            for v in self._associations.values()
            if not active_only or v.get("association_status") == "active"
        )

    def update_fingerprints_for_all(self):
        """
        Update all associations with current fingerprints from the fingerprint manager.
        Useful after files have been reorganized or fingerprints have been updated.
        """
        if not self.fingerprint_manager:
            self.logger.error_logs("Fingerprint manager not available for update")
            return
        
        updated_count = 0
        for key in list(self._associations.keys()):
            src_file = key[0]
            tgt_file = key[1]
            
            new_src_hash = self._get_fingerprint_for_file(src_file)
            new_tgt_hash = self._get_fingerprint_for_file(tgt_file)
            
            self._associations[key]["source_hash"] = new_src_hash
            self._associations[key]["target_hash"] = new_tgt_hash
            updated_count += 1
        
        self._save_associations()
        self.logger.update_logs("[FINGERPRINTS UPDATED]", f"Updated {updated_count} associations with current fingerprints")
    
    def update_missing_fingerprints(self):
        """
        Update only missing (empty) source or target fingerprints in associations.
        Existing hashes are preserved.
        """
        if not self.fingerprint_manager:
            self.logger.error_logs(
                "[FINGERPRINT UPDATE SKIPPED]",
                "Fingerprint manager not available"
            )
            return

        updated_fields = 0
        updated_associations = 0

        for key in list(self._associations.keys()):
            src_file, tgt_file, _ = key
            assoc = self._associations[key]

            src_hash = assoc.get("source_hash")
            tgt_hash = assoc.get("target_hash")

            updated = False

            if not src_hash:
                new_src_hash = self._get_fingerprint_for_file(src_file)
                if new_src_hash:
                    assoc["source_hash"] = new_src_hash
                    updated_fields += 1
                    updated = True
                    self.logger.update_logs(
                        "[UPDATED SOURCE HASH]",
                        f"{src_file} -> {new_src_hash}"
                    )

            if not tgt_hash:
                new_tgt_hash = self._get_fingerprint_for_file(tgt_file)
                if new_tgt_hash:
                    assoc["target_hash"] = new_tgt_hash
                    updated_fields += 1
                    updated = True
                    self.logger.update_logs(
                        "[UPDATED TARGET HASH]",
                        f"{tgt_file} -> {new_tgt_hash}"
                    )

            if updated:
                updated_associations += 1

        if updated_fields > 0:
            self._save_associations()
            self.logger.update_logs(
                "[FINGERPRINTS PARTIALLY UPDATED]",
                f"Updated {updated_fields} missing hashes "
                f"across {updated_associations} associations"
            )
        else:
            self.logger.update_logs(
                "[FINGERPRINTS UP TO DATE]",
                "No missing fingerprints found"
            )


if __name__ == "__main__":
    # Example usage
    from fingerprint_manager import MediaFingerprintManager
    from deletion_manager import DeletionManager
    fm = MediaFingerprintManager()
    dm = DeletionManager()
    associator = FileAssociator(deletion_manager=dm, fingerprint_manager=fm)