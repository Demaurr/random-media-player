from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import os
from datetime import datetime
from typing import Dict, List, Set, Optional
from fingerprint_manager import MediaFingerprintManager
from player_constants import (
    WATCHED_HISTORY_LOG_PATH,
    VIDEO_STATS_CSV,
    ALL_MEDIA_CSV
)
from static_methods import build_transfer_graph, normalise_path, get_all_related_paths, parse_duration_to_seconds
from deletion_manager import DeletionManager

class MediaPathsCollector:
    def __init__(self, deletion_manager: Optional[DeletionManager] = None, fingerprint_manager: Optional[MediaFingerprintManager] = None):
        self.deletion_manager = deletion_manager or DeletionManager()
        self.file_data: Dict[str, Dict] = {}
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()

    def collect_from_watch_history(self) -> None:
        """Read watch history CSV and extract file paths and sizes."""
        if not os.path.exists(WATCHED_HISTORY_LOG_PATH):
            return

        with open(WATCHED_HISTORY_LOG_PATH, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = normalise_path(row.get('File Name', ''))
                if not path:
                    continue
                
                if path not in self.file_data:
                    self.file_data[path] = {}

                try:
                    size = os.path.getsize(path)
                except (FileNotFoundError, PermissionError):
                    size = self.deletion_manager.get_deleted_file_size(path)

                duration_str = row.get("Total Duration")
                duration_sec = parse_duration_to_seconds(duration_str)

                self.file_data[path].update({
                    'size': size or 0,
                    'duration': round(duration_sec, 3) if duration_sec else None,
                    'from_watch_history': True
                })


    def collect_from_video_stats(self) -> None:
        """Update using video stats if watch history didn’t provide duration or size."""
        if not os.path.exists(VIDEO_STATS_CSV):
            return

        with open(VIDEO_STATS_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = normalise_path(row.get('File Path', ''))
                if not path:
                    continue

                if path not in self.file_data:
                    self.file_data[path] = {}

                try:
                    size = int(row.get('File Size') or 0)
                except ValueError:
                    size = 0
                try:
                    duration = round(float(row.get('Duration (s)') or 0), 3)
                except ValueError:
                    duration = 0

                existing = self.file_data[path]
                if not existing.get('duration') or existing.get('duration') in (0, "0", None, ""):
                    existing['duration'] = duration
                if not existing.get('size') or existing.get('size') in (0, "0", None, ""):
                    existing['size'] = size

                existing['from_video_stats'] = True


    def collect_from_all_media(self) -> None:
        """Update using all media if size is still missing/zero."""
        if not os.path.exists(ALL_MEDIA_CSV):
            return

        with open(ALL_MEDIA_CSV, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                path = normalise_path(os.path.join(
                    row.get('Source Folder', ''),
                    row.get('File Name', '')
                ))
                if not path:
                    continue

                if path not in self.file_data:
                    self.file_data[path] = {}

                size = row.get('File Size (Bytes)')
                try:
                    size = int(size) if size else 0
                except ValueError:
                    size = 0

                if not size:
                    try:
                        size = os.path.getsize(path)
                    except (FileNotFoundError, PermissionError):
                        size = self.deletion_manager.get_deleted_file_size(path)

                existing = self.file_data[path]
                if not existing.get('size') or existing.get('size') in (0, "0", None, ""):
                    existing['size'] = size

                existing['from_all_media'] = True

    def collect_all(self, 
                    build_related_paths: bool = True, 
                    all: bool = True, 
                    video_stats: bool= False, 
                    watch_history: bool = False, 
                    all_media: bool = False
                ) -> Dict[str, Dict]:
        """
        Collect data from all sources and optionally link related paths.
        Ensures related paths share the same size/duration (if non-zero).
        """

        if watch_history or all:
            print("Collecting media paths and metadata from watch_history....")
            self.collect_from_watch_history()
            print("Collected from Watch History")

        if video_stats or all:
            print("Collecting media paths and metadata from video_stats....")
            self.collect_from_video_stats()
            print("Collected from Video Stats")

        if all_media or all:
            print("Collecting media paths and metadata from all_media....")
            self.collect_from_all_media()
            print("Collected from Video Stats")
        

        if build_related_paths:
            graph = build_transfer_graph()
            all_paths = list(self.file_data.keys())

            for path in all_paths:
                related = get_all_related_paths(path, graph)

                # Collect best size/duration across related paths
                best_size = None
                best_duration = None

                for rel_path in related:
                    if rel_path in self.file_data:
                        s = self.file_data[rel_path].get("size")
                        d = self.file_data[rel_path].get("duration")

                        if s not in (None, "", 0, "0"):
                            best_size = s
                        if d not in (None, "", 0, "0"):
                            best_duration = d

                for rel_path in related:
                    if rel_path in self.file_data:
                        if best_size is not None:
                            self.file_data[rel_path]["size"] = best_size
                        if best_duration is not None:
                            self.file_data[rel_path]["duration"] = best_duration

        return self.file_data

    
    def save_to_csv(self, output_path: str) -> None:
        """
        Save self.file_data into a CSV file.
        Each row = one file path + its metadata.
        """
        if not self.file_data:
            return

        all_keys = set()
        for meta in self.file_data.values():
            all_keys.update(meta.keys())

        fieldnames = ["file_path"] + sorted(all_keys)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for path, meta in self.file_data.items():
                row = {"file_path": path, **meta}
                writer.writerow(row)

    def create_fingerprints_from_file_data(
        self, 
        fingerprint_manager: Optional[MediaFingerprintManager] = None, 
        force_partial: bool = False
    ) -> None:
        """
        Create fingerprints for all collected file paths using MediaFingerprintManager.
        If `force_partial` is True, always compute partial hash when file exists.
        Otherwise only do it if duplicates are suspected.
        """
        if not self.file_data:
            print("No file data collected. Run collect_all() first.")
            return

        manager = fingerprint_manager or self.fingerprint_manager
        seen_index_hashes = {}

        for file_path, meta in self.file_data.items():
            duration = meta.get("duration")
            size = meta.get("size")

            if not duration or not size or size in (0, "0", None, ""):
                continue

            index_hash = manager._generate_index_hash(str(duration), str(size))

            if index_hash in seen_index_hashes:
                force_partial = force_partial
            else:
                seen_index_hashes[index_hash] = file_path

            added = manager.add_fingerprint(file_path, str(duration), str(size), force_partial=force_partial)
            if added:
                print(f"[FINGERPRINT CREATED] {file_path}")
            else:
                print(f"[FINGERPRINT EXISTS] {file_path}")
        manager.flush()

    def create_fingerprints_parallel(self, workers: int = 4):
        manager = MediaFingerprintManager()
        created, skipped = 0, 0
        tasks = []

        with ThreadPoolExecutor(max_workers=workers) as executor:
            for file_path, meta in self.file_data.items():
                duration = meta.get("duration")
                size = meta.get("size")
                if not duration or not size or size in (0, "0", None, ""):
                    continue
                tasks.append(
                    executor.submit(
                        manager.add_fingerprint, file_path, str(duration), str(size)
                    )
                )

            for future in as_completed(tasks):
                try:
                    if future.result():
                        created += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print("Error creating fingerprint:", e)

        manager.flush()

def test_fingerprinting():
    collector = MediaPathsCollector()
    
    collector.file_data = {
        "C:/media/video1.mp4": {"duration": 123.456, "size": 1048576}, 
        "C:/media/video2.mp4": {"duration": 123.456, "size": 1048576},
        "C:/media/audio1.mp3": {"duration": 245.12, "size": 512000},
        "C:/media/missing.mp4": {"duration": 300.000, "size": 2048000}, 
        "C:/media/zero_size.mp4": {"duration": 150.000, "size": 0},      
    }

    fingerprint_manager = MediaFingerprintManager()

    print("\n=== Creating fingerprints ===")
    collector.create_fingerprints_from_file_data(fingerprint_manager, force_partial=False)

    print("\n=== Stored Fingerprints ===")
    for fp, record in fingerprint_manager.fingerprints.items():
        print(f"Fingerprint: {fp}")
        print(f"  Index hash : {record['index_hash']}")
        print(f"  Partial hash: {record['partial_hash']}")
        print(f"  Duration   : {record['duration']}")
        print(f"  Size       : {record['size']}")
        print(f"  Paths      : {record['paths']}")
        print()

if __name__ == "__main__":
    collector = MediaPathsCollector()
    collector.collect_all(all=False, video_stats=True)
    collector.create_fingerprints_parallel(workers=8)
    # test_fingerprinting()
