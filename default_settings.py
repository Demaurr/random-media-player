FILES_FOLDER = r"Files"
CSV_FOLDER = FILES_FOLDER  # change this to the folder where you want to get your Watched_History.csv from.
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
SKIP_FOLDERS = {r"$RECYCLE.BIN", r"._Datasets", r"._Workbooks", r"._text", r".bzr", r".cache", r".env", r".git", r".gitignore", r".hg", r".idea", r".next", r".nuxt", r".pytest_cache", r".svn", r".vs", r".vscode", r"Logs", r"Reports", r"Screenshots", r"Styles", r"System32", r"Video_Snippets", r"Windows", r"__pycache__", r"bin", r"build", r"cache", r"dist", r"env", r"log", r"logs", r"node_modules", r"obj", r"target", r"temp", r"tmp", r"venv", r"venv.bat", r"virtualenv"}

CATEGORIES_FILE = rf"{CSV_FOLDER}\categories.csv"

VIDEO_EXTENSIONS = r"['.3g2', '.3gp', '.avi', '.f4v', '.flv', '.m4v', '.mkv', '.mov', '.mp4', '.webm', '.wmv']"
SHOW_SNIPPETS = True
FAST_TRIM = True
DELETE_ORIGINAL_PNG = True
