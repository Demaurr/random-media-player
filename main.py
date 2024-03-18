from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
if __name__ == "__main__":
    folder_path_string = input("Enter folder path(s) separated by comma: ").strip()
    # video_files = VideoFileLoader(csv_folder="Files/")
    vf_loader = VideoFileLoader()
    if folder_path_string == "play favs":
        favs = FavoritesManager()
        video_files = favs.get_favorites()
    else:
        video_files = vf_loader.start_here(folder_path_string)
    # testing_csv_path = video_files.check_folders_path(folder_paths)
    # if testing_csv_path:
    #     print("Testing CSV Path:", testing_csv_path)
    # video_files = vf_loader.get_videos_from_paths(folder_paths=folder_paths)
    # video_files = vf_loader.get_videos_from_csv(folder_paths)

    if video_files:
        app = MediaPlayerApp(video_files)
        app.update_video_progress()
        app.mainloop()
    else:
        print("No video files found in the specified folder path(s).")