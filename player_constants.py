# Path of Folders
FILES_FOLDER = r"Files"
CSV_FOLDER = FILES_FOLDER # change this to the folder where you want to get your Watched_History.csv from.
SCREENSHOTS_FOLDER = rf"{FILES_FOLDER}\Screenshots"
SCREENSHOTS_COMPRESSED_FOLDER = rf"{SCREENSHOTS_FOLDER}\Compressed"
REPORTS_FOLDER = rf"{FILES_FOLDER}\Reports"
LOGS_FOLDER = rf"{FILES_FOLDER}\Logs"
ANALYTICS_FOLDER = rf"{FILES_FOLDER}\Analytics"
VIDEO_SNIPPETS_FOLDER = rf"{FILES_FOLDER}\Video_Snippets"
BACKUP_FOLDER = rf"{FILES_FOLDER}\Backup"
STYLES_FOLDER = r"Styles"
DEMO_FOLDER = r"Dummy Data"

# Path of Files
FOLDER_LOGS = rf"{CSV_FOLDER}\Log_Folders.csv"
DEMO_WATCHED_HISTORY = rf"{DEMO_FOLDER}\Demo_Watched_History.csv"
LOG_PATH = rf"{LOGS_FOLDER}\Action_Logs.log"
STATS_LOG_PATH = rf"{LOGS_FOLDER}\Stats_Logs.log"
DESCRIPTION_LOG_PATH = rf"{LOGS_FOLDER}\Description_Logs.log"
ASSOCIATION_LOG_PATH = rf"{LOGS_FOLDER}\Association_Logs.log"
FAV_PATH = rf"{FILES_FOLDER}\fav_paths.txt"
WATCHED_HISTORY_LOG_PATH = rf"{CSV_FOLDER}\Watched_History.csv"
DELETE_FILES_CSV = rf"{CSV_FOLDER}\To_Delete.csv"
STYLE_FILE = rf"..\..\{STYLES_FOLDER}\style.css"
FAV_FILES = rf"{CSV_FOLDER}\Favorites.csv"
FILE_TRANSFER_LOG = rf"{CSV_FOLDER}\file_transfer_log.csv"
ALL_MEDIA_CSV = rf"{CSV_FOLDER}\ALL_MEDIA.csv"
VIDEO_STATS_CSV = rf"{CSV_FOLDER}\Video_Stats.csv"
NOTES_CSV = rf"{CSV_FOLDER}\Video_Notes.csv"
NOTES_LOG_PATH = rf"{LOGS_FOLDER}\Notes_Logs.log"
SNIPPETS_HISTORY_CSV = rf"{CSV_FOLDER}\Trim_History.csv"
DESCRIPTION_CSV = rf"{CSV_FOLDER}\Video_Description.csv"
FINGERPRINTS_CSV = rf"{CSV_FOLDER}\Media_Fingerprints.csv"
FINGERPRINTS_LOG_PATH = rf"{LOGS_FOLDER}\Media_Fingerprints.log"
FINGERPRINTS_PATHS_CSV = rf"{CSV_FOLDER}\Fingerprint_Paths.csv"
SCREENSHOTS_CSV = rf"{CSV_FOLDER}\Screenshots.csv"
ASSOCIATIONS_CSV = rf"{CSV_FOLDER}\File_Associations.csv"
MEMBERS_CSV = rf"{CSV_FOLDER}\Members.csv"
MEDIA_MEMBERS_CSV = rf"{CSV_FOLDER}\Media_Members.csv"
MEMBERS_LOG_PATH = rf"{LOGS_FOLDER}\Members_Logs.log"
ANNOTATIONS_CSV = rf"{CSV_FOLDER}\Annotations.csv"
ANNOTATIONS_LOG_PATH = rf"{LOGS_FOLDER}\Annotations_Logs.log"
SKIP_FOLDERS = {r"$RECYCLE.BIN", r"._Datasets", r"._Workbooks", r"._text", r".bzr", r".cache", r".env", r".git", r".gitignore", r".hg", r".idea", r".next", r".nuxt", r".pytest_cache", r".svn", r".vs", r".vscode", r"Logs", r"Reports", r"Screenshots", r"Styles", r"System32", r"Video_Snippets", r"Windows", r"__pycache__", r"bin", r"build", r"cache", r"dist", r"env", r"log", r"logs", r"node_modules", r"obj", r"target", r"temp", r"tmp", r"venv", r"venv.bat", r"virtualenv"}

CATEGORIES_FILE = rf"{CSV_FOLDER}\categories.csv"
# under construction
CATEGORIES_OPERATIONS_FILE = rf"{ANALYTICS_FOLDER}\categories_operations.csv"
CATEGORIES_USAGE_FILE = rf"{ANALYTICS_FOLDER}\categories_usage.csv"
CATEGORIES_INTERACTION_FILE = rf"{ANALYTICS_FOLDER}\categories_interaction.csv"

