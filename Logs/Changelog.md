# Changelog

All notable changes to this project will be documented in this file.

## **Version [3.5.0]** **2025-06-29**

### Added
- Subtitle support in videos, including speed management and dedicated keybindings.
- Video Snippets feature: mark start/end points and trim snippets directly in the videoplayer.
- **snippets_manager** module to manage trimmed video snippets in a dedicated folder.
- New constants for Video Snippets folder and CSV in *`player_constants.py`*.
- Playback speeds for 1.25x and 1.75x.
- Keybinding to toggle Autoplay setting.
- Messageboxes for filedialogs now appear on top of the parent window for better UX.

### Changed
- MediaPlayer now uses `Toplevel` instead of a separate `tk.Tk` instance, preventing crashes.
- Added Always on Top Functionality for Mediaplayer, allowing user to work on the background while the Mediaplayer stays in place.
- Improved error handling and media releasing in `release_current_media`, `play_next`, and `play_previous`.
- Updated **Colors** class for consistent theme and increased max volume to 200 (as supported by python-vlc).
- Modified volume bar to support new max volume.

### Fixed
- Autoplay settings now correctly update via keybinding.
- Improved speed of `refresh_categories` and `on_category_select` methods for large file sets.

## **Version [3.4.0]** **2025-06-03**

### Added
- Category management system for organizing and saving video playlists.
- Custom messagebox to prevent GUI conflicts during error handling.
- Category management features in videoplayer and gui_main with keybindings.
- **Colors** class in *`player_constants.py`* for centralized color management.
- Additional **PATHS** in *`player_constants.py`* for categories management.
- Show categories command in *`gui_main.py`* for displaying and playing from categories.
- **`sort_treeview_column()`** method from *`static_methods.py`* for table sorting.
- Parent window parameter to *`deletion_manager.py`* for proper window stacking.
- Profile management system allowing creation of new profiles via **FILES_FOLDER**.

### Changed
- Restructured *`settings_manager.py`* with improved GUI and better constants management.
- Modified Dashboard overview style using grid layout for cleaner appearance.
- Improved path normalization when moving files.
- Enhanced error handling across `gui_main`, `deletion_manager` and other modules.
- Updated timeout duration in videoplayer for smoother playback.
- Modified comments and docstrings for better code maintenance.
- Modularized player creation and media release processes.

### Fixed
- Memory leaks by properly stopping mediaplayer in background on window close.
- Category updates when moving files between directories.
- Various minor issues related to video playback and UI responsiveness.
- Error handling with improved user feedback and engagement.

## **Version [3.3.0]** **2025-05-26**

### Added
- Messagebox in `deletion_manager` to display info if no updates are available.
- `bd=1` to `volume_bar` layout for a cleaner look.
- Rotation option in `image_player` for easier image viewing.
- Sample method to add/remove images from favorites (not yet implemented).
- `ensure_trailing_backslash` method to normalize paths and prevent duplicate tables for the same path.
- Mute option in `videoplayer`.
- Focusing new windows using **`.lift()`** and **`.focus_force()`** in tkinter for better UX.
- *`media_dashboard.py`* module for dashboard creation with detailed plots.
- Opening of video_stats report in a default browser using method from *`static_methods.py`*.

### Changed
- `gather_all_media` now works with threading in *`gui_main.py`* for improved performance.
- Completely revamped `image_player` for faster image loading and fixed image display bugs.
- Modified `get_favorites` to use threading for the "play favs" section in *`gui_main.py`*.
- Changed **"time.sleep"** duration in `play_video` from 0.1s to 0.3s.
- Added threading for filtering file existence in favorites.
- Modularized codebase and removed unnecessary code and comments.

### Fixed
- Bugs related to image displaying in `image_player`.
- Bug of calculating the watch duration based on video duration even if the video is set to 2x.

## **Version [3.2.6]** **2025-05-23**
### Added
- Icons for pause and resume actions on mouse leave for improved UI feedback.
- Method for displaying previously used paths, replacing hard-coded logic.
- Count of selected files in the file table for easier file management.

### Changed
- Button placements for a more visually appealing layout.
- Top-level folder selection changed from a checkbox to a selection button.
- Removed multiple initializations of **`fav_manager`** to improve performance.

### Updated
- requirements.txt to include the `Pillow` library.
- readme to include the instructions to download vlc Mediaplayer before use.

## **Version [3.2.3]** **2025-05-22**

### Added
- Playback speed adjustments and keybindings for changing speed.
- Autoplay option for videos to randomly start after one finishes (default is on).
- Helper methods for modularity: `reset_values`, `cycle_playback_speed`, etc.
- Threading for loading and playing videos for a smoother experience.
- Sorting of the file table by clicking table headers.
- Option to search only in the top-level folder.
- Browse button for folder selection and updating constants.
- Info button to display usage instructions for new users.
- Settings manager for changing app constants and updating via `open_settings`.
- Buttons for settings, analyses (not yet functional), and all media.
- Method in `static_methods` to gather all media files from previously searched folders.
- Constants: `ALL_MEDIA_CSV` and `SKIP_FOLDERS`.
- Managing skip folders using defined folders from `player_constants.py`.

