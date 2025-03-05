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
            # Run ffprobe to get video width and height
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
            # Parse the width and height from the ffprobe output
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
        
        # Collect vertical videos based on the results
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

    def get_video_durations(self):
        """
        Retrieves the duration of each video file using parallel processing.

        :return: Dictionary mapping video files to their durations (in seconds) or None if an error occurs.
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            durations = list(executor.map(self._get_duration, self.video_files))
        return dict(zip(self.video_files, durations))

    def _get_duration(self, video_file):
        """
        Helper method to retrieve the duration of a single video file using ffprobe.

        :param video_file: Path to the video file
        :return: Duration in seconds as float, or None if an error occurs.
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_file
                ],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"FFprobe error for {video_file}: {result.stderr}")
                return None
            duration_str = result.stdout.strip()
            if not duration_str:
                print(f"No duration found for {video_file}")
                return None
            return float(duration_str)
        except Exception as e:
            print(f"Error getting duration for {video_file}: {e}")
            return None