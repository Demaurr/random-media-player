import os
import shutil
from pathlib import Path

def main():
    project_dir = os.path.abspath(os.getcwd())
    main_script = os.path.join(project_dir, "gui_main.py")

    batch_content = f'''@echo off
cd "{project_dir}"
py "{main_script}"
pause
'''

    batch_path = os.path.join(project_dir, "media_analyser_gui.bat")
    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)

    desktop_path = Path.home() / "Desktop"
    shortcut_path = desktop_path / "Media Analyser.bat"

    shutil.copy(batch_path, shortcut_path)

    print("Batch file created successfully:")
    print(f"----> {batch_path}")
    print("A desktop shortcut has also been created for easy access:")
    print(f"----> {shortcut_path}")
    print("\nYou can now double-click the desktop shortcut to launch the player instantly!")

if __name__ == "__main__":
    main()
