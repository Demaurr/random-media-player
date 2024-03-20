from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
from favorites_manager import FavoritesManager
if __name__ == "__main__":
    folder_path_string = input("Enter folder path(s) separated by comma: ").strip()
    vf_loader = VideoFileLoader()
    try:
        if folder_path_string == "play favs":
            favs = FavoritesManager()
            video_files = favs.get_favorites()
        else:
            video_files = vf_loader.start_here(folder_path_string)
    except Exception as e:
        print(f"An Error Occurred: {e}")
        video_files = vf_loader.get_videos_from_paths(folder_paths=folder_path_string.split(","))
    if video_files:
        print(f"Total Videos Found: {len(video_files)}")
        app = MediaPlayerApp(video_files)
        app.update_video_progress()
        app.mainloop()
    else:
        print("No video files found in the specified folder path(s).")