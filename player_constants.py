# Path of Folders
FILES_FOLDER = r"Testing"
CSV_FOLDER = FILES_FOLDER # change this to the folder where you want to get your Watched_History.csv from.
SCREENSHOTS_FOLDER = rf"{FILES_FOLDER}\Screenshots"
REPORTS_FOLDER = rf"{FILES_FOLDER}\Reports"
LOGS_FOLDER = rf"{FILES_FOLDER}\Logs"
ANALYTICS_FOLDER = rf"{FILES_FOLDER}\Analytics"
STYLES_FOLDER = r"Styles"
DEMO_FOLDER = r"Dummy Data"

# Path of Files
FOLDER_LOGS = rf"{CSV_FOLDER}\Log_Folders.csv"
DEMO_WATCHED_HISTORY = rf"{DEMO_FOLDER}\Demo_Watched_History.csv"
LOG_PATH = rf"{LOGS_FOLDER}\Action_Logs.log"
FAV_PATH = rf"{FILES_FOLDER}\fav_paths.txt"
WATCHED_HISTORY_LOG_PATH = rf"{CSV_FOLDER}\Watched_History.csv"
DELETE_FILES_CSV = rf"{CSV_FOLDER}\To_Delete.csv"
STYLE_FILE = rf"..\..\{STYLES_FOLDER}\style.css"
FAV_FILES = rf"{CSV_FOLDER}\Favorites.csv"
FILE_TRANSFER_LOG = rf"{CSV_FOLDER}\file_transfer_log.csv"
ALL_MEDIA_CSV = rf"{CSV_FOLDER}\ALL_MEDIA.csv"
SKIP_FOLDERS = {r".bzr", r".cache", r".env", r".git", r".hg", r".idea", r".next", r".nuxt", r".pytest_cache", r".svn", r".vs", r".vscode", r"Files\Reports", r"Files\Screenshots", r"Logs", r"Styles", r"__pycache__", r"bin", r"build", r"cache", r"dist", r"env", r"log", r"logs", r"node_modules", r"obj", r"target", r"temp", r"tmp", r"venv", r"venv.bat", r"virtualenv"}

CATEGORIES_FILE = rf"{CSV_FOLDER}\categories.csv"
# under construction
CATEGORIES_OPERATIONS_FILE = rf"{ANALYTICS_FOLDER}\categories_operations.csv"
CATEGORIES_USAGE_FILE = rf"{ANALYTICS_FOLDER}\categories_usage.csv"
CATEGORIES_INTERACTION_FILE = rf"{ANALYTICS_FOLDER}\categories_interaction.csv"

class Colors:
    """A class to hold color constants for the application."""
    GREEN = "#28a745"
    GREEN_HOVER = "#218838"
    ORANGE = "#ffa500"
    ORANGE_HOVER = "#cc8400"
    RED = "#dc3545"
    RED_HOVER = "#c82333"
    PLAIN_BLACK = "black"
    BLACK = "#2a2a2a"
    BLACK_HOVER = "#1a1a1a"
    PLAIN_WHITE = "white"
    PLAIN_RED = "red"
    PLAIN_ORANGE = "orange"
    WHITE_HOVER = "#f0f0f0"
    HEADER_COLOR_RED = "#ff4444"
    TEXT_COLOR = "white"