### Changed
- Name of the application to **Media Analyser**.
- Theme and frontend of MediaPlayer and Statsapp to a more modern, responsive look with bigger fonts and more icons.
- Layout with more icons instead of text.
- Modified watched duration calculation to take playback speed into account.
- Summary Report Layout to be More Responsive and Match the theme of the App.
- The structure of imports, removed unused variables and unnecessary comments.
- The paths in **`player_constants.py`**.
- Docstrings and standardized documentation.
- The requirements with the `Filing` package.

### Fixed
- Getting files from the same folder multiple times (now uses sets to clean paths).
- Video progress bar now expands correctly when maximized.
- Minor bugs and UI responsiveness issues.

### Documentation
- Updated documentation for new features and usage patterns.

## **Version [3.1.0]** **2025-03-08**

### Added
- Landscape and Vertical file filtering using ffmpeg in get_aspect.py
- Compare folder method in static_methods to ensure given directories are same regardless of the slashes used.
- Folder existence checking in the gui_main instead of videoplayer resolving folder_not_found bug.
- Added use of shutil instead of os.rename for moving files between the drives.  
- Added use of rename_if_exists when moving to favorites folder to prevent the overwriting of the files with the same name.
- Added methods refractor_csv and check_deleted to refactor the csv if need and refresh the csv by checking the availablity of the files in deletion_list.

### Changed
- The structure of the Deletion Csv by also having size and modification_date data.
- The paths and changed them to raw strings instead of simple format strings in player_constants.py.
- The getting favs and added get_favs_by_name which will get and save any file as fav using only the name.

### Fixed
- Spaces issues with the Paths (now strips paths for outer spaces)
- Minor Bugs

## **Version [3.0.2]** **2024-9-29**

### Added
- A new videotype **`.flv`**
- Logs writing in **`favorites_manager.py`** and calculation of Total Size of favorite files.
- Normalisation of paths in multiple places through the whole project to be consistent with the paths stored.
- A Context Menu in the **`gui_main.py`** to move or delete the selected files.
- Removal and addition to favorites through main ***file_table*** for easily maintaining files without playing each of them.
- ***Delete-All*** and ***Refresh-Delete*** Button to manage deletion easily and mark any file which is **un-deleted** or **deleted** outside this app.
- Filtering of favorites in the listed files in the **file_table** for easily maintaining and viewing of the favorites.
- Commands "`show deleted`" and "`show history`" to get deleted flies and watched history of the past 30 days.
- Moving files from one Directory to another and Updating the file_paths in the favorites and deletion_list.
- Handling of the Renaming of Files and maintaining the file_tranfer_log.csv and keep records of every transfer.
- More Keybindings in the `file_table` of **`gui_main.py`** to manage moving and favorites easily.
- Removal of file from deletion from within the videoplayer and Displaying of feedback marquee.
- More helpful methods in **`static_methods.py`** for renaming, covnerting data format and getting file size.


### Changed
- The Layout of the ***gui_main*** with more logical button placing and better **stats** info.
- Calculating the Duration Watched, now works with more precision by considering the forward and backward counts before storing in the **watched_history_csv**.
- Logs writing for favorite files in videoplayer and other places, now the logs are written within the methods in `Favorites_Manager` class.
- The Path strings in the player_constants, now follow a more consistent and easily changable method.
- `get_selected_video` in **`gui_main.py`**, now allows multiple selections.


### Fixed
- Deletion list wrting bugs in an event of an error.
- Date format in the **Watched_History_Csv** to follow a consistent format.

## **Version [2.7.4]** **2024-9-18**

### Added 
- Handling of deleting files that are in favorites
- A new videotype `'.mov'`
- An Extra_Paths file in the **"`FILES_FOLDER`"** which contains FAV_FOLDER to move the favorites file (set for delelion) to this if a folder is not provided by user.


### Changed
- Managing of Deletion Now It's Done Through separate **DeletionManager** from **`deletion_manager.py`**
- Using of methods like ensure_folder_exists and other from ***`static_methods.py`***

## **Version [2.7.2]** **2024-9-11**

### Added
- File position in the video title in videoplayer.
- A '**#**' column in the file table to Display the position no. of the files.
- `stats_frame` in the gui to display stats related to ***Total Size***, ***No. of Videos*** and ***Search Results***.
- Displaying of error messages encountered in the main methods using the tkinter's **messagebox**.
- A method for converting of bytes into a Human Readable Formats.
- A messagebox in **`image_player`** and **`videoplayer`** to display error encountered in core functions.
- Methods for File Deletion Functionality with Separate **Delete Marked** Button and Keybinding like '`<Delete>`', '`<Shift-Delete>`', '`<Control-Shift-Delete>`'.
- Marking a video For deletion in a csv and moving it to the recycle bin using lib '***`send2trash`***'.
- '**show deletes**' command to display the files marked for Deletion in ***DELETE_FILES_CSV***.
- Method for pausing the main root window (Unused).
- Using static files from ***`static_methods.py`*** to mark, delete and check for file existence.

