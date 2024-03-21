# Changelog

All notable changes to this project will be documented in this file.

## Version [2.1.2] - 2024-03-22

### Added
- functionality in `file_loader` to refresh `path(s)` if files are moved using **--update** after Path.
- sequential search check to play media as retrieved (sequentially)

### Changed
- Calculation of Watch time with Previous and Forward Counts For More Precision.

### Bug Fixes
- Fixed Closing  Mediaplayer after Current Stats Window is Closed.

## Version [2.1.1] - 2024-03-21

### Added
- writing Logs in `file_loader.py` and `watch_history_logger`
- checking of files existence on retrieval in `favorites_manager.py`

### Bug Fixes
- Resolved "after script" error in `videoplayer.py`. Might also stop Some Crashing related issues.


## Version [2.0.0] - 2024-03-19

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

## Version [1.1.0] - 2024-03-14

### Added
- Keyboard Shortcuts for Player Buttons

### Changed
- App Theme From Bright To Red, White and Black
- Html File Theme to match App's

## Version [1.0.0]

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

## [Version 1.0.0] - 2024-03-09
- First official release of the Media Player Application

