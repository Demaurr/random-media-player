import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
import json
from logs_writer import LogManager
from player_constants import STATS_LOG_PATH

class VideoProcessor:
    def __init__(self, video_files=None, max_workers=None):
        self.video_files = video_files or []
        self.logger = LogManager(STATS_LOG_PATH)
        self.max_workers = max_workers or max(1, (os.cpu_count() or 4) - 3)

    def is_video_vertical(self, video_file):
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
            print(f"Error checking orientation for {video_file}: {e}")
            self.logger.error_logs(f"Error checking orientation for {video_file}: {e}")
            return False

    def get_vertical_videos(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.is_video_vertical, self.video_files))
        return [file for file, is_vertical in zip(self.video_files, results) if is_vertical]

    def get_horizontal_videos(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.is_video_vertical, self.video_files))
        return [file for file, is_vertical in zip(self.video_files, results) if not is_vertical]

    def probe_video(self, video_file):
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries",
                    "format=duration,format_name",
                    "-show_entries",
                    "stream=index,codec_type,codec_name,width,height,bit_rate,r_frame_rate,profile,level,channels,sample_rate,pix_fmt,color_space",
                    "-of", "json",
                    video_file
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"FFprobe failed: {result.stderr}")
                return None

            data = json.loads(result.stdout)

            # General file info
            duration = float(data["format"].get("duration", 0))
            format_name = data["format"].get("format_name", "Unknown")

            # Initialize values
            width = height = bitrate = frame_rate = pix_fmt = None
            codec = profile = level = None
            audio_codec = channels = sample_rate = None

            for stream in data["streams"]:
                if stream.get("codec_type") == "video":
                    width = stream.get("width")
                    height = stream.get("height")
                    bitrate = stream.get("bit_rate")
                    frame_rate = stream.get("r_frame_rate")
                    pix_fmt = stream.get("pix_fmt")
                    codec = stream.get("codec_name")
                    profile = stream.get("profile")
                    level = stream.get("level")
                elif stream.get("codec_type") == "audio":
                    audio_codec = stream.get("codec_name")
                    channels = stream.get("channels")
                    sample_rate = stream.get("sample_rate")

            resolution = f"{width}x{height}" if width and height else "Unknown"
            aspect_ratio = round(width / height, 2) if width and height else "Unknown"
            orientation = "Vertical" if height and width and height > width else "Horizontal"
            frame_rate_val = eval(frame_rate) if frame_rate and "/" in frame_rate else frame_rate

            return {
                "Duration (s)": duration,
                "Resolution": resolution,
                "Aspect Ratio": aspect_ratio,
                "Orientation": orientation,
                "Format": format_name,
                "Video Codec": codec,
                "Bitrate (kbps)": round(int(bitrate) / 1000) if bitrate else None,
                "Frame Rate": frame_rate_val,
                "Pixel Format": pix_fmt,
                "Profile": profile,
                "Level": level,
                "Audio Codec": audio_codec,
                "Audio Channels": channels,
                "Audio Sample Rate": sample_rate,
            }

        except Exception as e:
            print(f"Error probing {video_file}: {e}")
            self.logger.error_logs(f"Error probing {video_file}: {e}")
            return None


    def process_videos(self, video_files):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self._process_single, video_files))
        return results

    def _process_single(self, video_file):
        metadata = self.probe_video(video_file)
        if not metadata:
            return None
        return {
            "File Path": video_file,
            "File Size": str(os.path.getsize(video_file)),
            **metadata
        }
