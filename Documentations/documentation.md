# Random Media Player
![Defualt Screen](Screenshots/Main_Screen4.PNG)
### Overview
The Media Player Application is a Python-based desktop application designed to play video files with various control functionalities. 

It helps users to keep track of their watch_time while watching movies or any videos.

It provides all the typical mediaplayer features such as playing, pausing, fast forwarding, rewinding, selecting files, saving favs. The application uses the Tkinter library for the graphical user interface (GUI) and the python-vlc library for video playback.

The Player Can Play Typical Media Files and Keep Stats tracking and Saving Your Favorites and Play Your Favorites in a easy and efficient way.

## Project Structure

The project follows a modular structure to separate concerns and improve maintainability:

- **file_loader.py**: Handles file loading functionalities.
- **logs_writer.py**: Class which can be used to record update/error logs in a given file.
- **favorites_manager.py**: Manages Favorites Saving, Removing and Reading to a given csv for Favorites.
- **video_progress_bar.py**: Manages the video progress bar widget.
- **video_stats.py**: Handles video playback statistics.
- **videoplayer.py**: Implements the main media player application. Contains all the methods for Functionalities in Mediaplayer.
- **volume_bar.py**: Controls the volume adjustment widget.
- **watch_dictionary.py**: Defines the custom dictionary class for watch history.
- **watch_history_logger.py**: Logs watch history data to a CSV file.
- **summary_generator.py**: Generates Summary in HTML file format For the Recent Session's Watches.
- **main.py**: Entry point for running the application.

## Functionality
* Walk the Given Folder using `os` library and get all the media files in the directory and its sub-directory.
* Keep Track of the All The Videos Watched related Info and store it in a **csv** through `watch_history_logger.py`.
* Records the Statistics for the Current Open Session and shows stats through `video_stats.py` in a separate window.
* Generates Summary in HTML Format Through The respective Button in **"Session Statistics"** window.
* Keyboard keys with Player Buttons
    * KeyPress-Right: When the right arrow key is pressed, the function fast_forward is triggered.
    * Shift-KeyPress-Right: When the right arrow key is pressed while holding down the Shift key, the function play_next is triggered.
    * KeyPress-space: When the spacebar is pressed, the function pause_video is triggered.
    * KeyPress-Left: When the left arrow key is pressed, the function rewind is triggered.
    * Shift-KeyPress-Left: When the left arrow key is pressed while holding down the Shift key, the function play_previous is triggered.
    * Shift-KeyPress-s: Saves Snapshot of the screen with the name containing filename and time(in milliseconds) when it captured.
    * Control-f/F: Saves the Current File to The Favorites.
    * Control-d/d: Removes the Current File from Favorites.
    * KeyPress-n/N: Plays The Next Video.
    * KeyPress-p/P: Plays The Previously played Video.


## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/Demaurr/random-media-player.git
    ```

2. Navigate to the project directory:

    ```bash
    cd random-media-player
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Files

The project consists of the following files:

1. **file_loader.py**:
    > Having Class For **Loading** From Given **Path(s)** or **Csv(s)**. Note This Uses Another My(Filing) Library Which Can Be Downloaded from here: **[Filer](https://github.com/Demaurr/Filer)**.
2. **logs_writer.py**: Class which can be used to record update/error logs in a given file.
3. **favorites_manager.py**: Manages Favorites Saving, Removing and Reading to a given csv for Favorites.
4. **video_progress_bar.py**: Defines a custom progress bar widget for displaying video playback progress.
5. **video_stats.py**: Contains classes for managing and displaying video playback statistics.
6. **videoplayer.py**: Implements the main video player application, including playback controls and user interface.
7. **volume_bar.py**: Provides a volume control widget for adjusting audio levels during video playback.
8. **watch_dict.py**: Defines a custom dictionary class for managing watch history.
9. **watch_history_logger.py**: Logs watch history data to a CSV file.
10. **summary_generator.py**: Generates Summary in HTML file format For the Recent Session's Watches.
11. **main.py**: Entry point for running the media player application.



## Features

- **Video Playback**: Users can select and play video files from their local directories.
- **Playback Controls**: Provides controls for play, pause, stop, fast-forward, and rewind.
- **Watch History**: Keeps track of watched videos and their playback durations.
- **Statistics**: Displays statistics on watched videos, including total duration watched and frequency of playback.
- **Customization**: Users can customize the application by selecting different video files, adjusting volume, and viewing playback progress.

## Usage
*   Change the ***CONSTANT VARIABLES*** in `videoplayer.py`, `summary_generator.py` and `video_stats.py` to set the Path you want to store record files.
*   Then Run `main.py`, through `py main.py`, to launch the application.
*   Provide a **Folder Path** To Searching media files in **cmd** as input.
*   Use the interface to select video files from your directories.
*   Control video playback using the buttons provided (play, pause, rewind, fast forward, etc.).
*   **Current Stats** button will show the Statistic uptill that point.
*   **Play** button will restart the current video.
*   Close the application when finished.
*   After closing The Sessions Watch Statistics Window will be Shown.
*   These Statistics can be saved as a HTML file by clicking on **Generate Summary** Button.

## Contributing

Contributions to the Media Player Application are welcome! If you have any suggestions, bug fixes, or feature requests, please feel free to open an issue or submit a pull request on GitHub.

## Acknowledgments

Special thanks to the developers of the Tkinter and python-vlc libraries and [makeuseof](https://www.makeuseof.com/python-video-media-player-how-to-build/) site for their contributions to open-source software.

## Future Enhancements

* ### **Playback Events**

    Capture events related to video playback, such as start, pause, resume, stop, seek, etc., along with timestamps for each event. 
    This feature can be implemented by adding event listeners to the media player instance and logging the relevant information (event type, timestamp) to a log file or database whenever an event occurs.
