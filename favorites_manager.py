import os
import csv
from datetime import datetime
from player_constants import DEFAULT_FAV
import hashlib


class FavoritesManager:
    def __init__(self, fav_csv=None):
        self.fav_csv = fav_csv if fav_csv is not None else DEFAULT_FAV

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
        if current_file and not self.check_favorites(current_file):
            video_name = os.path.basename(current_file)
            source_path = os.path.dirname(current_file)
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hashed_string = self.hash_string(video_name + source_path)


            # Write data to CSV file
            with open(self.fav_csv, "a", newline="", encoding="utf-8") as file:
                fieldnames = ["Hash", "Video Name", "Source Path", "Date Added"]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                if file.tell() == 0:
                    writer.writeheader()  # Write header if file is empty
                writer.writerow({"Hash": hashed_string, "Video Name": video_name, "Source Path": source_path, "Date Added": date_added})
                print(f"ADDED {current_file} to Favorites\n")
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
                    print(f"ALREADY {row['Video Name']} is listed in Favorites")
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
            return True
        return False

    def get_favorites(self):
        """Returns the list of favorites (source path + filename)."""
        favorites = []
        with open(self.fav_csv, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                path = os.path.join(row["Source Path"], row["Video Name"])
                if os.path.exists(path):
                    favorites.append(path)
        return favorites
