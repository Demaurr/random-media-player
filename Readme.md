# Random Media Analyser

![Main Screen Page](Screenshots/Current_Gui_Main_Screen.png)

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

4. **Download VLC Media Player:**  
   This application uses `python-vlc`, which requires the VLC Media Player and its libraries to be installed on your system.  
   **Download and install VLC from:** [https://www.videolan.org/vlc/](https://www.videolan.org/vlc/)  
   > Without VLC installed, video playback will not work.
---
## Screenshots
![Media Player](Screenshots/Current_Main_Screen.png)

---

## Dashboard Screenshots

The **Dashboard** provides a visual summary of your media activity and library. Below are some example dashboard screens and what they show:

### Overview
![Media Consumption Overview](Screenshots/Dashboard_Overview.png)
- **Overview of Media Consumption:**
  Shows the summary of media consumption with listing the trend of Past 30 days.

### Hourly Consumption

![Dashboard Hourly Consumption](Screenshots/Dashboard_Hourly_Consumption.png)

- **Media Consumption by Hour of Day:**  
  Shows at what hours you most frequently watch media, helping you spot your peak viewing times.
- **Hour vs Duration Category:**  
  A heatmap showing how many videos of each duration category (short, medium, long, etc.) are watched at each hour.

---

### Weekly Consumption

![Dashboard Weekly Consumption](Screenshots/Dashboard_Weekly_Consumption.png)

- **Media Watched by Day of Week:**  
  Bar chart showing how many videos are watched on each weekday.
- **Weekday Watched by Duration Category:**  
  Line chart showing trends for each duration category across the week.
- **Total Watch Duration by Day of Week:**  
  Bar chart of total minutes watched per weekday.
- **Weekly Consumption Table:**  
  Table summarizing the count and total duration watched for each weekday.

---

These dashboards help you understand your viewing habits, spot trends, and manage your media consumption more effectively.


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

## Quick Launch (Batch File)

If you haven't created an executable yet, you can use a batch file to run the app as if it were an executable.  
This also ensures the current directory is set correctly for relative paths:

1. Create a new file named `RunRandomMediaAnalyser.bat` in the project directory.
2. Add the following code to the batch file:

    ```bat
    @echo off
    cd <path to random-media-player dir>
    python gui_main.py
    pause
    ```

3. Double-click the batch file to launch the app.
4. This way you can use this program as an executable.

## More Information

- **Keyboard Shortcuts**
- **Advanced Commands**
- **Troubleshooting**
- **Contributing**
- **Project Structure**

See the [full documentation](Documentations/documentation.md) for details on all features, usage tips, and development guidelines.