# Other Constants
VIDEO_EXTENSIONS = r"['.3g2', '.3gp', '.avi', '.f4v', '.flv', '.m4v', '.mkv', '.mov', '.mp4', '.webm', '.wmv']"
SHOW_SNIPPETS = True
FAST_TRIM = True
DELETE_ORIGINAL_PNG = True

CSV_CONFIG = {
    DELETE_FILES_CSV: {
        "headers": ["File Path", "Delete_Status", "File Size", "Modification Time"],
        "descriptions": {
            "File Path": "Path of file to be deleted",
            "Delete_Status": "Status of deletion operation",
            "File Size": "Size of the file in bytes",
            "Modification Time": "Last modification time of the file"
        }
    },
    
    FOLDER_LOGS: {
        "headers": ["Folder Path", "Csv Path", "Date"],
        "descriptions": {
            "Folder Path": "Path of the scanned folder",
            "Csv Path": "Path to the CSV file containing logs",
            "Date": "Date when the folder was scanned"
        }
    },
    
    FILE_TRANSFER_LOG: {
        "headers": ["Source Path", "Destination Path", "Status", "Date"],
        "descriptions": {
            "Source Path": "Original path of the file",
            "Destination Path": "Destination path where file was transferred",
            "Status": "Status of the transfer operation",
            "Date": "Date and time of transfer"
        }
    },
    
    ANNOTATIONS_CSV: {
        "headers": [
            "annotation_id",
            "index_hash",
            "file_path",
            "timestamp_seconds",
            "annotation_text",
            "created_at",
            "modified_at"
        ],
        "descriptions": {
            "annotation_id": "Unique identifier for the annotation",
            "index_hash": "Hash index (fingerprint) of the media file",
            "file_path": "Full path to the annotated file",
            "timestamp_seconds": "Timestamp in seconds where annotation was added",
            "annotation_text": "Text content of the annotation",
            "created_at": "Date and time when annotation was created",
            "modified_at": "Date and time when annotation was last modified"
        }
    },
    
    ASSOCIATIONS_CSV: {
        "headers": [
            "source_file", "source_hash", "target_file", "target_hash",
            "association_type", "source_size", "target_size",
            "association_date", "association_status"
        ],
        "descriptions": {
            "source_file": "Path of the source file",
            "source_hash": "Hash index (fingerprint) of the source file",
            "target_file": "Path of the target/associated file",
            "target_hash": "Hash index (fingerprint) of the target file",
            "association_type": "Type of association between files",
            "source_size": "Size of the source file in bytes",
            "target_size": "Size of the target file in bytes",
            "association_date": "Date when association was created/updated",
            "association_status": "Status of the association (active/inactive)"
        }
    },
    
    CATEGORIES_FILE: {
        "headers": [
            "Category Name", "File Path", "Index Hash", "Date Added"
        ],
        "descriptions": {
            "Category Name": "Name of the category",
            "File Path": "Path of the file in this category",
            "Index Hash": "file's fingerprint from the fingerprint manager",
            "Date Added": "Date when the file was added to category"
        }
    },
    
    DESCRIPTION_CSV: {
        "headers": [
            "video_path", "size", "description", "timestamp"
        ],
        "descriptions": {
            "video_path": "Full path to the video file",
            "size": "Size of the video file in bytes",
            "description": "Description or metadata of the video",
            "timestamp": "Date and time when description was added"
        }
    },
    
    FAV_FILES: {
        "headers": ["Hash", "Video Name", "Source Path", "Date Added"],
        "descriptions": {
            "Hash": "Hash of filepath and filename for quick lookup (not the media fingerprint)",
            "Video Name": "Name of the video file",
            "Source Path": "Original path of the file",
            "Date Added": "Date when file was added to favorites"
        }
    },
    
    FINGERPRINTS_CSV: {
        "headers": [
            "name", "duration", "size_bytes", "partial_hash", "index_hash"
        ],
        "descriptions": {
            "name": "Name or identifier of the media file",
            "duration": "Duration of the video in seconds",
            "size_bytes": "Size of the file in bytes",
            "partial_hash": "Partial hash of the file for quick comparison",
            "index_hash": "Full index hash unique identifier of the file"
        }
    },
    
    FINGERPRINTS_PATHS_CSV: {
        "headers": [
            "index_hash", "file_path", "unique_id", "added_at"
        ],
        "descriptions": {
            "index_hash": "Hash index (fingerprint) of the media file",
            "file_path": "Full path where the file is located",
            "unique_id": "Unique identifier for this fingerprint entry",
            "added_at": "Date and time when fingerprint was recorded"
        }
    },
    
    NOTES_CSV: {
        "headers": [
            "index_hash",
            "file_path",
            "note",
            "rating",
            "tags",
            "mood",
            "context",
            "timestamp"
        ],
        "descriptions": {
            "index_hash": "Hash index (fingerprint) of the media file",
            "file_path": "Full path to the media file",
            "note": "Text note or comment about the file",
            "rating": "User rating of the file (numeric)",
            "tags": "Comma-separated tags for categorization",
            "mood": "Mood or emotion associated with the content",
            "context": "Context or additional information",
            "timestamp": "Date and time when note was created"
        }
    },
    
    SNIPPETS_HISTORY_CSV: {
        "headers": [
            "Timestamp", "Original File", "Original File Size", "Output File",
            "Start Time (s)", "End Time (s)", "Trim Mode",
            "Total Duration (s)", "Resolution", "File Size (MB)", "File Size (Bytes)",
            "Video Format", "Notes", "Original Fingerprint", "Snippet Fingerprint"
        ],
        "descriptions": {
            "Timestamp": "Date and time when snippet was created",
            "Original File": "Path of the original video file",
            "Original File Size": "Size of the original file in bytes",
            "Output File": "Path of the created snippet file",
            "Start Time (s)": "Start time of the clip in seconds",
            "End Time (s)": "End time of the clip in seconds",
            "Trim Mode": "Method used for trimming",
            "Total Duration (s)": "Total duration of the original video",
            "Resolution": "Video resolution of the snippet",
            "File Size (MB)": "Size of snippet file in megabytes",
            "File Size (Bytes)": "Size of snippet file in bytes",
            "Video Format": "Video format/codec of the snippet",
            "Notes": "User notes about the snippet",
            "Original Fingerprint": "Fingerprint hash of the original file",
            "Snippet Fingerprint": "Fingerprint hash of the created snippet"
        }
    },
    
    VIDEO_STATS_CSV: {
        "headers": [
            "File Path", "File Size", "Duration (s)", "Resolution", "Aspect Ratio", "Orientation",
            "Format", "Video Codec", "Bitrate (kbps)", "Frame Rate", "Pixel Format",
            "Profile", "Level", "Audio Codec", "Audio Channels", "Audio Sample Rate"
        ],
        "descriptions": {
            "File Path": "Full path to the video file",
            "File Size": "Size of the video file in bytes",
            "Duration (s)": "Duration of the video in seconds",
            "Resolution": "Resolution of the video (e.g., 1920x1080)",
            "Aspect Ratio": "Aspect ratio of the video",
            "Orientation": "Orientation of the video (portrait/landscape)",
            "Format": "Container format of the video",
            "Video Codec": "Video codec used for encoding",
            "Bitrate (kbps)": "Bitrate of the video in kilobits per second",
            "Frame Rate": "Frame rate in frames per second",
            "Pixel Format": "Pixel format/color space of the video",
            "Profile": "Codec profile used",
            "Level": "Codec level used",
            "Audio Codec": "Audio codec used for encoding",
            "Audio Channels": "Number of audio channels",
            "Audio Sample Rate": "Audio sample rate in Hz"
        }
    },
    
    WATCHED_HISTORY_LOG_PATH: {
        "headers": [
            "File Name", "Total Duration", "Date Watched",
            "Duration Watched", "Last Position", "Fingerprint"
        ],
        "descriptions": {
            "File Name": "Name of the video file",
            "Total Duration": "Total duration of the video in seconds",
            "Date Watched": "Date and time when the video was last watched",
            "Duration Watched": "Duration watched in the current session",
            "Last Position": "Last playback position in seconds",
            "Fingerprint": "Hash fingerprint identifier of the file"
        }
    },
}

