# Script Developer: Gabriel Mihai Sandu
# GitHub Profile: https://github.com/Gabrieliam42

import os
import sys
import subprocess
import platform
import ctypes
import shutil
import stat

def is_user_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv + ["--as-admin"]), None, 1
        )
        return True
    except:
        return False

def clean_broken_distributions(venv_root):
    site_packages = os.path.join(
        venv_root, "Lib", "site-packages"
    ) if platform.system() == "Windows" else os.path.join(
        venv_root, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
    )

    if os.path.isdir(site_packages):
        for entry in os.listdir(site_packages):
            if entry.startswith("~"):
                path = os.path.join(site_packages, entry)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                        print(f"Deleted broken directory: {path}")
                    else:
                        os.remove(path)
                        print(f"Deleted broken file: {path}")
                except Exception as e:
                    print(f"Failed to delete {path}: {e}")

def make_pip_writable(site_packages):
    for entry in os.listdir(site_packages):
        if entry.lower().startswith("pip-") and (entry.endswith(".dist-info") or os.path.isdir(os.path.join(site_packages, entry))):
            pip_path = os.path.join(site_packages, entry)
            for root, dirs, files in os.walk(pip_path):
                for name in files:
                    fpath = os.path.join(root, name)
                    try:
                        os.chmod(fpath, stat.S_IWRITE | stat.S_IREAD)
                    except Exception as e:
                        print(f"Could not change permissions on {fpath}: {e}")

def upgrade_pip(scripts_path, site_packages):
    make_pip_writable(site_packages)

    python_exe = os.path.join(scripts_path, "python.exe")
    base_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "pip"]
    force_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "--force-reinstall", "pip"]
    ensure_cmd = [python_exe, "-m", "ensurepip", "--upgrade"]

    try:
        print("Trying normal pip upgrade...")
        result = subprocess.run(base_cmd)
        if result.returncode == 0:
            return
        print("Normal upgrade failed. Trying --force-reinstall...")
        result = subprocess.run(force_cmd)
        if result.returncode == 0:
            return
        print("Force-reinstall failed. Trying ensurepip --upgrade...")
        subprocess.run(ensure_cmd)
    except Exception as e:
        print(f"All pip upgrade attempts failed: {e}")

def find_and_activate_venv():
    cwd = os.getcwd()
    
    for root, dirs, files in os.walk(cwd):
        if 'Scripts' in dirs or 'bin' in dirs:
            scripts_path = os.path.join(root, 'Scripts' if platform.system() == 'Windows' else 'bin')
            required_files = {'Activate.ps1' if platform.system() == 'Windows' else 'activate'}
            
            if required_files.issubset(set(os.listdir(scripts_path))):
                print(f"Virtual environment found and activated at: {root}")

                if is_user_admin():
                    clean_broken_distributions(root)

                site_packages = os.path.join(
                    root, "Lib", "site-packages"
                ) if platform.system() == "Windows" else os.path.join(
                    root, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
                )

                if platform.system() == 'Windows':
                    upgrade_pip(scripts_path, site_packages)
                    activate_script = os.path.join(scripts_path, "Activate.ps1")
                    activate_command = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", activate_script]
                else:
                    activate_command = f'source "{os.path.join(scripts_path, "activate")}"'

                subprocess.run(
                    activate_command,
                    shell=False if platform.system() == 'Windows' else True,
                    executable='/bin/bash' if platform.system() != 'Windows' else None
                )
                return

    print("No virtual environment found.")

if __name__ == "__main__":
    if platform.system() == "Windows":
        if "--as-admin" not in sys.argv:
            if not is_user_admin():
                print("Not running as admin. Attempting to relaunch with elevated privileges...")
                if run_as_admin():
                    sys.exit(0)
                else:
                    print("Failed to relaunch as admin. Continuing without admin rights...")
    find_and_activate_venv()