### Updated
- requirements.txt with library used to send to recyclebin, '***`send2trash`***'

### Fixed
- the position of the play_images tag, now works fine with the '`CapShots`'.

## **Version [2.5.0]** **2024-7-30**

### Added
- An Image Player to View Saved Image Captures from the Videos through the Class ImageViewer in `image_player.py`.
- An Static method in ***file_loader.py*** to get Screenshots(Captures) files from the Screenshots folder defined in ***player_constants.py***.
- Added a Separate Button in `Videoplayer.py` to Directly Access the Screen Captures from the gui and display all the File in the File/Folder table.

### Updated
- The on_double_click, on_search_pressed and on_enter_pressed methods to comply with the image viewing and searching options.

## **Version [2.4.1]** **2024-06-15**

### Added
- A Functionality to Show Previously Recorded/Searched Paths For Ease of Displaying and Playing videos from it.
- A method update_entry() to update the entry input box with a given text value.
- A Seperate Log_Folders constant to access this Folder Log File from anywhere easily.

### Updated
- The on_double_click method to comply with the show paths options and display the videos from the path through double click or ```Return``` Press.

### Fixed
- Displaying of Duration in the Marquee when user forwards or backwards a video. This now displayes the changed Duration Correctly.

## **Version [2.3.0]** **2024-04-20**

### Added
- Added support for *.wmv* file-type.
- Added Search Bar for filtering videos returned from the given path in `gui_main.py`.
- Added Marquee Display for media functionalities and volume inc/dec.
- Added Playing Immediate Next/Previous file in the returned files_list in `gui_main.py`.
- Added Keyboard Shorcuts For `gui_main.py` to directly play a random file on search using *`Ctrl+Enter`*.

### Changed
- The Paths in `player_constants.py` to have **\\** rather than **/**.
- The Logic of random and sequential playing.

### Fixed
- Volume Controls in FullScreen Mode.

## **Version [2.2.0]** **2024-04-14**

### Added
- `gui_main.py` file which doesn't require the passing of path through the cmd, instead the path can be provided through the input in the gui app.

### Changed
- Contants Setting. Now Stores the Constants in a Separate File `player_contants.py`
- Closing of Stats App from window.quit() to window.destroy()
- Closing of Mediaplayer App, causing the "(after script)" issue again(Nothing serious).
- The setting of feedback. Now using vlc's **marquee** method to display this.
- The Loading of Files by normalising paths with **\\** instead of **/**.

## **Version [2.1.2]** **2024-03-22**

### Added
- functionality in `file_loader` to refresh `path(s)` if files are moved using **--update** after Path.
- sequential search check to play media as retrieved (sequentially)

### Changed
- Calculation of Watch time with Previous and Forward Counts For More Precision.

### Bug Fixes
- Fixed Closing  Mediaplayer after Current Stats Window is Closed.

## **Version [2.1.1]** **2024-03-21**

### Added
- writing Logs in `file_loader.py` and `watch_history_logger`
- checking of files existence on retrieval in `favorites_manager.py`

### Bug Fixes
- Resolved "after script" error in `videoplayer.py`. Might also stop Some Crashing related issues.


## **Version [2.0.0]** **2024-03-19**

### Added
- Functionality to Save Favorites
- Saving Logs for Favorites updation and Errors
- Videos Count in Summary Report
- File Loading by Saving Hashed Filenames Csv And Storing Media Files Locations For Fast Access
- Getting Files and Csvs Together in a Single Input
- Feedback label To Display Videoname and display Favorites Trigger
- Full Screen Functionality
- Saving Screen Capture of any Playing video.

### Changed
- Player Window Size from **800x600** to **1000x600**
- Media Playing by Skiping any File That Doesn't Exist
- Length of Media Progress Bar from **600** to **800**
- Displaying Button's Action Feedback by Showing it both on the Media Screen and Console

## **Version [1.1.0]** **2024-03-14**

### Added
- Keyboard Shortcuts for Player Buttons

### Changed
- App Theme From Bright To Red, White and Black
- Html File Theme to match App's

## **Version [1.0.0]**

### Added
- Initial project setup
- Implemented basic video playback functionality
- Added video file loading from local directories
- Implemented playback controls (play, pause, stop, rewind, fast forward)
- Added volume control functionality
- Implemented watch history logging to CSV file
- Added session statistics display
- Implemented HTML summary generation for session statistics
- Created project documentation (README.md, documentation.md)

## **[Version 1.0.0]** **2024-03-09**
- First official release of the Media Player Application

