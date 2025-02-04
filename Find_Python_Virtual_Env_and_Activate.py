# Script Developer: Gabriel Mihai Sandu
# GitHub Profile: https://github.com/Gabrieliam42

import os
import subprocess
import platform

def find_and_activate_venv():
    cwd = os.getcwd()
    
    for root, dirs, files in os.walk(cwd):
        if 'Scripts' in dirs or 'bin' in dirs:
            scripts_path = os.path.join(root, 'Scripts' if platform.system() == 'Windows' else 'bin')
            required_files = {'activate.bat' if platform.system() == 'Windows' else 'activate'}
            
            if required_files.issubset(set(os.listdir(scripts_path))):
                print(f"Virtual environment found and activated at: {root}")
                
                if platform.system() == 'Windows':
                    activate_command = f'cmd /k ""{os.path.join(scripts_path, "activate.bat")}" && python.exe -m pip install --upgrade pip"'
                else:
                    activate_command = f'source "{os.path.join(scripts_path, "activate")}" && python3 -m pip install --upgrade pip'
                
                subprocess.run(activate_command, shell=True, executable='/bin/bash' if platform.system() != 'Windows' else None)
                return

    print("No virtual environment found.")

if __name__ == "__main__":
    find_and_activate_venv()