class Colors:
    """A class to hold color constants for the application."""
    GREEN = "#28a745"
    GREEN_HOVER = "#218838"
    ORANGE = "#ffa500"
    ORANGE_HOVER = "#cc8400"
    RED = "#dc3545"
    RED_HOVER = "#c82333"
    ACTIVE_RED = "#b30000"
    ACTIVE_WHITE = "#e0e0e0"
    RED_PROGRESS_BAR = "#A23333"
    PLAIN_BLACK = "black"
    BLACK = "#2a2a2a"
    BLACK_HOVER = "#1a1a1a"
    BLACK_ENTRYBOX = "#181818"
    CATEGORY_PURPLE = "#4B0082"
    PLAIN_WHITE = "white"
    PLAIN_RED = "red"
    PLAIN_ORANGE = "orange"
    PLAIN_GREEN = "green"
    PLAIN_PURPLE = "purple"
    PLAIN_GRAY = "gray"
    PLAIN_BLUE = "blue"
    INFO_BLUE = "#4FC3F7"
    WHITE_HOVER = "#f0f0f0"
    HEADER_COLOR_RED = "#ff4444"
    SUCCESS_GREEN = "#4CAF50"
    WARNING_ORANGE = "#FF9800"
    TEXT_COLOR = "white"
    TEXT_MUTED_GRAY = "#78909C"
