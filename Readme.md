# Random Media Analyser

![Main Screen Page](Screenshots/Current_GUI_Main_Screen.PNG)

## Overview

**Random Media Analyser** is a Python-based desktop application for playing local video files, tracking your watch time, and managing your media library. It features all the conventional video playing options with an addition to the analysing of media consumption.

Supported video formats include: **avi, mp4, mkv, m4v, mov, webm, wmv, flv**.

For full details, advanced features, keyboard shortcuts, troubleshooting, and contributing guidelines, please see the [Documentation](Documentations/documentation.md).

---

## Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/Demaurr/random-media-player.git
    ```

2. **Navigate to the project directory:**
    ```bash
    cd random-media-player
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---
## Screenshots
![Media Player](Screenshots/Current_Main_Screen.PNG)

## Main Features

- **Video Playback:** Play videos from your local directories with a user-friendly interface.
- **Playback Controls:** Play, pause, stop, fast-forward, rewind, and adjust volume.
- **Watch History:** Automatically logs watched videos and durations.
- **Favorites:** Save and quickly access your favorite media files.
- **Image Viewing:** View screenshots taken during playback.
- **File Management:** Move or mark files for deletion directly from the app.
- **Session Statistics:** View and export watch statistics for your sessions.

---

## Usage

1. **Configure Paths:**  
   Edit `player_constants.py` to set your preferred folders for media, screenshots, and logs.

2. **Launch the Application:**  
   Run the GUI version (recommended):
   ```bash
   python gui_main.py
   ```
   - Enter a folder path in the search box to list all media files.
   - Use the interface or keyboard shortcuts for playback and management.
   - Double-click a file to start playback.
   - Access favorites, screenshots, and statistics from within the app.

3. **Command-Line Mode (Optional/Deprecated):**  
   Run `main.py` for a command-line interface:
   ```bash
   python main.py
   ```
   - Follow prompts to select and play media.

---

## More Information

- **Keyboard Shortcuts**
- **Advanced Commands**
- **Troubleshooting**
- **Contributing**
- **Project Structure**

See the [full documentation](Documentations/documentation.md) for details on all features, usage tips, and development guidelines.
