from videoplayer import MediaPlayerApp
from file_loader import VideoFileLoader
if __name__ == "__main__":
    folder_paths = input("Enter folder path(s) separated by comma: ").split(", ")
    video_files = VideoFileLoader()
    video_files = video_files.get_video_files(folder_paths=folder_paths)
    if video_files:
        app = MediaPlayerApp(video_files)
        app.update_video_progress()
        app.mainloop()
    else:
        print("No video files found in the specified folder path(s).")