from datetime import datetime
import csv
import os
from logs_writer import LogManager
from player_constants import LOG_PATH, WATCHED_HISTORY_LOG_PATH
from static_methods import normalise_path, build_path_to_fingerprint_map, measure_time, calculate_duration_in_seconds
from fingerprint_manager import MediaFingerprintManager

class WatchHistoryLogger:
    """A class for logging the history of watched videos with fingerprint support."""

    def __init__(self, csv_file=WATCHED_HISTORY_LOG_PATH, fingerprint_manager=None):
        self.csv_file = csv_file
        self.logger = LogManager(LOG_PATH)
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self.fieldnames = ['File Name', 'Total Duration', 'Date Watched', 'Duration Watched', 'Last Position', 'Fingerprint']
        self.file_exists = self.check_file_exists()
        if not self.file_exists:
            self.create_csv_file()
        else:
            # self.refresh_csv_if_needed()
            pass

    def build_last_position_index(self):
        """Build a dictionary mapping file names to their last known position."""
        index = {}
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_name = normalise_path(row['File Name'])
                    last_position = row.get('Last Position') or row.get('Duration Watched')
                    index[file_name] = last_position
        except FileNotFoundError:
            pass
        return index

    def check_file_exists(self):
        return os.path.isfile(self.csv_file)

    def create_csv_file(self):
        with open(self.csv_file, 'a', newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames)
            writer.writeheader()

    def refresh_csv_if_needed(self):
        """Refresh the CSV file to add missing columns ('Last Position', 'Fingerprint')."""
        if not os.path.exists(self.csv_file):
            self.create_csv_file()
            return

        with open(self.csv_file, 'r', newline='', encoding="utf-8") as file:
            reader = csv.reader(file)
            headers = next(reader)
            rows = list(reader)

        old_fieldnames = headers
        new_fieldnames = self.fieldnames

        path_to_fingerprint = build_path_to_fingerprint_map(self.fingerprint_manager)

        new_rows = []
        for row in rows:
            row_dict = dict(zip(old_fieldnames, row))

            if 'Last Position' not in row_dict or not row_dict['Last Position']:
                row_dict['Last Position'] = row_dict.get("Duration Watched", "00:00:00")

            if 'Fingerprint' not in row_dict or not row_dict['Fingerprint']:
                file_path = normalise_path(row_dict['File Name'])
                row_dict['Fingerprint'] = path_to_fingerprint.get(file_path, "")

            new_rows.append(row_dict)

        with open(self.csv_file, 'w', newline='', encoding="utf-8") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(new_rows)


    def log_watch_history(self, file_name, total_duration, video_duration, last_position, fingerprint=None):
        """Log a watched video entry."""
        try:
            date_watched = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not fingerprint:
                fingerprint = self.fingerprint_manager.get_index_hash_by_path(file_name)

            with open(self.csv_file, 'a', newline='', encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=self.fieldnames)
                writer.writerow({
                    'File Name': file_name,
                    'Total Duration': total_duration,
                    'Date Watched': date_watched,
                    'Duration Watched': video_duration,
                    'Last Position': last_position,
                    'Fingerprint': fingerprint or ""
                })

            # following is for when we'll use a single WatchHistoryLogger from gui_main.py for the whole app.
            # self.update_indexes_after_log(
            #     file_name,
            #     total_duration,
            #     video_duration,
            #     last_position,
            #     fingerprint,
            #     date_watched
            # )
            if hasattr(self, "_last_position_index"):
                self._last_position_index[normalise_path(file_name)] = last_position
        except Exception as e:
            print(f"Error Occurred While Writing Watch History Logs: {e}")
            self.logger.error_logs(f"{e} While Writing Watch History")

    def get_last_position(self, file_name):
        if not hasattr(self, "_last_position_index"):
            self._last_position_index = self.build_last_position_index()
        return self._last_position_index.get(normalise_path(file_name))

    def get_fingerprint_by_file(self, file_name):
        """
        Uses file_name as input, which is essentially a file_path
        """

        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if normalise_path(row['File Name']) == normalise_path(file_name):
                        return row.get('Fingerprint') or self.fingerprint_manager.get_index_hash_by_path(file_name)
        except Exception as e:
            print(f"Error while fetching fingerprint: {e}")
        return None

    def build_fingerprint_index(self):
        """Build an in-memory index: fingerprint -> list of rows."""
        self._fingerprint_index = {}
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fp = row.get('Fingerprint', '').strip()
                    if not fp:
                        continue
                    self._fingerprint_index.setdefault(fp, []).append(row)
        except Exception as e:
            print(f"Error building fingerprint index: {e}")
            self._fingerprint_index = {}

    @measure_time(print_time=True)
    def build_fingerprint_stats_index(self):
        """
        Build an in-memory index for fast stats lookup by fingerprint.
        Structure: {fingerprint: {"watch_count": int, "total_seconds": float, "last_watched": datetime, "entries": [rows]}}
        
        Call this once at startup or when you need fresh data.
        """
        self._fingerprint_stats_index = {}
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fp = row.get('Fingerprint', '').strip()
                    if not fp:
                        continue
                    
                    if fp not in self._fingerprint_stats_index:
                        self._fingerprint_stats_index[fp] = {
                            "watch_count": 0,
                            "total_seconds": 0.0,
                            "last_watched": None,
                            "file_duration": 0.0,
                            "entries": []
                        }
                    
                    stats = self._fingerprint_stats_index[fp]
                    stats["watch_count"] += 1
                    stats["entries"].append(row)
                    
                    try:
                        duration_seconds = calculate_duration_in_seconds(row.get("Duration Watched", "0:00.0"))
                        stats["total_seconds"] += duration_seconds
                    except Exception:
                        pass

                    try:
                        if stats["file_duration"] == 0.0:
                            file_duration = calculate_duration_in_seconds(row.get("Total Duration", "0:00:00"))
                            stats["file_duration"] = file_duration
                    except Exception:
                        pass
                    
                    try:
                        dt = datetime.strptime(row.get("Date Watched", ""), "%Y-%m-%d %H:%M:%S")
                        if not stats["last_watched"] or dt > stats["last_watched"]:
                            stats["last_watched"] = dt
                    except Exception:
                        pass
        
        except Exception as e:
            print(f"Error building fingerprint stats index: {e}")
            self._fingerprint_stats_index = {}

    def clear_fingerprint_index(self):
        """
        Clear the in-memory fingerprint index to free memory.
        Safe to call multiple times.
        """
        if hasattr(self, "_fingerprint_index"):
            self._fingerprint_index.clear()
            del self._fingerprint_index


    def update_fingerprint_for_file(self, file_name, fingerprint):
        """Update fingerprint in watch history for a file."""
        try:
            with open(self.csv_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            found = False
            for row in reversed(rows):
                if normalise_path(row['File Name']) == normalise_path(file_name):
                    row['Fingerprint'] = fingerprint
                    found = True
                    break

            if found:
                with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                self.logger.update_logs("[FINGERPRINT UPDATED]", f"{file_name} -> {fingerprint}")
                return True
            return False
        except Exception as e:
            print(f"Error while updating fingerprint: {e}")
            self.logger.error_logs(f"Error updating fingerprint for {file_name}: {e}")
            return False
        
    def update_indexes_after_log(self, file_name, total_duration, video_duration, last_position, fingerprint, date_watched):
        """
        Fast incremental update of in-memory indexes after logging a watch entry.
        This avoids rebuilding indexes from the CSV file.
        """

        norm_path = normalise_path(file_name)

        if hasattr(self, "_last_position_index"):
            self._last_position_index[norm_path] = last_position

        if hasattr(self, "_fingerprint_index"):
            row = {
                "File Name": file_name,
                "Total Duration": total_duration,
                "Date Watched": date_watched,
                "Duration Watched": video_duration,
                "Last Position": last_position,
                "Fingerprint": fingerprint or ""
            }

            self._fingerprint_index.setdefault(fingerprint, []).append(row)

        if hasattr(self, "_fingerprint_stats_index") and fingerprint:

            from static_methods import calculate_duration_in_seconds

            duration_seconds = 0.0
            try:
                duration_seconds = calculate_duration_in_seconds(video_duration)
            except Exception:
                pass

            try:
                dt = datetime.strptime(date_watched, "%Y-%m-%d %H:%M:%S")
            except Exception:
                dt = None

            stats = self._fingerprint_stats_index.setdefault(
                fingerprint,
                {
                    "watch_count": 0,
                    "total_seconds": 0.0,
                    "last_watched": None,
                    "entries": []
                }
            )

            stats["watch_count"] += 1
            stats["total_seconds"] += duration_seconds

            if dt and (not stats["last_watched"] or dt > stats["last_watched"]):
                stats["last_watched"] = dt

            stats["entries"].append({
                "File Name": file_name,
                "Total Duration": total_duration,
                "Date Watched": date_watched,
                "Duration Watched": video_duration,
                "Last Position": last_position,
                "Fingerprint": fingerprint
            })
        
    def get_watch_history_by_fingerprint(self, fingerprint, sort_result=True):
        if not fingerprint:
            return []

        if not hasattr(self, "_fingerprint_index"):
            self.build_fingerprint_index()

        entries = self._fingerprint_index.get(fingerprint, [])

        if sort_result:
            entries = sorted(entries, key=lambda x: x.get('Date Watched', ''), reverse=True)

        return entries

    def get_watch_stats_for_fingerprint(self, fingerprint):
        """
        Get combined watch stats for a single fingerprint.
        Fast O(1) lookup if index is built.
        
        Args:
            fingerprint (str): The fingerprint to look up.
        
        Returns:
            dict: {
                "watch_count": int,
                "total_seconds": float,
                "last_watched": "YYYY-MM-DD HH:MM:SS" or "Never",
                "found": bool
            }
        """
        if not hasattr(self, "_fingerprint_stats_index"):
            self.build_fingerprint_stats_index()
        
        stats = self._fingerprint_stats_index.get(fingerprint.strip())
        
        if not stats:
            return {
                "watch_count": 0,
                "total_seconds": 0.0,
                "last_watched": "Never",
                "found": False
            }
        
        return {
            "watch_count": stats["watch_count"],
            "total_seconds": stats["total_seconds"],
            "last_watched": stats["last_watched"].strftime("%Y-%m-%d %H:%M:%S") if stats["last_watched"] else "Never",
            "found": True
        }

    @measure_time(print_time=True)
    def get_watch_stats_for_fingerprints_batch(self, fingerprints, aggregate: bool = False):
        """
        Get watch stats for multiple fingerprints efficiently.

        Args:
            fingerprints (list[str]): fingerprints to look up
            aggregate (bool): if True return combined statistics

        Returns:
            dict
        """

        if not hasattr(self, "_fingerprint_stats_index"):
            self.build_fingerprint_stats_index()

        results = {}
        fingerprint_set = {fp.strip() for fp in fingerprints if fp}

        total_views = 0
        total_duration = 0.0
        file_duration = 0.0
        last_watched = None
        last_watched_fp = None
        fingerprints_found = 0

        for fp in fingerprint_set:
            stats = self._fingerprint_stats_index.get(fp)

            if not stats:
                stats_dict = {
                    "watch_count": 0,
                    "total_seconds": 0.0,
                    "file_duration": 0.0,
                    "last_watched": "Never",
                    "found": False
                }

            else:
                lw = stats["last_watched"]

                stats_dict = {
                    "watch_count": stats["watch_count"],
                    "total_seconds": stats.get("total_seconds", 0.0),
                    "file_duration": stats.get("file_duration", 0.0),
                    "last_watched": lw.strftime("%Y-%m-%d %H:%M:%S") if lw else "Never",
                    "found": True
                }

                total_views += stats["watch_count"]
                total_duration += stats["total_seconds"]
                file_duration += stats.get("file_duration", 0.0)
                fingerprints_found += 1

                if lw and (last_watched is None or lw > last_watched):
                    last_watched = lw
                    last_watched_fp = fp

            results[fp] = stats_dict

        if aggregate:
            return {
                "total_views": total_views,
                "total_duration": total_duration,
                "file_duration": file_duration,
                "fingerprints_found": fingerprints_found,
                "last_watched": last_watched.strftime("%Y-%m-%d %H:%M:%S") if last_watched else "Never",
                "last_watched_fingerprint": last_watched_fp
            }

        return results

    @measure_time(print_time=True)
    def get_watch_stats_for_file_paths_batch(self, file_paths, aggregate: bool = False):
        """
        Get watch stats for multiple file paths.

        Args:
            file_paths (list[str]): file paths or file names
            aggregate (bool): if True returns combined stats

        Returns:
            dict
        """

        if not hasattr(self, "_fingerprint_stats_index"):
            print("Building fingerprint stats index for file path batch lookup...")
            self.build_fingerprint_stats_index()

        results = {}

        total_views = 0
        total_duration = 0.0
        last_watched = None
        last_watched_file = None
        files_found = 0

        for file_path in file_paths:
            norm_path = normalise_path(file_path)
            
            # Get fingerprint directly from fingerprint_manager's in-memory dict
            fp = self.fingerprint_manager.get_index_hash_by_path(norm_path)

            if not fp:
                stats_dict = {
                    "watch_count": 0,
                    "total_seconds": 0.0,
                    "last_watched": "Never",
                    "found": False
                }
            else:
                stats = self._fingerprint_stats_index.get(fp)

                if not stats:
                    stats_dict = {
                        "watch_count": 0,
                        "total_seconds": 0.0,
                        "last_watched": "Never",
                        "found": False
                    }
                else:
                    lw = stats["last_watched"]

                    stats_dict = {
                        "watch_count": stats["watch_count"],
                        "total_seconds": stats["total_seconds"],
                        "last_watched": lw.strftime("%Y-%m-%d %H:%M:%S") if lw else "Never",
                        "found": True
                    }

                    # aggregate updates
                    total_views += stats["watch_count"]
                    total_duration += stats["total_seconds"]
                    files_found += 1

                    if lw and (last_watched is None or lw > last_watched):
                        last_watched = lw
                        last_watched_file = norm_path

            results[norm_path] = stats_dict

        if aggregate:
            return {
                "total_views": total_views,
                "total_duration": total_duration,
                "files_found": files_found,
                "last_watched": last_watched.strftime("%Y-%m-%d %H:%M:%S") if last_watched else "Never",
                "last_watched_file": last_watched_file
            }

        return results


    def clear_fingerprint_stats_index(self):
        """Clear the in-memory fingerprint stats index to free memory."""
        if hasattr(self, "_fingerprint_stats_index"):
            self._fingerprint_stats_index.clear()
            del self._fingerprint_stats_index

        
    def fix_missing_fingerprints_by_name_and_duration(self):
        """
        Find rows where fingerprint is missing, then match them by:
        1. Same basename
        2. Same total duration
        If a matching file has a fingerprint, apply it.
        """

        def duration_to_ms_rounded(duration_str):
            """
            Convert duration string 'H:MM:SS.sss' to milliseconds (rounded to nearest ms).
            Example: '0:00:18.756' -> 18756
            """
            try:
                parts = duration_str.split(":")
                if len(parts) == 3:
                    h, m, s = parts
                elif len(parts) == 2:
                    h = 0
                    m, s = parts
                else:
                    return None
                s_parts = s.split(".")
                sec = int(s_parts[0])
                ms = int(s_parts[1].ljust(3, "0")) if len(s_parts) > 1 else 0

                total_ms = int(h) * 3600 * 1000 + int(m) * 60 * 1000 + sec * 1000 + ms

                return round(total_ms)
            except:
                return None

        try:
            with open(self.csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            signature_to_fingerprint = {}

            for row in rows:
                fp = row.get("Fingerprint", "").strip()
                file_path = normalise_path(row["File Name"])
                basename = os.path.basename(file_path)
                duration_ms = duration_to_ms_rounded(row.get("Total Duration", "0:00:00"))

                if fp and basename and duration_ms is not None:
                    signature_to_fingerprint[(basename, duration_ms)] = fp

            updated_count = 0

            for row in rows:
                if row.get("Fingerprint", "").strip():
                    continue

                file_path = normalise_path(row["File Name"])
                basename = os.path.basename(file_path)
                duration_ms = duration_to_ms_rounded(row.get("Total Duration", "0:00:00"))

                if not basename or duration_ms is None:
                    continue

                key = (basename, duration_ms)
                if key in signature_to_fingerprint:
                    row["Fingerprint"] = signature_to_fingerprint[key]
                    updated_count += 1

            with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            self.logger.update_logs("[FINGERPRINT FIXED]", f"Updated {updated_count} missing fingerprints")
            return updated_count

        except Exception as e:
            print("Error fixing fingerprints:", e)
            self.logger.error_logs(f"[FINGERPRINT FIXING ERROR] {e}")
            return 0


if __name__ == "__main__":
    logger = WatchHistoryLogger()
    # run the following for the updates till 10/12/2025
    # logger.refresh_csv_if_needed()
    # logger.fix_missing_fingerprints_by_name_and_duration()
    logger.get_watch_history_by_fingerprint("c227c88949826f0f9fd0b8199d24ab89")
