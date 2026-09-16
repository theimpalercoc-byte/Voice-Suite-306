import os, subprocess, sys

def build_windows_exe():
    print("Building standalone VoiceSuite306.exe for Windows...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "VoiceSuite306",
        "--add-data", "avatars;avatars",
        "--add-data", "weights;weights",
        "--add-data", "voices;voices",
        "studio_app.py"
    ]
    subprocess.run(cmd)
    print("Build complete! Check the dist/VoiceSuite306 folder for your .exe.")

if __name__ == "__main__":
    build_windows_exe()
