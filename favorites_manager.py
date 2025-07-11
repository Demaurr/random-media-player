import os
import csv
from datetime import datetime
from logs_writer import LogManager
from player_constants import FAV_FILES, LOG_PATH, LOGS_FOLDER
from static_methods import create_csv_file, get_file_size, normalise_path, ensure_folder_exists
import hashlib
from pprint import pprint

class FavoritesManager:
    def __init__(self, fav_csv=FAV_FILES):
        ensure_folder_exists(LOGS_FOLDER)
        self.fav_csv = fav_csv
        self._ensure_favorites_csv()
        self.logger = LogManager(LOG_PATH)
        self.total_size = 0.0

    def _ensure_favorites_csv(self):
        create_csv_file(["Hash", "Video Name", "Source Path", "Date Added"], self.fav_csv)

    @staticmethod
    def hash_string(input_string, hash_length=32):
        """Generates a hash of the input string."""
        input_bytes = input_string.encode('utf-8')
        hasher = hashlib.sha256()
        hasher.update(input_bytes)
        hashed_string = hasher.hexdigest()
        return hashed_string[:hash_length]

    def add_to_favorites(self, current_file):
        """Adds the currently playing video to favorites and writes data to CSV."""
        current_file = normalise_path(current_file)
        if current_file and not self.check_favorites(current_file):
            video_name = os.path.basename(current_file)
            source_path = os.path.dirname(current_file)
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hashed_string = self.hash_string(video_name + source_path)

            with open(self.fav_csv, "a", newline="", encoding="utf-8") as file:
                fieldnames = ["Hash", "Video Name", "Source Path", "Date Added"]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if file.tell() == 0:
                    writer.writeheader()
                writer.writerow({"Hash": hashed_string, "Video Name": video_name, "Source Path": source_path, "Date Added": date_added})
                print(f"ADDED {current_file} to Favorites\n")
                self.logger.update_logs(f"[FAVORITES ADDED]", current_file)
            return True
        return False

    def check_favorites(self, current_file):
        """Checks if the given file is already in the favorites."""
        if not current_file:
            return False
        video_name = os.path.basename(current_file)
        source_path = os.path.dirname(current_file)
        hash_value = self.hash_string(video_name + source_path)
        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["Hash"] == hash_value:
                    return True
        return False

    def delete_from_favorites(self, current_file):
        """Deletes the given file from the favorites."""
        if current_file and self.check_favorites(current_file):
            video_name = os.path.basename(current_file)
            source_path = os.path.dirname(current_file)
            hash_value = self.hash_string(video_name + source_path)
            temp_csv = self.fav_csv + ".temp"

            with open(self.fav_csv, "r", newline="", encoding="utf-8") as file, \
                open(temp_csv, "w", newline="", encoding="utf-8") as temp_file:
                reader = csv.DictReader(file)
                writer = csv.DictWriter(temp_file, fieldnames=reader.fieldnames)
                writer.writeheader()
                for row in reader:
                    if row["Hash"] != hash_value:
                        writer.writerow(row)

            os.replace(temp_csv, self.fav_csv)
            print(f"REMOVED {current_file} from Favorites.\n")
            self.logger.update_logs(f"[FAVORITES REMOVED]", current_file)
            return True
        return False

    def get_favorites(self):
        """Returns the list of favorites (source path + filename) without checking file existence."""
        favorites = []
        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                path = os.path.join(row["Source Path"], row["Video Name"])
                favorites.append(path)
                self.total_size += get_file_size(path)
        return favorites
    
    def get_favorites_by_name(self) -> dict:
        """Returns a dictionary with video names as keys and sets of valid source paths as values."""
        favorites_dict = {}
        try:
            with open(self.fav_csv, "r", newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    video_name = row["Video Name"]
                    source_path = row["Source Path"]
                    full_path = os.path.join(source_path, video_name)
                    if video_name not in favorites_dict:
                        favorites_dict[video_name] = set()
                    favorites_dict[video_name].add(source_path)
        except FileNotFoundError:
            print(f"Favorites file {self.fav_csv} not found.")
            self.logger.error_logs(f"Favorites file {self.fav_csv} not found.")
        return favorites_dict
    
    def delete_favorites_by_name(self, video_name):
        """Deletes all entries with the given video name from favorites."""
        temp_csv = self.fav_csv + ".temp"
        removed = False
        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file, \
             open(temp_csv, "w", newline="", encoding="utf-8") as temp_file:
            reader = csv.DictReader(file)
            writer = csv.DictWriter(temp_file, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                if row["Video Name"] != video_name:
                    writer.writerow(row)
                else:
                    removed = True
                    self.logger.update_logs(f"[FAVORITES REMOVED]", f"{row['Video Name']} from {row['Source Path']}")
        if removed:
            os.replace(temp_csv, self.fav_csv)
        else:
            os.remove(temp_csv)
        return removed

    def update_path_and_hash(self):
        updated_rows = []
        hashes = set()
        with open(self.fav_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                updated_path = row['Source Path'].replace('/', '\\')
                updated_hash = self.hash_string(row['Video Name'] + updated_path, hash_length=32)
                hashes.add(updated_hash)
                row['Source Path'] = updated_path
                row['Hash'] = updated_hash
                updated_rows.append(row)
        print(updated_rows)
        print(len(updated_rows))
        print(len(hashes))

        # Write the updated data back to the CSV file
        with open(self.fav_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

    def update_favorite_path(self, old_path, new_path):
        """Updates the favorites CSV with the new file location after the file is moved."""
        if not old_path or not new_path:
            print("Invalid paths provided for update.")
            return False

        video_name = os.path.basename(old_path)
        old_source_path = normalise_path(os.path.dirname(old_path))
        new_source_path = normalise_path(os.path.dirname(new_path))
        old_hash = self.hash_string(video_name + old_source_path)
        new_hash = self.hash_string(video_name + new_source_path)

        updated = False
        temp_csv = self.fav_csv + ".temp"

        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file, \
                open(temp_csv, "w", newline="", encoding="utf-8") as temp_file:
            reader = csv.DictReader(file)
            writer = csv.DictWriter(temp_file, fieldnames=reader.fieldnames)
            writer.writeheader()

            for row in reader:
                if row["Hash"] == old_hash:
                    row["Source Path"] = new_source_path
                    row["Hash"] = new_hash
                    updated = True
                    print(f"[UPDATED FAVORITE]: {video_name} moved from {old_path} to {new_path}")
                    self.logger.update_logs(f"[FAVORITES UPDATED]", f"{video_name} changed from {old_path} to {new_path}")
                writer.writerow(row)

        if updated:
            os.replace(temp_csv, self.fav_csv)
            return True
        else:
            os.remove(temp_csv)  # If no update was made, remove the temp file
            print(f"File {old_path} was not found in favorites.")
            return False

    def normalize_favorites_paths_and_hashes(self):
        """
        Normalizes the file paths in the favorites CSV and updates the corresponding hash values.
        Converts all slashes to the appropriate format (e.g., backslashes for Windows).
        """
        updated_rows = []
        seen_hashes = set()
        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                original_path = os.path.join(row["Source Path"], row["Video Name"])
                
                normalized_path = normalise_path(original_path)
                row["Source Path"] = os.path.dirname(normalized_path)
                row["Video Name"] = os.path.basename(normalized_path)
                
                new_hash = self.hash_string(row["Video Name"] + row["Source Path"])
                
                if new_hash in seen_hashes:
                    print(f"Warning: Duplicate hash for {normalized_path}. Skipping entry.")
                    continue
                
                row["Hash"] = new_hash
                seen_hashes.add(new_hash)
                updated_rows.append(row)

        # Write the updated rows back to the favorites CSV
        with open(self.fav_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Hash", "Video Name", "Source Path", "Date Added"])
            writer.writeheader()
            writer.writerows(updated_rows)

        print(f"Favorites CSV file '{self.fav_csv}' has been updated with normalized paths and hashes.")
if __name__ == "__main__":
    # favs = FavoritesManager()
    # favs.update_path_and_hash()
    fav_manager = FavoritesManager()

    # Normalize paths and update hashes in the favorites CSV
    # fav_manager.normalize_favorites_paths_and_hashes()
    favorites_by_name = fav_manager.get_favorites_by_name()
    # for video_name, paths in favorites_by_name.items():
    #     if len(paths) > 1:
    #         print(f"Video: {video_name}, Paths: {paths}")

    pprint(favorites_by_name)
    pass