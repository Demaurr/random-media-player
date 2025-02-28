import subprocess
from concurrent.futures import ThreadPoolExecutor

class VideoProcessor:
    def __init__(self, video_files, max_workers=8):
        """
        Initializes the VideoProcessor with a list of video files and the number of workers for parallel processing.

        :param video_files: List of paths to video files
        :param max_workers: Maximum number of threads to use for parallel processing
        """
        self.video_files = video_files
        self.max_workers = max_workers

    def is_video_vertical(self, video_file):
        """
        Checks if a video file is vertical using ffprobe.

        :param video_file: Path to the video file
        :return: True if the video is vertical, False otherwise
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe", 
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height",
                    "-of", "csv=p=0",
                    video_file
                ],
                capture_output=True,
                text=True
            )
            width, height = map(int, result.stdout.strip().split(','))
            return height > width
        except Exception as e:
            print(f"Error checking video {video_file}: {e}")
            return False

    def get_vertical_videos(self):
        """
        Determines which videos are vertical using parallel processing.

        :return: List of paths to vertical videos
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.is_video_vertical, self.video_files))
        
        vertical_videos = [file for file, is_vertical in zip(self.video_files, results) if is_vertical]
        return vertical_videos

    def get_horizontal_videos(self):
        """
        Determines which videos are horizontal using parallel processing.

        :return: List of paths to horizontal videos
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.is_video_vertical, self.video_files))
        
        # Collect horizontal videos based on the results
        horizontal_videos = [file for file, is_vertical in zip(self.video_files, results) if not is_vertical]
        return horizontal_videos

# Example usage:
# video_files = ['video1.mp4', 'video2.m4v', 'video3.mp4']
# video_processor = VideoProcessor(video_files)
# vertical_videos = video_processor.get_vertical_videos()
# horizontal_videos = video_processor.get_horizontal_videos()
# print("Vertical Videos:", vertical_videos)
# print("Horizontal Videos:", horizontal_videos)
